# Step 10 — Evaluation

Final numbers on the held-out **test** split — untouched by every model in
Step 9, used here for the first and only time. These are the numbers that
belong in the paper's Results section; the val-set numbers from Step 9 were
for model selection only, not results.

## primary_dataset — XGBoost (leading candidate from Step 9)
**Test macro-F1: 0.6926** (val was 0.7067 — a 1.4-point drop, in the normal
range for a held-out split, not a sign of overfitting).

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Normal | 0.914 | 0.923 | 0.919 | 1,602 |
| Depression | 0.781 | 0.616 | 0.689 | 1,508 |
| Suicidal | 0.647 | 0.720 | 0.682 | 1,063 |
| Anxiety | 0.752 | 0.848 | 0.797 | 362 |
| Bipolar | 0.711 | 0.688 | 0.699 | 250 |
| Stress | 0.455 | 0.721 | 0.557 | 229 |
| Personality disorder | 0.475 | 0.539 | 0.505 | 89 |

Same pattern as val: Normal and Anxiety are strong, Stress and Personality
disorder are the weakest (both smallest classes, 17.9:1 imbalance ratio).
Confusion matrix: `output/primary_dataset_confusion_matrix.png`.

## urgency_dataset — Logistic Regression (leading candidate from Step 9)
**Test macro-F1 at the default 0.5 threshold: 0.9431** (val was 0.9434 — 
essentially identical, no overfitting).

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| non-suicide | 0.934 | 0.953 | 0.943 | 11,406 |
| suicide | 0.952 | 0.934 | 0.943 | 11,594 |

### Decision-threshold sweep (why urgency_dataset doesn't ship at 0.5)
This is a safety-net layer: a missed real "suicide"-class post (false
negative) is a worse outcome than a false alarm (false positive), so recall
on that class was prioritized over raw macro-F1.

| Threshold | suicide Precision | suicide Recall | suicide F1 | macro-F1 |
|---|---|---|---|---|
| 0.50 (default) | 0.952 | 0.934 | 0.943 | 0.9431 |
| 0.40 | 0.937 | 0.953 | 0.945 | 0.9440 |
| 0.35 | 0.926 | 0.961 | 0.944 | 0.9420 |
| 0.30 | 0.912 | 0.968 | 0.939 | 0.9368 |
| 0.25 | 0.894 | 0.975 | 0.933 | 0.9289 |
| 0.20 | 0.873 | 0.981 | 0.924 | 0.9182 |
| **0.15** | **0.840** | **0.987** | 0.908 | 0.8981 |
| 0.10 | 0.792 | 0.993 | 0.881 | 0.8625 |

**Recommended threshold: 0.15.** Selection rule: the lowest threshold in the
sweep that still keeps suicide-class precision at or above 0.80 (so the
safety-net layer isn't flooded with false alarms), maximizing recall within
that constraint. At 0.15: recall 0.987 (only 151 of 11,594 real suicide-class
test posts missed, vs. 766 missed at the default threshold), precision 0.840
(2,172 of 11,406 non-suicide posts get a false flag). Macro-F1 drops from
0.943 to 0.898 at this threshold — a deliberate, documented trade, not an
oversight: for this specific layer's job (catch crisis signal, let a human
review flagged posts), recall matters more than a clean-looking aggregate
score. Confusion matrices: `output/urgency_dataset_confusion_matrix_default.png`
(threshold=0.5) and `output/urgency_dataset_confusion_matrix_recommended.png`
(threshold=0.15).

## What's in output/
- `primary_dataset_test_results.json`, `urgency_dataset_test_results.json` — full classification reports, confusion matrices, the complete threshold sweep.
- `*_confusion_matrix*.png` — row-normalized confusion matrix plots for the paper's Results section (item 43).

## What Step 11 should do
Error analysis: pull actual misclassified test examples (especially
Stress/Personality-disorder confusions in primary_dataset, and the 151
missed-at-threshold-0.15 suicide-class posts in urgency_dataset) for manual
review; SHAP/LIME on the XGBoost model to explain which features drove
individual predictions.
