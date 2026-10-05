"""
Step 7b -- Classical/handcrafted feature extraction.

Runs on Step 5's preprocessed outputs (needs both `text` -- Step 4 cleaned,
case/punctuation intact -- and `text_lemmatized` -- Step 5's tokenized,
POS-lemmatized, still-has-negation/pronouns text). Produces one row of
numeric features per input row; label/split/urgency_flag columns are carried
through unchanged so this file can be joined straight back to the dataset.

Feature groups (see README for the full rationale on each):
  1. Stylistic / surface features (from `text`, since lemmatizing lowercases
     and drops punctuation) -- length, exclamation/question marks, ALL-CAPS
     ratio, repeated punctuation runs.
  2. VADER sentiment (from `text` -- VADER is tuned for real punctuation and
     case, so this deliberately does NOT use the lemmatized text).
  3. Readability (Flesch reading ease + grade level, from `text`).
  4. Pronoun ratio, negation count, absolutist-word ratio (from
     `text_lemmatized` tokens -- these are exactly the signals Step 5 kept
     stopwords around FOR).
  5. NRC Word-Emotion Association lexicon frequencies (8 emotions + 2
     sentiments), looked up directly against `text_lemmatized` tokens --
     bypasses NRCLex's own (slow, TextBlob-based) tokenizer/lemmatizer since
     Step 5 already did that job.
  6. Custom emotion-association lexicon built in Step 7a from
     Emotion_Sentiment_DataSet.csv (leakage-guarded -- see
     build_emotion_lexicon.py), mean-pooled over `text_lemmatized` tokens.
  7. Curated urgency-keyword count + flag, from Step 6's curated list.
"""
import sys
import json
import re
import time
import pandas as pd
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import textstat
from nrclex import NRCLex
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IN_DIR = REPO_ROOT / "Step 5 - Text Preprocessing" / "output"
KEYWORDS_PATH = REPO_ROOT / "Step 6 - EDA on Cleaned Data" / "findings" / "urgency_keyword_candidates.json"
LEXICON_PATH = REPO_ROOT / "Step 7 - Feature Extraction" / "output" / "emotion_lexicon.json"
GARBAGE_PATH = REPO_ROOT / "Step 6 - EDA on Cleaned Data" / "findings" / "garbage_flagged_rows.csv"
OUT_DIR = REPO_ROOT / "Step 7 - Feature Extraction" / "output"

# Step 6 already identified and audited these rows as spam/filler (see that
# step's README) -- excluded here from the actual feature matrices used for
# modeling, per that step's stated plan. Matched by exact text, not
# recomputed, so this can never drift from Step 6's already-reviewed list.
_garbage_df = pd.read_csv(GARBAGE_PATH)
GARBAGE_TEXTS = {
    "primary_dataset_clean_preprocessed.csv": set(
        _garbage_df.loc[_garbage_df["dataset"] == "primary_dataset", "text"].astype(str)
    ),
    "urgency_dataset_clean_preprocessed.csv": set(
        _garbage_df.loc[_garbage_df["dataset"] == "urgency_dataset", "text"].astype(str)
    ),
}

# ---------- shared resources (loaded once) ----------
SIA = SentimentIntensityAnalyzer()
NRC_LEXICON = NRCLex().__lexicon__  # {word: [emotion, ...]}
NRC_CATEGORIES = ["fear", "anger", "anticipation", "trust", "surprise",
                   "positive", "negative", "sadness", "disgust", "joy"]

with open(KEYWORDS_PATH) as f:
    URGENCY_KEYWORDS = set(json.load(f)["curated_urgency_keywords"])

with open(LEXICON_PATH) as f:
    _emo = json.load(f)
    EMO_CLASSES = _emo["classes"]
    EMO_LEXICON = _emo["lexicon"]

PRONOUNS = {"i", "me", "my", "mine", "myself"}
NEGATIONS = {"not", "no", "never", "none", "nobody", "nothing", "neither", "nor", "n't", "cannot"}
ABSOLUTIST = {"always", "never", "completely", "entirely", "totally", "all", "none",
              "every", "everyone", "everybody", "everything", "nothing", "definitely",
              "must", "constantly", "forever", "whole", "full", "fully"}

EXCLAIM_RE = re.compile(r"!")
QUESTION_RE = re.compile(r"\?")
ELLIPSIS_RE = re.compile(r"\.\.\.|…")
REPEAT_PUNCT_RE = re.compile(r"([!?])\1{1,}")  # "!!" "???" etc
WORD_SPLIT_RE = re.compile(r"\S+")


def stylistic_features(text):
    words = WORD_SPLIT_RE.findall(text)
    n_words = len(words) or 1
    caps_words = sum(1 for w in words if len(w) >= 2 and w.isupper())
    return {
        "char_count": len(text),
        "word_count": len(words),
        "avg_word_len": sum(len(w) for w in words) / n_words,
        "exclam_count": len(EXCLAIM_RE.findall(text)),
        "question_count": len(QUESTION_RE.findall(text)),
        "ellipsis_count": len(ELLIPSIS_RE.findall(text)),
        "all_caps_ratio": caps_words / n_words,
        "repeated_punct_count": len(REPEAT_PUNCT_RE.findall(text)),
    }


def vader_features(text):
    s = SIA.polarity_scores(text)
    return {"vader_neg": s["neg"], "vader_neu": s["neu"], "vader_pos": s["pos"], "vader_compound": s["compound"]}


def readability_features(text):
    try:
        return {
            "flesch_reading_ease": textstat.flesch_reading_ease(text),
            "flesch_kincaid_grade": textstat.flesch_kincaid_grade(text),
        }
    except Exception:
        return {"flesch_reading_ease": 0.0, "flesch_kincaid_grade": 0.0}


def token_features(tokens):
    n = len(tokens) or 1
    tok_set_counts = {}
    pronoun_n = sum(1 for t in tokens if t in PRONOUNS)
    negation_n = sum(1 for t in tokens if t in NEGATIONS)
    absolutist_n = sum(1 for t in tokens if t in ABSOLUTIST)

    # NRC lexicon: count category hits across matched tokens, normalize by
    # total matched-category hits (same definition as NRCLex.affect_frequencies)
    nrc_hits = []
    for t in tokens:
        if t in NRC_LEXICON:
            nrc_hits.extend(NRC_LEXICON[t])
    nrc_total = len(nrc_hits) or 1
    nrc_counts = {c: 0 for c in NRC_CATEGORIES}
    for c in nrc_hits:
        nrc_counts[c] += 1
    nrc_feats = {f"nrc_{c}": nrc_counts[c] / nrc_total for c in NRC_CATEGORIES}

    # custom emotion lexicon: mean-pool P(class|word) over matched tokens
    emo_sums = {c: 0.0 for c in EMO_CLASSES}
    emo_matched = 0
    for t in tokens:
        if t in EMO_LEXICON:
            emo_matched += 1
            for c in EMO_CLASSES:
                emo_sums[c] += EMO_LEXICON[t][c]
    emo_denom = emo_matched or 1
    emo_feats = {f"emo_lex_{c}": emo_sums[c] / emo_denom for c in EMO_CLASSES}

    urgency_hits = sum(1 for t in tokens if t in URGENCY_KEYWORDS)

    out = {
        "pronoun_ratio": pronoun_n / n,
        "negation_count": negation_n,
        "absolutist_ratio": absolutist_n / n,
        "urgency_keyword_count": urgency_hits,
        "urgency_keyword_flag": int(urgency_hits > 0),
    }
    out.update(nrc_feats)
    out.update(emo_feats)
    return out


def extract_all(text, text_lemmatized):
    tokens = str(text_lemmatized).split()
    row = {}
    row.update(stylistic_features(str(text)))
    row.update(vader_features(str(text)))
    row.update(readability_features(str(text)))
    row.update(token_features(tokens))
    return row


def run(name, carry_cols):
    print(f"=== {name} ===", flush=True)
    df = pd.read_csv(f"{IN_DIR}/{name}")
    n0 = len(df)
    garbage_texts = GARBAGE_TEXTS.get(name, set())
    is_garbage_row = df["text"].astype(str).isin(garbage_texts)
    n_dropped = int(is_garbage_row.sum())
    df = df[~is_garbage_row].reset_index(drop=True)
    print(f"[{name}] dropping {n_dropped:,}/{n0:,} rows flagged as spam/filler by "
          f"Step 6's is_garbage() audit -> {len(df):,} rows remain", flush=True)
    n = len(df)
    t0 = time.time()
    records = []
    # fillna BEFORE astype(str): a handful of rows lemmatize down to an empty
    # string (e.g. raw text that was pure punctuation, like "?????"), which
    # round-trips through CSV as a true missing value, not the string "nan" --
    # astype(str) alone on pandas' newer string dtype leaves it NA rather than
    # stringifying it, and str(<NA>) would otherwise produce a spurious "nan"
    # token that can spuriously match a lexicon entry.
    text_col = df["text"].fillna("").astype(str)
    lem_col = df["text_lemmatized"].fillna("").astype(str)
    for i, (text, lem) in enumerate(zip(text_col, lem_col)):
        records.append(extract_all(text, lem))
        if (i + 1) % 20000 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (n - i - 1) / rate
            print(f"[{name}] {i+1}/{n} ({(i+1)/n*100:.1f}%) elapsed={elapsed:.0f}s "
                  f"rate={rate:.0f} rows/s eta={eta:.0f}s", flush=True)
    feat_df = pd.DataFrame(records)
    for col in carry_cols:
        feat_df[col] = df[col].values
    out_path = f"{OUT_DIR}/{name.replace('.csv', '')}_handcrafted_features.csv.gz"
    feat_df.to_csv(out_path, index=False, compression="gzip")
    print(f"Saved {out_path} ({len(feat_df):,} rows, {feat_df.shape[1]} cols) "
          f"in {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "both"
    if target in ("primary", "both"):
        run("primary_dataset_clean_preprocessed.csv",
            carry_cols=["label", "split", "urgency_flag", "source_dataset", "likely_non_english"])
    if target in ("urgency", "both"):
        run("urgency_dataset_clean_preprocessed.csv",
            carry_cols=["label", "split", "source_dataset", "likely_non_english"])
    print("DONE", flush=True)
