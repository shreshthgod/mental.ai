"""
Step 5 -- Text preprocessing.

Runs on the two Step 4 outputs. Per row:
  1. Expand contractions ("don't" -> "do not") BEFORE tokenizing, so negation
     words end up as their own token rather than fused into a contraction.
  2. Lowercase + tokenize (NLTK word_tokenize).
  3. POS-tag (batched via pos_tag_sents -- much faster than per-row pos_tag)
     and lemmatize each token with its POS, so "running"/"ran" -> "run" etc.
  4. Drop tokens that are pure punctuation (they contribute nothing to a
     bag-of-words/TF-IDF vocabulary; punctuation-PATTERN features like
     exclamation-mark count or ALL-CAPS ratio are computed in Step 7 from the
     Step 4 cleaned text, not from this token list, so nothing is lost).

Deliberately NOT done here: stopword removal. Negation words ("no", "not",
"never") and pronouns ("I", "me", "my") are signal for this task, and standard
stopword lists remove them -- so no blanket stopword filter is applied at all.
If a curated vocabulary needs pruning later, Step 7's TF-IDF min_df/max_df
does that without needing a hand-picked stopword list.

Writes text_lemmatized (space-joined lemmas) as a new column alongside the
existing cleaned `text` column (kept for reference / feature extraction).
"""
import sys
import time
import pandas as pd
import contractions
from nltk import word_tokenize
from nltk.tag import pos_tag_sents
from nltk.stem import WordNetLemmatizer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IN_DIR = REPO_ROOT / "Step 4 - Cleaning" / "output"
OUT_DIR = REPO_ROOT / "Step 5 - Text Preprocessing" / "output"

LEM = WordNetLemmatizer()
BATCH = 2000
CHECKPOINT_EVERY = 10  # batches (=20,000 rows) -- avoids losing all progress on a crash
CONTRACTIONS_FAILURES = []  # (row_index, text) where contractions.fix() itself errored


def safe_fix(s):
    """contractions.fix() (via the textsearch lib) can raise IndexError on
    certain rare edge-case strings (hit in practice on ~row 126,000 of the
    232k-row urgency_dataset -- a textsearch bounds-check bug, not something
    wrong with our data). Falls back to the original, un-expanded string
    rather than crashing the whole multi-hundred-thousand-row job; the
    failure is logged for the audit trail rather than silently swallowed."""
    try:
        return contractions.fix(s)
    except Exception as e:
        CONTRACTIONS_FAILURES.append((s, repr(e)))
        return s


def wn_pos(tag):
    if tag.startswith("J"):
        return "a"
    if tag.startswith("V"):
        return "v"
    if tag.startswith("R"):
        return "r"
    return "n"


def is_word(tok):
    return any(ch.isalnum() for ch in tok)


def preprocess_series(texts, label="", df=None, out_path=None):
    n = len(texts)
    out = [None] * n
    t_start = time.time()
    for batch_i, start in enumerate(range(0, n, BATCH)):
        end = min(start + BATCH, n)
        chunk = texts[start:end]
        expanded = [safe_fix(str(s)) for s in chunk]
        tok_lists = [word_tokenize(s.lower()) for s in expanded]
        tagged_lists = pos_tag_sents(tok_lists)
        for i, tagged in enumerate(tagged_lists):
            lemmas = [LEM.lemmatize(w, wn_pos(t)) for w, t in tagged if is_word(w)]
            out[start + i] = " ".join(lemmas)
        elapsed = time.time() - t_start
        rate = (end) / elapsed if elapsed > 0 else 0
        eta = (n - end) / rate if rate > 0 else float("inf")
        print(f"[{label}] {end}/{n} rows ({end/n*100:.1f}%) "
              f"elapsed={elapsed:.0f}s rate={rate:.1f} rows/s eta={eta:.0f}s", flush=True)
        # checkpoint: save partial progress every CHECKPOINT_EVERY batches so a
        # crash (e.g. the textsearch bug above, or anything else) doesn't waste
        # everything computed so far -- large background jobs on 2 CPUs run for
        # 10+ minutes and this dataset alone already crashed once mid-run.
        if df is not None and out_path is not None and (batch_i + 1) % CHECKPOINT_EVERY == 0:
            partial = df.iloc[:end].copy()
            partial["text_lemmatized"] = out[:end]
            partial.to_csv(out_path + ".partial", index=False)
            print(f"[{label}] checkpoint saved at {end}/{n} rows", flush=True)
    return out


def run(name):
    print(f"=== {name} ===", flush=True)
    CONTRACTIONS_FAILURES.clear()
    df = pd.read_csv(f"{IN_DIR}/{name}")
    out_path = f"{OUT_DIR}/{name.replace('.csv', '')}_preprocessed.csv"
    df["text_lemmatized"] = preprocess_series(
        df["text"].astype(str).tolist(), label=name, df=df, out_path=out_path
    )
    df.to_csv(out_path, index=False)
    import os
    if os.path.exists(out_path + ".partial"):
        os.remove(out_path + ".partial")
    print(f"Saved {out_path} ({len(df):,} rows)", flush=True)
    if CONTRACTIONS_FAILURES:
        fail_path = f"{OUT_DIR}/{name.replace('.csv', '')}_contractions_failures.txt"
        with open(fail_path, "w", encoding="utf-8") as f:
            for s, err in CONTRACTIONS_FAILURES:
                f.write(f"{err}\t{s}\n")
        print(f"[{name}] {len(CONTRACTIONS_FAILURES)} row(s) fell back to un-expanded "
              f"text after a contractions.fix() error -- see {fail_path}", flush=True)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "both"
    if target in ("primary", "both"):
        run("primary_dataset_clean.csv")
    if target in ("urgency", "both"):
        run("urgency_dataset_clean.csv")
    print("DONE", flush=True)
