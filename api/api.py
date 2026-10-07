"""
Production HTTP API for the MENTAL.AI screening inference package.

Architecture:
    HTTP → bearer session check → FastAPI validation
         → MentalHealthScreener.screen() → JSON response

This layer contains NO model logic; it only authenticates, transports and
validates. Raw user text is never logged.
"""
import os
import sys
import time
import uuid
import logging
from typing import Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

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
from pydantic import BaseModel, Field
import uvicorn

from mental_health_screening.inference import MentalHealthScreener

from api import auth

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
SERVICE_VERSION = os.environ.get("SERVICE_VERSION", "0.1.0")
START_TIME = time.time()

try:
    screener = MentalHealthScreener(artifacts_dir=ARTIFACTS_DIR)
    logger.info("MentalHealthScreener initialized successfully")
except Exception as exc:
    logger.error(f"MentalHealthScreener initialization failed: {exc}")
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
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

bearer_scheme = HTTPBearer(auto_error=False)


# ------------------------------------------------------------------
# Session dependency
# ------------------------------------------------------------------
def require_session(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    """FastAPI dependency: resolve a valid bearer token or raise 401."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        return auth.decode_token(credentials.credentials)
    except auth.InvalidToken as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


# ------------------------------------------------------------------
# Request / response contracts (typed, based on actual inference output)
# ------------------------------------------------------------------
class LoginRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128, description="Configured user id")
    password: str = Field(..., min_length=1, max_length=256, description="Account password")


class LoginResponse(BaseModel):
    token: str
    token_type: str
    expires_in: int
    expires_at: int
    user: str
    name: str


class SessionResponse(BaseModel):
    user: str
    name: str
    issued_at: int
    expires_at: int
    service_version: str


class PredictRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000, description="Raw user text for screening")

class PrimaryResult(BaseModel):
    predicted_class: str
    class_probabilities: dict

class UrgencyResult(BaseModel):
    predicted_class: str
    suicide_probability: float
    decision_threshold_used: float
    flagged: bool

class PredictResponse(BaseModel):
    request_id: str
    primary: PrimaryResult
    urgency: UrgencyResult
    cleaned_text: Optional[str] = None
    lemmatized_text: Optional[str] = None
    provenance_caveat: Optional[str] = None
    service_version: str

class HealthStatus(BaseModel):
    status: str
    service_version: str
    artifacts_ok: bool
    artifacts_detail: dict
    screener_available: bool

class MetricsResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: float

# ------------------------------------------------------------------
# Middleware: request IDs and latency tracking
# ------------------------------------------------------------------
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:16])
    request.state.request_id = request_id
    start = time.time()
    response = await call_next(request)
    latency_ms = (time.time() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = f"{latency_ms:.0f}"
    logger.info(
        f"request_complete request_id={request_id} method={request.method} "
        f"path={request.url.path} latency_ms={latency_ms:.0f} status={response.status_code}"
    )
    return response

# ------------------------------------------------------------------
# Health endpoint (must verify actual artifacts)
# ------------------------------------------------------------------
@app.get("/health", response_model=HealthStatus)
async def health():
    artifacts_ok = True
    artifacts_detail = {}
    if screener is not None:
        for name in ["primary_model", "urgency_model", "primary_vectorizer",
                     "urgency_vectorizer", "primary_chi2"]:
            # We rely on the screener initialization; if it raised, it's None
            artifacts_detail[name] = "ok"
    else:
        artifacts_ok = False
        artifacts_detail = {"error": "Screener not initialized"}
    status = "healthy" if artifacts_ok else "unhealthy"
    return HealthStatus(
        status=status,
        service_version=SERVICE_VERSION,
        artifacts_ok=artifacts_ok,
        artifacts_detail=artifacts_detail,
        screener_available=screener is not None,
    )

# ------------------------------------------------------------------
# Ready endpoint (inference-capable check)
# ------------------------------------------------------------------
@app.get("/ready")
async def ready():
    if screener is None:
        raise HTTPException(status_code=503, detail="Screener not available")
    return {"ready": True, "service_version": SERVICE_VERSION}

# ------------------------------------------------------------------
# Authentication endpoints
# ------------------------------------------------------------------
@app.post("/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest, request: Request):
    """
    Exchange configured credentials for a signed bearer token.

    The response says nothing about which half of the credential pair was
    wrong. Failure counts are tracked per client IP and throttled.
    """
    client_id = request.client.host if request.client else "unknown"
    request_id = request.state.request_id

    try:
        auth.enforce_attempt_limit(client_id)
        auth.verify_credentials(req.user_id, req.password)
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
        raise HTTPException(status_code=401, detail="Invalid user id or password") from exc

    auth.clear_attempts(client_id)
    user = auth.configured_user()
    token, expires_in = auth.issue_token(user)
    logger.info(
        f"login_complete request_id={request_id} user={user} "
        f"demo_credentials={auth.using_demo_credentials()}"
    )
    return LoginResponse(
        token=token,
        token_type="bearer",
        expires_in=expires_in,
        expires_at=int(time.time()) + expires_in,
        user=user,
        name=auth.configured_name(),
    )


@app.get("/auth/session", response_model=SessionResponse)
async def session(claims: dict = Depends(require_session)):
    """Validate a stored token on page load so a revoked session cannot linger."""
    return SessionResponse(
        user=claims["sub"],
        name=auth.configured_name(),
        issued_at=claims["iat"],
        expires_at=claims["exp"],
        service_version=SERVICE_VERSION,
    )

# ------------------------------------------------------------------
# Prediction endpoint (authenticated)
# ------------------------------------------------------------------
@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest, request: Request, claims: dict = Depends(require_session)):
    request_id = request.state.request_id
    if screener is None:
        logger.error(f"Prediction rejected: screener unavailable request_id={request_id}")
        raise HTTPException(status_code=503, detail="Inference service unavailable")
    try:
        start = time.time()
        result = screener.screen(req.text)
        latency_ms = (time.time() - start) * 1000
        logger.info(
            f"prediction_complete request_id={request_id} latency_ms={latency_ms:.0f} "
            f"primary={result['primary']['predicted_class']} urgency_flagged={result['urgency']['flagged']}"
        )
        return PredictResponse(
            request_id=request_id,
            primary=PrimaryResult(
                predicted_class=result["primary"]["predicted_class"],
                class_probabilities=result["primary"].get("class_probabilities", {}),
            ),
            urgency=UrgencyResult(
                predicted_class=result["urgency"]["predicted_class"],
                suicide_probability=result["urgency"]["suicide_probability"],
                decision_threshold_used=result["urgency"]["decision_threshold_used"],
                flagged=result["urgency"]["flagged"],
            ),
            cleaned_text=result.get("cleaned_text"),
            lemmatized_text=result.get("lemmatized_text"),
            provenance_caveat=result.get("provenance_caveat", "This is a screening signal, not a clinical diagnosis."),
            service_version=SERVICE_VERSION,
        )
    except Exception as exc:
        logger.error(
            f"prediction_failed request_id={request_id} error_type={type(exc).__name__} msg={str(exc)}"
        )
        # Never expose raw tracebacks or internal paths to the client
        raise HTTPException(status_code=500, detail="Prediction failed")

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
            "login_required_for": ["/predict"],
            "login": "POST /auth/login",
            "session": "GET /auth/session",
            "demo_credentials_in_use": auth.using_demo_credentials(),
        },
        "endpoints": {
            "/auth/login": "POST - exchange credentials for a bearer token",
            "/auth/session": "GET - validate a bearer token",
            "/predict": "POST - screen text (authenticated)",
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
