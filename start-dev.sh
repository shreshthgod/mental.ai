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
API_LOG="${DEV_BACKEND_LOG:-$ROOT/.dev-backend.log}"
STARTUP_TIMEOUT="${DEV_STARTUP_TIMEOUT_SECONDS:-60}"
ISOLATED=0
if [ "${1:-}" = "--isolated-development" ] && [ "$#" -eq 1 ]; then
  ISOLATED=1
elif [ "$#" -ne 0 ]; then
  echo "usage: bash start-dev.sh [--isolated-development]"
  exit 2
fi
for value in "$API_PORT" "$WEB_PORT"; do
  if ! [[ "$value" =~ ^[0-9]{1,5}$ ]] || ((10#$value < 1 || 10#$value > 65535)); then
    echo "API_PORT and WEB_PORT must be integers in 1..65535"
    exit 2
  fi
done
if ! [[ "$STARTUP_TIMEOUT" =~ ^[0-9]{1,3}$ ]] || ((10#$STARTUP_TIMEOUT < 1 || 10#$STARTUP_TIMEOUT > 300)); then
  echo "DEV_STARTUP_TIMEOUT_SECONDS must be an integer in 1..300"
  exit 2
fi
STARTUP_TIMEOUT=$((10#$STARTUP_TIMEOUT))

PYTHON="${PYTHON:-python3}"

export PYTHONPATH="$ROOT/Step 12 - Packaging/package:$ROOT${PYTHONPATH:+:$PYTHONPATH}"

# PYTHONPATH is set above because Python resolves it before the app reads .env.
# Everything else is left unset on purpose: the API loads .env itself, and
# hardcoding a fallback here would shadow whatever that file configures.

if [ ! -d "$ROOT/web/node_modules" ]; then
  echo "web dependencies are missing. Run: npm install && npm --prefix web install"
  exit 1
fi

# The application resolves .env/artifacts and optional degradation itself.
# Missing primary artifacts cannot disable a working independent safety path.
BACKEND_PID=""

cleanup() {
  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo ""
    echo "stopping backend (pid $BACKEND_PID)"
    kill "$BACKEND_PID" 2>/dev/null
    wait "$BACKEND_PID" 2>/dev/null
  fi
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo "MENTAL.AI dev"
echo "  backend  $API_URL"
echo "  frontend http://localhost:$WEB_PORT"
echo "  log      $API_LOG"
echo ""

# Uvicorn's own log level is a CLI concern, so it is resolved here rather than
# left to the app. Only an already-exported LOG_LEVEL is honoured: .env is read
# by the API process, but this flag has to be built before it starts.
UVICORN_LOG_LEVEL="$(printf '%s' "${LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]')"

if [ "$ISOLATED" -eq 1 ]; then
  echo "isolated development: synthetic identities/in-memory provider STUB; no real Supabase"
  export VITE_SUPABASE_URL='' VITE_SUPABASE_PUBLISHABLE_KEY='' VITE_API_URL='/api'
  "$PYTHON" tests/serve_synthetic_api.py --isolated-development --port "$API_PORT" > "$API_LOG" 2>&1 &
else
  "$PYTHON" -m uvicorn api.api:app \
    --host "$API_HOST" --port "$API_PORT" --log-level "$UVICORN_LOG_LEVEL" > "$API_LOG" 2>&1 &
fi
BACKEND_PID=$!

# /health always responds200 even when capabilities are unhealthy. Readiness
# requires the actual /ready response and required-capability flag.
READY=0
STARTUP_DEADLINE=$((SECONDS + STARTUP_TIMEOUT))
while [ "$SECONDS" -lt "$STARTUP_DEADLINE" ]; do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "backend exited during startup. Last 30 log lines:"
    tail -n 30 "$API_LOG"
    exit 1
  fi
  if "$PYTHON" -c 'import json, sys, urllib.request
try:
    with urllib.request.urlopen(sys.argv[1], timeout=2) as response:
        sys.exit(0 if json.load(response).get("ready") is True else 1)
except Exception:
    sys.exit(1)' "$API_URL/ready" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 1
done

if [ "$READY" -ne 1 ]; then
  echo "backend did not become ready within ${STARTUP_TIMEOUT}s. Last 30 log lines:"
  tail -n 30 "$API_LOG"
  exit 1
fi

echo "backend ready"
echo ""

export VITE_DEV_PROXY_TARGET="$API_URL"
npm --prefix web run dev -- --host 127.0.0.1 --port "$WEB_PORT" --strictPort
