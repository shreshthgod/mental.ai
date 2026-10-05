"""
Step 9 -- shared data loading for all training scripts.

Loads Step 7's saved feature matrices (TF-IDF .npz + handcrafted features
.csv.gz) and Step 8's class weights, for one dataset ("primary" or
"urgency"). Row alignment between the handcrafted-feature CSV and the
per-split TF-IDF .npz files was verified before this step started (both
scripts in Step 7 read the same Step-5 source file, apply the identical
Step-6 garbage-row exclusion, and never reorder rows -- confirmed by
matching row counts per split for both datasets).
"""
import json
import pickle
import numpy as np
import pandas as pd
import scipy.sparse as sp
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FEAT_DIR = REPO_ROOT / "Step 7 - Feature Extraction" / "output"
WEIGHTS_PATH = REPO_ROOT / "Step 8 - Class Imbalance Handling" / "output" / "class_weights.json"

DATASETS = {
    "primary": {
        "name": "primary_dataset",
        "features_csv": f"{FEAT_DIR}/primary_dataset_clean_preprocessed_handcrafted_features.csv.gz",
        "label_col": "label",
        "classes": ["Normal", "Depression", "Suicidal", "Anxiety", "Bipolar",
                    "Stress", "Personality disorder"],
    },
    "urgency": {
        "name": "urgency_dataset",
        "features_csv": f"{FEAT_DIR}/urgency_dataset_clean_preprocessed_handcrafted_features.csv.gz",
        "label_col": "label",
        "classes": ["non-suicide", "suicide"],
    },
}

# handcrafted feature columns == everything except carry-through columns
NON_FEATURE_COLS = {"label", "split", "urgency_flag", "source_dataset", "likely_non_english"}


def load_handcrafted(dataset_key):
    cfg = DATASETS[dataset_key]
    df = pd.read_csv(cfg["features_csv"])
    feat_cols = [c for c in df.columns if c not in NON_FEATURE_COLS]
    return df, feat_cols


def load_tfidf(dataset_key, split):
    cfg = DATASETS[dataset_key]
    return sp.load_npz(f"{FEAT_DIR}/{cfg['name']}_tfidf_{split}.npz")


def load_vectorizer(dataset_key):
    cfg = DATASETS[dataset_key]
    with open(f"{FEAT_DIR}/{cfg['name']}_tfidf_vectorizer.pkl", "rb") as f:
        return pickle.load(f)


def load_class_weights(dataset_key):
    cfg = DATASETS[dataset_key]
    with open(WEIGHTS_PATH) as f:
        all_weights = json.load(f)
    return all_weights[cfg["name"]]["class_weights_train"]


def splits_for(dataset_key, df):
    """Return boolean masks (train, val, test) aligned to df's row order."""
    return (df["split"] == "train").values, (df["split"] == "val").values, (df["split"] == "test").values


def labels_for(dataset_key, df, mask):
    cfg = DATASETS[dataset_key]
    return df.loc[mask, cfg["label_col"]].values
