"""
Step 6 -- EDA on cleaned data, and finalize the urgency-keyword list.

Uses:
  - primary_dataset_clean_preprocessed.csv (fully lemmatized -- ready)
  - urgency_dataset_clean.csv (Step 4 cleaned; NOT yet lemmatized at the time
    this was first run -- lemmatization for it was still running in the
    background. Word-frequency keyword mining works fine on cleaned-but-not-
    lemmatized text; it just won't merge word variants (e.g. "kill"/"killing"
    counted separately). Noted as a known gap, re-run once available.

Produces:
  - class distribution + text length stats (final, post-cleaning numbers)
  - top words per class
  - a data-driven urgency-keyword candidate list, built independently from
    BOTH primary_dataset's "Suicidal" class and urgency_dataset's "suicide"
    class, then cross-checked against each other
  - a sample of likely_non_english-flagged rows for manual review
"""
import re
import json
import pandas as pd
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PRIMARY_PATH = REPO_ROOT / "Step 5 - Text Preprocessing" / "output" / "primary_dataset_clean_preprocessed.csv"
URGENCY_PATH = REPO_ROOT / "Step 5 - Text Preprocessing" / "output" / "urgency_dataset_clean_preprocessed.csv"
OUT_DIR = REPO_ROOT / "Step 6 - EDA on Cleaned Data" / "findings"

WORD_RE = re.compile(r"[a-z']+")


def tokenize(s):
    return WORD_RE.findall(str(s).lower())


def class_distribution(df, label_col, text_col):
    lines = []
    n = len(df)
    lengths = df[text_col].astype(str).apply(lambda s: len(tokenize(s)))
    lines.append(f"rows: {n:,}")
    lines.append(f"word length -> mean:{lengths.mean():.1f} median:{lengths.median():.0f} p95:{lengths.quantile(0.95):.0f}")
    vc = df[label_col].value_counts()
    for k, v in vc.items():
        lines.append(f"  {k:<25} {v:>8,}  ({v/n*100:5.1f}%)")
    lines.append(f"  imbalance ratio (largest:smallest): {vc.max()/vc.min():.1f} : 1")
    return "\n".join(lines)


def top_words_per_class(df, label_col, text_col, top_n=20):
    out = {}
    for label, sub in df.groupby(label_col):
        counts = Counter()
        for s in sub[text_col].astype(str):
            counts.update(tokenize(s))
        out[label] = counts.most_common(top_n)
    return out


def distinctive_words(df, label_col, text_col, target_label, min_count=20, top_n=50):
    """Log-likelihood-ratio-style word distinctiveness: words common in
    `target_label` relative to everything else, with add-1 smoothing."""
    target = df[df[label_col] == target_label]
    rest = df[df[label_col] != target_label]

    target_counts = Counter()
    for s in target[text_col].astype(str):
        target_counts.update(tokenize(s))
    rest_counts = Counter()
    for s in rest[text_col].astype(str):
        rest_counts.update(tokenize(s))

    total_target = sum(target_counts.values())
    total_rest = sum(rest_counts.values())
    vocab = len(set(target_counts) | set(rest_counts))

    scores = []
    for w, c in target_counts.items():
        if c < min_count:
            continue
        p_target = (c + 1) / (total_target + vocab)
        p_rest = (rest_counts.get(w, 0) + 1) / (total_rest + vocab)
        ratio = p_target / p_rest
        scores.append((w, c, rest_counts.get(w, 0), ratio))
    scores.sort(key=lambda x: -x[3])
    return scores[:top_n]


RUN_RE = re.compile(r"(.)\1*")


def _longest_run_len(s):
    m = 0
    for run in RUN_RE.finditer(s):
        m = max(m, len(run.group(0)))
    return m


def _repeated_char_spam(s):
    """A single character repeated so much it dominates the whole text
    (e.g. a wall of '1's). Two-part condition on purpose: a first attempt
    that flagged any 15+ or 20+ char run caught a real ~1500-char crisis
    disclosure post (abuse/trafficking/suicidal ideation) purely because it
    contained "f**kkkkkkkkkkkkkkk...kkking" -- an emphatic elongated WORD
    inside an otherwise genuine, long sentence, not spam. Requiring the run
    to also be >50% of the (whitespace-stripped) text length means a long
    emphatic elongation embedded in real prose is not flagged, while a post
    that basically *is* the repeated character still is."""
    run = _longest_run_len(s)
    if run < 30:
        return False
    non_ws = re.sub(r"\s+", "", s)
    return bool(non_ws) and run / len(non_ws) > 0.5


def _repeated_word_spam(s):
    """A single word repeated so much it dominates the whole text (e.g.
    "Balls balls balls balls..."). Requires both a high share of repetition
    AND a minimum absolute repeat count, so a short genuine sentence that
    happens to reuse a word 2-3 times is never caught."""
    toks = re.findall(r"[a-zA-Z']+", s.lower())
    if len(toks) < 8:
        return False
    word, n = Counter(toks).most_common(1)[0]
    return n >= 6 and n / len(toks) > 0.4


def _non_latin_spam(s):
    """Heavy non-Latin-script content among the letters present (>40%) --
    catches phone-number-farming / non-English spam posts, independent of
    length or repetition."""
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return False
    non_latin = sum(1 for c in letters if not ("a" <= c.lower() <= "z"))
    return non_latin / len(letters) > 0.4


def is_garbage(s):
    """Conservative spam/garbage detector -- deliberately high bar so a
    genuinely distressed, emphatic post is never mistaken for spam (see
    _repeated_char_spam docstring for the false positive that shaped this).
    Three narrow, independent conditions; anything not caught by one of
    these stays in the dataset -- this is a spam filter, not a quality
    filter, so recall is intentionally sacrificed for precision. Known gap:
    non-repetitive symbol/binary spam (e.g. a wall of '01101000 01110100...'
    ASCII-binary) is NOT caught by any of these three conditions and slips
    through -- documented in the Step 6 README rather than chased further,
    since catching it would need pattern rules that risk false positives
    on real content again, for a data-quality issue affecting <0.5% of
    either dataset."""
    s = str(s)
    return _repeated_char_spam(s) or _repeated_word_spam(s) or _non_latin_spam(s)


report_lines = []

# ---------- primary_dataset ----------
primary = pd.read_csv(PRIMARY_PATH)
# a handful of rows lemmatize down to an empty string (raw text that was pure
# punctuation) and round-trip through CSV as a true missing value rather than
# the string "nan" -- fillna guards against a spurious "nan" token appearing
# in the word-frequency analysis.
primary["text_lemmatized"] = primary["text_lemmatized"].fillna("").astype(str)
report_lines.append("=" * 70)
report_lines.append("PRIMARY_DATASET (7-class) -- final class distribution")
report_lines.append("=" * 70)
report_lines.append(class_distribution(primary, "label", "text_lemmatized"))

report_lines.append("\nTop 15 words per class (lemmatized):")
top_primary = top_words_per_class(primary, "label", "text_lemmatized", top_n=15)
for label, words in top_primary.items():
    report_lines.append(f"  {label}: {', '.join(w for w, c in words)}")

report_lines.append("\nDistinctive words for 'Suicidal' vs rest of primary_dataset (lemmatized):")
suicidal_words = distinctive_words(primary, "label", "text_lemmatized", "Suicidal", min_count=20, top_n=50)
for w, c_t, c_r, ratio in suicidal_words[:30]:
    report_lines.append(f"  {w:<20} suicidal_count={c_t:<6} rest_count={c_r:<6} ratio={ratio:.1f}")

# ---------- urgency_dataset ----------
urgency = pd.read_csv(URGENCY_PATH)
urgency["text_lemmatized"] = urgency["text_lemmatized"].fillna("").astype(str)
report_lines.append("\n" + "=" * 70)
report_lines.append("URGENCY_DATASET (binary) -- final class distribution")
report_lines.append("(using Step 5 lemmatized text -- re-run after the urgency-dataset")
report_lines.append(" lemmatization background job completed)")
report_lines.append("=" * 70)
report_lines.append(class_distribution(urgency, "label", "text_lemmatized"))

report_lines.append("\nTop 15 words per class (lemmatized):")
top_urgency = top_words_per_class(urgency, "label", "text_lemmatized", top_n=15)
for label, words in top_urgency.items():
    report_lines.append(f"  {label}: {', '.join(w for w, c in words)}")

report_lines.append("\nDistinctive words for 'suicide' vs 'non-suicide' in urgency_dataset (lemmatized):")
suicide_words = distinctive_words(urgency, "label", "text_lemmatized", "suicide", min_count=50, top_n=50)
for w, c_t, c_r, ratio in suicide_words[:30]:
    report_lines.append(f"  {w:<20} suicide_count={c_t:<6} non_suicide_count={c_r:<6} ratio={ratio:.1f}")

# ---------- cross-check: words that show up as distinctive in BOTH datasets ----------
set_primary = {w for w, *_ in suicidal_words}
set_urgency = {w for w, *_ in suicide_words}
overlap = set_primary & set_urgency
report_lines.append("\n" + "=" * 70)
report_lines.append(f"CROSS-VALIDATED urgency keywords (distinctive in BOTH datasets independently): {len(overlap)}")
report_lines.append("=" * 70)
report_lines.append(", ".join(sorted(overlap)))

# ---------- curated keyword list: exclude slurs from the statistically-distinctive lists ----------
# Slurs show up as statistically "distinctive" for the suicide/Suicidal classes (they
# correlate with distress in this data) but are not clinically meaningful risk indicators
# and are inappropriate to ship in a keyword list. Excluded explicitly here, not silently.
SLUR_WORDS = {"retarded", "retard", "faggot", "tranny", "fag"}

curated_pool = set(overlap) | {w for w, *_ in suicidal_words} | {w for w, *_ in suicide_words}
excluded_slurs_found = sorted(SLUR_WORDS & curated_pool)
curated_urgency_keywords = sorted(curated_pool - SLUR_WORDS)

report_lines.append("\n" + "=" * 70)
report_lines.append(f"CURATED urgency keyword list (slurs excluded): {len(curated_urgency_keywords)} words")
report_lines.append(f"Excluded (statistically distinctive but not appropriate for a keyword list): {excluded_slurs_found}")
report_lines.append("=" * 70)
report_lines.append(", ".join(curated_urgency_keywords))

# ---------- garbage / spam detection (is_garbage) ----------
report_lines.append("\n" + "=" * 70)
report_lines.append("GARBAGE / SPAM DETECTION (is_garbage) -- row-drop recommendation")
report_lines.append("=" * 70)

primary_garbage_mask = primary["text"].apply(is_garbage)
urgency_garbage_mask = urgency["text"].apply(is_garbage)
n_primary_garbage = int(primary_garbage_mask.sum())
n_urgency_garbage = int(urgency_garbage_mask.sum())

report_lines.append(
    f"primary_dataset: {n_primary_garbage:,} / {len(primary):,} rows flagged "
    f"({n_primary_garbage/len(primary)*100:.3f}%)"
)
report_lines.append(
    f"urgency_dataset: {n_urgency_garbage:,} / {len(urgency):,} rows flagged "
    f"({n_urgency_garbage/len(urgency)*100:.3f}%)"
)
report_lines.append(
    "Not dropped here -- flagged rows saved to garbage_flagged_rows.csv for manual review "
    "(reversible, auditable). Step 7 (feature extraction) excludes flagged rows when "
    "building the training matrices."
)

flagged_out = []
for _, row in primary[primary_garbage_mask].iterrows():
    flagged_out.append({"dataset": "primary_dataset", "label": row["label"], "text": row["text"]})
for _, row in urgency[urgency_garbage_mask].iterrows():
    flagged_out.append({"dataset": "urgency_dataset", "label": row["label"], "text": row["text"]})
pd.DataFrame(flagged_out).to_csv(f"{OUT_DIR}/garbage_flagged_rows.csv", index=False)

with open(f"{OUT_DIR}/eda_cleaned_report.txt", "w") as f:
    f.write("\n".join(report_lines))

# save keyword candidates as structured JSON for Step 0's urgency safety net
keyword_candidates = {
    "cross_validated_single_words": sorted(overlap),
    "curated_urgency_keywords": curated_urgency_keywords,
    "excluded_slurs": excluded_slurs_found,
    "primary_dataset_suicidal_top_words": [w for w, *_ in suicidal_words],
    "urgency_dataset_suicide_top_words": [w for w, *_ in suicide_words],
}
with open(f"{OUT_DIR}/urgency_keyword_candidates.json", "w") as f:
    json.dump(keyword_candidates, f, indent=2)

# sample of likely_non_english rows for manual review
sample_flagged_primary = primary[primary.get("likely_non_english", False) == True].sample(
    min(15, (primary.get("likely_non_english", pd.Series(dtype=bool)) == True).sum()), random_state=1
) if "likely_non_english" in primary.columns else pd.DataFrame()
sample_flagged_urgency = urgency[urgency["likely_non_english"] == True].sample(
    min(15, (urgency["likely_non_english"] == True).sum()), random_state=1
)
with open(f"{OUT_DIR}/likely_non_english_sample.txt", "w") as f:
    f.write("=== primary_dataset flagged rows ===\n")
    if len(sample_flagged_primary):
        for t in sample_flagged_primary["text"].astype(str):
            f.write(f"- {t[:200]}\n")
    else:
        f.write("(no likely_non_english column present at this point -- see README)\n")
    f.write("\n=== urgency_dataset flagged rows ===\n")
    for t in sample_flagged_urgency["text"].astype(str):
        f.write(f"- {t[:200]}\n")

print("\n".join(report_lines))
print("\nDONE")
