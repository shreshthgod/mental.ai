# SHAP - Corrected Findings (Reliable, Prevalence-Gated Only)

Only the corrected view: terms present in ≥0.5% of test rows, ranked by
SHAP impact measured on the rows that actually contain them (not diluted
by the rows that don't), cross-checked against Step 6's curated
crisis-keyword list and Step 7's emotion lexicon. The old frequency-averaged
rankings are not repeated here - see Step 11's README for those and for
the full methodology.

## primary_dataset (XGBoost) - top 20 reliable terms

| Feature | Prevalence | Impact when present | Signal category |
|---|---|---|---|
| restless | 0.6% (n=31) | 0.337 | emotion_specific |
| health anxiety | 1.2% (n=61) | 0.229 | emotion_specific |
| suicidal | 4.9% (n=250) | 0.222 | emotion_specific |
| stress | 4.5% (n=228) | 0.175 | emotion_specific |
| emo_lex_worry *(structural)* | 99.2% (n=5,060) | 0.168 | structural_feature |
| depression | 12.1% (n=619) | 0.165 | emotion_specific |
| ha | 2.1% (n=107) | 0.163 | emotion_specific |
| ve | 2.3% (n=116) | 0.157 | emotion_specific |
| urgency_keyword_count *(structural)* | 19.9% (n=1,016) | 0.150 | structural_feature |
| word_count *(structural)* | 100.0% (n=5,103) | 0.128 | structural_feature |
| char_count *(structural)* | 100.0% (n=5,103) | 0.127 | structural_feature |
| bipolar | 2.5% (n=130) | 0.125 | emotion_specific |
| avg_word_len *(structural)* | 100.0% (n=5,103) | 0.118 | structural_feature |
| depress | 4.3% (n=218) | 0.114 | emotion_specific |
| fuck | 8.5% (n=432) | 0.110 | emotion_specific |
| don | 2.9% (n=150) | 0.110 | emotion_specific |
| mania | 0.6% (n=32) | 0.110 | unmatched_needs_manual_review |
| ptsd | 0.8% (n=42) | 0.109 | unmatched_needs_manual_review |
| flesch_kincaid_grade *(structural)* | 100.0% (n=5,102) | 0.108 | structural_feature |
| manic | 1.0% (n=49) | 0.106 | emotion_specific |

Rare-but-real, below the 0.5% cutoff so excluded above: avpd, pdoc,
lamictal, depakote - each in 5–19 of 5,103 test posts (0.1–0.4%),
individually strong when present, too rare to call "top words."

## urgency_dataset (Logistic Regression) - reliable terms, n=2,000 sample

**Toward suicide:**

| Feature | Prevalence | Impact when present | Signal category |
|---|---|---|---|
| suicidal | 7.5% (n=151) | 0.857 | emotion_specific |
| suicide | 11.4% (n=228) | 0.837 | curated_crisis_keyword |
| overdose | 1.8% (n=36) | 0.604 | curated_crisis_keyword |
| pill | 3.0% (n=60) | 0.574 | emotion_specific |
| rope | 0.7% (n=14) | 0.501 | curated_crisis_keyword |
| noose | 0.6% (n=12) | 0.467 | curated_crisis_keyword |
| hang myself | 0.9% (n=18) | 0.467 | emotion_specific |
| tonight | 2.8% (n=56) | 0.464 | emotion_specific |
| painless | 0.8% (n=16) | 0.421 | curated_crisis_keyword |
| kill yourself | 0.8% (n=15) | 0.413 | curated_crisis_keyword |
| end it | 5.0% (n=100) | 0.410 | emotion_specific |
| kill myself | 11.6% (n=232) | 0.407 | curated_crisis_keyword |
| kill | 16.3% (n=326) | 0.406 | curated_crisis_keyword |
| method | 1.1% (n=22) | 0.393 | curated_crisis_keyword |
| jump | 1.9% (n=39) | 0.387 | emotion_specific |

**Toward non-suicide:**

| Feature | Prevalence | Impact when present | Signal category |
|---|---|---|---|
| filler | 0.7% (n=14) | −1.594 | emotion_specific |
| filler filler | 0.6% (n=11) | −0.956 | emotion_specific |
| horny | 0.7% (n=13) | −0.917 | emotion_specific |
| award | 0.8% (n=16) | −0.873 | emotion_specific |
| minecraft | 0.9% (n=19) | −0.832 | unmatched_needs_manual_review |
| dm | 1.3% (n=26) | −0.807 | emotion_specific |
| meme | 1.2% (n=24) | −0.807 | emotion_specific |
| discord | 0.9% (n=19) | −0.800 | unmatched_needs_manual_review |
| teenager | 1.6% (n=33) | −0.700 | emotion_specific |
| bore | 2.0% (n=40) | −0.666 | emotionally_flat_likely_correlate |
| anyone want | 1.0% (n=20) | −0.657 | emotion_specific |
| my crush | 0.8% (n=17) | −0.612 | emotion_specific |
| dm me | 0.8% (n=15) | −0.597 | emotion_specific |
| be bore | 1.0% (n=20) | −0.566 | emotion_specific |
| hot | 1.1% (n=23) | −0.551 | emotion_specific |

For reference: "die" (15.9% of the sample, impact −0.302) and "to die"
(8.3%, −0.329) are still real non-suicide signal - they just no longer
lead this ranking once rarer, more specific terms are compared on equal
footing.

Full CSVs: `output/explainability/primary_dataset_shap_reliable_terms.csv`,
`output/explainability/urgency_dataset_shap_reliable_terms.csv`. Charts:
`primary_dataset_shap_reliable_bar.png`, `urgency_dataset_shap_reliable_bar.png`.
