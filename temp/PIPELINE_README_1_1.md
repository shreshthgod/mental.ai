# Pipeline folder convention

Each phase-1 step gets its own folder directly in this project directory, named
`Step N - <name>`. Every step folder holds up to three things:

- `code/` - the actual script(s) run for that step.
- `findings/` (or a README/notes file) - what was done, what was found, and any
  decisions that changed the plan.
- the resulting dataset file(s), when that step changes the data (EDA steps that
  only analyze, like Step 2, don't produce a new dataset - later steps like
  cleaning, preprocessing, and feature engineering will).

Folders so far:

- `Step 1 - Data Sourcing/` - the 3 datasets confirmed, decisions on what's used and why.
- `Step 2 - Raw Data EDA/` - automated checks on all 3 raw files before any changes;
  found major cross-file duplication between Combined Data.csv and
  Emotion_Sentiment_DataSet.csv, which changed how Step 3 is being built.
- `Step 3 - Unified Dataset/` - built two separate tables instead of one merged one
  (primary 7-class set from Combined Data.csv, binary urgency set from
  Suicide_Detection.csv - see that step's README for why), split 80/10/10 stratified.
  Output datasets are gzipped and chunked to fit file-transfer limits; a full local
  copy stays in the working environment.
- `Step 4 - Cleaning/` - URL/username/subreddit stripping, emoji-to-text conversion,
  unicode fixes, light PII scrub, junk-marker removal, dedup of duplicates created by
  cleaning itself. One documented limitation: no compiled language-detection library
  would install in this sandbox, so a lightweight stopword-overlap heuristic flags
  (doesn't drop) likely non-English rows for Step 6 to manually review. **Revised**
  after Step 6 surfaced a real upstream data bug: many raw posts have their title and
  body concatenated with zero separator (e.g. `"...anymoreI'm having a hard time"`),
  affecting 4.8% of Combined Data.csv and 28.6% of Suicide_Detection.csv. Fixed with a
  targeted regex; Step 4 and Step 5 were fully re-run on the corrected data.
- `Step 5 - Text Preprocessing/` - contraction expansion, tokenization, POS-tagging,
  lemmatization (NLTK), deliberately no stopword removal (negation/pronouns are signal
  for this task). Both datasets done; `urgency_dataset`'s lemmatization crashed once
  partway through on a rare third-party library bug (`contractions`/`textsearch`,
  triggered by a Turkish `İ` character), fixed with a safe-fallback wrapper +
  incremental checkpointing, and completed cleanly on restart.
- `Step 6 - EDA on Cleaned Data/` - final class distributions, top/distinctive words
  per class, a data-driven + cross-validated urgency-keyword list (curated to exclude
  slurs that were statistically distinctive but not clinically meaningful), and a
  conservative `is_garbage()` spam/filler detector (flags, doesn't drop - see that
  step's README for the false-positive it was designed around and its known gaps).
- `Step 7 - Feature Extraction/` - handcrafted features (stylistic/surface, VADER
  sentiment, readability, pronoun/negation/absolutist-word ratios, NRC emotion lexicon,
  a custom leakage-guarded emotion-association lexicon built from
  Emotion_Sentiment_DataSet.csv, curated urgency-keyword count) plus TF-IDF (fit on
  train only). Both feature scripts exclude Step 6's spam/filler-flagged rows.
  Raw TF-IDF matrices aren't shipped to the DE folder (one is 237MB and regenerates
  in under a minute from the saved vectorizer + Step 5's output) - see that step's
  README.

- `Step 8 - Class Imbalance Handling/` - decided class weighting (inverse-frequency,
  computed from train split only) over SMOTE (invalid on sparse 30k-dim TF-IDF vectors)
  or undersampling (throws away real Normal/Depression rows for no benefit). urgency_dataset
  needs no handling - already ~50/50. Also produced an optional, clearly-marked
  oversampled train-split variant (duplicate-with-replacement, not synthetic) for Step 9
  to A/B test.

More folders are added as each step is completed (Step 9 - Model Training next).

## Note on dataset file sizes
Some steps' output datasets are large (the urgency set is 232k rows). To keep every
file under the transfer size limit, outputs are saved gzip-compressed and, where
still too large, split into numbered parts (e.g. `_part1of4`). Load them with
`pandas.read_csv("file.csv.gz")` - pandas decompresses gzip automatically - and
`pd.concat()` the numbered parts of the same split back together if needed.
