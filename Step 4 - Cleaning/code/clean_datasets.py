"""
Step 4 -- Cleaning.

Runs on the two Step 3 outputs (primary_dataset.csv, urgency_dataset.csv).
Step 3 already removed empty text and exact duplicates (required before the
split). This step handles everything else: junk markers, URL/username/subreddit
stripping, emoji-to-text conversion, unicode normalization, a light PII scrub,
and a language-likelihood filter. Every removal/change is counted so the effect
of cleaning is auditable, not silent.
"""
import pandas as pd
import numpy as np
import re
import ftfy
import emoji
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
IN_DIR = REPO_ROOT / "Step 3 - Unified Dataset" / "output"
OUT_DIR = REPO_ROOT / "Step 4 - Cleaning" / "output"

# ---------- regex patterns ----------
URL_RE = re.compile(r"http\S+|www\.\S+")
REDDIT_USER_RE = re.compile(r"/?u/[A-Za-z0-9_-]+")
REDDIT_SUB_RE = re.compile(r"/?r/[A-Za-z0-9_-]+")
TWITTER_MENTION_RE = re.compile(r"@\w+")
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"\b(\+?\d{1,2}[\s.-]?)?(\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b")
JUNK_MARKER_RE = re.compile(r"^\s*\[(removed|deleted)\]\s*$", re.IGNORECASE)
MULTI_WS_RE = re.compile(r"\s+")
GLUED_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")  # e.g. "anymoreI'm" -> "anymore I'm"

ENGLISH_STOPWORDS = set("""the a an is are was were be been being to of and in on for with
that this it as at by from or but not have has had do does did i you he she we they
my your his her our their me him them what which who whom this these those am""".split())


def word_tokens(s):
    return re.findall(r"[a-zA-Z']+", str(s).lower())


def english_ratio(s):
    toks = word_tokens(s)
    if not toks:
        return 0.0
    hits = sum(1 for t in toks if t in ENGLISH_STOPWORDS)
    return hits / len(toks)


def clean_text(s):
    s = ftfy.fix_text(s)                          # unicode/mojibake normalization
    s = GLUED_BOUNDARY_RE.sub(" ", s)              # split title/body glued together with no separator
    s = URL_RE.sub(" ", s)
    s = REDDIT_USER_RE.sub(" ", s)
    s = REDDIT_SUB_RE.sub(" ", s)
    s = TWITTER_MENTION_RE.sub(" ", s)
    s = EMAIL_RE.sub(" ", s)
    s = PHONE_RE.sub(" ", s)
    s = emoji.demojize(s, delimiters=(" :", ": "))  # emoji -> text description, not deleted
    s = s.replace("_", " ")                         # "smiling_face" -> "smiling face"
    s = MULTI_WS_RE.sub(" ", s).strip()
    return s


def clean_dataset(name, text_col="text", label_col="label"):
    path = f"{IN_DIR}/{name}"
    df = pd.read_csv(path)
    n0 = len(df)

    # 1. drop junk markers (guard -- Step 2 found 0, but re-check post-Step-3)
    junk_mask = df[text_col].astype(str).str.match(JUNK_MARKER_RE)
    n_junk = int(junk_mask.sum())
    df = df[~junk_mask]

    # 2. clean text (unicode fix, strip urls/mentions/subs/emails/phones, emoji->text)
    df[text_col] = df[text_col].astype(str).apply(clean_text)

    # 3. drop rows that became empty after cleaning
    empty_after = df[text_col].str.strip() == ""
    n_empty_after = int(empty_after.sum())
    df = df[~empty_after]

    # 4. drop exact duplicates that may have been CREATED by cleaning
    #    (e.g. two posts that only differed by a URL are now identical)
    dup_after = df[text_col].duplicated(keep="first")
    n_dup_after = int(dup_after.sum())
    df = df[~dup_after]

    # 5. language-likelihood heuristic (documented limitation: no compiled
    #    langdetect library available in this environment; using the same
    #    stopword-overlap heuristic validated in Step 2 as a stand-in).
    ratios = df[text_col].apply(english_ratio)
    likely_non_english = ratios == 0.0
    n_flagged = int(likely_non_english.sum())
    # flagged, not dropped outright -- see README for reasoning
    df["likely_non_english"] = likely_non_english

    n_final = len(df)
    print(f"\n--- {name} ---")
    print(f"rows in: {n0:,}")
    print(f"  dropped junk markers:          {n_junk:,}")
    print(f"  dropped empty after cleaning:  {n_empty_after:,}")
    print(f"  dropped dupes created by clean:{n_dup_after:,}")
    print(f"rows out: {n_final:,}")
    print(f"  flagged likely_non_english (kept, not dropped): {n_flagged:,} ({n_flagged/n_final*100:.2f}%)")
    print(f"label distribution after cleaning:")
    print(df[label_col].value_counts())

    return df


primary = clean_dataset("primary_dataset.csv", text_col="text", label_col="label")
primary.to_csv(f"{OUT_DIR}/primary_dataset_clean.csv", index=False)

urgency = clean_dataset("urgency_dataset.csv", text_col="text", label_col="label")
urgency.to_csv(f"{OUT_DIR}/urgency_dataset_clean.csv", index=False)

print("\nDONE")
