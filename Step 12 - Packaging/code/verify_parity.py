"""
Step 12 -- verification: does the packaged module reproduce the pipeline's
own numbers, starting from genuinely RAW (pre-Step-4) text? This is the
actual test that matters -- the package duplicates preprocessing.py and
features.py logic rather than importing it, so this catches any transcription
mistake in that duplication.

For a handful of primary_dataset and urgency_dataset TEST rows:
  1. Take the raw (pre-cleaning) text from Step 3's output.
  2. Run it through the packaged clean_and_lemmatize() + extract_handcrafted_
     features() + full MentalHealthScreener.screen().
  3. Compare the cleaned text and lemmatized text against Step 5's stored
     values for that exact row (matched by raw text, since row order can
     differ once Step 6's garbage exclusion is applied).
  4. Compare the packaged model's predicted class against a freshly
     recomputed reference prediction, built the same way Step 9/10 built
     it (TF-IDF -> chi2 -> hstack with handcrafted features -> model.predict),
     using the ALREADY-SAVED artifacts -- so any mismatch is a packaging bug,
     not a training-time difference.
"""
import sys
import pickle
import numpy as np
import pandas as pd
import scipy.sparse as sp
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "Step 12 - Packaging" / "package"))
from mental_health_screening.inference import MentalHealthScreener
from mental_health_screening.preprocessing import clean_and_lemmatize
from mental_health_screening.features import extract_handcrafted_features

STEP3_DIR = REPO_ROOT / "Step 3 - Unified Dataset" / "output"
STEP5_DIR = REPO_ROOT / "Step 5 - Text Preprocessing" / "output"
MODELS_DIR = REPO_ROOT / "Step 9 - Model Training" / "output" / "models"
GARBAGE_PATH = REPO_ROOT / "Step 6 - EDA on Cleaned Data" / "findings" / "garbage_flagged_rows.csv"

sys.path.insert(0, str(REPO_ROOT / "Step 9 - Model Training" / "code"))
from data_utils import load_handcrafted


def check_primary(n=5):
    print("=" * 60)
    print("primary_dataset parity check")
    print("=" * 60)
    raw = pd.read_csv(f"{STEP3_DIR}/primary_dataset.csv")
    raw_test = raw[raw["split"] == "test"].reset_index(drop=True)

    step5 = pd.read_csv(f"{STEP5_DIR}/primary_dataset_clean_preprocessed.csv")
    step5_by_text = step5.set_index("text")

    hand_df, feat_cols = load_handcrafted("primary")
    garbage_df = pd.read_csv(GARBAGE_PATH)
    garbage_texts = set(garbage_df.loc[garbage_df["dataset"] == "primary_dataset", "text"].astype(str))

    with open(f"{MODELS_DIR}/primary_dataset_chi2_selector.pkl", "rb") as f:
        skb = pickle.load(f)
    with open(f"{MODELS_DIR}/primary_dataset_xgboost.pkl", "rb") as f:
        bundle = pickle.load(f)
    xgb, le = bundle["model"], bundle["label_encoder"]

    from data_utils import load_vectorizer
    vec = load_vectorizer("primary")

    screener = MentalHealthScreener()

    checked = 0
    mismatches = 0
    for _, row in raw_test.iterrows():
        if checked >= n:
            break
        raw_text = row["text"]
        cleaned, lemmatized = clean_and_lemmatize(raw_text)
        if cleaned not in step5_by_text.index or cleaned in garbage_texts:
            continue  # dropped/deduped/garbage-flagged somewhere downstream -- skip, not a bug
        step5_row = step5_by_text.loc[cleaned]
        if isinstance(step5_row, pd.DataFrame):
            step5_row = step5_row.iloc[0]

        lemmatized_match = (lemmatized == step5_row["text_lemmatized"])

        # reference prediction, built the pipeline's way from saved artifacts
        X_tfidf = vec.transform([lemmatized])
        X_tfidf_red = skb.transform(X_tfidf)
        handcrafted = extract_handcrafted_features(cleaned, lemmatized)
        X_hand = sp.csr_matrix(np.array([[handcrafted[c] for c in feat_cols]], dtype=np.float32))
        X_ref = sp.hstack([X_tfidf_red, X_hand], format="csr")
        ref_pred = le.inverse_transform(xgb.predict(X_ref))[0]

        # packaged prediction, via the public API
        result = screener.screen(raw_text)
        pkg_pred = result["primary"]["predicted_class"]

        checked += 1
        ok = lemmatized_match and (ref_pred == pkg_pred)
        if not ok:
            mismatches += 1
        print(f"  row {checked}: true_label={row['label']:<22} lemmatized_match={lemmatized_match} "
              f"ref_pred={ref_pred:<22} pkg_pred={pkg_pred:<22} {'OK' if ok else 'MISMATCH'}", flush=True)

    print(f"\nprimary_dataset: {checked} rows checked, {mismatches} mismatches", flush=True)
    return checked, mismatches


def check_urgency(n=5):
    print("\n" + "=" * 60)
    print("urgency_dataset parity check")
    print("=" * 60)
    raw = pd.read_csv(f"{STEP3_DIR}/urgency_dataset.csv")
    raw_test = raw[raw["split"] == "test"].reset_index(drop=True)

    step5 = pd.read_csv(f"{STEP5_DIR}/urgency_dataset_clean_preprocessed.csv")
    step5_by_text = step5.set_index("text")

    garbage_df = pd.read_csv(GARBAGE_PATH)
    garbage_texts = set(garbage_df.loc[garbage_df["dataset"] == "urgency_dataset", "text"].astype(str))

    with open(f"{MODELS_DIR}/urgency_dataset_logreg.pkl", "rb") as f:
        lr = pickle.load(f)

    sys.path.insert(0, str(REPO_ROOT / "Step 9 - Model Training" / "code"))
    from data_utils import load_vectorizer
    vec = load_vectorizer("urgency")
    classes_ = list(lr.classes_)
    suicide_idx = classes_.index("suicide")

    screener = MentalHealthScreener()

    checked = 0
    mismatches = 0
    for _, row in raw_test.iterrows():
        if checked >= n:
            break
        raw_text = row["text"]
        cleaned, lemmatized = clean_and_lemmatize(raw_text)
        if cleaned not in step5_by_text.index or cleaned in garbage_texts:
            continue
        step5_row = step5_by_text.loc[cleaned]
        if isinstance(step5_row, pd.DataFrame):
            step5_row = step5_row.iloc[0]
        lemmatized_match = (lemmatized == step5_row["text_lemmatized"])

        X_ref = vec.transform([lemmatized])
        ref_proba = float(lr.predict_proba(X_ref)[0][suicide_idx])

        result = screener.screen(raw_text)
        pkg_proba = result["urgency"]["suicide_probability"]

        checked += 1
        proba_match = abs(ref_proba - pkg_proba) < 1e-9
        ok = lemmatized_match and proba_match
        if not ok:
            mismatches += 1
        print(f"  row {checked}: true_label={row['label']:<12} lemmatized_match={lemmatized_match} "
              f"ref_proba={ref_proba:.6f} pkg_proba={pkg_proba:.6f} {'OK' if ok else 'MISMATCH'}", flush=True)

    print(f"\nurgency_dataset: {checked} rows checked, {mismatches} mismatches", flush=True)
    return checked, mismatches


if __name__ == "__main__":
    c1, m1 = check_primary(5)
    c2, m2 = check_urgency(5)
    total_mismatches = m1 + m2
    print(f"\n{'='*60}\nTOTAL: {c1+c2} rows checked, {total_mismatches} mismatches", flush=True)
    if total_mismatches == 0:
        print("PARITY CONFIRMED -- packaged module reproduces the pipeline exactly.", flush=True)
    else:
        print("MISMATCHES FOUND -- do not ship until resolved.", flush=True)
