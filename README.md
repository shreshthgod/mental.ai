# Mental Health Screening Pipeline (Phase 1) — Hardened & Deployable

Research pipeline + packaged inference + production API + Docker deployment + documentation.

## What This Project Is

A text-based mental-health screening research project with two independent prediction tracks:

- **Primary (7-class)**: Normal, Depression, Suicidal, Anxiety, Bipolar, Stress, Personality disorder
- **Urgency (binary)**: suicide / non-suicide (tuned threshold 0.15, NOT clinical diagnosis)

Both are trained on public proxy-label datasets (Kaggle / Pushshift subreddit origins). This is a screening/research signal, NOT a clinical diagnostic system. The urgency layer is designed for human review routing, not autonomous intervention.

## Verified Current State (Based on Actual Code)

### Working
- Pipeline orchestration (`pipeline.py`) with 12 stages (prepare / train / report)
- Dataset sourcing and cleaning (`datasets/`, `Step 2-4`)
- Unified dataset construction (`Step 3` — primary from `Combined Data.csv`, urgency from `Suicide_Detection.csv`)
- Text preprocessing (`Step 5`) — encoding crash (`\u0130`) fixed; defensive error handling added; full urgency run times out at 300s (232k rows)
- Feature engineering (`Step 7`) — handcrafted features + TF-IDF (primary `.npz` regenerated; urgency `.npz` partial: `train` present, `val`/`test` missing due to timeout)
- Model artifacts (`primary_xgboost.pkl`, `urgency_logreg.pkl`, `primary_chi2_selector.pkl`, vectorizers, lexicons)
- SHAP explainability (`Step 11`) — global importance and bar plots verified
- Packaged inference (`Step 12/package/mental_health_screening/`) — `MentalHealthScreener.screen()` produces predictions
- API (`api/api.py`) — `/predict`, `/health`, `/ready`, `/metrics`
- Docker (`Dockerfile`, `.dockerignore`) — container builds with dependencies + NLTK resources

### Fixed During Hardening
- Dependency installation (`ftfy`, `emoji`, `contractions`, `textstat`, `NRCLex`, `nltk` data) verified
- `Step 5 - Text Preprocessing/code/preprocess_text.py`: `encoding="utf-8"` added to `to_csv()`; `try/except` around tokenization/lemmatization
- `Step 12 - Packaging/package/mental_health_screening/inference.py`: artifact verification, input validation, defensive prediction error handling
- `REPRODUCIBILITY.md` created
- `MODEL_CARD.md` (`docs/MODEL_CARD.md`) created
- `.env.example`, `Dockerfile`, `.dockerignore` added
- `tests/test_service.py` added (unit + integration smoke tests)
- `scripts/verify_project.py` added (verification: 6 PASS, 2 FAIL, 1 SKIPPED)

### Not Completed / Verified Incomplete
- **Urgency TF-IDF `.npz` matrices** (`urgency_dataset_tfidf_val.npz`, `.test.npz`) — missing; urgency preprocessing timed out at 300s; `train.npz` verified present. Does NOT block inference (`.pkl` vectorizer sufficient for predictions).
- **Statistical significance tests** — not added; only point estimates preserved from `config.json` (primary macro F1 ≈ 0.6926; urgency 0.8981 @ threshold 0.15)
- **Full urgency preprocessing cycle** — requires >10 minutes; not completed within environment timeout constraints
- **Transformer fine-tuning script** (`Step 9/code/train_transformer_finetune.py`) — exists but NOT integrated into `pipeline.py` STAGES; NOT included in packaged artifacts
- **Frontend** — NOT built (must wait for stable API contract; this repository delivers verified backend + documentation per instructions)

## Quick Start

### Dependencies

```bash
pip install -r Step\ 12\ -\ Packaging/package/requirements.txt
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
python -m uvicorn api.api:app --host 0.0.0.0 --port 8000
```

Then:
```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"text":"test input"}'
```

### Docker

```bash
docker build -t mental-health-screening .
docker run -p 8000:8000 mental-health-screening
```

## Architecture

```
Raw datasets (datasets/)
  ↓
Pipeline (pipeline.py) → Step 1–12
  ↓
Packaged artifacts (Step 12/package/mental_health_screening/artifacts/)
  ↓
Inferred predictions (MentalHealthScreener.screen())
  ↓
API transport (FastAPI /predict, /health, /metrics)
  ↓
Container deployment (Dockerfile + healthcheck)
  ↓
Documentation / verification (REPRODUCIBILITY.md, MODEL_CARD.md, scripts/)
```

## Important Safety Note

This system produces **research/screening signals**, not clinical diagnoses. The urgency layer uses a 0.15 threshold to prioritize recall (suicide recall 0.987 vs default 0.934, precision 0.840 vs 0.952). It is designed for routing to human review, NOT for autonomous crisis intervention. No emergency services are contacted automatically.

## Project Structure (Post-Hardening)

```
project/
├── pipeline.py                 # Orchestrator (verified working)
├── datasets/                     # Raw data
├── Step 1 ... Step 12/           # Research pipeline stages (preserved)
├── api/
│   ├── api.py                    # FastAPI service
│   └── ...
├── docs/
│   └── MODEL_CARD.md            # Verified model documentation
├── scripts/
│   └── verify_project.py         # Verification (PASS/FAIL/SKIPPED)
├── tests/
│   └── test_service.py           # Unit + integration smoke tests
├── REPRODUCIBILITY.md             # Verified reproduction steps
├── MODEL_CARD.md                 # Research artifact documentation
├── Dockerfile                     # Production container
├── .dockerignore                 # Clean build exclusions
├── .env.example                  # Environment variables
└── Step 12 - Packaging/package/  # Inference package (hardened)
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
- FAIL: NLTK resource path discrepancy (package works; verification script searches different path) — does NOT block inference; urgency `.npz` incomplete (`val`, `test` missing)
- SKIPPED: API not running locally (expected unless `uvicorn` started manually)

## Git Safety Note

This repository was initialized with `git init` at the start of hardening. The original state is preserved in the initial commit. All modifications are tracked.
