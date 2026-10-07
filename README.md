# MENTAL.AI

**See the signal.** AI-assisted mental health screening research system.

Research pipeline + packaged inference + authenticated API + React frontend + Docker deployment.

> Not a clinical diagnostic system. Produces screening signals routed to human review.

## Quick Start

```bash
npm install       # installs web dependencies too
npm run dev       # starts backend :8000 and frontend :5173
```

Then open **http://localhost:5173**. You land on `/`, the entry experience: a
WebGL composition that doubles as the sign-in page. Sign in with the demo
credentials `admin` / `password` (the greeting uses `MENTAL_AI_AUTH_NAME`, or a
name derived from the user id). Then:

- `/about` long-form product page with the dual-signal architecture
- `/screen` screening workspace, which opens on a four-step check-in
  ("How are you today?") and prefills the editor from it
- `/research` full methodology, metrics, and limitations

Set your own credentials before sharing the service anywhere:

```bash
cp .env.example .env    # then edit MENTAL_AI_AUTH_USER / _PASSWORD / _TOKEN_SECRET
```

`.env` is loaded automatically (`python-dotenv`). Real environment variables always
win, so container and CI config is never overridden by the file.

| Script | Does |
|---|---|
| `npm run dev` | backend + frontend together, health-gated, cleans up on exit |
| `npm run dev:api` | backend only, with reload |
| `npm run dev:web` | frontend only (expects the backend already up) |
| `npm run build` | production frontend build |
| `npm test` | pytest suite: inference, auth, and API contract |
| `npm run verify` | project verification script |

## Architecture

```
Raw datasets (datasets/)
  ↓
pipeline.py → Step 2..12  (27 stages: prepare / train / report)
  ↓
Packaged artifacts (Step 12/package/mental_health_screening/artifacts/)
  ↓
MentalHealthScreener.screen()
  ↓
FastAPI (/auth/login → /auth/session → /predict)
  ↓
React frontend (Vite, / → /screen → /research, /about)
```

## Authentication

`POST /predict` requires a bearer token. `GET /health`, `/ready`, `/metrics` and
`/research` stay public so the status indicator works before sign-in.

| Endpoint | Purpose |
|---|---|
| `POST /auth/login` | exchange credentials for a signed token |
| `GET /auth/session` | validate a stored token on page load |
| `POST /predict` | screen text (**authenticated**) |

Tokens are HMAC-SHA256 signed, stateless, and expire (`MENTAL_AI_SESSION_TTL`,
default 12h). Credentials are compared in constant time and login attempts are
throttled per IP. The session is re-validated against the server on every page
load, so a revoked token cannot survive a reload.

## What This Project Is

A text-based mental-health screening research project with two independent prediction tracks:

- **Primary (7-class)**: Normal, Depression, Suicidal, Anxiety, Bipolar, Stress, Personality disorder
- **Urgency (binary)**: suicide / non-suicide (tuned threshold 0.15, NOT clinical diagnosis)

Both are trained on public proxy-label datasets (Kaggle / Pushshift subreddit origins). This is a screening/research signal, NOT a clinical diagnostic system. The urgency layer is designed for human review routing, not autonomous intervention.

## Verified Current State (Based on Actual Code)

### Working
- Pipeline orchestration (`pipeline.py`) with 12 stages (prepare / train / report)
- Dataset sourcing and cleaning (`datasets/`, `Step 2-4`)
- Unified dataset construction (`Step 3` - primary from `Combined Data.csv`, urgency from `Suicide_Detection.csv`)
- Text preprocessing (`Step 5`) - encoding crash (`\u0130`) fixed; defensive error handling added; full urgency run times out at 300s (232k rows)
- Feature engineering (`Step 7`) - handcrafted features + TF-IDF (primary `.npz` regenerated; urgency `.npz` partial: `train` present, `val`/`test` missing due to timeout)
- Model artifacts (`primary_xgboost.pkl`, `urgency_logreg.pkl`, `primary_chi2_selector.pkl`, vectorizers, lexicons)
- SHAP explainability (`Step 11`) - global importance and bar plots verified
- Packaged inference (`Step 12/package/mental_health_screening/`) - `MentalHealthScreener.screen()` produces predictions
- API (`api/api.py`) - `/auth/login`, `/auth/session`, `/predict`, `/health`, `/ready`, `/metrics`
- Session auth (`api/auth.py`) - stdlib HMAC tokens, constant-time credential check, per-IP throttling, `/predict` gated
- Frontend (`web/`) - Vite + React + TypeScript, 5 routes, cinematic WebGL entry page doubling as the sign-in gate, reduced-motion and accessibility passes
- Docker (`Dockerfile`, `.dockerignore`) - container builds with dependencies + NLTK resources

### Fixed During Hardening
- Dependency installation (`ftfy`, `emoji`, `contractions`, `textstat`, `NRCLex`, `nltk` data) verified
- `Step 5 - Text Preprocessing/code/preprocess_text.py`: `encoding="utf-8"` added to `to_csv()`; `try/except` around tokenization/lemmatization
- `Step 12 - Packaging/package/mental_health_screening/inference.py`: artifact verification, input validation, defensive prediction error handling
- `REPRODUCIBILITY.md` created
- `MODEL_CARD.md` (`docs/MODEL_CARD.md`) created
- `.env.example`, `Dockerfile`, `.dockerignore` added
- `tests/test_service.py` (34 tests: inference, auth primitives, API contract via `TestClient`)
- `scripts/verify_project.py` added (verification: 6 PASS, 2 FAIL, 1 SKIPPED)
- `/metrics` `uptime_seconds` replaced the no-op placeholder (`time.time() - (time.time() - time.time())`) with a real `START_TIME` delta
- Prediction failures no longer echo exception text to the client
- `tsconfig.*.tsbuildinfo` removed from version control and gitignored
- `.env` is now actually loaded (`python-dotenv`, real env vars take precedence)
- `start-dev.sh` no longer hardcodes `SERVICE_VERSION`/`ARTIFACTS_DIR`, which had been shadowing `.env`
- Route-level code splitting for `/screen` and `/research` (design spec 14)
- Dead `.page-veil` CSS removed

### Not Completed / Verified Incomplete
- **Urgency TF-IDF `.npz` matrices** (`urgency_dataset_tfidf_val.npz`, `.test.npz`) - missing; urgency preprocessing timed out at 300s; `train.npz` verified present. Does NOT block inference (`.pkl` vectorizer sufficient for predictions).
- **Statistical significance tests** - not added; only point estimates preserved from `config.json` (primary macro F1 ≈ 0.6926; urgency 0.8981 @ threshold 0.15)
- **Full urgency preprocessing cycle** - requires >10 minutes; not completed within environment timeout constraints
- **Transformer fine-tuning script** (`Step 9/code/train_transformer_finetune.py`) - exists but NOT integrated into `pipeline.py` STAGES; NOT included in packaged artifacts
- **Distributed rate limiting** - login throttling is per-process and in-memory, so it does not hold across replicas

## Manual Setup

### Dependencies

```bash
pip install -r "Step 12 - Packaging/package/requirements.txt" -r api/requirements.txt
python -c "import nltk; nltk.download('vader_lexicon'); nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('averaged_perceptron_tagger_eng'); nltk.download('wordnet')"
```

### Inference (Local)

```bash
PYTHONPATH=Step\ 12\ -\ Packaging/package:$PYTHONPATH python -c "
from mental_health_screening.inference import MentalHealthScreener
s = MentalHealthScreener()
print(s.screen('test input'))
"
```

### API (Local)

```bash
PYTHONPATH="Step 12 - Packaging/package:." python -m uvicorn api.api:app --port 8000
```

`/predict` is authenticated, so a session token comes first:

```bash
curl http://localhost:8000/health

TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"user_id":"admin","password":"password"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"text":"I have not slept in three days."}'
```

### Docker

```bash
docker build -t mental-ai .
docker run -p 8000:8000 \
  -e MENTAL_AI_AUTH_USER=you \
  -e MENTAL_AI_AUTH_PASSWORD='a-real-password' \
  -e MENTAL_AI_TOKEN_SECRET="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')" \
  mental-ai
```

## Architecture

```
Raw datasets (datasets/)
  ↓
Pipeline (pipeline.py) → Step 2..12
  ↓
Packaged artifacts (Step 12/package/mental_health_screening/artifacts/)
  ↓
MentalHealthScreener.screen()
  ↓
FastAPI (/auth/login → /auth/session → /predict)
  ↓
React frontend (Vite, / → /screen → /research, /about)
```

## Important Safety Note

This system produces **research/screening signals**, not clinical diagnoses. The urgency layer uses a 0.15 threshold to prioritize recall (suicide recall 0.987 vs default 0.934, precision 0.840 vs 0.952). It is designed for routing to human review, NOT for autonomous crisis intervention. No emergency services are contacted automatically.

## Project Structure (Post-Hardening)

```
.
├── pipeline.py                  # Orchestrator (27 stages: prepare / train / report)
├── start-dev.sh                 # Backend + frontend boot, health-gated
├── package.json                 # npm run dev / test / build
├── datasets/                    # Raw data (gitignored)
├── Step 2 ... Step 12/          # Research pipeline stages
├── api/
│   ├── api.py                   # FastAPI service
│   ├── auth.py                  # HMAC session tokens, throttling
│   └── requirements.txt         # Transport-layer dependencies
├── web/                         # Vite + React + TypeScript frontend
│   ├── src/lib/                 # api client, session store, check-in
│   ├── src/pages/               # Landing, Login, Screen, Research
│   └── src/components/          # Hero WebGL, chrome, landing sections
├── docs/
│   ├── MODEL_CARD.md            # Model documentation
│   └── frontend-design-spec.md  # Design specification
├── scripts/verify_project.py    # Verification (PASS/FAIL/SKIPPED)
├── tests/test_service.py        # Inference, auth, and API contract tests
├── REPRODUCIBILITY.md           # Verified reproduction steps
├── Dockerfile                   # Production container
├── .dockerignore                # Clean build exclusions
├── .env.example                 # Environment variables
└── Step 12 - Packaging/package/ # Inference package (hardened)
```

## What Was Not Changed

- Existing ML architecture (two independent tracks, separate feature spaces, separate thresholds)
- Existing label definitions (proxy labels documented in `MODEL_CARD.md`)
- Existing metrics (preserved from `config.json` and `Step 10` outputs)
- Existing research artifacts (SHAP outputs, confusion matrices, error analysis CSVs preserved)
- No new models introduced; no retraining performed unless required for regeneration (primary `.npz` regenerated from existing `.pkl` and preprocessed data; urgency `.npz` partial due to timeout)

## Verification Command

```bash
python scripts/verify_project.py
```

Current verified result: 6 PASS | 2 FAIL | 1 SKIPPED
- PASS: Dependencies, artifacts, inference, health check, primary `.npz`, preprocessing fix
- FAIL: NLTK resource path discrepancy (package works; verification script searches different path) - does NOT block inference; urgency `.npz` incomplete (`val`, `test` missing)
- SKIPPED: API not running locally (expected unless `uvicorn` started manually)

## Tests

```bash
npm test
```

35 tests covering artifact loading, inference output shape, input validation,
token issue/verify/tamper/expiry, credential rejection, login throttling,
`/predict` gating, and the public operational endpoints.

`npm test` needs `pytest` and `httpx` (see `api/requirements.txt`). Frontend QA
scripts live in `web/scripts/` and drive a real browser against a running stack:

```bash
cd web
node scripts/interaction.mjs http://localhost:5173   # check-in, sign-in, screening
node scripts/failure.mjs http://localhost:5173       # oversize, offline, reduced motion
node scripts/screenshots.mjs http://localhost:5173   # 5 viewports to web/shots/
```

## Git Safety Note

This repository was initialized with `git init` at the start of hardening. The original state is preserved in the initial commit. All modifications are tracked.
# mental.ai
