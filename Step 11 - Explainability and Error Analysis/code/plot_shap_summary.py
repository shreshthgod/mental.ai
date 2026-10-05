"""
Step 11b (cont.) -- bar-chart versions of the SHAP importances, for the paper.

--- REVISION (post-review) ---
Every bar now carries its prevalence (what % of posts actually contain that
word) directly in the label, so a reader never sees "this word matters" without
also seeing "and here's how many posts it came from." Two charts per dataset:
the original frequency-weighted top-20 (kept, relabeled to be explicit about
what it is), and a new "reliable terms" chart -- prevalence-gated (>=0.5%),
ranked by impact when the word is actually present, and color-coded by
signal_category (cross-checked against the curated crisis-keyword list and
the emotion-association lexicon; see explainability_shap.py's docstring).
"""
import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "Step 11 - Explainability and Error Analysis" / "output" / "explainability"

CATEGORY_COLORS = {
    "curated_crisis_keyword": "#c53030",       # human-vetted crisis vocabulary -- highest trust
    "emotion_specific": "#2b6cb0",              # real, peaked emotional association
    "emotionally_flat_likely_correlate": "#a0aec0",   # generic word, flag as possible artifact
    "unmatched_needs_manual_review": "#dd6b20", # not found in either source -- needs a human
    "structural_feature": "#6b46c1",            # handcrafted, not a word at all
}


def _color_for(cats):
    return [CATEGORY_COLORS.get(c, "#718096") for c in cats]


def _labels_with_prevalence(df, feature_col="feature", prevalence_col="prevalence_pct"):
    return [f"{f}  ({p:.1f}%)" for f, p in zip(df[feature_col], df[prevalence_col])]


# ============================== primary_dataset ==============================

full = pd.read_csv(f"{OUT_DIR}/primary_dataset_shap_global_importance.csv")
reliable = pd.read_csv(f"{OUT_DIR}/primary_dataset_shap_reliable_terms.csv")

# Chart 1: original view, now labeled for what it actually is + prevalence shown
imp = full.head(20).iloc[::-1]
fig, ax = plt.subplots(figsize=(8, 7))
ax.barh(_labels_with_prevalence(imp), imp["mean_abs_shap"], color=_color_for(imp["signal_category"]))
ax.set_xlabel("mean |SHAP value| across ALL test rows (frequency-weighted)")
ax.set_title("primary_dataset (XGBoost) — top 20 by overall mean |SHAP|\n(label shows % of posts containing the term)")
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/primary_dataset_shap_bar.png", dpi=150)
plt.close(fig)
print(f"saved {OUT_DIR}/primary_dataset_shap_bar.png", flush=True)

# Chart 2 (new): reliable terms, prevalence-gated, ranked by impact when present
rel = reliable.head(20).iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 7))
ax.barh(_labels_with_prevalence(rel), rel["mean_abs_shap_when_present"], color=_color_for(rel["signal_category"]))
ax.set_xlabel("mean |SHAP value| among posts that actually contain the term")
ax.set_title("primary_dataset (XGBoost) — top 20 RELIABLE terms (≥0.5% prevalence)\nranked by impact WHEN PRESENT, not diluted by absence")
handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in CATEGORY_COLORS.values()]
ax.legend(handles, CATEGORY_COLORS.keys(), loc="lower right", fontsize=7)
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/primary_dataset_shap_reliable_bar.png", dpi=150)
plt.close(fig)
print(f"saved {OUT_DIR}/primary_dataset_shap_reliable_bar.png", flush=True)

# ============================== urgency_dataset ==============================

top = json.load(open(f"{OUT_DIR}/urgency_dataset_shap_top_terms.json"))
toward_s = pd.DataFrame(top["toward_suicide"]).iloc[::-1]
# NOTE (bugfix): toward_ns/rel_ns are already sorted strongest-first (most
# negative = strongest push toward non-suicide). barh() draws the first row
# at the BOTTOM of the chart, so without reversing, the strongest term ends
# up at the bottom and the weakest at the top -- backwards relative to the
# "toward suicide" panel, which IS reversed. Both lists need the same
# .iloc[::-1] so "strongest at top" holds on both sides of every chart.
toward_ns = pd.DataFrame(top["toward_non_suicide"]).iloc[::-1]

fig, axes = plt.subplots(1, 2, figsize=(13, 6), sharey=False)
axes[0].barh(toward_s["feature"], toward_s["mean_signed_shap"], color="#c53030")
axes[0].set_title("Pushes toward 'suicide'")
axes[0].set_xlabel("mean signed SHAP value (all test-sample rows)")
axes[1].barh(toward_ns["feature"], toward_ns["mean_signed_shap"], color="#2b6cb0")
axes[1].set_title("Pushes toward 'non-suicide'")
axes[1].set_xlabel("mean signed SHAP value (all test-sample rows)")
fig.suptitle(f"urgency_dataset (LogReg) — top terms by OVERALL mean SHAP (frequency-weighted), n={top['sample_size']}")
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/urgency_dataset_shap_bar.png", dpi=150)
plt.close(fig)
print(f"saved {OUT_DIR}/urgency_dataset_shap_bar.png", flush=True)

# Chart 2 (new): reliable terms, prevalence-gated, ranked by signed impact when present
rel_s = pd.DataFrame(top["reliable_toward_suicide"]).iloc[::-1]
rel_ns = pd.DataFrame(top["reliable_toward_non_suicide"]).iloc[::-1]  # same bugfix as toward_ns above

fig, axes = plt.subplots(1, 2, figsize=(15, 6.5), sharey=False)
axes[0].barh(_labels_with_prevalence(rel_s), rel_s["mean_signed_shap_when_present"],
             color=_color_for(rel_s["signal_category"]))
axes[0].set_title("Pushes toward 'suicide' (when present)")
axes[0].set_xlabel("mean signed SHAP value among rows containing the term")
axes[1].barh(_labels_with_prevalence(rel_ns), rel_ns["mean_signed_shap_when_present"],
             color=_color_for(rel_ns["signal_category"]))
axes[1].set_title("Pushes toward 'non-suicide' (when present)")
axes[1].set_xlabel("mean signed SHAP value among rows containing the term")
handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in CATEGORY_COLORS.values()]
fig.legend(handles, CATEGORY_COLORS.keys(), loc="lower center", ncol=3, fontsize=7)
fig.suptitle(f"urgency_dataset (LogReg) — RELIABLE terms (≥0.5% prevalence), n={top['sample_size']}\n"
             "label shows % of the sample containing the term")
fig.tight_layout(rect=[0, 0.08, 1, 1])
fig.savefig(f"{OUT_DIR}/urgency_dataset_shap_reliable_bar.png", dpi=150)
plt.close(fig)
print(f"saved {OUT_DIR}/urgency_dataset_shap_reliable_bar.png", flush=True)

print("DONE", flush=True)
