"""
Production HTTP API for the MENTAL.AI screening inference package.

Architecture:
    HTTP → bearer session check → FastAPI validation
         → MentalHealthScreener.screen() → JSON response

This layer contains NO model logic; it only authenticates, transports and
validates. Raw user text is never logged.
"""
import json
import os
import sys
import time
import uuid
import logging
import re
import threading
import sqlite3
from typing import Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
os.environ.setdefault("NLTK_DATA", os.path.join(_ROOT, "nltk_data"))

# Load .env before anything reads os.environ. Real environment variables win,
# so container and CI configuration is never overridden by a local file.
#
# The confirmation is printed rather than logged: logging is not configured until
# further down (it needs LOG_LEVEL, which may come from this file), so a logger
# call here would be discarded.
_ENV_PATH = os.environ.get("MENTAL_AI_ENV_FILE", os.path.join(_ROOT, ".env"))
_ENV_SOURCE: Optional[str] = None
try:
    from dotenv import load_dotenv
except ImportError:
    if os.path.isfile(_ENV_PATH):
        print(
            f"WARNING: python-dotenv is not installed, so {_ENV_PATH} was ignored. "
            "Install it or export the variables directly.",
            file=sys.stderr,
        )
else:
    if load_dotenv(_ENV_PATH, override=False):
        _ENV_SOURCE = _ENV_PATH

# Ensure the inference package and the repo root are importable, so this module
# works both as `uvicorn api.api:app` from the root and as `python3 api/api.py`.
sys.path.insert(0, os.path.join(_ROOT, "Step 12 - Packaging", "package"))
sys.path.insert(0, _ROOT)

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError
import uvicorn

from mental_health_screening.inference import MentalHealthScreener

from api import auth, db
from api.body_limit import BodyLimitMiddleware
from api.execution import BoundedExecutor, CapacityExceeded, WorkTimedOut
from api.limits import PredictLimiter, Limited
from api.contracts import (PrimaryResult, UrgencyResult, SafetyResult, PredictResponse,
                           AnalysisResult, PersistenceResult, SCHEMA_VERSION, ConfigurationResponse)

from mental_health_screening.safety import support_action

# ------------------------------------------------------------------
# Logging: structured, no raw user text, no PII
# ------------------------------------------------------------------
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("screening-api")

if _ENV_SOURCE:
    logger.info("configuration loaded from %s", _ENV_SOURCE)

# ------------------------------------------------------------------
# App initialization with explicit artifact verification
# ------------------------------------------------------------------
ARTIFACTS_DIR = os.environ.get("ARTIFACTS_DIR", os.path.join(
    _ROOT, "Step 12 - Packaging", "package", "mental_health_screening", "artifacts"
))
DEFAULT_MAX_TEXT_LENGTH = 10000
MIN_ALLOWED_MAX_TEXT_LENGTH = 1000
MAX_ALLOWED_MAX_TEXT_LENGTH = 100000


def max_text_length() -> int:
    """
    Advertised input limit, in characters.

    `MAX_TEXT_LENGTH` was documented in .env.example and read nowhere, so an
    operator who changed it got the old limit with no error (D-008). It is now
    read here, with the documented default preserved. An unparseable or
    out-of-range value falls back to that default rather than failing startup:
    a typo in a limit should not take the screening service down.
    """
    raw = os.environ.get("MAX_TEXT_LENGTH", "").strip()
    if not raw:
        return DEFAULT_MAX_TEXT_LENGTH
    try:
        value = int(raw)
    except ValueError:
        logger.warning("max_text_length_unparseable; using default %d", DEFAULT_MAX_TEXT_LENGTH)
        return DEFAULT_MAX_TEXT_LENGTH
    if not MIN_ALLOWED_MAX_TEXT_LENGTH <= value <= MAX_ALLOWED_MAX_TEXT_LENGTH:
        logger.warning(
            "max_text_length_out_of_range value=%d; using default %d",
            value, DEFAULT_MAX_TEXT_LENGTH,
        )
        return DEFAULT_MAX_TEXT_LENGTH
    return value


SERVICE_VERSION = os.environ.get("SERVICE_VERSION", "0.1.0")
START_TIME = time.time()
inference_executor = BoundedExecutor(workers=1, outstanding=8)
persistence_executor = BoundedExecutor(workers=1, outstanding=8)
INFERENCE_TIMEOUT_SECONDS = 30.0
PERSISTENCE_TIMEOUT_SECONDS = 12.0
predict_limiter = PredictLimiter(os.environ.get("MENTAL_AI_LIMIT_STORE", "/tmp/mental-ai-predict-limits.sqlite3"))

try:
    screener = MentalHealthScreener(
        artifacts_dir=ARTIFACTS_DIR, max_text_length=max_text_length()
    )
    logger.info("MentalHealthScreener initialized successfully")
except Exception as exc:
    logger.error("screener_initialization_failed error_type=%s", type(exc).__name__)
    screener = None  # Will be caught by /health

app = FastAPI(
    title="mental.ai Screening API",
    description="Research/screening inference layer over packaged ML artifacts. NOT a clinical diagnostic system.",
    version=SERVICE_VERSION,
)

# Dev origin is proxied through Vite (no CORS needed in the default setup).
# Listed explicitly so a split-origin deployment via VITE_API_URL works too.
_DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.environ.get("MENTAL_AI_CORS_ORIGINS", _DEFAULT_ORIGINS).split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
app.add_middleware(BodyLimitMiddleware, limit=lambda: max_text_length() * 12 + 4096)

bearer_scheme = HTTPBearer(auto_error=False)


# ------------------------------------------------------------------
# Session dependency
# ------------------------------------------------------------------
def require_session(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> auth.Claims:
    """
    FastAPI dependency: resolve the verified identity behind a bearer token.

    The token is validated by Supabase, so what comes back is an authenticated
    user id. Two failure modes are deliberately different status codes:
    401 means the visitor is not signed in, 503 means we cannot tell right now.
    Conflating them would either log people out on a Supabase hiccup, or tell
    them to sign in when the service is down.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        return auth.decode_token(credentials.credentials)
    except auth.InvalidToken as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except auth.AuthUnavailable as exc:
        logger.error("auth_unavailable error_type=%s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Authentication service unavailable") from exc
    except db.SupabaseError as exc:
        # D-006: decode_token maps an unusable token to InvalidToken, but an
        # unreachable Supabase raises the base SupabaseError, which was not
        # caught here. That escaped to FastAPI and became HTTP 500, so an
        # identity-provider outage looked like a server fault instead of the
        # 503 this function promises. SupabaseError is the parent of
        # InvalidSession, so it is caught after the 401 case above.
        logger.error("auth_backend_unreachable: %s", type(exc).__name__)
        raise HTTPException(
            status_code=503, detail="Authentication service unavailable"
        ) from exc


# ------------------------------------------------------------------
# Request / response contracts (typed, based on actual inference output)
# ------------------------------------------------------------------
class LoginRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=256, description="Email address")
    password: str = Field(..., min_length=1, max_length=256, description="Account password")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1, max_length=2048)


class LoginResponse(BaseModel):
    """Same shape the browser already consumes, so the client change is small."""

    token: str
    refresh_token: str
    token_type: str
    expires_in: int
    expires_at: int
    user: str
    user_id: str
    name: str


class SessionResponse(BaseModel):
    user: str
    user_id: str
    name: str
    issued_at: int
    expires_at: int
    service_version: str


class ScreeningSummary(BaseModel):
    analysis_result: Optional[AnalysisResult] = None
    assessment_kind: str = "legacy_unassessed"
    id: str
    created_at: str
    condition_label: Optional[str] = None
    condition_probabilities: dict = {}
    urgency_label: Optional[str] = None
    urgency_probability: Optional[float] = None
    urgency_flagged: bool = False
    provenance_caveat: Optional[str] = None


    @model_validator(mode="after")
    def classify_snapshot(self):
        self.assessment_kind = "authoritative" if self.analysis_result is not None else "legacy_unassessed"
        return self


class ScreeningListResponse(BaseModel):
    screenings: list[ScreeningSummary]
    count: int


class DeleteResponse(BaseModel):
    deleted: int


class PredictRequest(BaseModel):
    # D-005: min_length counts raw characters, so " " passed validation and
    # then raised inside screen(), where the route's generic handler turned a
    # caller mistake into HTTP 500 "Prediction failed". A blank request is a
    # contract error and is rejected as one, before any model runs.
    text: str = Field(
        ...,
        min_length=1,
        description="Raw user text for screening",
    )

    @field_validator("text")
    @classmethod
    def _check_text(cls, value: str) -> str:
        # Checked here rather than only in `screen()` so a blank or oversized
        # request is a deliberate 422 and never reaches model code.
        if not value.strip():
            raise ValueError("text must contain at least one non-whitespace character")
        limit = max_text_length()
        if len(value) > limit:
            raise ValueError(f"text exceeds the service limit of {limit} characters")
        return value

# Re-export common contract names for existing imports/OpenAPI consumers.

class HealthStatus(BaseModel):
    status: str
    service_version: str
    artifacts_ok: bool
    artifacts_detail: dict
    screener_available: bool
    probe_age_seconds: Optional[float] = None
    probe_ttl_seconds: float = 10.0

class MetricsResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float


@app.get("/configuration", response_model=ConfigurationResponse)
async def configuration():
    limit = screener.max_text_length if screener is not None else max_text_length()
    from mental_health_screening.safety import POLICY_VERSION
    return ConfigurationResponse(schema_version=SCHEMA_VERSION, max_text_length=limit,
        max_body_bytes=limit*12+4096,
        urgency_threshold=screener._urgency_threshold if screener is not None else None,
        policy_version=POLICY_VERSION, semantic_status="disabled")

# ------------------------------------------------------------------
# Middleware: request IDs and latency tracking
# ------------------------------------------------------------------
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    supplied_id = request.headers.get("X-Request-ID", "")
    request_id = supplied_id if re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", supplied_id) else uuid.uuid4().hex[:16]
    request.state.request_id = request_id
    start = time.time()
    response = await call_next(request)
    latency_ms = (time.time() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = f"{latency_ms:.0f}"
    # Use the registered route template, not caller-controlled URL text.
    route = request.scope.get("route")
    logger.info("request_complete request_id=%s method=%s route=%s latency_ms=%.0f status=%s",
                request_id, request.method, getattr(route, "path", "unmatched"), latency_ms, response.status_code)
    return response

# ------------------------------------------------------------------
# Health / readiness: verify, do not assert
# ------------------------------------------------------------------
# D-007: /health used to fill every artifact with the literal "ok" whenever the
# screener object existed, and /ready returned ready for the same reason. Both
# reported INITIALIZATION, not working inference: a deleted artifact, an
# unreadable pickle or a model that raises on every input still read healthy.
# /health now stats the real files and /ready reports a real inference attempt.

_ARTIFACT_PURPOSES = ("primary_model", "urgency_model", "primary_vectorizer",
                      "urgency_vectorizer", "primary_chi2")


def _verify_artifacts() -> tuple[bool, dict]:
    """Stat every artifact the screener loaded. Missing or empty is not ok."""
    detail: dict[str, str] = {}
    ok = True
    for purpose in _ARTIFACT_PURPOSES:
        path = os.path.join(ARTIFACTS_DIR, _ARTIFACT_FILENAMES.get(purpose, ""))
        if not path or not os.path.isfile(path):
            detail[purpose] = "missing"
            ok = False
        elif os.path.getsize(path) == 0:
            detail[purpose] = "empty"
            ok = False
        else:
            detail[purpose] = "ok"
    return ok, detail


_ARTIFACT_FILENAMES: dict[str, str] = {}


def _load_artifact_filenames() -> None:
    """Record which file each artifact purpose resolves to, from the live config."""
    try:
        with open(os.path.join(ARTIFACTS_DIR, "config.json"), encoding="utf-8") as fh:
            config = json.load(fh)
        primary, urgency = config["primary_dataset"], config["urgency_dataset"]
        _ARTIFACT_FILENAMES.update({
            "primary_model": primary["model_file"],
            "urgency_model": urgency["model_file"],
            "primary_vectorizer": primary["tfidf_vectorizer_file"],
            "urgency_vectorizer": urgency["tfidf_vectorizer_file"],
            "primary_chi2": primary["chi2_selector_file"],
        })
    except Exception as exc:  # pragma: no cover - config unreadable is reported, not raised
        logger.error("artifact_config_unreadable error_type=%s", type(exc).__name__)


_load_artifact_filenames()


def _inference_probe() -> tuple[bool, str]:
    """
    Run one real, minimal inference.

    This is the difference between "the object exists" and "the service can
    screen text". The probe text carries no risk content; it exists only to
    exercise loading, vectorization, both model tracks and the safety layer.
    """
    if screener is None:
        return False, "screener_not_initialized"
    try:
        result = screener.screen("hello")
    except Exception as exc:
        return False, f"{type(exc).__name__}"
    if not result.get("primary") or not result.get("urgency") or not result.get("safety"):
        return False, "incomplete_result"
    if result["safety"].get("level") not in (
        "NONE_DETECTED", "NEEDS_CLARIFICATION", "CONCERNING", "HIGH", "IMMEDIATE", "UNKNOWN"
    ):
        return False, "invalid_safety_level"
    if result.get("components", {}).get("independent_safety") != "complete":
        return False, "required_safety_unavailable"
    return True, "complete" if result["safety"].get("analysis_status") == "complete" else "degraded"


PROBE_TTL_SECONDS = 10.0
_probe_cache = None
_probe_lock = threading.Lock()
_probe_clock = time.monotonic


async def _fresh_probe():
    global _probe_cache
    now = _probe_clock()
    identity = id(screener)
    if _probe_cache is not None:
        checked, owner, ok, detail = _probe_cache
        if owner == identity and 0 <= now - checked < PROBE_TTL_SECONDS:
            return ok, detail, now - checked
    # Polls cannot enqueue unrestricted parallel probes. Expired success is
    # never served as ready while a replacement is pending or unavailable.
    if not _probe_lock.acquire(blocking=False):
        return False, "probe_pending", None
    try:
        try:
            ok, detail = await inference_executor.run(_inference_probe, timeout=2.0)
        except (CapacityExceeded, WorkTimedOut):
            return False, "probe_unavailable", None
        _probe_cache = (_probe_clock(), identity, ok, detail)
        return ok, detail, 0.0
    finally:
        _probe_lock.release()


@app.get("/live")
async def live():
    return {"alive": True, "service_version": SERVICE_VERSION}


@app.get("/health", response_model=HealthStatus)
async def health():
    if screener is None:
        return HealthStatus(
            status="unhealthy",
            service_version=SERVICE_VERSION,
            artifacts_ok=False,
            artifacts_detail={"error": "Screener not initialized"},
            screener_available=False,
        )
    artifacts_ok, artifacts_detail = _verify_artifacts()
    probe_ok, probe_detail, probe_age = await _fresh_probe()
    if not probe_ok:
        artifacts_detail["inference_probe"] = probe_detail
    status = "healthy" if (artifacts_ok and probe_ok) else "unhealthy"
    return HealthStatus(
        status=status,
        service_version=SERVICE_VERSION,
        artifacts_ok=artifacts_ok and probe_ok,
        artifacts_detail=artifacts_detail,
        screener_available=True,
        probe_age_seconds=probe_age,
    )


@app.get("/ready")
async def ready():
    """
    Readiness means a screening can actually be served right now.

    Both conditions are reported: the screener loaded, and a real inference
    completed. `inference_checked` is false when the probe could not run, so a
    caller can tell "not ready" from "not verified".
    """
    if screener is None:
        raise HTTPException(status_code=503, detail="Screener not available")
    artifacts_ok, _detail = _verify_artifacts()
    probe_ok, probe_detail, probe_age = await _fresh_probe()
    if not probe_ok:
        raise HTTPException(
            status_code=503, detail=f"Inference not ready: {probe_detail}"
        )
    return {
        "ready": True,
        "inference_checked": True,
        "capability": probe_detail,
        "probe_age_seconds": probe_age,
        "probe_ttl_seconds": PROBE_TTL_SECONDS,
        "optional_artifacts_ok": artifacts_ok,
        "service_version": SERVICE_VERSION,
    }

# ------------------------------------------------------------------
# Authentication endpoints
# ------------------------------------------------------------------
def _session_response(session: db.AuthSession) -> LoginResponse:
    """Project a Supabase session onto the response shape the browser expects."""
    expires_at = session.expires_at or int(time.time()) + auth.session_ttl_seconds()
    return LoginResponse(
        token=session.access_token,
        refresh_token=session.refresh_token,
        token_type="bearer",
        expires_in=max(0, expires_at - int(time.time())),
        expires_at=expires_at,
        # `user` stays a human-facing id so the existing UI and account menu keep
        # working untouched; `user_id` is the authoritative Supabase UUID.
        user=session.email or session.user_id,
        user_id=session.user_id,
        name=auth.resolve_display_name(session.display_name, session.email),
    )


@app.post("/auth/login", response_model=LoginResponse)
def login(req: LoginRequest, request: Request):
    """
    Exchange credentials for a session via Supabase Auth.

    The password goes to Supabase and nowhere else. The response says nothing
    about which half of the credential pair was wrong, and failure counts are
    tracked per client IP so one client cannot grind through an account.
    """
    client_id = request.client.host if request.client else "unknown"
    request_id = request.state.request_id

    try:
        auth.enforce_attempt_limit(client_id)
        session = auth.verify_credentials(req.user_id, req.password)
    except auth.RateLimited as exc:
        logger.warning(
            f"login_throttled request_id={request_id} client={client_id} "
            f"retry_after_s={exc.retry_after_seconds}"
        )
        raise HTTPException(
            status_code=429,
            detail=(
                "Too many failed sign-in attempts. "
                f"Try again in {exc.retry_after_seconds} seconds."
            ),
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    except auth.InvalidCredentials as exc:
        auth.record_failed_attempt(client_id)
        logger.warning(f"login_failed request_id={request_id} client={client_id}")
        raise HTTPException(status_code=401, detail="Invalid email or password") from exc
    except auth.AuthUnavailable as exc:
        logger.error("login_unavailable request_id=%s error_type=%s", request_id, type(exc).__name__)
        raise HTTPException(status_code=503, detail="Authentication service unavailable") from exc

    auth.clear_attempts(client_id)
    logger.info(f"login_complete request_id={request_id} provider={auth.auth_provider()}")
    return _session_response(session)


@app.post("/auth/refresh", response_model=LoginResponse)
def refresh(req: RefreshRequest, request: Request):
    """
    Exchange a refresh token for a new access token.

    Present so the browser can keep a session alive without the service ever
    minting a token of its own. Supabase decides whether the refresh token is
    still good.
    """
    request_id = request.state.request_id
    try:
        session = auth.refresh(req.refresh_token)
    except auth.InvalidToken as exc:
        logger.info(f"refresh_rejected request_id={request_id}")
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except auth.AuthUnavailable as exc:
        logger.error("refresh_unavailable request_id=%s error_type=%s", request_id, type(exc).__name__)
        raise HTTPException(status_code=503, detail="Authentication service unavailable") from exc
    logger.info(f"refresh_complete request_id={request_id}")
    return _session_response(session)


@app.get("/auth/session", response_model=SessionResponse)
async def session(claims: auth.Claims = Depends(require_session)):
    """Validate a stored token on page load so a revoked session cannot linger."""
    return SessionResponse(
        user=claims.email or claims.user_id,
        user_id=claims.user_id,
        name=claims.name,
        issued_at=claims.issued_at,
        expires_at=claims.expires_at,
        service_version=SERVICE_VERSION,
    )


@app.get("/auth/providers", response_model=dict)
async def auth_providers():
    """
    Which sign-in methods this deployment offers.

    These are local deployment declarations, not a remote provider probe.
    The browser checks Supabase's public settings before a Google redirect.
    """
    return {
        "email_password": True,
        "google": os.environ.get("MENTAL_AI_ENABLE_GOOGLE", "true").strip().lower() != "false",
        "provider": auth.auth_provider(),
    }


# ------------------------------------------------------------------
# Prediction endpoint (authenticated)
# ------------------------------------------------------------------
@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest, request: Request, claims: auth.Claims = Depends(require_session)):
    request_id = request.state.request_id
    if screener is None:
        logger.error(f"Prediction rejected: screener unavailable request_id={request_id}")
        raise HTTPException(status_code=503, detail="Inference service unavailable")
    try:
        start = time.time()
        result = await inference_executor.run(_screen_with_limit, claims.user_id, req.text, timeout=INFERENCE_TIMEOUT_SECONDS)
        latency_ms = (time.time() - start) * 1000
        # Metadata only. The participant's words are never logged.
        logger.info(
            f"prediction_complete request_id={request_id} latency_ms={latency_ms:.0f} "
            f"safety={result['safety']['level']} "
            f"primary_status={result['primary'].get('status')} "
            f"urgency_flagged={result['urgency']['flagged']}"
        )
        payload = PredictResponse(
            request_id=request_id,
            components=result["components"],
            model_version=result["model_version"],
            safety=SafetyResult(**result["safety"]),
            primary=PrimaryResult(
                predicted_class=result["primary"]["predicted_class"],
                class_probabilities=result["primary"].get("class_probabilities", {}),
                status=result["primary"].get("status", "complete"),
            ),
            urgency=UrgencyResult(
                predicted_class=result["urgency"]["predicted_class"],
                suicide_probability=result["urgency"]["suicide_probability"],
                decision_threshold_used=result["urgency"]["decision_threshold_used"],
                flagged=result["urgency"]["flagged"],
                status=result["urgency"].get("status", "complete"),
            ),
            cleaned_text=result.get("cleaned_text"),
            lemmatized_text=result.get("lemmatized_text"),
            provenance_caveat=result.get("provenance_caveat", "This is a screening signal, not a clinical diagnosis."),
            service_version=SERVICE_VERSION,
        )

        # Persist the screening against the verified user id from the token,
        # never anything in the request body. Best effort: the screening is the
        # product, and a database hiccup must not cost someone their result.
        # Saving acknowledgment/failure is surfaced separately from support.
        try:
            payload.persistence = await persistence_executor.run(
                _persist_screening, claims, request_id, req.text,
                {**result, "analysis_result": payload.model_dump(exclude={"persistence"})}, latency_ms,
                timeout=PERSISTENCE_TIMEOUT_SECONDS)
        except CapacityExceeded:
            payload.persistence = PersistenceResult(status="not_saved")
        except WorkTimedOut:
            payload.persistence = PersistenceResult(status="unconfirmed")


        return payload
    except Limited as exc:
        raise HTTPException(status_code=429, detail="Analysis request limit reached; please retry later",
                            headers={"Retry-After":str(exc.retry_after)}) from exc
    except (CapacityExceeded, WorkTimedOut, sqlite3.Error) as exc:
        logger.warning("prediction_unavailable request_id=%s reason=%s", request_id, type(exc).__name__)
        raise HTTPException(status_code=503, detail="Analysis capacity unavailable; please retry later",
                            headers={"Retry-After":"5"}) from exc
    except Exception as exc:
        logger.error(
            f"prediction_failed request_id={request_id} error_type={type(exc).__name__}"
        )
        # Never expose raw tracebacks or internal paths to the client
        raise HTTPException(status_code=500, detail="Prediction failed")

# ------------------------------------------------------------------
# Screening persistence (Supabase Postgres)
# ------------------------------------------------------------------
def _screen_with_limit(user_id, text):
    predict_limiter.check(user_id)
    return screener.screen(text)


def _persist_screening(
    claims: auth.Claims,
    request_id: str,
    text: str,
    result: dict,
    latency_ms: float,
) -> PersistenceResult:
    """One bounded HTTP attempt; preserve support if save is rejected/unconfirmed."""
    attempted = False
    try:
        client = db.get_client()
        attempted = True
        stored_id = client.record_screening(
            user_id=claims.user_id,
            request_id=request_id,
            result={
                **result,
                "text": text,
                "service_version": SERVICE_VERSION,
                "model_latency_ms": latency_ms,
            },
        )
        if stored_id:
            return PersistenceResult(status="saved", record_id=stored_id)
        logger.warning("screening_not_stored request_id=%s", request_id)
        return PersistenceResult(status="not_saved")
    except db.SupabaseError as exc:
        logger.warning("screening_store_skipped request_id=%s reason=%s", request_id, type(exc).__name__)
        return PersistenceResult(status="unconfirmed" if attempted else "not_saved")


@app.get("/screenings", response_model=ScreeningListResponse)
def list_screenings(
    request: Request,
    claims: auth.Claims = Depends(require_session),
    limit: int = 25,
):
    """
    The signed-in account's screening history, newest first.

    Scoped by the verified token subject, so one account can never read another's
    history. The same isolation is enforced again by RLS in the database.
    """
    request_id = request.state.request_id
    try:
        rows = db.get_client().list_screenings(claims.user_id, limit=limit)
    except db.SupabaseError as exc:
        logger.error("screening_list_failed request_id=%s reason=%s", request_id, type(exc).__name__)
        raise HTTPException(status_code=503, detail="Screening history unavailable") from exc

    try:
        return ScreeningListResponse(
            screenings=[ScreeningSummary(**row) for row in rows], count=len(rows))
    except ValidationError as exc:
        logger.error("screening_snapshot_invalid request_id=%s", request_id)
        raise HTTPException(status_code=503, detail="Screening history unavailable") from exc


@app.delete("/screenings", response_model=DeleteResponse)
def delete_screenings(request: Request, claims: auth.Claims = Depends(require_session)):
    """Remove the signed-in account's screening history."""
    request_id = request.state.request_id
    try:
        deleted = db.get_client().delete_screenings(claims.user_id)
    except db.SupabaseError as exc:
        logger.error("screening_delete_failed request_id=%s reason=%s", request_id, type(exc).__name__)
        raise HTTPException(status_code=503, detail="Screening history unavailable") from exc

    logger.info(f"screenings_deleted request_id={request_id} count={deleted}")
    return DeleteResponse(deleted=deleted)


# ------------------------------------------------------------------
# Metrics endpoint (operational, no user data)
# ------------------------------------------------------------------
@app.get("/metrics", response_model=MetricsResponse)
async def metrics():
    return MetricsResponse(
        status="operational",
        version=SERVICE_VERSION,
        uptime_seconds=round(time.time() - START_TIME, 3),
    )

# ------------------------------------------------------------------
# Root info endpoint
# ------------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "service": "mental.ai",
        "version": SERVICE_VERSION,
        "description": "Research/screening inference API. Not a clinical diagnostic system.",
        "uptime_seconds": round(time.time() - START_TIME, 3),
        "auth": {
            "provider": auth.auth_provider(),
            "login_required_for": ["/predict", "/screenings"],
            "login": "POST /auth/login",
            "refresh": "POST /auth/refresh",
            "session": "GET /auth/session",
            "providers": "GET /auth/providers",
            "storage": "supabase_postgres" if db.is_configured() else "unconfigured",
        },
        "endpoints": {
            "/auth/login": "POST - exchange credentials for a session",
            "/auth/refresh": "POST - exchange a refresh token for a session",
            "/auth/session": "GET - validate a bearer token",
            "/auth/providers": "GET - available sign-in methods",
            "/predict": "POST - screen text (authenticated)",
            "/screenings": "GET/DELETE - own screening history (authenticated)",
            "/health": "GET - service health",
            "/ready": "GET - readiness",
            "/metrics": "GET - operational metrics",
            "/docs": "GET - OpenAPI documentation",
        },
    }

# ------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "api.api:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        reload=os.environ.get("RELOAD", "false").lower() == "true",
        log_level=os.environ.get("LOG_LEVEL", "info").lower(),
    )
