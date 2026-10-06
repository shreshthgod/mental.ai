# Step 8 - Class Imbalance Handling

## The problem
primary_dataset has a 17.9:1 imbalance (Normal 16,012 rows vs. Personality disorder 894
rows, post-Step-7 counts). urgency_dataset does not - it's already ~50/50 by construction
(115,984 suicide vs. 113,770 non-suicide). So this step is really only about
primary_dataset; urgency_dataset needs no imbalance handling at all.

## Decision: class weighting, not SMOTE, not undersampling
The plan named three options (class weighting / SMOTE / capping the majority class).
Went with **inverse-frequency class weighting at training time** as the primary strategy:

- **Why not SMOTE**: SMOTE interpolates between a minority sample's feature vector and
  its nearest neighbors to invent a new "synthetic" sample. That's a well-defined
  operation in dense, continuous feature spaces, but Step 7's main text representation
  is a 30,000-dimension sparse TF-IDF vector - interpolating between two TF-IDF vectors
  produces a point that doesn't correspond to any real (or even plausible) sentence, and
  decoding it back to text isn't possible. Applying SMOTE in TF-IDF space is a known
  pitfall in NLP for exactly this reason (it manufactures nonsense feature vectors, not
  nonsense-but-readable text) - so it wasn't used here.
- **Why not capping/undersampling the majority class**: primary_dataset's Normal class
  is exactly the "not in distress" signal the model needs to see plenty of to avoid
  false positives - throwing away real Normal/Depression rows to force-balance the
  classes would remove genuine data for no benefit, especially since class weighting
  achieves the same re-balancing effect on the loss function without deleting anything.
- **Why class weighting**: reweights each class's contribution to the training loss
  without touching a single row of data - every scikit-learn model planned for Step 9
  (Logistic Regression, Linear SVM, Random Forest, XGBoost) accepts `class_weight` or
  `sample_weight` directly, and a PyTorch/HuggingFace fine-tune (MentalBERT) accepts
  per-class weights in its loss function the same way.

## What was computed
`code/compute_class_weights.py` - inverse-frequency weights, computed from the **train
split only** (never val/test - those must stay at the natural class distribution so
evaluation reflects real-world frequencies, not an artificially rebalanced one):

```
weight(c) = n_train_samples / (n_classes * count(c))
```

This is the same formula scikit-learn's `class_weight="balanced"` uses, computed
explicitly here so the exact numbers are saved and reproducible rather than recomputed
silently inside a model call.

| primary_dataset class | train count | weight |
|---|---|---|
| Normal | 12,810 | 0.4553 |
| Depression | 12,063 | 0.4835 |
| Suicidal | 8,508 | 0.6855 |
| Anxiety | 2,894 | 2.0153 |
| Bipolar | 2,001 | 2.9146 |
| Stress | 1,834 | 3.1800 |
| Personality disorder | 715 | 8.1568 |

| urgency_dataset class | train count | weight |
|---|---|---|
| suicide | 92,794 | 0.9903 |
| non-suicide | 90,992 | 1.0099 |

Confirms urgency_dataset needs essentially no reweighting (both weights ≈ 1.0) -
consistent with it being balanced by construction.

Saved as `output/class_weights.json` for Step 9 to load directly (no need to recompute).

## Secondary, optional artifact: a modestly oversampled train split
`code/make_oversampled_train.py` produces `output/primary_dataset_train_oversampled.csv.gz`
- **not** the recommended default, but available for Step 9 to A/B test against plain
class weighting, in case a model architecture doesn't expose a clean `class_weight`
hook (e.g. some off-the-shelf transformer training loops).

Method: duplicate-with-replacement of **real, existing rows** - deliberately not SMOTE,
for the same TF-IDF-interpolation reason above. Any class below 30% of the majority
class's train count is resampled-with-replacement up to that floor; classes already
above it are untouched:

| class | before | after |
|---|---|---|
| Normal | 12,810 | 12,810 (unchanged) |
| Depression | 12,063 | 12,063 (unchanged) |
| Suicidal | 8,508 | 8,508 (unchanged) |
| Anxiety | 2,894 | 3,843 (+949 duplicated) |
| Bipolar | 2,001 | 3,843 (+1,842 duplicated) |
| Stress | 1,834 | 3,843 (+2,009 duplicated) |
| Personality disorder | 715 | 3,843 (+3,128 duplicated) |

New train size: 48,753 (was 40,825). New imbalance ratio: 3.3:1 (was 17.9:1). Every
duplicated row is marked `is_oversampled_duplicate=True` - nothing is silently changed,
and Step 9 can filter back to the original 40,825 rows at any time.

**val and test are never touched** by this script - oversampling a held-out split would
let a duplicated row's exact text influence both training and evaluation with no actual
benefit (the point of oversampling is only to change what the model sees during
training, not to inflate evaluation counts).

## What Step 9 should do with these artifacts
Default/recommended path: train on primary_dataset's ORIGINAL train split (Step 7's
output, 40,825 rows, natural distribution) with `class_weight` set from
`class_weights.json`. Treat `primary_dataset_train_oversampled.csv.gz` as an optional
experiment to compare against, not a required input.
