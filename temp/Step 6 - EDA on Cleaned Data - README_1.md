# Step 6 - EDA on Cleaned Data

## What this step does
Runs the first real analysis pass on the cleaned (Step 4) / preprocessed (Step 5) data:
final class distributions, top words per class, a data-driven urgency-keyword list built
independently from both datasets and cross-validated, a curated (slur-free) version of that
list, and a conservative spam/garbage detector used to flag (not silently drop) rows.

Code: `code/eda_cleaned_data.py`. Outputs: `findings/eda_cleaned_report.txt`,
`findings/urgency_keyword_candidates.json`, `findings/likely_non_english_sample.txt`,
`findings/garbage_flagged_rows.csv`.

## Major finding: a real upstream data bug (glued title/body text)
Running this step's word-frequency analysis for the first time surfaced a strange pattern:
top "distinctive words" full of glued-together tokens like `anymorei`, `helpi`, `wallsi`.
Traced this back to a genuine bug in the **original raw Kaggle files** (not introduced by
this pipeline): many posts have their title and body concatenated with zero separator
character, e.g. `"i dont want to live anymoreI'm having a hard time..."` is actually the
title *"I don't want to live anymore"* stuck directly onto the body. Confirmed against the
raw source files: affects 4.8% of `Combined Data.csv` and 28.6% of `Suicide_Detection.csv`.

Fixed in Step 4 (`clean_text()`, `GLUED_BOUNDARY_RE`) with a regex that inserts a space at a
lowercase/digit → uppercase boundary. Step 4 and Step 5 were fully re-run after the fix, and
this README's numbers reflect the corrected data. Full writeup: Step 4's README, "Revision"
section. A small residual remains: 116 `anymoreI`-style occurrences in urgency_dataset where
the second word starts with a **lowercase** `i` (e.g. `"anymorei'm"`) aren't caught by the
fix since there's no uppercase letter to detect - left as a documented known gap rather than
chased further, since a regex loose enough to catch it risks corrupting genuine text.

## Final class distributions

**primary_dataset** (51,055 rows, 7-class):

| label | count | % |
|---|---|---|
| Normal | 16,031 | 31.4% |
| Depression | 15,083 | 29.5% |
| Suicidal | 10,638 | 20.8% |
| Anxiety | 3,617 | 7.1% |
| Bipolar | 2,501 | 4.9% |
| Stress | 2,291 | 4.5% |
| Personality disorder | 894 | 1.8% |

Imbalance ratio 17.9:1 (Normal vs. Personality disorder) - flagged for Step 7/8 to handle
via class weighting or resampling, not addressed in this step.

**urgency_dataset** (231,943 rows, binary): suicide 116,031 (50.0%) / non-suicide 115,912
(50.0%) - essentially balanced by construction (this is how the source Kaggle dataset was
built).

## Distinctive words and the urgency keyword list
Used the same log-likelihood-ratio-style scoring from Step 3's design (add-1 smoothing,
target-class vs. rest), computed **independently** on primary_dataset's "Suicidal" class and
urgency_dataset's "suicide" class, then intersected the two top-50 lists as a cross-check.
Only 1 word (`painless`) survived strict intersection - expected, since the two datasets
have very different vocabularies (primary_dataset is multi-topic Reddit/Twitter text,
urgency_dataset is r/SuicideWatch vs. r/teenagers), so a single-word intersection undersells
how much real signal exists in each list on its own.

Built a broader **curated urgency keyword list** instead: the union of both datasets' top-50
distinctive-word lists (95 words after exclusions - see below), covering genuine risk
vocabulary across several categories: method/means words (`gun`, `rope`, `noose`, `slit`,
`overdose`, `wrist`, `firearm`, `shotgun`, `monoxide`), medication names (`lexapro`, `paxil`,
`prozac`, `wellbutrin`, `ativan`, `klonopin`, `acetaminophen`, `aspirin`), clinical/treatment
terms (`ideation`, `inpatient`, `outpatient`, `hospitalization`, `ssri`), and emotional-state
phrases (`goodbye`, `worthlessness`, `peacefully`, `painless`, `coward`, `defective`). Saved
as `curated_urgency_keywords` in `urgency_keyword_candidates.json`, alongside the raw
per-dataset lists (kept for transparency/audit) and the strict cross-validated intersection.

**Slur exclusion.** Four words - `retarded`, `retard`, `faggot`, `tranny` - appeared as
statistically distinctive for the suicide/Suicidal classes (i.e. they genuinely correlate
with distress in this data), but are not clinically meaningful risk indicators and are
inappropriate to ship in a keyword list. Explicitly excluded from `curated_urgency_keywords`
and listed separately as `excluded_slurs` in the JSON, rather than silently dropped - the
raw distinctive-word lists still show them for full transparency about what the data
contains.

## Garbage/spam detection (`is_garbage`)
The `likely_non_english` flag from Step 4 turned out too blunt to use for dropping rows -
manually reviewing `likely_non_english_sample.txt` showed it mixes genuine short/slangy
English text, actual foreign-language text, and outright spam, with no way to split those
apart from the flag alone. Built a separate, narrower `is_garbage()` function instead, aimed
only at the clearest, safest-to-remove cases.

**Design history - the false positive that shaped this.** A first version flagged any
15-or-more-repeated-character run as spam. Testing it against the actual data caught a real,
severe, ~1500-character crisis-disclosure post (describing abuse, trafficking, and suicidal
ideation) purely because it contained `"fuckkkkkkkkkkkkkkk...kkking"` - an emphatic elongated
word inside an otherwise genuine, long sentence, not spam. Raising the run threshold to 20+
did not fix it (the actual elongation in that post runs 80+ characters). The fix was to stop
using run length alone and instead require the run to dominate the *entire* text (run length
> 50% of the whitespace-stripped text), which correctly separates "one repeated character
that basically **is** the whole post" (garbage) from "a long emphatic elongation embedded in
an otherwise normal multi-sentence post" (genuine). Re-verified against the same post after
the fix: no longer flagged. Also checked a borderline case - `"AHHHHHHHHHHHHHHHH Im losing
my fucking mind"` - correctly not flagged (short text, elongation isn't dominant).

Final function has three narrow, independent conditions (see docstring in
`code/eda_cleaned_data.py` for full detail):
1. **Repeated-character spam** - one character's run is 30+ long *and* >50% of the text.
2. **Repeated-word spam** - one word makes up >40% of all tokens *and* appears 6+ times
   (catches patterns like `"Balls balls balls balls..."` and reddit filler-text spam).
3. **Heavy non-Latin content** - >40% of letters are non-Latin-script (catches
   phone-number-farming / non-English spam posts).

This is deliberately precision-over-recall: a **known gap** is non-repetitive symbol/binary
spam (e.g. a wall of `"01101000 01110100..."` ASCII-binary), which none of the three
conditions catch and which was found in a spot-check of the raw data. Not chased further -
catching it would need looser pattern rules that risk the same kind of false positive this
function was built to avoid, for an issue affecting well under 1% of either dataset.

**Results**: flagged, not dropped - saved to `findings/garbage_flagged_rows.csv` for manual
review, to be excluded when Step 7 builds the training matrices.

| dataset | flagged | % |
|---|---|---|
| primary_dataset | 25 / 51,055 | 0.049% |
| urgency_dataset | 2,189 / 231,943 | 0.944% |

Manually spot-checked a random sample of 20 flagged rows (both datasets) - all were
genuine spam/filler (reddit "filler filler filler..." padding text used to satisfy a
subreddit's minimum post-length rule, repeated-word copy-paste posts, ASCII-art/emoji
padding, non-Latin script spam). No genuine crisis or on-topic content found flagged in the
sample, consistent with the conservative design goal.

## Resolved: urgency_dataset lemmatization
This step originally ran urgency_dataset's word-frequency analysis on Step 4's
cleaned-but-not-lemmatized text, because Step 5's lemmatization job for urgency_dataset
crashed partway through (~54%, row ~126,000) on a rare `textsearch`/`contractions`
library bug (`IndexError` in its bounds-check, triggered by the Turkish dotted capital
`İ` character - a library bug, not a data problem). Fixed in `preprocess_text.py` with a
`safe_fix()` wrapper (falls back to the un-expanded string and logs the failure rather
than crashing) and incremental checkpointing every 20,000 rows; see Step 5's README for
the full account. The job was restarted and completed cleanly (only 2/231,943 rows fell
back to un-expanded text). This step was then re-run against the lemmatized file - the
report and `urgency_keyword_candidates.json` in this folder reflect that final run (word
variants like `kill`/`killing` now merge, and the curated keyword list picked up a few
additional lemmatized forms - e.g. `depressants`, `fraternity`, `existing` - that weren't
visible before lemmatization).

## Fixed here too: a stray "nan" token
While re-running this step, found and fixed the same missing-value edge case documented
in Step 7's README: a handful of rows lemmatize to an empty string, which round-trips
through CSV as a true NA rather than the string "nan" - and pandas' `.astype(str)` alone
doesn't stringify that away on this environment's pandas version. Added `.fillna("")`
before `.astype(str)` for both datasets' `text_lemmatized` column so a spurious "nan"
token can't sneak into the word-frequency/distinctiveness analysis.

## Output files
- `findings/eda_cleaned_report.txt` - full text report (distributions, top words,
  distinctive words, cross-validation, curated keyword list, garbage-detection results).
- `findings/urgency_keyword_candidates.json` - structured: `cross_validated_single_words`,
  `curated_urgency_keywords`, `excluded_slurs`, and the full raw per-dataset distinctive-word
  lists.
- `findings/likely_non_english_sample.txt` - manual-review sample of Step 4's
  `likely_non_english`-flagged rows (kept for reference; superseded by `is_garbage` as the
  actual row-drop criterion).
- `findings/garbage_flagged_rows.csv` - every row `is_garbage()` flagged, with dataset,
  label, and full text, for manual review / reversibility.
