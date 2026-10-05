"""
Step 9a -- baseline models: Logistic Regression + Linear SVM, TF-IDF only,
class-weighted (Step 8 weights). Run for both primary_dataset (7-class) and
urgency_dataset (binary). Evaluated on val (test is held out for the final
model-selection step, per Step 10's plan).
"""
import sys
import json
import time
import pickle
import numpy as np
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.metrics import classification_report, f1_score, confusion_matrix

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "Step 9 - Model Training" / "code"))
from data_utils import DATASETS, load_handcrafted, load_tfidf, load_class_weights, labels_for

OUT_DIR = REPO_ROOT / "Step 9 - Model Training" / "output"


def run(dataset_key):
    cfg = DATASETS[dataset_key]
    print(f"\n{'='*60}\n{cfg['name']} -- baselines\n{'='*60}", flush=True)

    df, _ = load_handcrafted(dataset_key)
    train_mask = (df["split"] == "train").values
    val_mask = (df["split"] == "val").values
    y_train = labels_for(dataset_key, df, train_mask)
    y_val = labels_for(dataset_key, df, val_mask)

    X_train = load_tfidf(dataset_key, "train")
    X_val = load_tfidf(dataset_key, "val")
    class_weights = load_class_weights(dataset_key)
    print(f"train: {X_train.shape}, val: {X_val.shape}, class_weights: {class_weights}", flush=True)

    results = {}

    # ---- Logistic Regression ----
    t0 = time.time()
    lr = LogisticRegression(
        max_iter=1000, class_weight=class_weights, solver="lbfgs" if len(cfg["classes"]) > 2 else "liblinear",
        n_jobs=-1 if len(cfg["classes"]) > 2 else None,
    )
    lr.fit(X_train, y_train)
    pred = lr.predict(X_val)
    macro_f1 = f1_score(y_val, pred, average="macro")
    report = classification_report(y_val, pred, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_val, pred, labels=cfg["classes"]).tolist()
    elapsed = time.time() - t0
    print(f"[LogReg] macro-F1={macro_f1:.4f} ({elapsed:.0f}s)", flush=True)
    results["logistic_regression"] = {
        "macro_f1_val": macro_f1, "report_val": report, "confusion_matrix_val": cm,
        "labels_order": cfg["classes"], "train_seconds": elapsed,
        "params": lr.get_params(),
    }
    with open(f"{OUT_DIR}/models/{cfg['name']}_logreg.pkl", "wb") as f:
        pickle.dump(lr, f)

    # ---- Linear SVM ----
    t0 = time.time()
    svm = LinearSVC(class_weight=class_weights, max_iter=5000)
    svm.fit(X_train, y_train)
    pred = svm.predict(X_val)
    macro_f1 = f1_score(y_val, pred, average="macro")
    report = classification_report(y_val, pred, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_val, pred, labels=cfg["classes"]).tolist()
    elapsed = time.time() - t0
    print(f"[LinearSVM] macro-F1={macro_f1:.4f} ({elapsed:.0f}s)", flush=True)
    results["linear_svm"] = {
        "macro_f1_val": macro_f1, "report_val": report, "confusion_matrix_val": cm,
        "labels_order": cfg["classes"], "train_seconds": elapsed,
        "params": {k: str(v) for k, v in svm.get_params().items()},
    }
    with open(f"{OUT_DIR}/models/{cfg['name']}_linear_svm.pkl", "wb") as f:
        pickle.dump(svm, f)

    with open(f"{OUT_DIR}/metrics/{cfg['name']}_baselines.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Saved {OUT_DIR}/metrics/{cfg['name']}_baselines.json", flush=True)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "both"
    if target in ("primary", "both"):
        run("primary")
    if target in ("urgency", "both"):
        run("urgency")
    print("\nDONE", flush=True)
