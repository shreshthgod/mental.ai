# Step 7 — Feature Extraction & Engineering

## What this step does
Turns Step 5/6's cleaned, lemmatized text into the numeric features Step 9's models
actually train on. Two kinds of features, built by three scripts:

- `code/build_emotion_lexicon.py` — a supporting lexicon, not features themselves
  (run first; the other two scripts depend on its output).
- `code/feature_engineering.py` — handcrafted/classical features (one row per input row).
- `code/tfidf_vectorize.py` — TF-IDF vectors (fit on train only, transformed onto val/test).

Both feature scripts **exclude** the rows Step 6's `is_garbage()` flagged as spam/filler
(25 primary, 2,189 urgency — matched by exact text against Step 6's audit file, not
recomputed, so this can never quietly drift from what Step 6 actually reviewed).

## Handcrafted features (`feature_engineering.py`)
43 columns for primary_dataset, 42 for urgency_dataset (urgency has no `urgency_flag`
column to carry through — it *is* the urgency layer). Every feature, and why it's here:

**Stylistic / surface** (computed on `text` — Step 4's cleaned text, case and punctuation
intact; lemmatizing lowercases and drops punctuation, so these have to come from before
that step): `char_count`, `word_count`, `avg_word_len`, `exclam_count`, `question_count`,
`ellipsis_count`, `all_caps_ratio`, `repeated_punct_count` (runs like "!!!" or "???").
These are standard proxies for emotional intensity/urgency in text-based screening
literature.

**VADER sentiment** (`vader_neg/neu/pos/compound`, from `text`) — a general-purpose,
rule-based sentiment scorer; deliberately run on the un-lemmatized text since VADER's
rules depend on real capitalization and punctuation (e.g. "SO SAD!!!" scores more
intensely than "so sad").

**Readability** (`flesch_reading_ease`, `flesch_kincaid_grade`, from `text`, via
`textstat`) — captures how simple/fragmented vs. structured the writing is, which
correlates with some conditions in the literature (e.g. more fragmented language during
acute distress).

**Pronoun / negation / absolutism** (from `text_lemmatized` tokens — exactly why Step 5
refused to strip stopwords): `pronoun_ratio` (share of tokens that are first-person
singular: i/me/my/mine/myself — self-focus is a documented depression correlate),
`negation_count` (not/no/never/none/nobody/nothing/neither/nor/cannot), `absolutist_ratio`
(share of tokens like always/never/completely/entirely/everyone/nothing/must — absolutist
thinking is a documented correlate of depression/anxiety/suicidal ideation in the
computational-linguistics literature, e.g. Al-Mosaiwi & Johnstone 2018).

**NRC Word-Emotion Association Lexicon** (`nrc_fear/anger/anticipation/trust/surprise/
positive/negative/sadness/disgust/joy`, 10 columns) — the standard NRC EmoLex, looked up
directly against `text_lemmatized` tokens (bypassing the `nrclex` package's own, much
slower, TextBlob-based tokenizer/lemmatizer, since Step 5 already did that job — this
alone was the difference between ~90 rows/sec and ~700+ rows/sec). Normalized the same
way `nrclex` defines it: each category's share of all category-hits in the text.

**Custom emotion-association lexicon** (`emo_lex_Normal/anger/fun/happiness/hate/love/
sadness/surprise/worry`, 9 columns) — built in `build_emotion_lexicon.py` from
Emotion_Sentiment_DataSet.csv (the dataset Step 1/2 excluded as training rows, kept for
exactly this purpose: a feature-engineering signal). **Leakage guard**: 26,683 of that
dataset's 160,000 rows (16.7%) are exact-duplicate text of a primary/urgency raw row —
almost entirely its "Normal" (16,350/16,351 rows) and "Depression" (10,333/10,333 rows,
i.e. *all* of them) classes, which is strong evidence of how that dataset was assembled
and fully confirms Step 2's original overlap finding. Those rows are excluded before
building the lexicon, so nothing in this feature can be memorization of a duplicate row's
own label — only the 133,317 non-overlapping rows across the other 8 emotion classes
(love, happiness, sadness, hate, anger, fun, surprise, worry) feed the lexicon. Per-word
`P(class | word)` (add-1 smoothed, min doc-count 5), mean-pooled over a text's matched
tokens.

**Urgency-keyword signal** (`urgency_keyword_count`, `urgency_keyword_flag`) — count and
binary presence of Step 6's 95-word curated keyword list (slurs already excluded there)
in `text_lemmatized`.

## Feature sanity-check (primary_dataset, by label)
Spot-checked the handcrafted features against the 7 labels before trusting them:

| feature | pattern found |
|---|---|
| `urgency_keyword_flag` rate | Suicidal 48.2% vs. Normal 1.2% — a 40x spread |
| `absolutist_ratio` mean | Suicidal/Depression highest, Normal lowest, exactly as the literature predicts |
| `vader_compound` mean | Suicidal most negative (-0.43), Normal only class that's net positive (+0.09) |
| `nrc_negative` mean | Anxiety highest (0.22), Normal lowest (0.11) |

All in the expected direction — good sign these features will actually help Step 9's
models rather than being noise.

## TF-IDF (`tfidf_vectorize.py`)
Unigrams + bigrams (bigrams catch negation-flipped phrases like "not happy" that
unigram-only TF-IDF would otherwise split apart — important since Step 5 kept negation
words in the vocabulary on purpose), `min_df=5`, `max_df=0.9`, `max_features=30000`,
`sublinear_tf=True`. Fit **only** on the train split, then used to transform val/test —
fitting on the full dataset first would leak val/test vocabulary/IDF statistics into
training. No hand-picked stopword list (consistent with every step since Step 5) —
`min_df`/`max_df` prune the extremes instead.

| dataset | vocab size | train rows | val rows | test rows |
|---|---|---|---|---|
| primary_dataset | 30,000 | 40,825 | 5,102 | 5,103 |
| urgency_dataset | 30,000 | 183,786 | 22,968 | 23,000 |

## A data bug found and fixed here: the "nan" token
A handful of rows lemmatize down to an empty string (raw text that was pure punctuation,
e.g. `"?????"`)`. Written to CSV as an empty field, that round-trips back through pandas
as a true missing value — and on this environment's pandas version, `.astype(str)` alone
does **not** stringify a missing value in a "string"-dtype column the way it would on an
`object`-dtype column; it stays a real NA. The first version of `feature_engineering.py`
let `str(text_lemmatized)` run on that NA, which produced the literal string `"nan"` —
a token that happens to genuinely exist in the NRC lexicon and the custom emotion
lexicon, so that one row got spurious, meaningless emotion-feature values instead of all
zeros. Fixed with `.fillna("")` before `.astype(str)` in both feature scripts (and
retroactively in Step 6's `eda_cleaned_data.py`, since the same issue could have put a
"nan" token into the word-frequency analysis). Affected exactly 1 row out of 51,055 in
primary_dataset — caught by spot-checking a NaN-heavy row's output rather than trusting
the pipeline blindly.

## Handed off, not run here: transformer embeddings
MentalBERT/MentalRoBERTa embeddings are GPU-only and out of scope for this CPU sandbox —
per the project's division of labor, this is handed off as a ready-to-run script once
Step 9 needs it, not attempted here.

## Output files
- `output/emotion_lexicon.json` — the custom word→emotion-class lexicon from Step 7a.
- `output/*_handcrafted_features.csv.gz` (full, local) /
  `output/_delivery/*_features_{train,val,test[,_partN]}.csv.gz` (chunked for transfer,
  same gzip/split convention as every prior step) — one row per surviving (non-garbage)
  input row, `label`/`split`/(`urgency_flag`)/`source_dataset`/`likely_non_english`
  carried through so this joins straight back to the dataset.
- `output/*_tfidf_vectorizer.pkl` — the fitted vectorizer (vocabulary + IDF weights).
  **Not shipped**: the raw `*_tfidf_{train,val,test}.npz` sparse matrices themselves —
  at 30,000 features across up to 184k rows, the urgency_dataset train matrix alone is
  237MB, and every byte of it is exactly reproducible in under a minute by re-running
  `tfidf_vectorize.py` against the Step 5 outputs already saved in this folder tree (the
  vectorizer pickle is what actually needs to survive — it *is* the fitted state; the
  matrices are just its output). Shipping several hundred MB of a one-command-to-rebuild
  artifact isn't worth the transfer cost or the drive space.
