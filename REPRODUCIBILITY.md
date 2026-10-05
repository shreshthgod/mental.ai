# Reproducibility Guide

This document describes the verified steps to reproduce the mental-health screening pipeline, inference package, and API.

## Verified Repository State

- Pipeline stages defined in `pipeline.py` (STAGES tuple)
- Raw datasets in `datasets/text datasets/`
- Preprocessing code in `Step 5 - Text Preprocessing/code/preprocess_text.py`
- Feature engineering in `Step 7 - Feature Extraction/code/feature_engineering.py`
- TF-IDF vectorization in `Step 7 - Feature Extraction/code/tfidf_vectorize.py`
- Model artifacts in `Step 12 - Packaging/package/mental_health_screening/artifacts/`
- Packaged inference in `Step 12 - Packaging/package/mental_health_screening/inference.py`
- API in `api/api.py`
- Docker deployment in `Dockerfile`

## Dependency Installation (Verified)

```bash
pip install -r Step\ 12\ -\ Packaging/package/requirements.txt
python -c "import nltk; nltk.download('vader_lexicon'); nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('averaged_perceptron_tagger'); nltk.download('averaged_perceptron_tagger_eng'); nltk.download('wordnet'); print('Dependencies OK')"
```

Verified imports: `ftfy`, `emoji`, `contractions`, `textstat`, `nltk`, `scipy`, `numpy`, `pandas`, `scikit-learn`, `xgboost`, `NRCLex`.

## Pipeline Status

Run:
```bash
python pipeline.py status all
```

Verified results (before hardening):
- 18 stages PRESENT
- `tfidf-primary` MISSING `.npz` matrices (regenerated during hardening; urgency `.npz` still missing due to preprocessing timeout at 300s)
- `features-primary` HYDRATABLE (reconstructable from delivery chunks)
- `preprocess-urgency` has verified crash at `preprocess_text.py:118` (encoding fixed with `encoding="utf-8"`)

## Preprocessing Fix

The original `preprocess_text.py` used default encoding for file writes, causing `UnicodeEncodeError: 'charmap' codec can't encode character '\\u0130'` on urgency data. Fixed by:
- Adding `encoding="utf-8"` to `df.to_csv()`
- Adding defensive `try/except` around tokenization/lemmatization per batch
- Logging failures without exposing raw user text

Preprocessing runs slowly (~75 rows/s on primary dataset); urgency dataset (232k rows) exceeds 300-second timeout on this environment.

## Inference Verification

```bash
PYTHONPATH=Step\ 12\ -\ Packaging/package:$PYTHONPATH python -c "
from mental_health_screening.inference import MentalHealthScreener
s = MentalHealthScreener()
r = s.screen('test input')
print('Prediction:', r['primary']['predicted_class'], '| Urgency flagged:', r['urgency']['flagged'])
"
```

Verified result: package loads artifacts (`primary_xgboost.pkl`, `urgency_logreg.pkl`, `primary_tfidf_vectorizer.pkl`, `config.json`), produces predictions, and includes provenance caveat.

## API Verification

```bash
python -m uvicorn api.api:app --host 0.0.0.0 --port 8000 --reload false
```

Then:
```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"text":"I feel really sad today"}'
```

Verified endpoints:
- `/health` checks artifact availability and returns 200/503
- `/predict` validates input, calls `MentalHealthScreener.screen()`, returns structured JSON with `request_id`, `primary`, `urgency`, `cleaned_text`
- `/ready` confirms inference capability
- `/metrics` provides basic operational metrics

## Docker Verification

```bash
docker build -t mental-health-screening .
docker run -p 8000:8000 mental-health-screening
```

Container includes:
- Python 3.13-slim base
- Installed dependencies (`requirements.txt`)
- Downloaded NLTK resources (`vader_lexicon`, `punkt`, `punkt_tab`, `averaged_perceptron_tagger_eng`, `wordnet`)
- Health check calling `/health`
- `ARTIFACTS_DIR` set to packaged artifacts

Note: The urgency `.npz` TF-IDF matrices are not regenerated (preprocessing timed out at 300s). This does not affect inference (only `.pkl` vectorizer needed), but full pipeline reproduction requires completing urgency preprocessing.

## Missing / Not Fully Verified

- Urgency `.npz` matrices (`urgency_dataset_tfidf_train.npz`, `.val`, `.test`) - not regenerated due to preprocessing timeout
- Full urgency preprocessing cycle on 232k rows requires >10 minutes; not completed within timeout constraints
- `REPRODUCIBILITY.md` (this file covers the verified state; formal experiment log not created)
- Statistical significance tests for model results (not added; only point estimates preserved from `config.json`)
- `MODEL_CARD.md` (created separately; see docs/ if present)

## Safety Note

The urgency classifier uses a threshold of 0.15 (configured in `config.json`) to prioritize recall for suicide-class detection. This is a screening/safety-net layer, NOT an autonomous intervention mechanism. No emergency services are contacted automatically.
