# mental_health_screening - Phase 1 inference module

Takes raw text in, returns predictions from both trained models. Bundles
everything needed: the fitted TF-IDF vectorizers, chi2 selector, curated
urgency-keyword list, custom emotion lexicon, and the two winning models
(Step 9/10's picks) - nothing to regenerate, nothing external except the
listed packages and NLTK's data files.

## Install

```
pip install -r requirements.txt
python -m nltk.downloader punkt punkt_tab averaged_perceptron_tagger_eng wordnet omw-1.4 vader_lexicon
```

## Use

```python
from mental_health_screening.inference import MentalHealthScreener

screener = MentalHealthScreener()
result = screener.screen("some raw text")
```

`result`:
```python
{
  "primary": {
    "predicted_class": "Depression",           # one of the 7 primary classes
    "class_probabilities": {"Normal": 0.02, "Depression": 0.61, ...},
  },
  "urgency": {
    "predicted_class": "suicide",              # "suicide" or "non-suicide"
    "suicide_probability": 0.73,
    "decision_threshold_used": 0.15,           # not 0.5 -- see below
    "flagged": True,
  },
  "cleaned_text": "...",       # after Step 4-equivalent cleaning
  "lemmatized_text": "...",    # after Step 5-equivalent lemmatization
  "provenance_caveat": "...",  # the line below, always included in the output itself
}
```

## Read this before using the output for anything real
Both models are trained on **proxy labels** - subreddit of origin via the
Pushshift API - not clinician-verified diagnoses. Treat every output as a
screening signal that should be reviewed by a person, never as a diagnosis
or an automatic action trigger. See the paper-details doc's Limitations
section (items 53–56) and Step 11's error analysis for the specific,
documented failure modes (Depression↔Suicidal confusion, a subreddit-source
artifact in the urgency model's top features, and known label noise in the
source datasets).

## Why urgency_dataset uses threshold 0.15, not 0.5
Step 10 swept the decision threshold and found 0.15 keeps suicide-class
recall at 0.987 (vs. 0.934 at the default 0.5) - missing only 151 of 11,594
real crisis posts in testing, instead of 766 - at the cost of more false
positives (precision 0.840 vs. 0.952). For a safety-net layer meant to
route posts to human review, a missed crisis post is a worse outcome than
an extra false alarm, so this was a deliberate choice, not an oversight.
Full reasoning in Step 10's README.

## What's inside `artifacts/`
| File | What it is |
|---|---|
| `primary_xgboost.pkl` | primary_dataset's winning model (XGBoost + label encoder) |
| `primary_tfidf_vectorizer.pkl` | fitted TF-IDF vectorizer (30k vocab, fit on train only) |
| `primary_chi2_selector.pkl` | chi2 selector reducing TF-IDF to the 1,500 terms the model was trained on |
| `urgency_logreg.pkl` | urgency_dataset's winning model (Logistic Regression) |
| `urgency_tfidf_vectorizer.pkl` | fitted TF-IDF vectorizer (30k vocab, fit on train only) |
| `curated_urgency_keywords.json` | Step 6's 95-word curated urgency-keyword list |
| `emotion_lexicon.json` | Step 7's leakage-guarded custom emotion-association lexicon |
| `config.json` | exact handcrafted-feature column order, class lists, thresholds, feature-space descriptions |

## Verified, not assumed
`code/verify_parity.py` (one directory up) feeds genuinely raw, pre-cleaning
text through this package end to end and checks the result against the
pipeline's own saved artifacts - 10/10 test rows matched exactly (both the
intermediate cleaned/lemmatized text and the final prediction) before this
was called done. Re-run it any time this package is modified.

## What this module does NOT include
- The transformer fine-tuning handoff script (Step 9c) - separate, GPU-only, not part of this classical-ML package.
- Training code - this is inference-only. Full training code is in Steps 7–9's folders.
- Batch/dataframe processing - `screen()` takes one string at a time; wrap it in a loop for batches.
