"""
Step 2 follow-up check.

The main EDA script (eda_raw_datasets.py) flagged that Emotion_Sentiment_DataSet.csv
is 83.6% internal duplicates. This script checks whether those duplicates (and the
unique texts that remain) also overlap with Combined Data.csv -- i.e. whether the
same underlying posts show up in more than one of our "different" source files.
This matters directly for Step 3: if we don't de-dup GLOBALLY across files before
building the unified dataset and the train/test split, the same post can leak
across both files and both sides of a split.
"""
import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "datasets" / "text datasets"

df1 = pd.read_csv(f"{DATA_DIR}/Combined Data.csv")
df3 = pd.read_csv(f"{DATA_DIR}/Emotion_Sentiment_DataSet.csv")

s1 = set(df1["statement"].astype(str).str.strip())
s3 = set(df3["Text"].astype(str).str.strip())

overlap = s1 & s3
print("unique texts in Combined Data.csv:", len(s1))
print("unique texts in Emotion_Sentiment_DataSet.csv:", len(s3))
print("exact-text overlap between the two files:", len(overlap))
print(f"overlap as % of Combined Data unique texts: {len(overlap)/len(s1)*100:.2f}%")
print(f"overlap as % of Emotion unique texts: {len(overlap)/len(s3)*100:.2f}%")

df3_dedup = df3.drop_duplicates(subset=["Text"])
print()
print("Emotion_Sentiment_DataSet.csv AFTER internal de-dup:", len(df3_dedup), "rows")
print(df3_dedup["Emotion"].value_counts())
