# Step 3 — Build the Unified Dataset

## What was done
Built two separate, split, ready-to-train tables instead of one merged table. Code:
`code/build_unified_dataset.py`. Full run log: `output/build_log.txt`.

## Key decision: two tables, not one merged table
The original plan (Step 3 as first written) was to merge Combined Data.csv and
Suicide_Detection.csv into a single multi-class table with a shared label-mapping.
On building it, that turned out to be the wrong call, so it was changed (per the
standing permission to adjust the dataset for the most accurate model):

- Combined Data.csv's `Suicidal` class maps cleanly to Suicide_Detection.csv's
  `suicide` class — but `non-suicide` (general Reddit posts not about suicide) has
  **no honest mapping** onto Normal/Depression/Anxiety/etc. Guessing one would inject
  116,037 mislabeled rows into the primary 7-class target.
- Adding only the `suicide` rows (mapped to `Suicidal`) without their matched
  `non-suicide` counterparts would have made `Suicidal` the dominant majority class
  by a huge margin (10,641 existing vs. +116,037 more) — a worse imbalance problem
  than the one Step 3 was supposed to solve.

**Decision:** keep the 7-class classifier and the urgency/crisis safety-net as two
separate models trained on two separate tables, matching the Step 0 design (urgency
was always meant to sit outside the multi-class model, not inside it):

| Output file | Source | Purpose |
|---|---|---|
| `output/primary_dataset.csv` | Combined Data.csv only | 7-class classifier training data |
| `output/urgency_dataset.csv` | Suicide_Detection.csv only | Binary urgency/crisis safety-net training data |

## Processing applied (both tables)
1. Dropped empty/NaN text rows.
2. Dropped exact-duplicate text rows (kept first occurrence) — required before
   splitting, otherwise the same post can land in both train and test.
3. Stratified 80/10/10 train/val/test split by label.

**Known limitation:** neither source file has an author/user id column, so a true
no-leakage-by-author split (Step 3's original design) isn't possible here. Exact-text
de-duplication is the mitigation actually available; near-duplicate (paraphrased)
leakage across splits is not fully ruled out and is worth a manual spot-check later.

## Results

**`primary_dataset.csv`** — 51,073 rows (from 53,043 raw: -362 empty, -1,608 exact
dupes after empty removal). `urgency_flag` column added (1 where label == Suicidal).

| Label | Rows | Share |
|---|---|---|
| Normal | 16,039 | 31.4% |
| Depression | 15,087 | 29.5% |
| Suicidal | 10,641 | 20.8% |
| Anxiety | 3,617 | 7.1% |
| Bipolar | 2,501 | 4.9% |
| Stress | 2,293 | 4.5% |
| Personality disorder | 895 | 1.8% |

Imbalance ratio is now ~17.9:1 (Normal vs. Personality disorder) — slightly worse
than the raw 13.6:1 because duplicate removal wasn't even across classes. This is
exactly what Step 8 (handle class imbalance) exists to address — no action needed yet.

**`urgency_dataset.csv`** — 232,074 rows, unchanged from raw (it was already
duplicate-free), perfectly balanced 50/50 suicide vs. non-suicide, split 80/10/10.

## Columns
- `primary_dataset.csv`: `text, label, urgency_flag, source_dataset, split`
- `urgency_dataset.csv`: `text, label, source_dataset, split`

## Next
Step 4 (cleaning) runs on both tables: URL/username stripping, emoji-to-text,
unicode normalization, PII scrub, language filtering — none of that has been applied
yet, this step only handled what was required to split safely.
