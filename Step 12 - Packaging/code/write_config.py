"""One-off: bakes the exact training-time feature order + metadata into
config.json, so the packaged module never has to guess column order --
it reads it from this file. Run once at packaging time, not at inference time."""
import sys
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "Step 9 - Model Training" / "code"))
from data_utils import load_handcrafted, DATASETS

OUT = REPO_ROOT / "Step 12 - Packaging" / "package" / "mental_health_screening" / "artifacts" / "config.json"

_, primary_feat_cols = load_handcrafted("primary")
_, urgency_feat_cols = load_handcrafted("urgency")
assert primary_feat_cols == urgency_feat_cols, "handcrafted feature order differs between datasets -- packaging assumption broken"

config = {
    "handcrafted_feature_order": primary_feat_cols,
    "primary_dataset": {
        "classes": DATASETS["primary"]["classes"],
        "chi2_k": 1500,
        "model_file": "primary_xgboost.pkl",
        "tfidf_vectorizer_file": "primary_tfidf_vectorizer.pkl",
        "chi2_selector_file": "primary_chi2_selector.pkl",
        "feature_space": "38 handcrafted + chi2-selected 1500 TF-IDF terms = 1538 dims",
        "test_macro_f1": 0.6926,
    },
    "urgency_dataset": {
        "classes": DATASETS["urgency"]["classes"],
        "model_file": "urgency_logreg.pkl",
        "tfidf_vectorizer_file": "urgency_tfidf_vectorizer.pkl",
        "feature_space": "full 30000-dim TF-IDF",
        "decision_threshold": 0.15,
        "default_threshold": 0.5,
        "test_macro_f1_at_default_threshold": 0.9431,
        "test_macro_f1_at_deployed_threshold": 0.8981,
        "threshold_rationale": (
            "0.15 chosen over the default 0.5 to prioritize suicide-class recall "
            "(0.987 vs 0.934) for a safety-net layer, at the cost of precision "
            "(0.840 vs 0.952). See Step 10's README for the full sweep."
        ),
    },
    "curated_urgency_keywords_file": "curated_urgency_keywords.json",
    "emotion_lexicon_file": "emotion_lexicon.json",
    "provenance_caveat": (
        "Both models are trained on proxy labels (subreddit of origin), not "
        "clinician-verified diagnoses. Outputs are a screening signal, not a "
        "diagnosis -- see the paper-details doc's Limitations section (items 53-56)."
    ),
}

with open(OUT, "w") as f:
    json.dump(config, f, indent=2)
print(f"Wrote {OUT}")
print(f"handcrafted_feature_order: {len(primary_feat_cols)} features")
