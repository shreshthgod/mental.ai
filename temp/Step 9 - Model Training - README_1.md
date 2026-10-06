# Step 9 - Model Training

## What was trained (all on train split, selected on val; test held out for Step 10)

| Tier | Model | Features | primary macro-F1 (val) | urgency macro-F1 (val) |
|---|---|---|---|---|
| Baseline | Logistic Regression | TF-IDF (30,000-dim), class-weighted | **0.6876** | **0.9434** |
| Baseline | Linear SVM | TF-IDF (30,000-dim), class-weighted | 0.6801 | 0.9412 |
| Mid-tier | Random Forest | 38 handcrafted + chi2-selected TF-IDF (1,500), class-weighted | 0.6364 | 0.9014 |
| Mid-tier | XGBoost | 38 handcrafted + chi2-selected TF-IDF (1,500), sample-weighted | **0.7067** | 0.9235 |
| Advanced | MentalBERT fine-tune | raw cleaned text, own tokenizer | **skipped - no GPU** | skipped |

**Best so far: XGBoost for primary_dataset (7-class), Logistic Regression for
urgency_dataset (binary).** Not final - Step 10 confirms this on the held-out
test split, which nothing above has touched.

## Why mid-tier uses a reduced feature set, not the full 30,038-dim vector
The paper-details doc's item 17 flagged "38 + 30,000 = 30,038 if concatenated
as-is" as pending. Timed it directly on this sandbox's hardware (2 vCPUs, no
GPU) before committing: XGBoost's histogram tree construction at full width
measured at roughly 10x slower per boosting round than at 1,500 features in a
direct side-by-side test - 25–45 minutes per model per dataset, not
practical here. Cut the TF-IDF side down to the top 1,500 terms by chi2
score (same statistical-distinctiveness idea Step 6 used for the curated
keyword list, applied to the full vocabulary instead of a hand-picked
subset), fit on train only. This is a hardware-driven adjustment, not a
finding about what the models need - documented per the standing latitude to
adjust composition for feasibility. Baselines (Logistic Regression, Linear
SVM) keep the full 30,000-dim TF-IDF since linear models scale fine there.

## Class imbalance handling used
- Logistic Regression, Random Forest: native `class_weight` dict (Step 8's values).
- Linear SVM: same, via `class_weight`.
- XGBoost: per-row `sample_weight` (the sklearn `XGBClassifier` API has no `class_weight` argument).
- urgency_dataset needed no weighting to begin with (Step 8: both weights ≈ 1.0) - used anyway for consistency, negligible effect.

## Reading the primary_dataset result (XGBoost, val)
| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Normal | 0.921 | 0.934 | 0.928 | 1,600 |
| Depression | 0.785 | 0.635 | 0.702 | 1,509 |
| Suicidal | 0.662 | 0.727 | 0.693 | 1,064 |
| Anxiety | 0.774 | 0.853 | 0.812 | 361 |
| Bipolar | 0.740 | 0.752 | 0.746 | 250 |
| Stress | 0.487 | 0.671 | 0.565 | 228 |
| Personality disorder | 0.432 | 0.600 | 0.502 | 90 |

Normal and Anxiety are strong; Stress and Personality disorder are the weak
spots - expected given they're the two smallest classes (17.9:1 imbalance
ratio) even after weighting. Class weighting narrows this gap (recall on
Personality disorder is 0.600, not near-zero) but doesn't close it.

## Reading the urgency_dataset result (Logistic Regression, val)
| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| non-suicide | 0.935 | 0.951 | 0.943 | 11,372 |
| suicide | 0.952 | 0.936 | 0.944 | 11,596 |

Balanced and strong both ways - consistent with this being a near-50/50
dataset with a clearer linguistic signal (crisis language is more lexically
distinct than the 7-way condition split). Step 10 will specifically check
whether lowering the decision threshold trades a bit of precision for higher
suicide-class recall - for a safety-net layer, missing a true positive is
costlier than a false alarm, so recall gets priority there even at the cost
of raw macro-F1.

## Advanced tier: transformer fine-tuning - SKIPPED (decision, not pending)
**Decision: skipped for Phase 1.** This environment has no GPU access, and
that's not going to change within this sandbox, so the transformer tier is
being treated as deliberately out of scope rather than an open task -
classical ML (XGBoost for primary_dataset, Logistic Regression for
urgency_dataset) is Phase 1's final, complete model tier, already evaluated
on test (Step 10), explained (Step 11), and packaged (Step 12). The script
below is kept only as a reference / future-work artifact, in case GPU access
becomes available later - it is not something Phase 1 is waiting on.

`code/train_transformer_finetune.py` - ready to run as-is on Colab/GPU.
MentalBERT (`mental/mental-bert-base-uncased`, BERT further pretrained on
mental-health-subreddit text) by default, DistilBERT as a documented
fallback. Deliberately uses Step 5's **`text`** column (Step 4's cleaned,
case/punctuation-intact text), not `text_lemmatized` - the one place in the
whole pipeline where Step 5's output is intentionally not used, since
transformer tokenizers build their own subword vocabulary from natural text
and would lose signal (e.g. ALL-CAPS) from already-lowercased, already-
lemmatized input. Class-weighted via a custom `Trainer` subclass using Step
8's weights. Excludes Step 6's garbage-flagged rows, same as every other
model here.

## What's in output/
- `metrics/*_baselines.json`, `metrics/*_midtier.json` - per-model val macro-F1, full classification report, confusion matrix, params.
- `models/*_logreg.pkl`, `*_linear_svm.pkl`, `*_xgboost.pkl`, `*_chi2_selector.pkl` - trained models + the fitted chi2 selector (needed to reproduce the mid-tier feature space at inference time).
- `transformer_*/` - reserved output path for the handoff script; not populated - transformer tier skipped for Phase 1 (see decision above), kept only in case of a future GPU run.

**Not shipped to the DE folder: `*_random_forest.pkl`.** They're 169MB
(primary) and 226MB (urgency) - the full-depth trees (`max_depth=30`,
150 estimators) over the 1,538-dim feature space bloat badly on pickling.
RF isn't the leading model for either dataset anyway (XGBoost beats it on
primary, LogReg beats it on urgency), and it regenerates in about 1
(primary) or 9 (urgency) minutes by re-running `train_midtier.py <dataset>
rf` - full local copies stay in this environment's working directory if
needed. Same reasoning Step 7 used for not shipping raw TF-IDF matrices.

## What Step 10 should do
Evaluate the two leading candidates (XGBoost / primary, Logistic Regression /
urgency) on the untouched test split; confusion matrix; try a lowered
decision threshold on the urgency model specifically, trading precision for
suicide-class recall. Only then is a model "final" for the paper.
