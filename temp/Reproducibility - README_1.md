# Reproducibility

## Is the pipeline reproducible on another machine?
Yes, provided `requirements.txt` (this folder) is installed exactly and the
same raw input CSVs are used. Every random draw in the pipeline is seeded:

| Step | Random operation | Seed |
|---|---|---|
| 2 | `.sample(3000)` for EDA summaries | `random_state=42` |
| 3 | `train_test_split` (both stages) | `RANDOM_STATE = 42` |
| 6 | `.sample(15)` manual-review printout | `random_state=1` |
| 8 | oversampling `.sample(replace=True)` | `random_state=42` |

Steps 4, 5, and 7 (cleaning, preprocessing, feature extraction) contain no
randomness — they're regex/unicode/lookup-table transforms and closed-form
math, so they're deterministic by construction, not by seeding.

## What can still differ across machines
Not randomness — **library version drift**. NLTK's tokenizer/POS-tagger/
lemmatizer, `contractions`, `ftfy`, `emoji`, and pandas's CSV/NaN handling
(we hit a real pandas-3.0.2-specific NaN bug in Step 7 — see that step's
README) can change their exact output between versions even with identical
input and seed. The row-level split will always match; a small number of
cleaned/lemmatized token strings might not, if versions differ.

## NLTK data
Also version-pinned, not just the library. Installed via:
```
python -m nltk.downloader punkt punkt_tab averaged_perceptron_tagger_eng wordnet omw-1.4 vader_lexicon cmudict
```
Corpus data (wordnet, punkt models) is itself versioned by NLTK and can
update independently of the `nltk` pip package — for a hard guarantee, copy
this environment's `nltk_data` folder rather than re-downloading on the
other machine.

## To reproduce exactly
```
pip install -r requirements.txt
python -m nltk.downloader punkt punkt_tab averaged_perceptron_tagger_eng wordnet omw-1.4 vader_lexicon cmudict
```
Then run Steps 3–8 in order on the same raw CSVs.
