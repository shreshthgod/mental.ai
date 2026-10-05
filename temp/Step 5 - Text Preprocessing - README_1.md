# Step 5 — Text Preprocessing

## What was done
Runs on both Step 4 cleaned outputs. Code: `code/preprocess_text.py`.

Per row: expand contractions ("don't" → "do not") **before** tokenizing so
negation survives as its own token → lowercase + tokenize (NLTK `word_tokenize`)
→ batch POS-tag (`pos_tag_sents`) → lemmatize each token with its POS
(`WordNetLemmatizer`) → drop pure-punctuation tokens → join back into a new
`text_lemmatized` column, kept alongside the original cleaned `text` column.

**Deliberately not done:** stopword removal. Standard stopword lists strip
"no", "not", "never", "I", "me", "my" — exactly the signal this task depends
on — so no blanket stopword filter is applied anywhere in this step.

## Environment note
NLTK's data downloader (tokenizer models, WordNet corpus) initially refused to
run because this sandbox's outbound traffic goes through a proxy, and NLTK's
SSRF protection doesn't trust proxied fetches by default. Opted into the
override (`NLTK_ALLOW_PROXIED_URLOPEN=1`) since this only fetches NLTK's own
public linguistic data files, not sensitive data. Running this script on a
different machine with direct internet access should not need this.

## Performance note
This sandbox has 2 CPU cores. POS-tagging+lemmatizing runs at roughly
200-210 rows/sec for `primary_dataset` and ~165-170 rows/sec for
`urgency_dataset` (its text is on average longer). `primary_dataset_clean.csv`
(51,048 rows) finished in ~4 minutes running in the foreground.
`urgency_dataset_clean.csv` (231,924 rows) takes ~20-25 minutes, so it was run
as a background process (`code/preprocess_text.py urgency`, logged to
`output/urgency_preprocess_log.txt`) rather than blocking the session.

## Spot-check (cleaned text -> lemmatized text)
```
CLEAN: I hate myself and do not understand why I should have lived...
LEMMA: i hate myself and do not understand why i should have live...

CLEAN: i wish i was free that night. i'm kind of mad that i didn't go.
LEMMA: i wish i be free that night i be kind of mad that i do not go
```
Negation ("do not") and first-person pronouns ("i", "myself") both survive
intact, confirming the no-stopword-removal decision is actually holding in
practice, not just in the plan.

## Status
- `primary_dataset_clean_preprocessed.csv` — **done**, 51,055 rows (re-run after
  Step 4's glued-title/body-text fix — see Step 4 and Step 6 READMEs).
- `urgency_dataset_clean_preprocessed.csv` — **done**, 231,943 rows. First attempt
  crashed at ~54% (row ~126,000/231,943) with an `IndexError` inside the
  `contractions`/`textsearch` library's bounds-check — a rare library bug,
  root-caused to the Turkish dotted capital `İ` character (U+0130) appearing in
  two posts, not a data problem otherwise. Fixed with two changes to
  `code/preprocess_text.py`:
  1. `safe_fix()` wraps `contractions.fix()` in a try/except — on failure it
     falls back to the original, un-expanded string and logs the failure to
     `output/<name>_contractions_failures.txt` instead of crashing the whole
     231,943-row job.
  2. Incremental checkpointing every 20,000 rows (`output/<name>_preprocessed.csv.partial`)
     so a future crash doesn't lose all progress on this 20-25 minute job again.

  Job was restarted as a background process after the fix and completed
  cleanly this time — only 2/231,943 rows (both containing `İ`) fell back to
  un-expanded contractions, logged in `output/urgency_dataset_clean_contractions_failures.txt`.
  Step 6's urgency-dataset word-frequency analysis and Step 7's feature
  extraction were both then run (or re-run) against this final lemmatized
  file.
