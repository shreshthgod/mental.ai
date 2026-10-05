"""
Step 11b -- SHAP explainability.

primary_dataset (XGBoost, tree model): shap.TreeExplainer -- exact, fast,
native support for tree ensembles. Run on the full test set (5,103 rows).

urgency_dataset (Logistic Regression, linear model): shap.LinearExplainer
-- exact and fast for linear models, using the train split's TF-IDF matrix
as the background distribution. Run on a random 2,000-row test sample
(sufficient for a stable global ranking; the full 23,000-row test set adds
runtime without changing which words come out on top).

Real feature names are recovered for both: for primary_dataset, chi2-selected
TF-IDF term names (from the fitted vectorizer, filtered by the chi2
selector's support mask) plus the 38 handcrafted feature names; for
urgency_dataset, the full 30,000-term TF-IDF vocabulary.

--- REVISION (post-review) ---
The first version of this script ranked words purely by mean |SHAP value|
averaged over every test row. That single number conflates two very
different things: how many posts actually contain the word, and how hard
the word pushes the prediction on the posts that do. A word used by 40% of
posts with a small, consistent nudge and a word used by 2% of posts with a
huge nudge can land at the same "mean |SHAP|" -- but they don't mean the
same thing, and the bar charts gave no way to tell them apart. That's
exactly the flaw flagged after the first pass: several "top words" (e.g.
"guy", "job", "like", "you all") are common, low-specificity words that
only rank high because of how many rows they touch, not because they
carry real signal -- it is not true that "everyone" used them.

This version adds three things per term, on top of the original metric:
  1. prevalence_pct / n_present -- what fraction of posts actually contain
     this feature. Printed and plotted everywhere the word itself is shown,
     so a reader never sees a word's importance without also seeing how
     many posts it came from.
  2. mean_abs_shap_when_present -- mean |SHAP| computed only over the rows
     where the feature is actually present, instead of diluted by all the
     rows where it isn't. This is "how much does it matter when it's
     actually used", which is what "this word means X" implicitly claims.
  3. signal_category -- a cross-check against two independent, pre-built
     sources instead of just the model's own SHAP output: Step 6's curated
     crisis-keyword list (human-vetted) and Step 7's custom per-word
     emotion-association lexicon (built from a separate labeled dataset).
     A term is tagged "curated_crisis_keyword" (highest trust), "emotion_
     specific" (has a real, peaked emotional association), "emotionally_
     flat_likely_correlate" (in the lexicon but with no specific emotional
     pull -- a generic/connective word whose SHAP rank is probably a
     frequency or co-occurrence artifact, not a meaningful signal), or
     "unmatched_needs_manual_review" (not found in either source --
     includes tokenization fragments and rare abbreviations that need a
     human to judge). Handcrafted (non-word) features are tagged
     "structural_feature".

The headline "reliable terms" table/plot for each dataset now ranks by
mean_abs_shap_when_present, restricted to terms with prevalence >= 0.5%
(so the estimate isn't based on a handful of rows), and always shows
prevalence and signal_category next to the word. The original overall
mean-|SHAP| ranking is kept too (unfiltered), so nothing is hidden -- it's
now clearly labeled as the frequency-weighted view rather than presented
as the only view.

This is a validation/filtering layer on top of the existing statistics,
not a semantic-understanding model -- it still can't "read" a word's
meaning. What it does is stop treating "appears often across many rows"
and "means something when it appears" as the same claim, and it flags
which top words are backed by an independent source vs. which are raw
statistical correlates that need a human to sanity-check.
"""
import sys
import json
import pickle
import numpy as np
import pandas as pd
import scipy.sparse as sp
import shap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "Step 9 - Model Training" / "code"))
from data_utils import DATASETS, load_handcrafted, load_tfidf, load_vectorizer, labels_for

MODELS_DIR = REPO_ROOT / "Step 9 - Model Training" / "output" / "models"
OUT_DIR = REPO_ROOT / "Step 11 - Explainability and Error Analysis" / "output" / "explainability"
EMOTION_LEXICON_PATH = REPO_ROOT / "Step 7 - Feature Extraction" / "output" / "emotion_lexicon.json"
CURATED_KEYWORDS_PATH = REPO_ROOT / "Step 6 - EDA on Cleaned Data" / "findings" / "urgency_keyword_candidates.json"

RELIABLE_MIN_PREVALENCE_PCT = 0.5     # a term needs to appear in >=0.5% of rows
                                       # before its "when present" mean is trusted
EMOTION_SPECIFIC_THRESHOLD = 0.10     # peak association minus the uniform baseline
                                       # (1/n_classes); above this = a real, specific
                                       # emotional pull, not a flat/generic profile


def _load_signal_sources():
    with open(EMOTION_LEXICON_PATH) as f:
        emo = json.load(f)
    emo_lexicon = emo["lexicon"]
    emo_classes = emo["classes"]
    baseline = 1.0 / len(emo_classes)

    with open(CURATED_KEYWORDS_PATH) as f:
        curated = json.load(f)
    curated_kw = set(curated["curated_urgency_keywords"] if isinstance(curated, dict) else curated)

    return emo_lexicon, baseline, curated_kw


def _term_signal(term, feature_type, emo_lexicon, baseline, curated_kw):
    """Cross-check one feature against independent sources. Returns
    (signal_category, dominant_emotion_if_specific)."""
    if feature_type == "handcrafted":
        return "structural_feature", ""

    words = term.split()
    if any(w in curated_kw for w in words):
        return "curated_crisis_keyword", ""

    best_peak, best_emotion, matched = -1.0, "", False
    for w in words:
        scores = emo_lexicon.get(w)
        if scores is None:
            continue
        matched = True
        dom = max(scores, key=scores.get)
        peak = scores[dom] - baseline
        if peak > best_peak:
            best_peak, best_emotion = peak, dom

    if not matched:
        return "unmatched_needs_manual_review", ""
    if best_peak >= EMOTION_SPECIFIC_THRESHOLD:
        return "emotion_specific", best_emotion
    return "emotionally_flat_likely_correlate", best_emotion


def explain_primary():
    cfg = DATASETS["primary"]
    hand_df, feat_cols = load_handcrafted("primary")
    test_mask = (hand_df["split"] == "test").values
    y_test = labels_for("primary", hand_df, test_mask)

    X_tfidf_test = load_tfidf("primary", "test")
    with open(f"{MODELS_DIR}/primary_dataset_chi2_selector.pkl", "rb") as f:
        skb = pickle.load(f)
    X_tfidf_test_red = skb.transform(X_tfidf_test)
    X_hand_test = sp.csr_matrix(hand_df.loc[test_mask, feat_cols].values.astype(np.float32))
    X_test = sp.hstack([X_tfidf_test_red, X_hand_test], format="csr")

    vec = load_vectorizer("primary")
    tfidf_names = np.array(vec.get_feature_names_out())[skb.get_support()]
    feature_names = list(tfidf_names) + list(feat_cols)
    feature_type = ["tfidf_term"] * len(tfidf_names) + ["handcrafted"] * len(feat_cols)
    assert len(feature_names) == X_test.shape[1]

    with open(f"{MODELS_DIR}/primary_dataset_xgboost.pkl", "rb") as f:
        bundle = pickle.load(f)
    xgb, le = bundle["model"], bundle["label_encoder"]

    explainer = shap.TreeExplainer(xgb)
    X_test_dense = X_test.toarray()
    shap_values = explainer.shap_values(X_test_dense)
    shap_values = np.array(shap_values)
    if shap_values.ndim == 3:
        per_sample_abs = np.abs(shap_values).mean(axis=2)   # (n_samples, n_features), averaged across classes
    else:
        per_sample_abs = np.abs(shap_values)

    mean_abs = per_sample_abs.mean(axis=0)                  # original metric: diluted by rows where absent

    present_mask = X_test_dense != 0
    n_present = present_mask.sum(axis=0)
    prevalence_pct = 100.0 * n_present / X_test_dense.shape[0]

    cond_mean_abs = np.full_like(mean_abs, np.nan)
    for j in range(len(mean_abs)):
        if n_present[j] > 0:
            cond_mean_abs[j] = per_sample_abs[present_mask[:, j], j].mean()

    emo_lexicon, baseline, curated_kw = _load_signal_sources()
    signal_category, dominant_emotion = [], []
    for term, ftype in zip(feature_names, feature_type):
        cat, emo = _term_signal(term, ftype, emo_lexicon, baseline, curated_kw)
        signal_category.append(cat)
        dominant_emotion.append(emo)

    importance = pd.DataFrame({
        "feature": feature_names,
        "feature_type": feature_type,
        "mean_abs_shap": mean_abs,
        "prevalence_pct": prevalence_pct,
        "n_present": n_present,
        "mean_abs_shap_when_present": cond_mean_abs,
        "signal_category": signal_category,
        "dominant_emotion_if_specific": dominant_emotion,
    })
    importance = importance.sort_values("mean_abs_shap", ascending=False)
    importance.to_csv(f"{OUT_DIR}/primary_dataset_shap_global_importance.csv", index=False)

    reliable = importance[importance["prevalence_pct"] >= RELIABLE_MIN_PREVALENCE_PCT].copy()
    reliable = reliable.sort_values("mean_abs_shap_when_present", ascending=False)
    reliable.to_csv(f"{OUT_DIR}/primary_dataset_shap_reliable_terms.csv", index=False)

    print("primary_dataset (XGBoost) -- top 20 by overall mean |SHAP| (frequency-weighted):", flush=True)
    for _, row in importance.head(20).iterrows():
        print(f"  {row['feature']:<30} mean_abs={row['mean_abs_shap']:.4f}  "
              f"prevalence={row['prevalence_pct']:.1f}%  category={row['signal_category']}", flush=True)

    print(f"\nprimary_dataset -- top 20 RELIABLE terms (>= {RELIABLE_MIN_PREVALENCE_PCT}% prevalence, "
          f"ranked by impact WHEN PRESENT, not diluted by absence):", flush=True)
    for _, row in reliable.head(20).iterrows():
        print(f"  {row['feature']:<30} when_present={row['mean_abs_shap_when_present']:.4f}  "
              f"prevalence={row['prevalence_pct']:.1f}% (n={int(row['n_present'])})  "
              f"category={row['signal_category']}", flush=True)

    return importance, reliable


def explain_urgency(sample_n=2000, seed=42):
    cfg = DATASETS["urgency"]
    hand_df, feat_cols = load_handcrafted("urgency")
    test_mask = (hand_df["split"] == "test").values
    train_mask = (hand_df["split"] == "train").values

    X_tfidf_test = load_tfidf("urgency", "test")
    X_tfidf_train = load_tfidf("urgency", "train")

    rng = np.random.default_rng(seed)
    n_test = X_tfidf_test.shape[0]
    sample_idx = rng.choice(n_test, size=min(sample_n, n_test), replace=False)
    X_sample = X_tfidf_test[sample_idx]

    bg_idx = rng.choice(X_tfidf_train.shape[0], size=500, replace=False)
    X_background = X_tfidf_train[bg_idx]

    vec = load_vectorizer("urgency")
    feature_names = vec.get_feature_names_out()

    with open(f"{MODELS_DIR}/urgency_dataset_logreg.pkl", "rb") as f:
        lr = pickle.load(f)

    explainer = shap.LinearExplainer(lr, X_background)
    shap_values = explainer.shap_values(X_sample)
    if isinstance(shap_values, list):
        shap_values = shap_values[list(lr.classes_).index("suicide")]
    shap_values = np.asarray(shap_values)

    mean_shap = shap_values.mean(axis=0)
    mean_abs_shap = np.abs(shap_values).mean(axis=0)

    importance = pd.DataFrame({
        "feature": feature_names, "mean_signed_shap": mean_shap, "mean_abs_shap": mean_abs_shap,
    }).sort_values("mean_abs_shap", ascending=False)
    importance.to_csv(f"{OUT_DIR}/urgency_dataset_shap_global_importance.csv", index=False)

    # Conditional stats + signal-source cross-check are only computed for a
    # candidate set of terms (union of top by |mean| and by each signed
    # extreme) -- covers everything that could plausibly appear in any
    # headline table, without densifying the full 2000x30000 sample matrix.
    candidates = pd.concat([
        importance.head(500),
        importance.sort_values("mean_signed_shap", ascending=False).head(200),
        importance.sort_values("mean_signed_shap", ascending=True).head(200),
    ]).drop_duplicates(subset="feature")

    vocab_index = {name: i for i, name in enumerate(feature_names)}
    X_sample_csc = X_sample.tocsc()
    emo_lexicon, baseline, curated_kw = _load_signal_sources()

    n_present_l, prevalence_l, cond_abs_l, cond_signed_l, cat_l, emo_l = [], [], [], [], [], []
    for term in candidates["feature"]:
        j = vocab_index[term]
        col = X_sample_csc[:, j]
        rows = col.indices  # row indices where this term is present in the sample
        n_present = len(rows)
        n_present_l.append(n_present)
        prevalence_l.append(100.0 * n_present / X_sample.shape[0])
        if n_present > 0:
            cond_abs_l.append(np.abs(shap_values[rows, j]).mean())
            cond_signed_l.append(shap_values[rows, j].mean())
        else:
            cond_abs_l.append(np.nan)
            cond_signed_l.append(np.nan)
        cat, emo = _term_signal(term, "tfidf_term", emo_lexicon, baseline, curated_kw)
        cat_l.append(cat)
        emo_l.append(emo)

    candidates = candidates.assign(
        n_present=n_present_l, prevalence_pct=prevalence_l,
        mean_abs_shap_when_present=cond_abs_l, mean_signed_shap_when_present=cond_signed_l,
        signal_category=cat_l, dominant_emotion_if_specific=emo_l,
    )

    reliable = candidates[candidates["prevalence_pct"] >= RELIABLE_MIN_PREVALENCE_PCT].copy()
    reliable_toward_suicide = reliable.sort_values("mean_signed_shap_when_present", ascending=False).head(15)
    reliable_toward_nonsuicide = reliable.sort_values("mean_signed_shap_when_present", ascending=True).head(15)
    reliable.sort_values("mean_abs_shap_when_present", ascending=False).to_csv(
        f"{OUT_DIR}/urgency_dataset_shap_reliable_terms.csv", index=False)

    # keep the original (unfiltered, frequency-weighted) top-terms view too
    top_toward_suicide = importance.sort_values("mean_signed_shap", ascending=False).head(15)
    top_toward_nonsuicide = importance.sort_values("mean_signed_shap", ascending=True).head(15)

    print(f"\nurgency_dataset (Logistic Regression, n={len(sample_idx)} test sample) "
          f"-- top terms toward 'suicide' by OVERALL mean SHAP (frequency-weighted):", flush=True)
    for _, row in top_toward_suicide.iterrows():
        print(f"  {row['feature']:<20} mean_shap={row['mean_signed_shap']:.4f}", flush=True)
    print("-- top terms toward 'non-suicide' (frequency-weighted):", flush=True)
    for _, row in top_toward_nonsuicide.iterrows():
        print(f"  {row['feature']:<20} mean_shap={row['mean_signed_shap']:.4f}", flush=True)

    print(f"\n-- RELIABLE terms toward 'suicide' (>= {RELIABLE_MIN_PREVALENCE_PCT}% prevalence, "
          f"ranked by signed impact WHEN PRESENT):", flush=True)
    for _, row in reliable_toward_suicide.iterrows():
        print(f"  {row['feature']:<20} when_present={row['mean_signed_shap_when_present']:.4f}  "
              f"prevalence={row['prevalence_pct']:.1f}% (n={int(row['n_present'])})  "
              f"category={row['signal_category']}", flush=True)
    print("-- RELIABLE terms toward 'non-suicide':", flush=True)
    for _, row in reliable_toward_nonsuicide.iterrows():
        print(f"  {row['feature']:<20} when_present={row['mean_signed_shap_when_present']:.4f}  "
              f"prevalence={row['prevalence_pct']:.1f}% (n={int(row['n_present'])})  "
              f"category={row['signal_category']}", flush=True)

    with open(f"{OUT_DIR}/urgency_dataset_shap_top_terms.json", "w") as f:
        json.dump({
            "toward_suicide": top_toward_suicide.to_dict(orient="records"),
            "toward_non_suicide": top_toward_nonsuicide.to_dict(orient="records"),
            "reliable_toward_suicide": reliable_toward_suicide.to_dict(orient="records"),
            "reliable_toward_non_suicide": reliable_toward_nonsuicide.to_dict(orient="records"),
            "sample_size": len(sample_idx),
            "reliable_min_prevalence_pct": RELIABLE_MIN_PREVALENCE_PCT,
        }, f, indent=2, default=str)

    return importance, reliable


if __name__ == "__main__":
    explain_primary()
    explain_urgency()
    print("\nDONE", flush=True)
