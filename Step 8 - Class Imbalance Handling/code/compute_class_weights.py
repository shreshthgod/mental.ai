"""
Step 8 -- Class imbalance handling.

Decision (see README for full reasoning): use inverse-frequency CLASS
WEIGHTING at training time as the primary strategy, not SMOTE and not
undersampling/capping the majority class. Weights are computed from the
TRAIN split only (never val/test -- those must stay at the natural
distribution so evaluation reflects real-world class frequencies).

Formula (identical to sklearn's class_weight="balanced"):
    weight(c) = n_train_samples / (n_classes * count(c))
This gives every class equal total influence on the loss regardless of its
raw frequency, without touching a single row of data or duplicating/
inventing any text.
"""
import json
import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FEATURES_DIR = REPO_ROOT / "Step 7 - Feature Extraction" / "output"
OUT_DIR = REPO_ROOT / "Step 8 - Class Imbalance Handling" / "output"


def compute_weights(name, label_col="label"):
    df = pd.read_csv(f"{FEATURES_DIR}/{name}")
    train = df[df["split"] == "train"]
    counts = train[label_col].value_counts().to_dict()
    n = len(train)
    n_classes = len(counts)
    weights = {c: round(n / (n_classes * cnt), 4) for c, cnt in counts.items()}

    print(f"\n=== {name} (train split, n={n:,}, {n_classes} classes) ===")
    for c in sorted(counts, key=lambda x: -counts[x]):
        print(f"  {c:<25} count={counts[c]:<8,} weight={weights[c]}")

    return {
        "dataset": name,
        "n_train": n,
        "n_classes": n_classes,
        "class_counts_train": counts,
        "class_weights_train": weights,
        "formula": "n_train_samples / (n_classes * count(c)) -- sklearn 'balanced' scheme",
    }


primary_info = compute_weights("primary_dataset_clean_preprocessed_handcrafted_features.csv.gz")
urgency_info = compute_weights("urgency_dataset_clean_preprocessed_handcrafted_features.csv.gz")

with open(f"{OUT_DIR}/class_weights.json", "w") as f:
    json.dump({"primary_dataset": primary_info, "urgency_dataset": urgency_info}, f, indent=2)

print("\nSaved output/class_weights.json")
print("DONE")
