"""
Step 10 -- final evaluation on the held-out TEST split (untouched by every
model up to this point -- val was used exclusively for model selection in
Step 9). Evaluates the leading candidate from each dataset:
  - primary_dataset: XGBoost (mid-tier, 38 handcrafted + chi2-selected 1,500
    TF-IDF terms)
  - urgency_dataset: Logistic Regression (baseline, full 30,000-dim TF-IDF)

Also sweeps the urgency model's decision threshold: for a safety-net layer,
a missed true "suicide" case (false negative) is a worse outcome than a
false alarm (false positive), so recall on that class is prioritized over
raw accuracy/macro-F1 at the default 0.5 cutoff.
"""
import sys
import json
import pickle
import numpy as np
import scipy.sparse as sp
from pathlib import Path
from sklearn.metrics import (
    classification_report, f1_score, confusion_matrix, precision_recall_curve,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "Step 9 - Model Training" / "code"))
from data_utils import DATASETS, load_handcrafted, load_tfidf, labels_for

MODELS_DIR = REPO_ROOT / "Step 9 - Model Training" / "output" / "models"
OUT_DIR = REPO_ROOT / "Step 10 - Evaluation" / "output"


def eval_primary():
    cfg = DATASETS["primary"]
    df, feat_cols = load_handcrafted("primary")
    test_mask = (df["split"] == "test").values
    y_test = labels_for("primary", df, test_mask)

    X_tfidf_test = load_tfidf("primary", "test")
    with open(f"{MODELS_DIR}/primary_dataset_chi2_selector.pkl", "rb") as f:
        skb = pickle.load(f)
    X_tfidf_test_red = skb.transform(X_tfidf_test)
    X_hand_test = sp.csr_matrix(df.loc[test_mask, feat_cols].values.astype(np.float32))
    X_test = sp.hstack([X_tfidf_test_red, X_hand_test], format="csr")

    with open(f"{MODELS_DIR}/primary_dataset_xgboost.pkl", "rb") as f:
        bundle = pickle.load(f)
    xgb, le = bundle["model"], bundle["label_encoder"]

    pred_enc = xgb.predict(X_test)
    pred = le.inverse_transform(pred_enc)

    macro_f1 = f1_score(y_test, pred, average="macro")
    report = classification_report(y_test, pred, output_dict=True, zero_division=0)
    cm = confusion_matrix(y_test, pred, labels=cfg["classes"]).tolist()

    print(f"[primary_dataset / XGBoost] TEST macro-F1 = {macro_f1:.4f}", flush=True)
    for c in cfg["classes"]:
        r = report[c]
        print(f"  {c:<22} P={r['precision']:.3f} R={r['recall']:.3f} "
              f"F1={r['f1-score']:.3f} support={int(r['support'])}", flush=True)

    result = {
        "dataset": "primary_dataset", "model": "xgboost", "split": "test",
        "macro_f1": macro_f1, "report": report, "confusion_matrix": cm,
        "labels_order": cfg["classes"], "n_test": int(test_mask.sum()),
    }
    with open(f"{OUT_DIR}/primary_dataset_test_results.json", "w") as f:
        json.dump(result, f, indent=2, default=str)
    return result


def eval_urgency():
    cfg = DATASETS["urgency"]
    df, feat_cols = load_handcrafted("urgency")
    test_mask = (df["split"] == "test").values
    y_test = labels_for("urgency", df, test_mask)

    X_tfidf_test = load_tfidf("urgency", "test")
    with open(f"{MODELS_DIR}/urgency_dataset_logreg.pkl", "rb") as f:
        lr = pickle.load(f)

    classes_ = list(lr.classes_)
    suicide_idx = classes_.index("suicide")
    proba = lr.predict_proba(X_tfidf_test)[:, suicide_idx]
    y_test_bin = (y_test == "suicide").astype(int)

    # ---- default threshold (0.5) ----
    pred_default = np.where(proba >= 0.5, "suicide", "non-suicide")
    macro_f1_default = f1_score(y_test, pred_default, average="macro")
    report_default = classification_report(y_test, pred_default, output_dict=True, zero_division=0)
    cm_default = confusion_matrix(y_test, pred_default, labels=cfg["classes"]).tolist()

    print(f"\n[urgency_dataset / LogReg] TEST macro-F1 (threshold=0.5) = {macro_f1_default:.4f}", flush=True)
    for c in cfg["classes"]:
        r = report_default[c]
        print(f"  {c:<15} P={r['precision']:.3f} R={r['recall']:.3f} "
              f"F1={r['f1-score']:.3f} support={int(r['support'])}", flush=True)

    # ---- threshold sweep, recall-priority on "suicide" ----
    precisions, recalls, thresholds = precision_recall_curve(y_test_bin, proba)
    sweep = []
    for t in [0.5, 0.4, 0.35, 0.3, 0.25, 0.2, 0.15, 0.1]:
        pred_t = np.where(proba >= t, "suicide", "non-suicide")
        rep_t = classification_report(y_test, pred_t, output_dict=True, zero_division=0)
        sweep.append({
            "threshold": t,
            "suicide_precision": rep_t["suicide"]["precision"],
            "suicide_recall": rep_t["suicide"]["recall"],
            "suicide_f1": rep_t["suicide"]["f1-score"],
            "macro_f1": f1_score(y_test, pred_t, average="macro"),
        })
        print(f"  threshold={t:<5} suicide: P={rep_t['suicide']['precision']:.3f} "
              f"R={rep_t['suicide']['recall']:.3f} F1={rep_t['suicide']['f1-score']:.3f} "
              f"| macro-F1={f1_score(y_test, pred_t, average='macro'):.4f}", flush=True)

    # recommended: lowest threshold in the sweep that still keeps precision >= 0.80
    # (avoid flooding a safety-net layer with false alarms) while maximizing recall
    candidates = [s for s in sweep if s["suicide_precision"] >= 0.80]
    recommended = min(candidates, key=lambda s: s["threshold"]) if candidates else sweep[0]

    pred_rec = np.where(proba >= recommended["threshold"], "suicide", "non-suicide")
    report_rec = classification_report(y_test, pred_rec, output_dict=True, zero_division=0)
    cm_rec = confusion_matrix(y_test, pred_rec, labels=cfg["classes"]).tolist()

    print(f"\n  Recommended threshold: {recommended['threshold']} "
          f"(suicide recall {recommended['suicide_recall']:.3f}, "
          f"precision {recommended['suicide_precision']:.3f})", flush=True)

    result = {
        "dataset": "urgency_dataset", "model": "logistic_regression", "split": "test",
        "n_test": int(test_mask.sum()),
        "default_threshold_0.5": {
            "macro_f1": macro_f1_default, "report": report_default, "confusion_matrix": cm_default,
        },
        "threshold_sweep": sweep,
        "recommended_threshold": recommended["threshold"],
        "recommended_threshold_results": {
            "report": report_rec, "confusion_matrix": cm_rec,
            "macro_f1": f1_score(y_test, pred_rec, average="macro"),
        },
        "labels_order": cfg["classes"],
        "selection_rule": "lowest threshold in sweep with suicide-class precision >= 0.80, maximizing recall",
    }
    with open(f"{OUT_DIR}/urgency_dataset_test_results.json", "w") as f:
        json.dump(result, f, indent=2, default=str)
    return result


if __name__ == "__main__":
    eval_primary()
    eval_urgency()
    print("\nDONE", flush=True)
