"""
Step 7c -- TF-IDF vectorization.

Fits a TfidfVectorizer on the TRAIN split only (never val/test -- fitting on
the full dataset would leak val/test vocabulary statistics into training),
then transforms all three splits with that fitted vectorizer. Runs on Step
5's `text_lemmatized` column (already tokenizable on whitespace since Step 5
already lemmatized + dropped punctuation-only tokens).

unigrams + bigrams (bigrams catch negation-flipped phrases like "not happy"
that unigram TF-IDF would otherwise split into two separately-weighted,
less-informative tokens -- important since Step 5 deliberately kept
negation words in the vocabulary). min_df=5 / max_df=0.9 prune the
extremes (typos/one-offs and near-universal words) without a hand-picked
stopword list, consistent with Step 5's no-blanket-stopword-removal
decision.
"""
import sys
import pickle
import pandas as pd
import scipy.sparse as sp
from sklearn.feature_extraction.text import TfidfVectorizer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IN_DIR = REPO_ROOT / "Step 5 - Text Preprocessing" / "output"
GARBAGE_PATH = REPO_ROOT / "Step 6 - EDA on Cleaned Data" / "findings" / "garbage_flagged_rows.csv"
OUT_DIR = REPO_ROOT / "Step 7 - Feature Extraction" / "output"

# Same exclusion as feature_engineering.py -- see that file's comment. Matched
# by exact text against Step 6's already-reviewed audit list, not recomputed.
_garbage_df = pd.read_csv(GARBAGE_PATH)
GARBAGE_TEXTS = {
    "primary_dataset_clean_preprocessed.csv": set(
        _garbage_df.loc[_garbage_df["dataset"] == "primary_dataset", "text"].astype(str)
    ),
    "urgency_dataset_clean_preprocessed.csv": set(
        _garbage_df.loc[_garbage_df["dataset"] == "urgency_dataset", "text"].astype(str)
    ),
}


def run(name, max_features=30000):
    print(f"=== {name} ===", flush=True)
    df = pd.read_csv(f"{IN_DIR}/{name}")
    n0 = len(df)
    garbage_texts = GARBAGE_TEXTS.get(name, set())
    is_garbage_row = df["text"].astype(str).isin(garbage_texts)
    n_dropped = int(is_garbage_row.sum())
    df = df[~is_garbage_row].reset_index(drop=True)
    print(f"[{name}] dropping {n_dropped:,}/{n0:,} spam/filler rows (Step 6 audit) "
          f"-> {len(df):,} rows remain", flush=True)
    # fillna BEFORE astype(str) -- see feature_engineering.py's comment on the
    # same issue: a handful of rows lemmatize to an empty string, which
    # round-trips through CSV as a true missing value that astype(str) alone
    # does not stringify away on pandas' newer string dtype.
    texts = df["text_lemmatized"].fillna("").astype(str)
    splits = df["split"]

    train_mask = splits == "train"
    vec = TfidfVectorizer(
        ngram_range=(1, 2), min_df=5, max_df=0.9,
        max_features=max_features, sublinear_tf=True,
    )
    vec.fit(texts[train_mask])
    print(f"[{name}] vocabulary size: {len(vec.vocabulary_):,}", flush=True)

    base = name.replace("_clean_preprocessed.csv", "")
    for split_name in ("train", "val", "test"):
        mask = splits == split_name
        X = vec.transform(texts[mask])
        out_path = f"{OUT_DIR}/{base}_tfidf_{split_name}.npz"
        sp.save_npz(out_path, X)
        print(f"[{name}] {split_name}: {X.shape[0]:,} rows x {X.shape[1]:,} features "
              f"-> {out_path}", flush=True)

    with open(f"{OUT_DIR}/{base}_tfidf_vectorizer.pkl", "wb") as f:
        pickle.dump(vec, f)
    print(f"[{name}] saved vectorizer -> {OUT_DIR}/{base}_tfidf_vectorizer.pkl", flush=True)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "both"
    if target in ("primary", "both"):
        run("primary_dataset_clean_preprocessed.csv")
    if target in ("urgency", "both"):
        run("urgency_dataset_clean_preprocessed.csv")
    print("DONE", flush=True)
