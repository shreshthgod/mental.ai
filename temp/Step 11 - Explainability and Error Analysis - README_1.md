# Step 11 — Explainability & Error Analysis

Applied to Step 10's leading models on the test split: XGBoost
(primary_dataset), Logistic Regression (urgency_dataset, at its deployed
0.15 threshold for the false-negative analysis).

> **Revised (post-review):** the first pass ranked SHAP "top words" purely
> by mean |SHAP| averaged across every test row. That conflates two
> different things — how many posts contain a word, and how hard it pushes
> the prediction on the posts that do — so a common, weakly-informative
> word (e.g. "guy", "job") and a rare, strongly-informative one (e.g.
> "overdose") could land at the same rank. It is a fair challenge that the
> original charts implied "everyone used these words," when for most of
> them that wasn't true. This revision adds prevalence (what % of posts
> actually contain the term), a "when present" conditional SHAP value (the
> word's impact only on the rows that have it, not diluted by the rows
> that don't), and a cross-check against two independent, pre-built
> sources — Step 6's human-curated crisis-keyword list and Step 7's
> emotion-association lexicon — so each top term is tagged with how much
> outside evidence backs it up. See `code/explainability_shap.py`'s
> docstring for the full mechanics. This is a validation/filtering layer
> on the existing statistics, not a semantic-understanding model: it still
> can't read meaning, but it stops presenting "used by a few rows with a
> huge effect" and "used by many rows with a small effect" as the same claim.

## Error analysis — primary_dataset (XGBoost)
1,238 of 5,103 test rows misclassified (24.3%). Top confusion pairs:

| True | Predicted | Count |
|---|---|---|
| Depression | Suicidal | 365 |
| Suicidal | Depression | 176 |
| Normal | Stress | 69 |
| Suicidal | Normal | 59 |
| Depression | Stress | 58 |
| Depression | Normal | 57 |
| Depression | Bipolar | 38 |
| Depression | Anxiety | 33 |

**Depression↔Suicidal is the dominant error mode** — 541 of 1,238 total
errors (43.7%), far ahead of any other pair. This isn't primarily a model
weakness: these two classes are genuinely adjacent in real posts (someone
describing depression often also expresses suicidal ideation in the same
post, and the reverse), and the labels are proxy subreddit-of-origin labels,
not a clinician's differential diagnosis. Worth stating directly in the
paper's limitations rather than treating it as a fixable error.

Full misclassified rows: `output/error_analysis/primary_dataset_misclassified.csv`.
Confusion-pair counts: `output/error_analysis/primary_dataset_confusion_pairs.csv`.

## Error analysis — urgency_dataset (Logistic Regression, threshold=0.15)
151 false negatives (real suicide-class posts missed), 2,172 false positives
— consistent with Step 10's numbers. Manually reading the lowest-probability
false negatives (the ones the model was most confidently wrong about)
surfaced a **likely labeling-noise issue**, not a model failure: e.g. a
post reading only "Sad songs — what sad song do you like and why?" carries
the "suicide" class label (probability the model assigned: 0.001) — almost
certainly a subreddit-scrape artifact (an off-topic post pulled from the
source subreddit) rather than a genuine crisis post the model should have
caught. This matches the pipeline's standing caveat that dataset labels are
proxy labels, not clinician-verified (see item 54 in the paper-details doc).

Full false-negative/false-positive rows, sorted by model confidence:
`output/error_analysis/urgency_dataset_false_negatives_at_0.15.csv`,
`..._false_positives_at_0.15.csv`.

## SHAP explainability — primary_dataset (XGBoost, TreeExplainer)
Ran on the full test set (5,103 rows), exact (not approximated) since
TreeExplainer computes exact Shapley values for tree ensembles.

**Two rankings are now reported side by side** (both in
`output/explainability/primary_dataset_shap_global_importance.csv`):

- `mean_abs_shap` — the original, overall-average metric (frequency-weighted;
  diluted by every row that doesn't have the term).
- `mean_abs_shap_when_present` — impact only on the rows that actually
  contain the term, alongside `prevalence_pct` (what share of the 5,103
  test posts contain it) and `n_present` (the raw count). This is the
  number that supports a claim like "this word means X."

`output/explainability/primary_dataset_shap_reliable_terms.csv` restricts
to terms with ≥0.5% prevalence (≥26 of 5,103 rows — enough that the "when
present" mean isn't a fluke of a handful of posts) and ranks by that
conditional impact. Top of that list, with prevalence and the independent
signal-source cross-check (`signal_category` — see the revision note above):

| Feature | Prevalence | Impact when present | Signal category |
|---|---|---|---|
| restless | 0.6% (n=31) | 0.337 | emotion_specific |
| health anxiety | 1.2% (n=61) | 0.229 | emotion_specific |
| suicidal | 4.9% (n=250) | 0.222 | emotion_specific |
| stress | 4.5% (n=228) | 0.175 | emotion_specific |
| emo_lex_worry (structural) | 99.2% (n=5,060) | 0.168 | structural_feature |
| depression | 12.1% (n=619) | 0.165 | emotion_specific |
| urgency_keyword_count (structural) | 19.9% (n=1,016) | 0.150 | structural_feature |
| bipolar | 2.5% (n=130) | 0.125 | emotion_specific |
| depress | 4.3% (n=218) | 0.114 | emotion_specific |
| ptsd | 0.8% (n=42) | 0.109 | unmatched_needs_manual_review |
| manic | 1.0% (n=49) | 0.106 | emotion_specific |

Full top-20 with bar chart: `primary_dataset_shap_reliable_bar.png` (new —
prevalence-gated, color-coded by signal category) and
`primary_dataset_shap_bar.png` (kept — the original overall-frequency view,
now with prevalence shown in each bar's label so it's never presented
without that context).

**Where the original top-ranked clinical terms went**: `avpd` (0.638),
`pdoc` (0.146), `lamictal` (0.142), `depakote` (0.115) each occur in only
5–19 of 5,103 test posts (0.1–0.4% prevalence) — real and individually
strong when they appear, but too rare to trust as a description of "what
the model generally keys on," so the reliable table (which requires
≥0.5% prevalence) correctly excludes them from the headline ranking. They're
still worth citing in the paper as evidence the model has *some* genuinely
clinical, high-precision signal (real diagnosis/medication abbreviations
forum users use) — just as rare-but-real evidence, not as "top words."
Full numbers preserved in the unfiltered CSV.

**Limitation, unchanged**: "pression" (unfiltered rank #2) is almost
certainly a tokenization artifact from a hyphenated/typo'd "de-pression"
split into two tokens by Step 5's tokenizer. It's tagged
`unmatched_needs_manual_review` under the new signal-category check (it
isn't a real word in either the emotion lexicon or the curated keyword
list) — the automated flag now catches this class of issue directly instead
of relying on someone spotting it by eye. Worth a line in the paper's
limitations (item 53).

## SHAP explainability — urgency_dataset (Logistic Regression, LinearExplainer)
Ran on a random 2,000-row test sample (background: 500 random train rows)
— sufficient for a stable ranking; the full 23,000-row test set would only
add runtime, not change which terms rank highest.

**Reliable terms** (≥0.5% prevalence in the 2,000-row sample, ranked by
signed SHAP impact when present — see
`output/explainability/urgency_dataset_shap_reliable_terms.csv` and
`urgency_dataset_shap_reliable_bar.png`):

Toward **suicide** — now dominated by unambiguous crisis vocabulary:
suicidal (7.5%), suicide (11.4%, curated keyword), overdose (1.8%, curated),
pill (3.0%), rope (0.7%, curated), noose (0.6%, curated), hang myself
(0.9%), tonight (2.8%), painless (0.8%, curated), kill yourself (0.8%,
curated), end it (5.0%), kill myself (11.6%, curated), kill (16.3%,
curated), method (1.1%, curated), jump (1.9%). Nine of the top 15 are
independently confirmed against Step 6's human-curated crisis-keyword list.

Toward **non-suicide** — now dominated by casual/social, clearly non-crisis
vocabulary: filler (0.7%), horny (0.7%), award (0.8%), minecraft (0.9%),
dm (1.3%), meme (1.2%), discord (0.9%), teenager (1.6%), bore (2.0%), my
crush (0.8%), hot (1.1%). "minecraft" and "discord" (both flagged
`unmatched_needs_manual_review` — not in either lexicon, but self-evidently
non-crisis) make the subreddit-source explanation below concrete rather
than speculative: these are exactly the words you'd expect from a casual
gaming/social subreddit, not a crisis one.

The **original overall (frequency-weighted) ranking** is kept unchanged for
comparison — help, horny, suicidal, guy, you all, like, job, pill (toward
suicide); to die, die, feel, hope, attempt, bore, will, hang, pain, alone
(toward non-suicide) — see `urgency_dataset_shap_bar.png` and
`urgency_dataset_shap_global_importance.csv`.

**"die" / "to die" — re-examined, not dismissed**: under the new
conditional metric these are still real, substantial signal toward
non-suicide — die appears in 15.9% of the sample (n=318, conditional signed
SHAP −0.302) and "to die" in 8.3% (n=166, −0.329) — they just no longer
look like the *single strongest* signal once rarer-but-more-specific words
(filler, horny, minecraft, discord) are given a fair, prevalence-aware
comparison. Both are tagged `emotion_specific` with a dominant association
of **"love"** in the emotion lexicon, which points to a second plausible
mechanism alongside the subreddit-source explanation: idiomatic hyperbole
("this is to die for," "I'm dying laughing") uses "die" in a positive/casual
register, which the lexicon and the model both pick up as anti-crisis
signal. Both explanations point the same direction — the model may be
partly reading register/subreddit style rather than purely crisis intent —
so the caution in item 56 of the paper-details doc stands, now with
firmer, more specific evidence behind it.

## What's in output/
- `error_analysis/` — misclassified rows (with actual text), confusion-pair counts, false-negative/positive rows for urgency, all sorted by model confidence.
- `explainability/` — SHAP global importance CSVs (`*_shap_global_importance.csv`, unfiltered/overall), the new prevalence-gated `*_shap_reliable_terms.csv`, top-terms JSON, and four bar-chart PNGs (`*_shap_bar.png` = original overall view, `*_shap_reliable_bar.png` = new prevalence-gated + signal-category view).

## What Step 12 should do
Package: bundle the winning models (primary_dataset XGBoost + chi2 selector;
urgency_dataset Logistic Regression + its 0.15 threshold), the fitted
vectorizers, and the feature-extraction code into one reusable inference
module — the last step before Phase 1 is "done." (Already done — see
Step 12's own folder; this note is kept for the record of what was planned
at the time.)
