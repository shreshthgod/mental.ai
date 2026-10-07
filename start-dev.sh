#!/usr/bin/env bash
#
# One-command dev boot for MENTAL.AI.
#
#   npm run dev
#
# Starts the FastAPI backend and the Vite frontend together, waits until the
# backend is actually answering before handing over the terminal to Vite, and
# shuts the backend down again when Vite exits.
#
# Ports: backend 8000, frontend 5173. Override with API_PORT / WEB_PORT.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT" || exit 1

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"
API_HOST="127.0.0.1"
API_URL="http://${API_HOST}:${API_PORT}"
API_LOG="$ROOT/.dev-backend.log"

PYTHON="${PYTHON:-python3}"

export PYTHONPATH="$ROOT/Step 12 - Packaging/package:$ROOT${PYTHONPATH:+:$PYTHONPATH}"

# PYTHONPATH is set above because Python resolves it before the app reads .env.
# Everything else is left unset on purpose: the API loads .env itself, and
# hardcoding a fallback here would shadow whatever that file configures.

if [ ! -d "$ROOT/web/node_modules" ]; then
  echo "web dependencies are missing. Run: npm install && npm --prefix web install"
  exit 1
fi

# Artifact location. Checked before launch, so a missing or misconfigured
# path reports here rather than as an opaque 503 from /health.
ARTIFACTS_DIR="${ARTIFACTS_DIR:-$ROOT/Step 12 - Packaging/package/mental_health_screening/artifacts}"

if [ ! -f "$ARTIFACTS_DIR/primary_xgboost.pkl" ]; then
  echo "model artifacts not found in:"
  echo "  $ARTIFACTS_DIR"
  echo "Run the pipeline (python pipeline.py run all) to regenerate them."
  exit 1
fi

BACKEND_PID=""

cleanup() {
  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo ""
    echo "stopping backend (pid $BACKEND_PID)"
    kill "$BACKEND_PID" 2>/dev/null
    wait "$BACKEND_PID" 2>/dev/null
  fi
}
trap cleanup EXIT INT TERM

echo "MENTAL.AI dev"
echo "  backend  $API_URL"
echo "  frontend http://localhost:$WEB_PORT"
echo "  log      $API_LOG"
echo ""

# Uvicorn's own log level is a CLI concern, so it is resolved here rather than
# left to the app. Only an already-exported LOG_LEVEL is honoured: .env is read
# by the API process, but this flag has to be built before it starts.
UVICORN_LOG_LEVEL="$(printf '%s' "${LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]')"

"$PYTHON" -m uvicorn api.api:app \
  --host "$API_HOST" \
  --port "$API_PORT" \
  --log-level "$UVICORN_LOG_LEVEL" \
  > "$API_LOG" 2>&1 &
BACKEND_PID=$!

# Poll /health rather than sleeping a fixed amount: model load time varies with
# disk and CPU, and starting Vite early produces a confusing first-run error.
READY=0
for _ in $(seq 1 60); do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "backend exited during startup. Last 30 log lines:"
    tail -n 30 "$API_LOG"
    exit 1
  fi
  if curl -fsS "$API_URL/health" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 1
done

if [ "$READY" -ne 1 ]; then
  echo "backend did not become healthy within 60s. Last 30 log lines:"
  tail -n 30 "$API_LOG"
  exit 1
fi

echo "backend ready"
echo ""

npm --prefix web run dev -- --port "$WEB_PORT"