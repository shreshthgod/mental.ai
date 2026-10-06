# Step 2 - Raw Data EDA: Findings

## What was done
Ran automated checks on all three raw source files before any cleaning or merging:
row counts, missing/empty text, exact duplicates (within-file and cross-file), junk
markers (`[removed]`/`[deleted]`), text length distribution, a rough English-language
heuristic, and class balance. Code: `code/eda_raw_datasets.py` and
`code/check_cross_dataset_overlap.py`. Raw console output saved in this folder as
`eda_output_log.txt` and `cross_dataset_overlap_log.txt`.

## Combined Data.csv (primary, 7-class)
- 53,043 rows; 362 empty/NaN text rows (0.68%); 3,373 exact duplicate rows (6.36%).
- Word length: median 62, mean 112.9, up to 6,300 words on the long tail (needs a cap later).
- Very short (<=2 words): 1,315 rows (2.48%).
- Class imbalance: Normal 30.8% down to Personality disorder 2.3% - **13.6:1** ratio.
- ~4.9% of a 3,000-row sample had zero common-English-stopword hits (rough non-English/junk
  proxy - needs manual spot-check, not all of this is necessarily bad data).

## Suicide_Detection.csv (urgency layer)
- 232,074 rows; 0 empty, 0 exact duplicates, 0 `[removed]`/`[deleted]` markers.
- Perfectly balanced: suicide 50.0% / non-suicide 50.0%.
- Cleanest of the three files by a wide margin - minimal cleaning needed.

## Emotion_Sentiment_DataSet.csv (10-class emotion) - key finding
- 160,000 rows but only **87,983 unique texts** - 72,017 rows (45%) are exact repeats
  within the file itself.
- Of those 87,983 unique texts, **26,357 are word-for-word identical to text already in
  Combined Data.csv** - i.e. 51.6% of Combined Data.csv's own unique content reappears
  verbatim in this "different" file.
- Its non-overlapping labels (love, hate, anger, fun, surprise, worry) don't map onto the
  7 target classes at all; only Normal and Depression do, and those are already the two
  best-covered classes in Combined Data.csv.

## Decision this drives (Step 3)
- Do **not** naively concatenate all three files - the cross-file duplication would
  double-count over half of the primary dataset and risks the same post landing on both
  sides of a train/test split.
- Combined Data.csv + Suicide_Detection.csv are the two row sources for the labeled
  training set, de-duplicated **globally** (across both files, not just within each).
- Emotion_Sentiment_DataSet.csv is set aside for Step 7 (feature engineering / emotion
  lexicon), not used as a fourth source of labeled rows.
- General principle going forward (per user instruction): dataset composition can be
  adjusted at each step whenever it clearly improves the trained model's accuracy -
  documented here, and in each subsequent step's README, whenever that happens.
