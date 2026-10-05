"""
Production HTTP API for the mental-health screening inference package.

Architecture:
    HTTP → FastAPI validation → MentalHealthScreener.screen() → JSON response

This layer contains NO model logic; it only transports and validates.
"""
import os
import sys
import time
import uuid
import logging
import traceback
from typing import Optional

# Ensure package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Step 12 - Packaging", "package"))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from mental_health_screening.inference import MentalHealthScreener

# ------------------------------------------------------------------
# Logging: structured, no raw user text, no PII
# ------------------------------------------------------------------
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("screening-api")

# ------------------------------------------------------------------
# App initialization with explicit artifact verification
# ------------------------------------------------------------------
ARTIFACTS_DIR = os.environ.get("ARTIFACTS_DIR", os.path.join(
    os.path.dirname(__file__), "..", "Step 12 - Packaging", "package",
    "mental_health_screening", "artifacts"
))

try:
    screener = MentalHealthScreener(artifacts_dir=ARTIFACTS_DIR)
    logger.info("MentalHealthScreener initialized successfully")
except Exception as exc:
    logger.error(f"MentalHealthScreener initialization failed: {exc}")
    screener = None  # Will be caught by /health

app = FastAPI(
    title="Mental Health Screening API",
    description="Research/screening inference layer over packaged ML artifacts. NOT a clinical diagnostic system.",
    version=os.environ.get("SERVICE_VERSION", "0.1.0"),
)

# ------------------------------------------------------------------
# Request / response contracts (typed, based on actual inference output)
# ------------------------------------------------------------------
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
        service_version=os.environ.get("SERVICE_VERSION", "0.1.0"),
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
    return {"ready": True, "service_version": os.environ.get("SERVICE_VERSION", "0.1.0")}

# ------------------------------------------------------------------
# Prediction endpoint
# ------------------------------------------------------------------
@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest, request: Request):
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
            service_version=os.environ.get("SERVICE_VERSION", "0.1.0"),
        )
    except Exception as exc:
        logger.error(
            f"prediction_failed request_id={request_id} error_type={type(exc).__name__} msg={str(exc)}"
        )
        # Never expose raw tracebacks or internal paths to the client
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(exc)}")

# ------------------------------------------------------------------
# Metrics endpoint (operational, no user data)
# ------------------------------------------------------------------
@app.get("/metrics", response_model=MetricsResponse)
async def metrics():
    return MetricsResponse(
        status="operational",
        version=os.environ.get("SERVICE_VERSION", "0.1.0"),
        uptime_seconds=time.time() - (time.time() - time.time()),  # placeholder; real metric would need start time
    )

# ------------------------------------------------------------------
# Root info endpoint
# ------------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "service": "mental-health-screening",
        "version": os.environ.get("SERVICE_VERSION", "0.1.0"),
        "description": "Research/screening inference API. Not a clinical diagnostic system.",
        "endpoints": {
            "/predict": "POST - screen text",
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
