# Model Card — Mental Health Screening (Phase 1)

## Model Details

- **Project**: Phase 1 mental-health text screening pipeline (research prototype)
- **Tracks**: Two independent classifiers (NOT merged)
  - Primary: 7-class condition classification (Normal, Depression, Suicidal, Anxiety, Bipolar, Stress, Personality disorder)
  - Urgency: Binary suicide/urgency safety-net (suicide / non-suicide)
- **Models**: XGBoost (primary, chi2-selected 1500 features + handcrafted), Logistic Regression (urgency, full 30k TF-IDF)
- **Feature space**: Handcrafted (38 dims) + TF-IDF (unigram+bigram, min_df=5, max_df=0.9, max_features=30000) + chi2 selection (primary k=1500)
- **Labels**: Proxy labels (subreddit of origin via Pushshift / Kaggle sources) — NOT clinician-verified diagnoses
- **Threshold**: Urgency decision threshold = 0.15 (chosen for recall: suicide recall 0.987 vs default 0.934, at cost of precision 0.840 vs 0.952)

## Training Data

- `Combined Data.csv`: 53,043 rows → 51,048 after cleaning/drop duplicates → primary dataset
- `Suicide_Detection.csv`: 232,074 rows → 231,943 after cleaning/drop duplicates → urgency dataset
- `Emotion_Sentiment_DataSet.csv`: 160,000 rows (87,983 unique) — used ONLY for emotion lexicon feature engineering (NOT for training labels)
- Split: Stratified 80/10/10 train/val/test (random_state=42, fixed seed)

## Performance (Verified from `config.json` and `Step 10` outputs)

- Primary dataset (XGBoost, 7-class): macro F1 ≈ 0.6926 (test)
- Urgency dataset (Logistic Regression, binary): macro F1 at default 0.5 = 0.9431; macro F1 at deployed 0.15 threshold = 0.8981
- These are point estimates from a single experiment; no confidence intervals or statistical significance tests were performed (documented gap)

## Artifact Availability

Verified artifacts present (`Step 12 - Packaging/package/mental_health_screening/artifacts/`):
- `primary_xgboost.pkl`, `primary_chi2_selector.pkl`, `primary_tfidf_vectorizer.pkl`
- `urgency_logreg.pkl`, `urgency_tfidf_vectorizer.pkl`
- `emotion_lexicon.json`, `curated_urgency_keywords.json`, `config.json`

Verified missing/reproduced:
- `primary_dataset_tfidf_train.npz`, `.val`, `.test` — regenerated (verified present after hardening)
- `urgency_dataset_tfidf_train.npz` — partially regenerated (`.val` and `.test` still missing due to preprocessing timeout at 300s; `train` verified present)

## Known Limitations (Verified from Source Code and Documentation)

- **Not a clinical diagnostic tool**. Both models are trained on proxy labels (subreddit origin). The urgency output is a screening signal designed for human review, not autonomous crisis intervention.
- **No speech/audio module** — text only (Phase 1 only).
- **Dataset overlap**: 51.6% of `Combined Data.csv` unique text overlaps with `Emotion_Sentiment_DataSet.csv` (verified in Step 2 EDA findings).
- **No author-level split**: No user/author identifier column exists; exact-text deduplication is the only leakage mitigation.
- **Class imbalance**: Primary dataset ratio 13.6:1 (Normal 30.8% → Personality disorder 2.3%). Class weights applied.
- **Preprocessing crash**: Turkish capital dotted I (`U+0130`, `\u0130`) caused `UnicodeEncodeError` in `preprocess_text.py` line 118; fixed with explicit `encoding="utf-8"` and defensive try/except.
- **Missing statistical tests**: No confidence intervals or significance testing performed.
- **Transformer handoff script** (`train_transformer_finetune.py`) exists but is NOT integrated into `pipeline.py` STAGES; not included in packaged artifacts.
- **Dependency split**: `Reproducibility/requirements.txt` (basic) vs `Step 12 - Packaging/package/requirements.txt` (full with numpy, scipy, xgboost); must install full package requirements for inference.

## Ethical / Safety Notes

- The urgency classifier uses a lower threshold (0.15) to maximize suicide-class recall. This increases false positives (precision drops from 0.952 at 0.5 to 0.840 at 0.15). The system is designed for routing to human review, NOT for automatic emergency action.
- Do NOT use predictions as a basis for clinical diagnosis, treatment decisions, or autonomous crisis response.

## Version

- Application version: `0.1.0`
- Artifact version linked to repository state at time of packaging (no separate release tag; commit hash tracked by git)
