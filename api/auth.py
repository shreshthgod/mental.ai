"""
Session authentication for the mental.ai screening service.

Identity is owned by Supabase Auth. This module is the adapter: it speaks the
supabase-js contract the browser already uses (an access token plus a refresh
token), and it decides what the rest of the service is allowed to trust.

What this service does NOT do
-----------------------------
- It never sees a password except in transit to Supabase.
- It never hashes, stores or compares a password. Supabase does that.
- It never accepts a user id from a request body. The only user id that reaches
  business logic came from `get_user`, i.e. from a token Supabase verified.
- It does no local token crypto. Signature and expiry are Supabase's call.

Design constraints preserved from the previous implementation:
    - Standard library only. No new runtime dependency.
    - Constant-time behaviour where a comparison exists at all.
    - Neither credentials nor tokens are ever logged.

The browser flow (unchanged from the client's point of view):
    POST /auth/login      -> Supabase sign_in_with_password -> session
    POST /auth/refresh    -> Supabase refresh_token         -> session
    GET  /auth/session    -> Supabase get_user              -> claims
    any authenticated call -> Supabase get_user             -> claims

Throttling stays here: Supabase rate-limits by IP too, but the counter is
per-deployment and an in-process window is what the previous behaviour promised.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Optional

from . import db

logger = logging.getLogger("screening-api.auth")

SESSION_HEADER_GRACE_SECONDS = 60


class AuthError(Exception):
    """Base class for authentication failures."""


class InvalidCredentials(AuthError):
    """Supplied email or password was rejected by Supabase Auth."""


class InvalidToken(AuthError):
    """Bearer token was missing, malformed, tampered with, or expired."""


@dataclass(frozen=True)
class Claims:
    """
    The verified identity behind a request.

    `user_id` is the Supabase Auth user id and is the only identity used for
    ownership decisions. `email` is present for display and must never be used
    as a key: addresses change, ids do not.
    """

    user_id: str
    email: Optional[str]
    name: str
    issued_at: int
    expires_at: int


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
def session_ttl_seconds() -> int:
    """
    Advisory lifetime reported to the browser.

    Supabase decides the real expiry; this only mirrors it so a client can tell
    a fresh session from a stale one without decoding anything.
    """
    raw = os.environ.get("MENTAL_AI_SESSION_TTL", "").strip()
    try:
        ttl = int(raw)
    except ValueError:
        ttl = 3600
    return max(300, min(ttl, 604_800))


def auth_provider() -> str:
    """Which identity providers this deployment is expected to offer."""
    return "supabase"


def display_name_for(user_id: str) -> str:
    """
    Turn an email or user id into a human-readable name.

    Kept for the case where Supabase supplies no name at all, so the interface
    can greet the person rather than print an address. Separators the id
    convention already uses (dot, dash, underscore) become word boundaries, and
    each word keeps the capitalisation it was given apart from its first letter,
    so "kArTiK" is not flattened to "Kartik".
    """
    import re

    local = (user_id or "").split("@")[0].strip()
    words = [w for w in re.split(r"[\s._\-]+", local) if w]
    if not words:
        return "there"
    return " ".join(w[:1].upper() + w[1:] for w in words)


def configured_name() -> Optional[str]:
    """
    An operator-set display name, applied to every account.

    Optional. Set it when the deployment greets one shared identity regardless
    of which account signed in; leave it unset and each account is greeted by
    its own Supabase name.
    """
    return os.environ.get("MENTAL_AI_AUTH_NAME", "").strip() or None


def resolve_display_name(supabase_name: Optional[str], email: Optional[str]) -> str:
    """Operator override, then Supabase's name, then something derived."""
    override = configured_name()
    if override:
        return override
    if supabase_name and supabase_name.strip():
        return supabase_name.strip()
    return display_name_for(email or "")


# ------------------------------------------------------------------
# Credential verification
# ------------------------------------------------------------------
def _client() -> db.SupabaseClient:
    try:
        return db.get_client()
    except db.SupabaseError as exc:
        # Configuration, not a bad password: surfaced as 503 by the caller so the
        # interface reports "service unavailable" rather than blaming the user.
        raise AuthUnavailable(str(exc)) from exc


class AuthUnavailable(AuthError):
    """Supabase is unconfigured or unreachable. Never the visitor's fault."""


def verify_credentials(email: str, password: str) -> db.AuthSession:
    """
    Exchange credentials for a session through Supabase Auth.

    Any rejection - unknown account, wrong password, disabled account - raises
    InvalidCredentials with the same message, so the response cannot be used to
    enumerate accounts. Supabase does the password work; nothing is compared
    here.
    """
    try:
        return _client().sign_in_with_password((email or "").strip(), password)
    except db.InvalidLogin as exc:
        raise InvalidCredentials("Invalid email or password") from exc


def refresh(refresh_token: str) -> db.AuthSession:
    """Trade a refresh token for a fresh session."""
    if not refresh_token or not isinstance(refresh_token, str):
        raise InvalidToken("Refresh token missing")
    try:
        return _client().refresh_session(refresh_token)
    except db.InvalidLogin as exc:
        raise InvalidToken("Refresh token is no longer valid") from exc


def decode_token(token: str) -> Claims:
    """
    Verify a bearer token and return the identity behind it.

    The token is checked by Supabase, never by this service. Raises InvalidToken
    on any failure, so a caller never receives unverified claims.
    """
    if not token or not isinstance(token, str):
        raise InvalidToken("Missing bearer token")

    try:
        user = _client().get_user(token)
    except db.InvalidSession as exc:
        raise InvalidToken("Session is not valid") from exc

    return Claims(
        user_id=user.user_id,
        email=user.email,
        name=resolve_display_name(user.display_name, user.email),
        issued_at=user.created_at,
        expires_at=int(time.time()) + session_ttl_seconds(),
    )


def bearer_token(authorization_header: str | None) -> str:
    """Extract the token from an 'Authorization: Bearer <token>' header."""
    if not authorization_header:
        raise InvalidToken("Authorization header missing")
    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise InvalidToken("Authorization header must use the Bearer scheme")
    return token.strip()


# ------------------------------------------------------------------
# Login throttling
# ------------------------------------------------------------------
# Fixed-window counter, keyed by client IP. Deliberately in-memory and
# single-process: this exists to blunt credential stuffing against a real
# account, not to be a distributed rate limiter. Supabase rate-limits
# independently; this is the per-deployment layer.
_ATTEMPT_WINDOW_SECONDS = 300
_MAX_ATTEMPTS_PER_WINDOW = 10
_attempts: dict[str, list[float]] = {}
_attempts_lock = threading.Lock()


def _prune(now: float) -> None:
    cutoff = now - _ATTEMPT_WINDOW_SECONDS
    for key in [k for k, stamps in _attempts.items() if not stamps or stamps[-1] < cutoff]:
        _attempts.pop(key, None)


class RateLimited(AuthError):
    """Too many failed logins from this client within the window."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("Too many failed sign-in attempts. Try again shortly.")
        self.retry_after_seconds = retry_after_seconds


def record_failed_attempt(client_id: str) -> None:
    now = time.time()
    with _attempts_lock:
        _prune(now)
        _attempts.setdefault(client_id, []).append(now)


def clear_attempts(client_id: str) -> None:
    with _attempts_lock:
        _attempts.pop(client_id, None)


def enforce_attempt_limit(client_id: str) -> None:
    """Raise RateLimited if this client has failed too many times recently."""
    now = time.time()
    with _attempts_lock:
        _prune(now)
        stamps = _attempts.get(client_id, [])
        if len(stamps) < _MAX_ATTEMPTS_PER_WINDOW:
            return
        retry_after = int(_ATTEMPT_WINDOW_SECONDS - (now - stamps[0])) + 1
    raise RateLimited(retry_after)
