"""
Step 3 -- Build the unified, split dataset(s).

Design decision (see Step 3 README for full reasoning): Combined Data.csv and
Suicide_Detection.csv are NOT merged row-wise into one multi-class table. Instead:

  1. primary_dataset.csv   -- the 7-class training set, built from Combined Data.csv
                              only. Suicide_Detection.csv's "non-suicide" class has no
                              honest mapping onto Normal/Depression/etc, so merging it
                              in would inject mislabeled rows into the primary target.
  2. urgency_dataset.csv   -- the binary urgency/crisis safety-net set, built from
                              Suicide_Detection.csv only (suicide / non-suicide).

Both go through the same minimal steps needed before a valid split can happen:
drop empty/NaN text, drop exact-duplicate text (keep first occurrence), then a
stratified 80/10/10 train/val/test split. Neither file has an author/user id column,
so a true no-leakage-by-author split isn't possible here -- de-duplicating exact
text first is the mitigation, documented as a known limitation.
"""
import pandas as pd
from sklearn.model_selection import train_test_split
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "datasets" / "text datasets"
OUT_DIR = REPO_ROOT / "Step 3 - Unified Dataset" / "output"

RANDOM_STATE = 42


def clean_and_split(df, text_col, label_col, source_name):
    n0 = len(df)
    df = df[[text_col, label_col]].rename(columns={text_col: "text", label_col: "label"})

    # drop empty / NaN text
    df["text"] = df["text"].astype(str)
    df = df[df["text"].str.strip() != ""]
    df = df.dropna(subset=["text", "label"])
    n1 = len(df)

    # drop exact duplicate text, keep first occurrence
    df = df.drop_duplicates(subset=["text"], keep="first")
    n2 = len(df)

    df["source_dataset"] = source_name

    # stratified 80/10/10 split
    train, temp = train_test_split(
        df, test_size=0.20, random_state=RANDOM_STATE, stratify=df["label"]
    )
    val, test = train_test_split(
        temp, test_size=0.50, random_state=RANDOM_STATE, stratify=temp["label"]
    )
    train = train.copy(); train["split"] = "train"
    val = val.copy(); val["split"] = "val"
    test = test.copy(); test["split"] = "test"
    out = pd.concat([train, val, test], ignore_index=True)

    print(f"\n--- {source_name} ---")
    print(f"raw rows: {n0:,} -> after dropping empty/NaN: {n1:,} -> after dropping exact dupes: {n2:,}")
    print(f"final split sizes: train={len(train):,} val={len(val):,} test={len(test):,}")
    print("label distribution (overall, post-clean):")
    print(out["label"].value_counts())
    print("\nlabel distribution by split (row counts):")
    print(pd.crosstab(out["label"], out["split"]))

    return out


# ---------- 1. Primary 7-class dataset (Combined Data.csv only) ----------
df_combined = pd.read_csv(f"{DATA_DIR}/Combined Data.csv")
primary = clean_and_split(df_combined, "statement", "status", "Combined Data.csv")
primary["urgency_flag"] = (primary["label"] == "Suicidal").astype(int)
primary = primary[["text", "label", "urgency_flag", "source_dataset", "split"]]
primary.to_csv(f"{OUT_DIR}/primary_dataset.csv", index=False)
print(f"\nSaved primary_dataset.csv -> {len(primary):,} rows")

# ---------- 2. Urgency / crisis binary dataset (Suicide_Detection.csv only) ----------
df_suicide = pd.read_csv(f"{DATA_DIR}/Suicide_Detection.csv/Suicide_Detection.csv")
urgency = clean_and_split(df_suicide, "text", "class", "Suicide_Detection.csv")
urgency = urgency[["text", "label", "source_dataset", "split"]]
urgency.to_csv(f"{OUT_DIR}/urgency_dataset.csv", index=False)
print(f"\nSaved urgency_dataset.csv -> {len(urgency):,} rows")

print("\nDONE")
