"""
Step 10 -- confusion matrix plots for the paper's Results section (item 43).
Reads the JSON results evaluate_test.py already produced; draws nothing new,
just visualizes what's already computed.
"""
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "Step 10 - Evaluation" / "output"


def plot_cm(cm, labels, title, out_path, normalize=True):
    cm = np.array(cm, dtype=float)
    if normalize:
        cm_norm = cm / cm.sum(axis=1, keepdims=True)
    else:
        cm_norm = cm
    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 1.1), max(5, len(labels) * 1.0)))
    im = ax.imshow(cm_norm, cmap="Blues", vmin=0, vmax=1 if normalize else cm.max())
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(title)
    for i in range(len(labels)):
        for j in range(len(labels)):
            val = cm[i, j]
            frac = cm_norm[i, j]
            color = "white" if frac > 0.5 else "black"
            ax.text(j, i, f"{int(val)}\n({frac*100:.0f}%)", ha="center", va="center",
                    color=color, fontsize=8)
    fig.colorbar(im, ax=ax, label="row-normalized proportion" if normalize else "count")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"saved {out_path}", flush=True)


primary = json.load(open(f"{OUT_DIR}/primary_dataset_test_results.json"))
plot_cm(primary["confusion_matrix"], primary["labels_order"],
        "primary_dataset (test) — XGBoost", f"{OUT_DIR}/primary_dataset_confusion_matrix.png")

urgency = json.load(open(f"{OUT_DIR}/urgency_dataset_test_results.json"))
plot_cm(urgency["default_threshold_0.5"]["confusion_matrix"], urgency["labels_order"],
        "urgency_dataset (test) — Logistic Regression, threshold=0.5",
        f"{OUT_DIR}/urgency_dataset_confusion_matrix_default.png")
plot_cm(urgency["recommended_threshold_results"]["confusion_matrix"], urgency["labels_order"],
        f"urgency_dataset (test) — Logistic Regression, threshold={urgency['recommended_threshold']}",
        f"{OUT_DIR}/urgency_dataset_confusion_matrix_recommended.png")

print("DONE", flush=True)
