"""
Step 8b -- OPTIONAL secondary artifact: a modestly oversampled copy of
primary_dataset's TRAIN split, for Step 9 to A/B test against plain class
weighting (the primary, recommended strategy -- see README).

Method: duplicate-with-replacement (real existing rows, never synthetic/
invented text -- this is deliberately NOT SMOTE, see README for why).
Any class below TARGET_FRACTION of the majority class's count is
resampled-with-replacement up to that floor; classes already above it are
left untouched. TARGET_FRACTION=0.30 takes the imbalance ratio from 17.9:1
down to ~3.3:1 without fabricating a single word of text.

val/test are NEVER touched by this script -- oversampling a held-out split
would let the same duplicated row's text appear in both a training
signal and evaluation, which is a leakage risk with zero benefit (the
point of oversampling is only to change what the model sees during
training).

Every duplicated row is marked with is_oversampled_duplicate=True so this
is fully auditable/reversible, not a silent data change.
"""
import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IN_PATH = REPO_ROOT / "Step 7 - Feature Extraction" / "output" / "primary_dataset_clean_preprocessed_handcrafted_features.csv.gz"
OUT_PATH = REPO_ROOT / "Step 8 - Class Imbalance Handling" / "output" / "primary_dataset_train_oversampled.csv.gz"
TARGET_FRACTION = 0.30
SEED = 42

df = pd.read_csv(IN_PATH)
train = df[df["split"] == "train"].copy()
train["is_oversampled_duplicate"] = False

counts = train["label"].value_counts()
majority_n = counts.max()
floor_n = int(majority_n * TARGET_FRACTION)
print(f"train rows: {len(train):,} | majority class: {counts.idxmax()} ({majority_n:,}) "
      f"| oversample floor: {floor_n:,} ({TARGET_FRACTION:.0%} of majority)")

extra_parts = []
for label, cnt in counts.items():
    if cnt >= floor_n:
        print(f"  {label:<25} count={cnt:<8,} -> unchanged (already >= floor)")
        continue
    need = floor_n - cnt
    pool = train[train["label"] == label]
    extra = pool.sample(n=need, replace=True, random_state=SEED).copy()
    extra["is_oversampled_duplicate"] = True
    extra_parts.append(extra)
    print(f"  {label:<25} count={cnt:<8,} -> +{need:,} duplicated rows -> {cnt + need:,}")

oversampled_train = pd.concat([train] + extra_parts, ignore_index=True)
oversampled_train = oversampled_train.sample(frac=1, random_state=SEED).reset_index(drop=True)  # shuffle

new_counts = oversampled_train["label"].value_counts()
print(f"\nnew train size: {len(oversampled_train):,} "
      f"(was {len(train):,}, +{len(oversampled_train) - len(train):,} duplicated rows)")
print(f"new imbalance ratio: {new_counts.max() / new_counts.min():.1f} : 1 (was "
      f"{counts.max() / counts.min():.1f} : 1)")

oversampled_train.to_csv(OUT_PATH, index=False, compression="gzip")
print(f"\nSaved {OUT_PATH}")
print("DONE")
