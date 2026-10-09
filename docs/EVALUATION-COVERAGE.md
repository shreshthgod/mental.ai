# Evaluation coverage and provenance

Current diagnostic reports: reports/safety-run-20261008T203220Z.json (default, exit1), reports/safety-run-20261008T203518Z.json (separate temporal proposal, exit1). Policy .6; repeat execution is reproducibility, not a new independent observation. Each report contains exact source/model/config/corpus hashes, raw output, temporal/subject/support assertions, failures and coverage. This is engineering evaluation, not clinical validation.

## Data roles

| Role | Actual data | Provenance / use | Status |
|---|---|---|---|
| A regression | tests/safety_corpus/cases.json and expansion.json;321 identities (S001–S072,M001–M006,243 X cases) |78 developer-engineered seeds and243 generated, no clinical review; consumed while repairing | PASSED provenance recorded; default behavior FAILED |
| A temporal annotations | temporal-seeds-v1.json supplies78 seed times; temporal-review-v2.json contains62 sparse original/proposed/rationale/review rows | Separate developer proposals only; input/route/subject originals untouched; not independent reviewed labels | PASSED metadata/explicit separation; external semantic review BLOCKED |
| B consumed diagnostics | holdout.json and holdout2.json; RUN-02/RUN-04 reports | Exposed past stage-specific holdouts; --include-holdout is diagnostic only. Historical25/35 and15/30 concern different stages, never combined into current score | PASSED preserved; not fresh evaluation |
| C development/validation | evaluation/semantic-development-v1.json,36/18 | Developer synthetic labels, authored before candidate inference; fit only36 development; shared semantic families; exact overlapA/B/within split0, independent pretraining/semantic overlap unknown | PASSED experiment/provenance; no reviewed validation claim |
| D final independent evaluation | unavailable | Needs independently sourced/reviewed labels, qualified policy review and sealed split; never tune from D | BLOCKED: reviewed data/reviewers missing |

Current exact duplicate group: X126/X129/X130, shared paraphrase group S054.321 cases contain311 distinct paraphrase groups; correlated cases are not321 independent observations. Subject asserted238,83 explicit opt-outs;0/238 asserted errors does not certify the83. Temporal expectations are asserted321/321 in each chosen annotation version. No missing mandatory family;43 actual families (aliases/extra families retained).

## Counts with declared scope

| Measure | Default engine | Default actual-model pipeline | Separate temporal-proposal pipeline |
|---|---|---|---|
| Required assertions pass |259/321|214/321|252/321|
| Mandatory urgent routed urgent |98/98|98/98|98/98|
| Mandatory urgent misses |0/98|0/98|0/98|
| Benign urgent escalation |0/73|0/73|0/73|
| Benign NONE / clarification / UNKNOWN |73 /0 /0 of73|14 /37 /22 of73|14 /37 /22 of73|
| UNKNOWN across all cases |9/321|44/321|44/321|
| Clarification across all cases |15/321|61/321|61/321|
| Subject errors |0/238 asserted|0/238 asserted|0/238 asserted|
| Temporal disagreements |62/321|62/321|0/321 under proposals|
| Support/prohibited assertion errors |0/321|0/321|0/321|

The131 urgent outputs in each layer are within an allowed urgent range131/131. This allowed-action agreement is not binary clinical precision:33 cases permit flexible urgency instead of supplying an independent binary urgent label. Raw classifiers have no valid diagnosis oracle in this synthetic corpus, so diagnostic accuracy/calibration is NOT_APPLICABLE here. Independent clinical precision/calibration and confidence intervals are BLOCKED on reviewed independent data. Binomial intervals treating these correlated engineered rows as independent are NOT_APPLICABLE; small sample limits and dependence are explicit. Benign37/73 clarifications and22/73 abstentions remain a usefulness limitation, not hidden success.

## Family coverage (default and proposed-temporal diagnostic)

All labels below are developer-generated/unreviewed. Combined transcript family multi_turn is plain one-field input; genuine memory is unsupported.

| Family | Cases | Groups | Default engine pass | Default pipeline pass | Proposed-time pipeline pass |
|---|---|---|---|---|---|
| abuse | 4 | 4 | 4/4 | 4/4 | 4/4 |
| benign_control | 28 | 28 | 28/28 | 10/28 | 10/28 |
| capitalization | 5 | 2 | 5/5 | 5/5 | 5/5 |
| devanagari | 9 | 9 | 5/9 | 5/9 | 6/9 |
| distress | 3 | 3 | 2/3 | 2/3 | 2/3 |
| double_negation | 6 | 6 | 4/6 | 4/6 | 6/6 |
| education_frame | 5 | 5 | 5/5 | 4/5 | 4/5 |
| explicit_intent | 18 | 18 | 18/18 | 18/18 | 18/18 |
| fiction_quotation | 6 | 6 | 1/6 | 1/6 | 6/6 |
| healthcare_context | 7 | 7 | 1/7 | 1/7 | 3/7 |
| hinglish | 12 | 12 | 8/12 | 8/12 | 8/12 |
| historical | 6 | 6 | 6/6 | 5/6 | 5/6 |
| idiom | 15 | 15 | 15/15 | 1/15 | 1/15 |
| immediate_danger | 1 | 1 | 1/1 | 1/1 | 1/1 |
| indirect_language | 6 | 6 | 2/6 | 2/6 | 6/6 |
| long_text | 4 | 1 | 3/4 | 3/4 | 3/4 |
| medical_emergency | 7 | 7 | 7/7 | 7/7 | 7/7 |
| minor_safety | 4 | 4 | 4/4 | 4/4 | 4/4 |
| mixed_context | 4 | 4 | 4/4 | 4/4 | 4/4 |
| multi_turn | 16 | 16 | 13/16 | 13/16 | 15/16 |
| negation | 16 | 16 | 10/16 | 9/16 | 15/16 |
| out_of_domain | 3 | 3 | 3/3 | 3/3 | 3/3 |
| out_of_vocabulary | 9 | 9 | 6/9 | 6/9 | 7/9 |
| overdiagnosis_control | 13 | 13 | 8/13 | 7/13 | 9/13 |
| passive_wish | 12 | 12 | 6/12 | 6/12 | 12/12 |
| present_access | 4 | 4 | 4/4 | 4/4 | 4/4 |
| prompt_injection | 15 | 15 | 15/15 | 11/15 | 11/15 |
| psychosis | 7 | 7 | 6/7 | 6/7 | 7/7 |
| quotation_self_assertion | 4 | 4 | 2/4 | 2/4 | 4/4 |
| recent_act | 6 | 6 | 5/6 | 5/6 | 6/6 |
| recovery | 4 | 4 | 0/4 | 0/4 | 0/4 |
| sarcasm_disclaimer | 1 | 1 | 1/1 | 1/1 | 1/1 |
| self_harm_no_intent | 5 | 5 | 4/5 | 4/5 | 5/5 |
| shorthand | 6 | 6 | 6/6 | 6/6 | 6/6 |
| stated_timing | 7 | 7 | 6/7 | 6/7 | 6/7 |
| technical_idiom | 5 | 5 | 5/5 | 0/5 | 0/5 |
| test_wrapper | 4 | 4 | 4/4 | 4/4 | 4/4 |
| third_party | 6 | 6 | 6/6 | 6/6 | 6/6 |
| uncertainty | 11 | 11 | 11/11 | 11/11 | 11/11 |
| unicode_obfuscation | 3 | 2 | 3/3 | 3/3 | 3/3 |
| unsupported_language | 5 | 5 | 5/5 | 5/5 | 5/5 |
| unwanted_thought | 5 | 5 | 3/5 | 3/5 | 5/5 |
| violence | 4 | 4 | 4/4 | 4/4 | 4/4 |

## Language and length scope

| Slice | Default pipeline required pass | Mandatory urgent routing |
|---|---|---|
| en | 196/295 | 87/87 |
| hi | 5/9 | 5/5 |
| hinglish | 8/12 | 6/6 |
| other | 5/5 | 0/0 |
| short, at most40 code points | 95/156 | 36/36 |
| long_text fixture family | 3/4 | 3/3 |

Language tags are corpus annotations, not proof that detection/comprehension works. Capability statuses are312 degraded/9 unsupported, no complete assessment. Unsupported text may still preserve reliably recognized supported danger. Hindi/Hinglish/mixed/homoglyph/short German examples are engineering coverage, not unrestricted multilingual validity.

## Candidate and operational evidence

Pinned local MiniLM ONNX/logistic comparison is reports/semantic-candidate-20261008-v1.json: baseline10/18 labels,1/6 urgent; candidate13/18 labels,5/6 urgent and1/6 benign urgent false escalation. Candidate disabled. Model card Apache2, model hash6fd5d72fe4589f189f8ebc006442dbb529bb7ce38f8082112682524616046452; underlying data licensing/pretraining overlap/qualified review not independently established. No repository license file was found; legacy dataset/artifact/lexicon license provenance needs source-owner evidence before a release licensing claim.

480-test pre-copy and481-test final backend suites,54 frontend module checks,35 actual browser checks are engineering checks, not statistical samples. Shared16 success/3 error fixtures are synthetic contract states; API inference overrides/fetch/provider stubs are explicitly recorded. Browser original/six disclosure states use actual local models with synthetic provider transport. See final report for exact commands and before/after.

Runtime experiment reports/runtime-asgi-20261008T184440Z.json:24 requests/concurrency4/single process and serial worker;0/24 errors/timeouts, cold import1520.13ms(n1),cold predict3295.96ms(n1),warm p5042.52,p9547.86,p9947.95ms, floor-index quantiles; whole-process peakRSS569132KiB. Actual model/ASGI, transport stub. It is not multi-worker/deployed/provider latency or a tail guarantee. Docker/platform/project/deployed load remains externally unverified.

## Independent evaluation procedure

Obtain reviewed source/consent/license provenance and qualified labels for intended languages/subject/time/immediacy/allowed actions/prohibited behavior. Declare groups and deduplicate exact and semantic overlaps before sealing D. Keep model/rules/threshold/normalization choices confined to C, including expected-abstention utility. Freeze source/model/config/policy hashes. Run actual engine/pipeline/auth/API/storage/browser layers with stubs identified, record urgent misses/false escalation/clarification/abstention/unsupported/subject/time/support errors with denominators and group-aware uncertainty. Do not alter correct labels because the model disagrees. Report clinical/generalization limitations and independent sample confidence intervals only if sampling/review supports them. No review approval or final dataset exists here.

Current-policy reproducibility (D096): reports/semantic-candidate-20261009-reproducibility.json runs the same pinned candidate/data/settings against independent engine policy .6, not production fusion. Baseline remains10/18 labels and1/6 urgent; candidate13/18,5/6 urgent,1/6 benign urgent escalation. Cold load241.49ms(n1),warm n18 p506.82/p95-p998.47ms, whole-process peakRSS322684KiB (CPU2threads,concurrency1). Repeat consumed-C observation, no tuning or independent final evidence; candidate stays disabled. Original .4 report preserved.
