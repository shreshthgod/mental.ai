"""
Step 11a -- manual error analysis on Step 10's TEST-set predictions.

Pulls the actual misclassified text (not just the confusion matrix numbers)
so mistakes can be read, not just counted. Re-derives the row set exactly
the way Step 7's feature_engineering.py did (same source file, same Step 6
garbage-row exclusion, no reordering) so it lines up 1:1 with the
handcrafted-feature rows scored in Step 10 -- verified below with an assert
before trusting the join.
"""
import sys
import json
import pickle
import numpy as np
import pandas as pd
import scipy.sparse as sp
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "Step 9 - Model Training" / "code"))
from data_utils import DATASETS, load_handcrafted, load_tfidf, labels_for

STEP5_DIR = REPO_ROOT / "Step 5 - Text Preprocessing" / "output"
GARBAGE_PATH = REPO_ROOT / "Step 6 - EDA on Cleaned Data" / "findings" / "garbage_flagged_rows.csv"
MODELS_DIR = REPO_ROOT / "Step 9 - Model Training" / "output" / "models"
OUT_DIR = REPO_ROOT / "Step 11 - Explainability and Error Analysis" / "output" / "error_analysis"

STEP5_FILE = {
    "primary": "primary_dataset_clean_preprocessed.csv",
    "urgency": "urgency_dataset_clean_preprocessed.csv",
}
GARBAGE_KEY = {"primary": "primary_dataset", "urgency": "urgency_dataset"}


def load_text_aligned(dataset_key):
    """Reproduce feature_engineering.py's row set/order exactly, keeping `text`."""
    df = pd.read_csv(f"{STEP5_DIR}/{STEP5_FILE[dataset_key]}")
    garbage_df = pd.read_csv(GARBAGE_PATH)
    garbage_texts = set(
        garbage_df.loc[garbage_df["dataset"] == GARBAGE_KEY[dataset_key], "text"].astype(str)
    )
    is_garbage = df["text"].astype(str).isin(garbage_texts)
    df = df[~is_garbage].reset_index(drop=True)
    return df


def analyze_primary():
    cfg = DATASETS["primary"]
    hand_df, feat_cols = load_handcrafted("primary")
    text_df = load_text_aligned("primary")
    assert len(hand_df) == len(text_df), "row count mismatch -- alignment assumption broken"
    assert (hand_df["label"].values == text_df["label"].values).all(), "label mismatch -- alignment assumption broken"
    assert (hand_df["split"].values == text_df["split"].values).all(), "split mismatch -- alignment assumption broken"

    test_mask = (hand_df["split"] == "test").values
    y_test = labels_for("primary", hand_df, test_mask)
    texts_test = text_df.loc[test_mask, "text"].values

    X_tfidf_test = load_tfidf("primary", "test")
    with open(f"{MODELS_DIR}/primary_dataset_chi2_selector.pkl", "rb") as f:
        skb = pickle.load(f)
    X_tfidf_test_red = skb.transform(X_tfidf_test)
    X_hand_test = sp.csr_matrix(hand_df.loc[test_mask, feat_cols].values.astype(np.float32))
    X_test = sp.hstack([X_tfidf_test_red, X_hand_test], format="csr")

    with open(f"{MODELS_DIR}/primary_dataset_xgboost.pkl", "rb") as f:
        bundle = pickle.load(f)
    xgb, le = bundle["model"], bundle["label_encoder"]
    pred = le.inverse_transform(xgb.predict(X_test))

    wrong = pred != y_test
    err_df = pd.DataFrame({
        "true_label": y_test[wrong], "predicted_label": pred[wrong], "text": texts_test[wrong],
    })
    err_df.to_csv(f"{OUT_DIR}/primary_dataset_misclassified.csv", index=False)

    # confusion pairs, ranked by frequency
    pair_counts = err_df.groupby(["true_label", "predicted_label"]).size().reset_index(name="count")
    pair_counts = pair_counts.sort_values("count", ascending=False)
    pair_counts.to_csv(f"{OUT_DIR}/primary_dataset_confusion_pairs.csv", index=False)

    print(f"primary_dataset: {wrong.sum()}/{len(y_test)} test rows misclassified "
          f"({wrong.mean()*100:.1f}%)", flush=True)
    print("Top confusion pairs:", flush=True)
    for _, row in pair_counts.head(10).iterrows():
        print(f"  true={row['true_label']:<22} pred={row['predicted_label']:<22} count={row['count']}", flush=True)

    # a few concrete examples from the two weakest classes
    examples = {}
    for weak_class in ["Stress", "Personality disorder"]:
        sub = err_df[err_df["true_label"] == weak_class].head(3)
        examples[weak_class] = sub.to_dict(orient="records")
    with open(f"{OUT_DIR}/primary_dataset_example_misses.json", "w") as f:
        json.dump(examples, f, indent=2, default=str)


def analyze_urgency(threshold=0.15):
    cfg = DATASETS["urgency"]
    hand_df, feat_cols = load_handcrafted("urgency")
    text_df = load_text_aligned("urgency")
    assert len(hand_df) == len(text_df), "row count mismatch -- alignment assumption broken"
    assert (hand_df["label"].values == text_df["label"].values).all(), "label mismatch -- alignment assumption broken"
    assert (hand_df["split"].values == text_df["split"].values).all(), "split mismatch -- alignment assumption broken"

    test_mask = (hand_df["split"] == "test").values
    y_test = labels_for("urgency", hand_df, test_mask)
    texts_test = text_df.loc[test_mask, "text"].values

    X_tfidf_test = load_tfidf("urgency", "test")
    with open(f"{MODELS_DIR}/urgency_dataset_logreg.pkl", "rb") as f:
        lr = pickle.load(f)
    classes_ = list(lr.classes_)
    suicide_idx = classes_.index("suicide")
    proba = lr.predict_proba(X_tfidf_test)[:, suicide_idx]
    pred = np.where(proba >= threshold, "suicide", "non-suicide")

    false_neg_mask = (y_test == "suicide") & (pred == "non-suicide")
    false_pos_mask = (y_test == "non-suicide") & (pred == "suicide")

    fn_df = pd.DataFrame({
        "text": texts_test[false_neg_mask], "suicide_probability": proba[false_neg_mask],
    }).sort_values("suicide_probability")
    fp_df = pd.DataFrame({
        "text": texts_test[false_pos_mask], "suicide_probability": proba[false_pos_mask],
    }).sort_values("suicide_probability", ascending=False)

    fn_df.to_csv(f"{OUT_DIR}/urgency_dataset_false_negatives_at_{threshold}.csv", index=False)
    fp_df.to_csv(f"{OUT_DIR}/urgency_dataset_false_positives_at_{threshold}.csv", index=False)

    print(f"\nurgency_dataset (threshold={threshold}): {false_neg_mask.sum()} false negatives "
          f"(missed real suicide posts), {false_pos_mask.sum()} false positives", flush=True)
    print("Lowest-probability false negatives (most confidently wrong):", flush=True)
    for _, row in fn_df.head(3).iterrows():
        snippet = row["text"][:150].replace("\n", " ")
        print(f"  p={row['suicide_probability']:.3f}  \"{snippet}...\"", flush=True)


if __name__ == "__main__":
    analyze_primary()
    analyze_urgency()
    print("\nDONE", flush=True)
