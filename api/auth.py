"""
Session authentication for the mental.ai screening service.

Design constraints:
    - Standard library only. No new runtime dependency.
    - Stateless HMAC-SHA256 signed bearer tokens, so the API stays
      horizontally scalable with no server-side session store.
    - Credential comparison is constant time (secrets.compare_digest).
    - Neither credentials nor tokens are ever logged.

Token format (opaque to the client, self-describing to us):

    v1.<base64url(payload_json)>.<base64url(hmac_sha256(payload))>

The payload carries {sub, iat, exp, jti}. Expiry is enforced server side;
the client mirror is a convenience only and is never trusted.

Configuration (environment):
    MENTAL_AI_AUTH_USER      expected user id       (default "admin")
    MENTAL_AI_AUTH_PASSWORD  expected password       (default "password")
    MENTAL_AI_AUTH_NAME      display name           (default: derived from the user id)
    MENTAL_AI_TOKEN_SECRET   HMAC signing key        (default: random per process)
    MENTAL_AI_SESSION_TTL    token lifetime seconds  (default 43200 = 12h)

The defaults exist so `npm run dev` works out of the box on a research
checkout. Any real deployment must set all three explicitly: when the
secret is unset it is generated per process, which invalidates every
issued token on restart and is logged as a warning.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import secrets
import threading
import time

logger = logging.getLogger("screening-api.auth")

TOKEN_VERSION = "v1"
ALGORITHM = "hs256"

DEFAULT_USER = "admin"
DEFAULT_PASSWORD = "password"  # noqa: S105 - documented research demo default
DEFAULT_TTL_SECONDS = 43_200  # 12 hours
MIN_TTL_SECONDS = 300
MAX_TTL_SECONDS = 604_800  # 7 days


class AuthError(Exception):
    """Base class for authentication failures."""


class InvalidCredentials(AuthError):
    """Supplied user id or password did not match configuration."""


class InvalidToken(AuthError):
    """Bearer token was missing, malformed, tampered with, or expired."""


# ------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------
def _signing_secret() -> bytes:
    """Resolve the HMAC key, generating an ephemeral one if unset."""
    raw = os.environ.get("MENTAL_AI_TOKEN_SECRET", "").strip()
    if raw:
        return raw.encode("utf-8")
    secret = secrets.token_bytes(32)
    logger.warning(
        "MENTAL_AI_TOKEN_SECRET is not set. Using an ephemeral signing key: "
        "existing sessions will be invalidated on restart. Set it explicitly "
        "before any non-local deployment."
    )
    return secret


# Resolved once at import. Regenerating this per request would make every
# previously issued token unverifiable.
_SECRET = _signing_secret()


def configured_user() -> str:
    return os.environ.get("MENTAL_AI_AUTH_USER", DEFAULT_USER).strip()


def display_name_for(user_id: str) -> str:
    """
    Turn a user id into a human-readable name.

    Used when no explicit display name is configured, so the interface can greet
    the person rather than print an account slug. Separators the id convention
    already uses (space, dot, dash, underscore) become word boundaries, and each
    word keeps the capitalisation it was given apart from its first letter, so
    "kArTiK" is not flattened to "Kartik".
    """
    words = [w for w in re.split(r"[\s._\-]+", (user_id or "").strip()) if w]
    if not words:
        return DEFAULT_USER
    return " ".join(w[:1].upper() + w[1:] for w in words)


def configured_name() -> str:
    """
    The name shown in greetings and the account menu.

    Read per request rather than at import so it can be changed without a
    restart, matching configured_user(). Falls back to a name derived from the
    user id when unset, so the greeting is never a hardcoded placeholder.
    """
    explicit = os.environ.get("MENTAL_AI_AUTH_NAME", "").strip()
    return explicit or display_name_for(configured_user())


def session_ttl_seconds() -> int:
    raw = os.environ.get("MENTAL_AI_SESSION_TTL", "").strip()
    try:
        ttl = int(raw)
    except ValueError:
        ttl = DEFAULT_TTL_SECONDS
    return max(MIN_TTL_SECONDS, min(ttl, MAX_TTL_SECONDS))


def using_demo_credentials() -> bool:
    """True when the service is running on the documented demo defaults."""
    return (
        configured_user() == DEFAULT_USER
        and os.environ.get("MENTAL_AI_AUTH_PASSWORD", DEFAULT_PASSWORD) == DEFAULT_PASSWORD
    )


# ------------------------------------------------------------------
# Credential verification
# ------------------------------------------------------------------
def verify_credentials(user_id: str, password: str) -> None:
    """
    Raise InvalidCredentials unless the pair matches configuration.

    Both halves are compared with secrets.compare_digest, and the user id is
    compared before the password is even read, so a wrong user id and a wrong
    password cost the same work. The submitted password is hashed to a fixed
    width first so compare_digest never sees differing input lengths, which
    would otherwise leak the configured length through timing.
    """
    expected_user = configured_user()
    expected_password = os.environ.get("MENTAL_AI_AUTH_PASSWORD", DEFAULT_PASSWORD)

    user_ok = hmac.compare_digest(
        (user_id or "").strip().encode("utf-8"), expected_user.encode("utf-8")
    )
    password_ok = hmac.compare_digest(
        hashlib.sha256((password or "").encode("utf-8")).digest(),
        hashlib.sha256(expected_password.encode("utf-8")).digest(),
    )

    if not (user_ok and password_ok):
        raise InvalidCredentials("Invalid user id or password")


# ------------------------------------------------------------------
# Token encode / decode
# ------------------------------------------------------------------
def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(payload_b64: str) -> str:
    digest = hmac.new(_SECRET, payload_b64.encode("ascii"), hashlib.sha256).digest()
    return _b64encode(digest)


def issue_token(user_id: str, ttl_seconds: int | None = None) -> tuple[str, int]:
    """Return (token, expires_in_seconds) for the given user id."""
    ttl = ttl_seconds if ttl_seconds is not None else session_ttl_seconds()
    now = int(time.time())
    exp = now + ttl
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": exp,
        "jti": secrets.token_hex(8),
        "alg": ALGORITHM,
    }
    payload_b64 = _b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    return f"{TOKEN_VERSION}.{payload_b64}.{_sign(payload_b64)}", ttl


def decode_token(token: str) -> dict:
    """
    Verify a bearer token and return its claims.

    Raises InvalidToken on any failure. The caller never receives partial or
    unverified claims, because the signature is checked before the payload is
    parsed.
    """
    if not token or not isinstance(token, str):
        raise InvalidToken("Missing bearer token")

    parts = token.split(".")
    if len(parts) != 3:
        raise InvalidToken("Malformed bearer token")

    version, payload_b64, signature = parts
    if version != TOKEN_VERSION:
        raise InvalidToken(f"Unsupported token version: {version}")

    expected_signature = _sign(payload_b64)
    if not hmac.compare_digest(signature.encode("ascii"), expected_signature.encode("ascii")):
        raise InvalidToken("Token signature mismatch")

    try:
        claims = json.loads(_b64decode(payload_b64))
    except Exception as exc:
        raise InvalidToken("Token payload is not readable") from exc

    if not isinstance(claims, dict):
        raise InvalidToken("Token payload is not an object")

    exp = claims.get("exp")
    if not isinstance(exp, int) or exp <= int(time.time()):
        raise InvalidToken("Token expired")

    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub:
        raise InvalidToken("Token subject missing")

    # A token issued before a credential change must not outlive that change.
    if not hmac.compare_digest(sub.encode("utf-8"), configured_user().encode("utf-8")):
        raise InvalidToken("Token subject is no longer valid")

    return claims


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
# single-process: this exists to blunt credential stuffing against the demo
# account, not to be a distributed rate limiter.
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