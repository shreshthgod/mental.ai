"""
Step 7a -- Build a word -> emotion-class association lexicon from
Emotion_Sentiment_DataSet.csv, for use as an extra feature signal on
primary_dataset and urgency_dataset (NOT as training rows -- Step 2 already
found this dataset is 51.6% exact-duplicate of Combined Data.csv's content
and its 10-class label scheme doesn't map onto our 7 target classes, so it
was excluded from training rows back in Step 1/3).

LEAKAGE GUARD: Emotion_Sentiment_DataSet.csv shares two label names with our
scheme ("Normal", "Depression") and thousands of exact-duplicate texts with
Combined Data.csv (the source of primary_dataset). If the lexicon were built
from those duplicate rows and then applied as a feature back onto
primary_dataset, rows that are exact text duplicates would get a
near-perfect, memorized "feature" instead of a generalizable one. Fixed by
excluding, before building the lexicon, every Emotion_Sentiment_DataSet.csv
row whose raw text exactly matches a raw primary_dataset (Combined Data.csv)
or urgency_dataset (Suicide_Detection.csv) text.

Method: for each of the 10 Emotion classes, compute a per-word "P(class |
word)" distribution (word must appear >= MIN_COUNT times total, add-1
smoothed) across all 10 classes. This is a continuous lexicon (not just a
top-K word list) -- feature_engineering.py mean-pools it over the words in a
given post to get a 10-dim "emotion association" feature vector.
"""
import re
import json
from collections import Counter, defaultdict
import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "datasets" / "text datasets"
STEP3_DIR = REPO_ROOT / "Step 3 - Unified Dataset" / "output"
OUT_DIR = REPO_ROOT / "Step 7 - Feature Extraction" / "output"

WORD_RE = re.compile(r"[a-z']+")
MIN_COUNT = 5


def tokenize(s):
    return WORD_RE.findall(str(s).lower())


print("Loading raw files...")
emotion = pd.read_csv(f"{RAW_DIR}/Emotion_Sentiment_DataSet.csv")
combined = pd.read_csv(f"{RAW_DIR}/Combined Data.csv")
suicide = pd.read_csv(f"{RAW_DIR}/Suicide_Detection.csv/Suicide_Detection.csv")

# find the text columns (same approach as Step 2's overlap check)
combined_text_col = "statement" if "statement" in combined.columns else combined.columns[1]
suicide_text_col = "text" if "text" in suicide.columns else suicide.columns[1]

n0 = len(emotion)
combined_texts = set(combined[combined_text_col].astype(str))
suicide_texts = set(suicide[suicide_text_col].astype(str))
overlap_mask = emotion["Text"].astype(str).isin(combined_texts) | emotion["Text"].astype(str).isin(suicide_texts)
n_overlap = int(overlap_mask.sum())
emotion = emotion[~overlap_mask]
print(f"Emotion_Sentiment_DataSet.csv: {n0:,} rows -> excluded {n_overlap:,} "
      f"({n_overlap/n0*100:.1f}%) that exactly match a primary/urgency raw text "
      f"-> {len(emotion):,} rows used to build the lexicon")

classes = sorted(emotion["Emotion"].unique())
print(f"Classes: {classes}")

# word -> Counter(class -> count)
word_class_counts = defaultdict(Counter)
for text, cls in zip(emotion["Text"].astype(str), emotion["Emotion"]):
    for w in set(tokenize(text)):  # count each word once per doc (presence, not frequency)
        word_class_counts[w][cls] += 1

n_vocab_total = len(word_class_counts)
lexicon = {}
for w, counts in word_class_counts.items():
    total = sum(counts.values())
    if total < MIN_COUNT:
        continue
    lexicon[w] = {c: (counts.get(c, 0) + 1) / (total + len(classes)) for c in classes}

print(f"Vocabulary: {n_vocab_total:,} words seen, {len(lexicon):,} kept "
      f"(total doc-count >= {MIN_COUNT})")

with open(f"{OUT_DIR}/emotion_lexicon.json", "w") as f:
    json.dump({"classes": classes, "min_count": MIN_COUNT, "lexicon": lexicon}, f)

# a few sanity-check examples
print("\nSanity check -- P(class | word) for a few emotionally-loaded words:")
for w in ["hopeless", "kill", "love", "worthless", "happy", "scared", "angry"]:
    if w in lexicon:
        top = sorted(lexicon[w].items(), key=lambda x: -x[1])[:3]
        print(f"  {w:<12} {top}")
    else:
        print(f"  {w:<12} (not in lexicon -- below min_count)")

print("\nDONE")
