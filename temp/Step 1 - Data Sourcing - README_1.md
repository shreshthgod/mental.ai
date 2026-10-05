# Step 1 — Data Sourcing

## What was done
Sourced public, already-labeled text datasets for the multi-class mental-health
classifier instead of collecting original data first. Three files were added to
`datasets/text datasets/` and confirmed usable; a fourth candidate turned out to
be a duplicate of an existing file, not a new dataset (see Decisions below).

## Datasets confirmed

| Dataset | Rows | Labels | Role in the pipeline |
|---|---|---|---|
| `Combined Data.csv` | 53,043 | Normal, Depression, Suicidal, Anxiety, Bipolar, Stress, Personality disorder (7) | **Primary training set** — matches the 7-class target scheme directly |
| `Suicide_Detection.csv` | 232,074 | suicide, non-suicide (2, perfectly balanced 50/50) | **Urgency/crisis safety-net layer** (Step 0) |
| `Emotion_Sentiment_DataSet.csv` | 160,000 (87,983 unique) | love, happiness, sadness, Normal, hate, anger, Depression, fun, surprise, worry (10) | **Feature-engineering signal only** (Step 7) — see Decisions |

## Decisions

- **Target labels**: multi-class condition classification (7 classes above), not binary risk or a severity score.
- **Scope order**: text NLP pipeline first, in full, before speech/audio is added in Phase 2.
- **"4th file" question**: user flagged that a 4th dataset was expected. On inspection, the
  `Sentiment, Emotion analysis for mental health base` folder was a duplicate packaging of
  `Emotion_Sentiment_DataSet.csv` (same file, same size, bundled with its own README), not a
  distinct fourth dataset. Confirmed with the user to proceed with the 3 files above.
- **Emotion_Sentiment_DataSet.csv usage**: Step 2's EDA found this file overlaps heavily with
  Combined Data.csv (51.6% of Combined Data's unique text reappears verbatim inside it), and its
  non-overlapping labels (love/hate/anger/fun/surprise/worry) don't map onto the 7 target classes.
  Decision: use it for emotion-lexicon feature engineering in Step 7, not as a fourth source of
  labeled training rows.

## License / attribution note
`Combined Data.csv` corresponds to the Kaggle "Sentiment Analysis for Mental Health" dataset;
`Suicide_Detection.csv` corresponds to the Kaggle Reddit SuicideWatch vs. non-suicide dataset;
`Emotion_Sentiment_DataSet.csv` is bundled with a Mendeley Data DOI citation requirement (see its
own README.txt). Cite all three appropriately in the project report.
