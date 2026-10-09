"""
Supabase client for the MENTAL.AI screening service.

One place that knows how to talk to Supabase. Every other module imports from
here, so credentials, timeouts and endpoints are configured exactly once.

Why the REST API and not the `supabase` Python SDK
--------------------------------------------------
This service pins its inference stack exactly (numpy, pandas, scikit-learn,
xgboost). `supabase-py` pulls in `realtime` -> `websockets`, plus a realtime
client this service never uses, and resolving that against the pinned ML stack
is the kind of change that breaks artifact reproducibility.

GoTrue and PostgREST are both plain HTTPS APIs, and the standard library can
speak them. This module uses `urllib.request` and no third-party package at
all, which keeps api/auth.py's "standard library only" promise true and means a
deployment cannot be broken by a resolver upgrade. Nothing about
authentication is hand-rolled: password hashing, session storage and token
signing stay entirely inside Supabase.

Configuration (environment):
    SUPABASE_URL             project URL, e.g. https://xyz.supabase.co
    SUPABASE_SECRET_KEY      secret / service_role key. Server-side only: it
                             bypasses RLS. Never a VITE_ variable, never the
                             browser.
    SUPABASE_PUBLISHABLE_KEY publishable (anon) key. Public by design; GoTrue
                             requires it on every auth call.
    SUPABASE_TIMEOUT_SECONDS per-request timeout (default 10)

`SUPABASE_SERVICE_ROLE_KEY` is accepted as the legacy name for the secret key.

Every method is a thin, typed wrapper over one HTTP call. The transport is
injectable so tests can exercise the whole request/response path without a
network or real credentials.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import math
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

logger = logging.getLogger("screening-api.supabase")

DEFAULT_TIMEOUT_SECONDS = 10.0


class SupabaseError(RuntimeError):
    """Supabase was unreachable, unconfigured, or returned an unusable answer.

    Never carries credentials or raw response bodies: this propagates into 5xx
    responses and log lines.
    """


class WriteUnconfirmed(SupabaseError):
    """A write response lacks a verifiable acknowledgement; no retry is performed."""


class InvalidLogin(SupabaseError):
    """Supabase rejected the credentials."""


class InvalidSession(SupabaseError):
    """The presented access or refresh token is not usable."""


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
def _env(*names: str) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def configured_url() -> str:
    return _env("SUPABASE_URL").rstrip("/")


def configured_secret_key() -> str:
    # New key model first, legacy name second.
    return _env("SUPABASE_SECRET_KEY", "SUPABASE_SERVICE_ROLE_KEY")


def configured_publishable_key() -> str:
    # New key model first, legacy name second.
    return _env("SUPABASE_PUBLISHABLE_KEY", "SUPABASE_ANON_KEY")


def is_configured() -> bool:
    return bool(configured_url() and configured_secret_key() and configured_publishable_key())


def configuration_problem() -> Optional[str]:
    """Name the first missing variable, or None when the service can run."""
    if not configured_url():
        return "SUPABASE_URL is not set"
    if not configured_publishable_key():
        return "SUPABASE_PUBLISHABLE_KEY (or SUPABASE_ANON_KEY) is not set"
    if not configured_secret_key():
        return "SUPABASE_SECRET_KEY (or SUPABASE_SERVICE_ROLE_KEY) is not set"
    return None


# ------------------------------------------------------------------
# Value objects
# ------------------------------------------------------------------
@dataclass(frozen=True)
class AuthSession:
    """A Supabase session, in the shape this service hands to the browser."""

    access_token: str
    refresh_token: str
    expires_at: int
    user_id: str
    email: Optional[str]
    display_name: Optional[str]


@dataclass(frozen=True)
class AuthUser:
    """The verified identity behind an access token.

    `user_id` is authoritative. Email is display data and can change, so it is
    never used as a key.
    """

    user_id: str
    email: Optional[str]
    display_name: Optional[str]
    created_at: int


def _first_name(value: Optional[str]) -> str:
    """First word of a display name, in sentence case."""
    word = (value or "").strip().split()[0] if (value or "").strip() else ""
    return word[:1].upper() + word[1:].lower() if word else ""


def _display_name(user: Mapping[str, Any]) -> str:
    """
    Best available display name for a Supabase user.

    Order: the profile row the signup trigger maintains, then OAuth metadata
    (Google puts the name there), then the local part of the email. Never
    returns an empty string, because the interface greets the person by name.
    """
    metadata = user.get("user_metadata") or {}
    if not isinstance(metadata, Mapping):
        metadata = {}

    profile_name = None
    profile = user.get("profile")
    if isinstance(profile, Mapping):
        profile_name = profile.get("display_name")

    for candidate in (
        profile_name,
        metadata.get("full_name"),
        metadata.get("name"),
        (user.get("email") or "").split("@")[0],
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return "there"


def _epoch_seconds(value: Any) -> int:
    """Epoch seconds from a numeric field, or 0."""
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0


def _iso_to_epoch(value: Any) -> int:
    """GoTrue reports expiry as an ISO-8601 string."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, str) and value:
        from datetime import datetime, timezone

        try:
            return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())
        except ValueError:
            return 0
    return 0


# Row mapping between the API's prediction result and the screenings table.
# Deliberately explicit: a rename here is visible in one dict instead of spread
# across a query builder.
ROW_MAPPING: tuple[tuple[str, str], ...] = (
    ("text", "text"),
    ("cleaned_text", "cleaned_text"),
    ("lemmatized_text", "lemmatized_text"),
    ("condition_label", "condition_label"),
    ("condition_probabilities", "condition_probabilities"),
    ("urgency_label", "urgency_label"),
    ("urgency_probability", "urgency_probability"),
    ("decision_threshold", "decision_threshold"),
    ("urgency_flagged", "urgency_flagged"),
    ("provenance_caveat", "provenance_caveat"),
    ("service_version", "service_version"),
    ("model_latency_ms", "model_latency_ms"),
)


# ------------------------------------------------------------------
# Transport
# ------------------------------------------------------------------
@dataclass(frozen=True)
class Response:
    """The only shape this module needs from an HTTP call."""

    status: int
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        if not self.body:
            return None
        return json.loads(self.body.decode("utf-8"))


# (method, url, headers, body, timeout) -> Response
Transport = Callable[[str, str, dict[str, str], Optional[bytes], float], Response]


def urllib_transport(
    method: str,
    url: str,
    headers: dict[str, str],
    body: Optional[bytes],
    timeout: float,
) -> Response:
    """
    Default transport.

    A transport-level failure is returned as a Response with status 0 rather
    than raised, so every caller handles "could not reach Supabase" through the
    same path as any other bad answer, and no URL or key can leak into an
    exception message.
    """
    request = urllib.request.Request(url, data=body, method=method)
    for name, value in headers.items():
        request.add_header(name, value)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as res:  # noqa: S310 - fixed https origin
            return Response(
                status=res.status,
                headers={k.lower(): v for k, v in res.headers.items()},
                body=res.read(),
            )
    except urllib.error.HTTPError as exc:
        # 4xx/5xx are answers, not failures: the caller maps them.
        try:
            payload = exc.read()
        except Exception:  # pragma: no cover - body already consumed
            payload = b""
        return Response(
            status=exc.code,
            headers={k.lower(): v for k, v in (exc.headers or {}).items()},
            body=payload,
        )
    except Exception as exc:
        logger.warning("supabase_unreachable error_type=%s", type(exc).__name__)
        return Response(status=0, headers={}, body=b"")


# ------------------------------------------------------------------
# Client
# ------------------------------------------------------------------
class SupabaseClient:
    """GoTrue + PostgREST, over an injectable transport."""

    def __init__(
        self,
        url: str,
        publishable_key: str,
        secret_key: str,
        *,
        transport: Optional[Transport] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self._url = url.rstrip("/")
        self._publishable_key = publishable_key
        self._secret_key = secret_key
        try:
            self._timeout = float(timeout if timeout is not None else
                os.environ.get("SUPABASE_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
        except (TypeError, ValueError) as exc:
            raise SupabaseError("Invalid provider timeout configuration") from exc
        if not math.isfinite(self._timeout) or not 0 < self._timeout <= 30:
            raise SupabaseError("Provider timeout must be finite and in (0, 30] seconds")
        self._send: Transport = transport or urllib_transport

    # -- plumbing ---------------------------------------------------------
    def _headers(self, *, privileged: bool) -> dict[str, str]:
        # The secret key only ever appears on PostgREST calls the server owns.
        key = self._secret_key if privileged else self._publishable_key
        headers = {
            "apikey": key,
            "Content-Type": "application/json",
        }
        # New application keys are not JWTs. GoTrue/PostgREST receives them on
        # apikey; Authorization is reserved for user JWTs or legacy JWT keys.
        if not key.startswith(("sb_publishable_", "sb_secret_")):
            headers["Authorization"] = f"Bearer {key}"
        return headers

    def _call(
        self,
        method: str,
        path: str,
        *,
        privileged: bool,
        params: Optional[Mapping[str, Any]] = None,
        json_body: Optional[Any] = None,
        access_token: Optional[str] = None,
        prefer: Optional[str] = None,
    ) -> Response:
        url = f"{self._url}{path}"
        if params:
            filtered = {k: v for k, v in params.items() if v is not None}
            if filtered:
                url = f"{url}?{urllib.parse.urlencode(filtered)}"

        headers = self._headers(privileged=privileged)
        if prefer is not None:
            headers["Prefer"] = prefer
        if access_token is not None:
            # A user token identifies the user; the apikey header still has to
            # be present for GoTrue, but the Authorization header is the user's.
            headers["Authorization"] = f"Bearer {access_token}"

        body = None if json_body is None else json.dumps(json_body).encode("utf-8")
        res = self._send(method, url, headers, body, self._timeout)
        if res.status == 0:
            raise SupabaseError("Supabase is unreachable")
        return res

    def _json_call(self, method: str, path: str, **kwargs: Any) -> Any:
        res = self._call(method, path, **kwargs)
        if res.status >= 400:
            raise _auth_error(res.status)
        try:
            return res.json()
        except ValueError as exc:
            raise SupabaseError("Supabase returned a non-JSON response") from exc

    # -- auth -------------------------------------------------------------
    def sign_in_with_password(self, email: str, password: str) -> AuthSession:
        """
        Exchange credentials for a session.

        The only place a password is ever transmitted, and only to Supabase.
        Raises InvalidLogin for any rejection, so callers cannot distinguish
        "no such account" from "wrong password".
        """
        body = self._json_call(
            "POST",
            "/auth/v1/token",
            privileged=False,
            json_body={"email": email, "password": password},
            params={"grant_type": "password"},
        )
        return self._session_from(body)

    def refresh_session(self, refresh_token: str) -> AuthSession:
        """Trade a refresh token for a new access token."""
        body = self._json_call(
            "POST",
            "/auth/v1/token",
            privileged=False,
            json_body={"refresh_token": refresh_token},
            params={"grant_type": "refresh_token"},
        )
        return self._session_from(body)

    def get_user(self, access_token: str) -> AuthUser:
        """
        Resolve the identity behind an access token.

        Verification is delegated to GoTrue on purpose. Verifying the JWT locally
        would mean owning this project's signing scheme, and the service would
        then carry JWT correctness it has no reason to own. Raises
        InvalidSession when the token is not usable.
        """
        res = self._call("GET", "/auth/v1/user", privileged=False, access_token=access_token)
        if res.status in (401, 403):
            raise InvalidSession("Access token is not valid")
        if res.status >= 400:
            raise _auth_error(res.status)
        try:
            user = res.json()
        except ValueError as exc:
            raise SupabaseError("Supabase returned a non-JSON response") from exc
        if not isinstance(user, Mapping) or not isinstance(user.get("id"), str):
            raise SupabaseError("Supabase returned a user without an id")
        return AuthUser(
            user_id=user["id"],
            email=user.get("email"),
            display_name=_display_name(user),
            created_at=_iso_to_epoch(user.get("created_at")),
        )

    def _session_from(self, body: Any) -> AuthSession:
        if not isinstance(body, Mapping) or not isinstance(body.get("access_token"), str):
            raise SupabaseError("Supabase returned a session without an access token")
        user = body.get("user") if isinstance(body.get("user"), Mapping) else {}
        # GoTrue reports `expires_at` (epoch seconds) and `expires_in`. Prefer
        # the absolute value; fall back to now + expires_in if a response only
        # carries the interval, because the browser mirrors this expiry.
        expires_at = _epoch_seconds(body.get("expires_at")) or _iso_to_epoch(body.get("expires_at"))
        if not expires_at:
            expires_in = body.get("expires_in")
            if isinstance(expires_in, (int, float)) and expires_in > 0:
                expires_at = int(time.time()) + int(expires_in)
        return AuthSession(
            access_token=body["access_token"],
            refresh_token=str(body.get("refresh_token") or ""),
            expires_at=expires_at,
            user_id=str(user.get("id") or ""),
            email=user.get("email"),
            display_name=_display_name(user),
        )

    # -- application data -------------------------------------------------
    def record_screening(
        self,
        *,
        user_id: str,
        request_id: str,
        result: Mapping[str, Any],
    ) -> Optional[str]:
        """
        Store one screening.

        `user_id` is the verified token subject, never anything from the request
        body. Returns the new row id, or None when Supabase declined the row.
        Raises SupabaseError only when Supabase could not be reached, so a
        caller can tell "could not store" from "stored nothing".
        """
        primary = result.get("primary") or {}
        urgency = result.get("urgency") or {}
        # Column names match ROW_MAPPING. Every NOT NULL column is given a value
        # here, so the insert cannot be rejected by a missing default.
        row: dict[str, Any] = {
            "user_id": user_id,
            "request_id": request_id,
            "text": result.get("text", ""),
            "cleaned_text": result.get("cleaned_text"),
            "lemmatized_text": result.get("lemmatized_text"),
            "condition_label": primary.get("predicted_class"),
            "analysis_result": result.get("analysis_result"),
            "condition_probabilities": primary.get("class_probabilities") or {},
            "urgency_label": urgency.get("predicted_class"),
            "urgency_probability": _number(urgency.get("suicide_probability")),
            "decision_threshold": _number(urgency.get("decision_threshold_used")),
            "urgency_flagged": bool(urgency.get("flagged", False)),
            "provenance_caveat": result.get("provenance_caveat"),
            "service_version": result.get("service_version"),
            "model_latency_ms": _number(result.get("model_latency_ms")),
        }

        res = self._call(
            "POST",
            "/rest/v1/screenings",
            privileged=True,
            params={"select": "id"},
            prefer="return=representation",
            json_body=row,
        )
        if res.status >= 400:
            logger.error(
                "screening_store_failed status=%s request_id=%s", res.status, request_id
            )
            return None
        try:
            body = res.json()
        except ValueError as exc:
            raise WriteUnconfirmed("Write acknowledgement is not valid JSON") from exc
        if isinstance(body, list) and body and isinstance(body[0], Mapping) and body[0].get("id"):
            return str(body[0]["id"])
        raise WriteUnconfirmed("Write acknowledgement has no record identifier")

    def list_screenings(self, user_id: str, *, limit: int = 25) -> list[dict[str, Any]]:
        """Newest-first history for one account. The filter is the isolation."""
        res = self._call(
            "GET",
            "/rest/v1/screenings",
            privileged=True,
            params={
                "select": (
                    "id,created_at,condition_label,condition_probabilities,"
                    "urgency_label,urgency_probability,urgency_flagged,provenance_caveat,analysis_result"
                ),
                "user_id": f"eq.{user_id}",
                "order": "created_at.desc",
                "limit": max(1, min(int(limit), 100)),
            },
        )
        if res.status >= 400:
            raise _auth_error(res.status)
        try:
            body = res.json()
        except ValueError as exc:
            raise SupabaseError("Supabase returned a non-JSON response") from exc
        return [dict(row) for row in body] if isinstance(body, list) else []

    def delete_screenings(self, user_id: str) -> int:
        """Remove an account's history. Scoped by user_id like every read."""
        res = self._call(
            "DELETE",
            "/rest/v1/screenings",
            privileged=True,
            params={"user_id": f"eq.{user_id}"},
        )
        if res.status >= 400:
            raise _auth_error(res.status)
        # PostgREST reports the affected row count in Content-Range.
        tail = res.headers.get("content-range", "").rsplit("/", 1)[-1]
        return int(tail) if tail.isdigit() else 0

    def profile(self, user_id: str) -> Optional[dict[str, Any]]:
        """Read the account's profile row, if the signup trigger made one."""
        res = self._call(
            "GET",
            "/rest/v1/profiles",
            privileged=True,
            params={
                "select": "id,email,display_name,created_at",
                "id": f"eq.{user_id}",
                "limit": 1,
            },
        )
        if res.status >= 400:
            return None
        try:
            body = res.json()
        except ValueError:
            return None
        if isinstance(body, list) and body and isinstance(body[0], Mapping):
            return dict(body[0])
        return None


def _number(value: Any) -> Optional[float]:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _auth_error(status: int) -> SupabaseError:
    """Map a GoTrue failure onto a typed, credential-free error."""
    # Supabase reports bad credentials as 400 with a stable error code, so the
    # status alone is enough to separate "wrong password" from "server trouble".
    if status in (400, 401, 403, 422):
        return InvalidLogin("Supabase rejected the credentials")
    if status == 429:
        return InvalidLogin("Supabase rate limited the sign-in attempt")
    return SupabaseError(f"Supabase responded {status}")


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------
_client: Optional[SupabaseClient] = None
_client_lock = threading.Lock()


def get_client() -> SupabaseClient:
    """
    Process-wide client.

    Built on first use so importing the app never requires Supabase to be
    reachable or even configured. Reset with reset_client() when the
    environment changes, which is also how tests inject a stub transport.
    """
    global _client
    if _client is not None:
        return _client
    with _client_lock:
        if _client is not None:
            return _client
        problem = configuration_problem()
        if problem:
            raise SupabaseError(
                f"Supabase is not configured: {problem}. "
                "Set SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY and SUPABASE_SECRET_KEY."
            )
        _client = SupabaseClient(
            configured_url(), configured_publishable_key(), configured_secret_key()
        )
        return _client


def reset_client() -> None:
    """Drop the cached client, so the next call re-reads the environment."""
    global _client
    with _client_lock:
        _client = None
