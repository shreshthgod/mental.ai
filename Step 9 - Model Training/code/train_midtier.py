"""
Step 9b -- mid-tier models: Random Forest + XGBoost.

Feature representation: 38 handcrafted features + a REDUCED TF-IDF
representation (chi2-selected top 1,500 terms out of the full 30,000-term
vocabulary, fit on train only), hstacked sparse -> 1,538 dims.

Why reduced, not the full 30,038 dims used in the paper-details doc's
"if concatenated as-is" note: empirically timed on this sandbox's actual
hardware (2 vCPUs, no GPU -- see item 33 in the paper-details doc) before
committing to a setting. At the full 30k width, XGBoost's histogram-based
tree construction scaled to an estimated ~25-45 minutes PER MODEL PER
DATASET on this hardware (measured: 1.49s/boosting-round at depth 6 with
just 1,500 features; the full-width equivalent was over 10x slower per
round in a direct side-by-side timing test). That's not a fundamental
limitation of the method, just of this box, so it was cut down: chi2
feature selection keeps the terms most statistically associated with the
label (same idea Step 6 used for the curated keyword list, applied here to
the full vocabulary instead of a hand-curated subset). Documented here per
the standing latitude to adjust dataset/feature composition for
feasibility, as long as it's written down.

Random Forest via native `class_weight`; XGBoost via explicit per-row
`sample_weight` (sklearn's XGBClassifier has no `class_weight` argument).
"""
import sys
import json
import time
import pickle
import numpy as np
import scipy.sparse as sp
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, f1_score, confusion_matrix
from xgboost import XGBClassifier

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "Step 9 - Model Training" / "code"))
from data_utils import DATASETS, load_handcrafted, load_tfidf, load_class_weights, labels_for

OUT_DIR = REPO_ROOT / "Step 9 - Model Training" / "output"
CHI2_K = 1500
RF_N_ESTIMATORS = 150
XGB_N_ESTIMATORS = 200


def run(dataset_key, which="both"):
    cfg = DATASETS[dataset_key]
    print(f"\n{'='*60}\n{cfg['name']} -- mid-tier\n{'='*60}", flush=True)

    df, feat_cols = load_handcrafted(dataset_key)
    train_mask = (df["split"] == "train").values
    val_mask = (df["split"] == "val").values
    y_train = labels_for(dataset_key, df, train_mask)
    y_val = labels_for(dataset_key, df, val_mask)

    X_tfidf_train = load_tfidf(dataset_key, "train")
    X_tfidf_val = load_tfidf(dataset_key, "val")

    t0 = time.time()
    le_chi2 = LabelEncoder()
    y_train_for_chi2 = le_chi2.fit_transform(y_train)
    skb = SelectKBest(chi2, k=CHI2_K)
    X_tfidf_train_red = skb.fit_transform(X_tfidf_train, y_train_for_chi2)
    X_tfidf_val_red = skb.transform(X_tfidf_val)
    print(f"chi2 selection: 30,000 -> {CHI2_K} terms ({time.time()-t0:.1f}s)", flush=True)
    with open(f"{OUT_DIR}/models/{cfg['name']}_chi2_selector.pkl", "wb") as f:
        pickle.dump(skb, f)

    X_hand_train = sp.csr_matrix(df.loc[train_mask, feat_cols].values.astype(np.float32))
    X_hand_val = sp.csr_matrix(df.loc[val_mask, feat_cols].values.astype(np.float32))
    X_train = sp.hstack([X_tfidf_train_red, X_hand_train], format="csr")
    X_val = sp.hstack([X_tfidf_val_red, X_hand_val], format="csr")
    class_weights = load_class_weights(dataset_key)
    print(f"train: {X_train.shape}, val: {X_val.shape} "
          f"({len(feat_cols)} handcrafted + {CHI2_K} chi2-selected TF-IDF)", flush=True)

    sample_weight_train = np.array([class_weights[y] for y in y_train])
    metrics_path = f"{OUT_DIR}/metrics/{cfg['name']}_midtier.json"
    try:
        with open(metrics_path) as f:
            results = json.load(f)
    except FileNotFoundError:
        results = {}

    # ---- Random Forest ----
    if which in ("rf", "both"):
        t0 = time.time()
        rf = RandomForestClassifier(
            n_estimators=RF_N_ESTIMATORS, max_depth=30, min_samples_leaf=2,
            class_weight=class_weights, n_jobs=-1, random_state=42,
        )
        rf.fit(X_train, y_train)
        pred = rf.predict(X_val)
        macro_f1 = f1_score(y_val, pred, average="macro")
        report = classification_report(y_val, pred, output_dict=True, zero_division=0)
        cm = confusion_matrix(y_val, pred, labels=cfg["classes"]).tolist()
        elapsed = time.time() - t0
        print(f"[RandomForest] macro-F1={macro_f1:.4f} ({elapsed:.0f}s)", flush=True)
        results["random_forest"] = {
            "macro_f1_val": macro_f1, "report_val": report, "confusion_matrix_val": cm,
            "labels_order": cfg["classes"], "train_seconds": elapsed,
            "params": {"n_estimators": RF_N_ESTIMATORS, "max_depth": 30, "min_samples_leaf": 2,
                       "class_weight": class_weights, "random_state": 42,
                       "feature_dims": f"{len(feat_cols)} handcrafted + {CHI2_K} chi2-selected TF-IDF"},
        }
        with open(f"{OUT_DIR}/models/{cfg['name']}_random_forest.pkl", "wb") as f:
            pickle.dump(rf, f)
        with open(metrics_path, "w") as f:
            json.dump(results, f, indent=2, default=str)

    # ---- XGBoost ----
    if which in ("xgb", "both"):
        le = LabelEncoder()
        y_train_enc = le.fit_transform(y_train)
        y_val_enc = le.transform(y_val)
        t0 = time.time()
        xgb = XGBClassifier(
            n_estimators=XGB_N_ESTIMATORS, max_depth=6, learning_rate=0.1,
            tree_method="hist", n_jobs=-1, random_state=42,
            eval_metric="mlogloss" if len(cfg["classes"]) > 2 else "logloss",
        )
        xgb.fit(X_train, y_train_enc, sample_weight=sample_weight_train)
        pred_enc = xgb.predict(X_val)
        pred = le.inverse_transform(pred_enc)
        macro_f1 = f1_score(y_val, pred, average="macro")
        report = classification_report(y_val, pred, output_dict=True, zero_division=0)
        cm = confusion_matrix(y_val, pred, labels=cfg["classes"]).tolist()
        elapsed = time.time() - t0
        print(f"[XGBoost] macro-F1={macro_f1:.4f} ({elapsed:.0f}s)", flush=True)
        results["xgboost"] = {
            "macro_f1_val": macro_f1, "report_val": report, "confusion_matrix_val": cm,
            "labels_order": cfg["classes"], "train_seconds": elapsed,
            "params": {"n_estimators": XGB_N_ESTIMATORS, "max_depth": 6, "learning_rate": 0.1,
                       "tree_method": "hist", "random_state": 42, "class_weighting": "sample_weight",
                       "feature_dims": f"{len(feat_cols)} handcrafted + {CHI2_K} chi2-selected TF-IDF"},
        }
        with open(f"{OUT_DIR}/models/{cfg['name']}_xgboost.pkl", "wb") as f:
            pickle.dump({"model": xgb, "label_encoder": le}, f)

    with open(f"{OUT_DIR}/metrics/{cfg['name']}_midtier.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Saved {OUT_DIR}/metrics/{cfg['name']}_midtier.json", flush=True)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "primary"
    which = sys.argv[2] if len(sys.argv) > 2 else "both"
    run(target, which)
    print("\nDONE", flush=True)
