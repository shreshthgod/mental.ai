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

- `Step 9 - Model Training/` - baseline (Logistic Regression, Linear SVM - full
  30k-dim TF-IDF) and mid-tier (Random Forest, XGBoost - 38 handcrafted +
  chi2-reduced 1,500-dim TF-IDF, cut down from the full 30,038-dim vector after
  timing showed it wasn't practical on this sandbox's 2-vCPU hardware) models
  trained and compared on val. Leading so far: XGBoost for primary_dataset
  (macro-F1 0.7067), Logistic Regression for urgency_dataset (macro-F1 0.9434).
  Test split untouched - Step 10 confirms the pick there. Transformer
  fine-tuning (MentalBERT/DistilBERT) - **skipped by decision**, not left
  pending: no GPU access in this environment, so classical ML is Phase 1's
  final model tier. The ready-to-run script is kept as a reference artifact
  only, not something Phase 1 is waiting on.

- `Step 10 - Evaluation/` - final TEST-split numbers (untouched until now).
  primary_dataset (XGBoost): macro-F1 0.6926. urgency_dataset (Logistic
  Regression): macro-F1 0.9431 at the default 0.5 threshold. Swept the
  urgency model's decision threshold and recommends 0.15 for deployment
  (suicide-class recall 0.987 vs. 0.934 at default, precision 0.840 vs.
  0.952 - a deliberate recall-priority trade for a safety-net layer, not an
  oversight). Confusion matrix plots included for the paper.

- `Step 11 - Explainability and Error Analysis/` - pulled actual
  misclassified test rows, not just confusion-matrix counts. Biggest finding:
  Depression↔Suicidal is 43.7% of all primary_dataset errors (genuinely
  adjacent classes/proxy labels, not a fixable model bug). SHAP
  (TreeExplainer for XGBoost, LinearExplainer for Logistic Regression):
  primary_dataset's top features are clinically meaningful (avpd, pdoc,
  lamictal, depakote - real diagnosis/medication terms forum users use,
  though rare - see revision below); urgency_dataset surfaced a genuine
  caution - "die"/"to die" push toward *non-suicide*, likely a
  subreddit-source artifact rather than a real signal about crisis
  language. Also found likely label noise in a handful of urgency false
  negatives (an off-topic post carrying the "suicide" label). **Revised**
  after a fair challenge that the original "top words" bar charts ranked
  purely by mean |SHAP| averaged over all rows, which conflates word
  frequency with per-occurrence effect size and can make common,
  low-signal words (e.g. "guy", "job") look as important as rare,
  high-signal ones. Added: prevalence (% of posts containing each term)
  reported alongside every word, a "when present" conditional SHAP value
  that isn't diluted by rows where the word is absent, and a cross-check
  against Step 6's curated crisis-keyword list and Step 7's emotion
  lexicon so each term is tagged by how much independent evidence backs
  it. The re-ranked, prevalence-gated tables read much more like genuine
  crisis vocabulary (suicide, overdose, kill myself, noose) vs. genuine
  casual/social vocabulary (minecraft, discord, meme) than the original
  frequency-weighted lists did - see that step's README for full tables.

- `Step 12 - Packaging/` - final step. Bundled both winning models (primary_dataset's
  XGBoost, urgency_dataset's Logistic Regression at its 0.15 threshold) plus the
  vectorizers, chi2 selector, curated keyword list, and emotion lexicon into one
  importable module (`mental_health_screening/`) with a single `.screen(text)` entry
  point. Preprocessing/feature-extraction logic is copied (not imported) from Steps
  4/5/7 so the package has no dependency on this sandbox's folder layout. Verified,
  not just tested: fed genuinely raw (pre-cleaning) text from 10 real test rows
  through the packaged pipeline and confirmed exact parity - cleaned text, lemmatized
  text, and final prediction all matched the pipeline's own saved results, 10/10.
  **This closes the planned Step 0–12 text-NLP pipeline.** With the
  transformer tier (Step 9c) now skipped by decision rather than left
  pending (see Step 9), Phase 1's text track has no open items remaining -
  classical ML (XGBoost / Logistic Regression) is the final, complete,
  packaged result.

- `Reproducibility/` - not a pipeline step, a standing check: every random draw across
  Steps 2-8 is confirmed seeded (splits, sampling, oversampling), so re-running the same
  code on the same input CSVs reproduces the same rows every time. The only real risk on
  a different machine is library version drift (NLTK/contractions/ftfy/pandas), so exact
  versions are pinned in `requirements.txt`.

## Note on dataset file sizes
Some steps' output datasets are large (the urgency set is 232k rows). To keep every
file under the transfer size limit, outputs are saved gzip-compressed and, where
still too large, split into numbered parts (e.g. `_part1of4`). Load them with
`pandas.read_csv("file.csv.gz")` - pandas decompresses gzip automatically - and
`pd.concat()` the numbered parts of the same split back together if needed.
