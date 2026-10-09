# Decision Log

Append-only. Newest entries at the bottom. Do not edit or delete an existing
entry; supersede it with a new one that names the entry it replaces.

Format: date, decision, why, what it costs.

---

## 2026-10-08 - Safety routing is a separate, authoritative layer

**Decision.** The response now carries a `safety` object, produced by a new
context-aware engine (`mental_health_screening/safety.py`), that is independent
of both existing models. `safety.level` is the field a consumer must read
first. The existing `primary` and `urgency` fields are unchanged.

**Why.** `primary` is trained on proxy labels (subreddit of origin), not
clinician-verified diagnoses. It reported `Normal` at p=0.95 for "i wanna jump
from 10th floor". `urgency` did flag the text (p=0.78), but nothing connected
that flag to an action, and the UI headline read `primary`. A condition guess
and a support decision are different questions and cannot share a field.

**Cost.** One more field in the response contract; every consumer must be
updated to read `safety` before `primary`.

## 2026-10-08 - Model evidence is additive and can never lower a level

**Decision.** `urgency.flagged` can only raise the safety level, never lower
it. Context evidence alone determines the level when the model is silent.

**Why.** "Do not let a probability threshold become the whole safety rule"
(user requirement). A threshold is a useful second signal and a terrible sole
signal: it is not scope-aware, has no subject attribution, and no tense.

**Cost.** Some texts the model scores low will still route CONCERNING or above.

## 2026-10-08 - A failed model track reports `unavailable`, never a label

**Decision.** If the primary or urgency model raises, that track reports
`status: "unavailable"` with `predicted_class: null` and
`suicide_probability: null`. The safety result is still returned. Previously a
primary-model exception raised out of `screen()` and aborted the call before any
safety output could exist.

**Why.** A high-priority safety route must survive an ordinary
condition-classifier error. Silently substituting a label would be the worst
possible failure mode.

**Cost.** Consumers that dereference `predicted_class` must handle `null`.

## 2026-10-08 - Safety runs on the raw text, not the model's preprocessed text

**Decision.** The safety engine sees a minimally normalized copy of the raw
input, not `cleaned_text` or `lemmatized_text`.

**Why.** The preprocessing pipeline strips PII patterns and lemmatizes. It was
built for topic classification. Feeding safety-critical text through a lossy,
PII-stripping transform is an unnecessary way to lose the signal that matters.

**Cost.** Two normalization paths must be maintained.

## 2026-10-08 - Additive evidence codes, never a fabricated score

**Decision.** Safety outputs `evidence_codes` naming the patterns that actually
matched, plus discrete fields for subject, temporal context and immediacy. It
never emits a safety probability.

**Why.** A number invites comparison against the condition probability and
would imply a calibration that does not exist. Traceable codes are auditable;
`test_evidence_codes_are_traceable_not_invented` enforces that every emitted
code corresponds to a real pattern match.

**Cost.** Consumers that want a single number must map the level themselves.

## 2026-10-08 - Historical and recovery context lowers the *presentation*, not the fact

**Decision.** "I attempted suicide before and I am going to jump tonight" still
escalates. "I tried to kill myself in 2019 and I am okay now" routes above
NONE_DETECTED but never IMMEDIATE.

**Why.** I first wrote the test asserting a recovered past attempt routes to
NONE_DETECTED. That expectation was wrong and the test was corrected, not the
engine. Attempt history is a genuine risk factor; reading "I am okay now" as
all-clear is the more dangerous defect.

**Cost.** Some recovered disclosures route higher than a user may expect. The
support action text is written for that case.

## 2026-10-08 - Unknown inputs abstain rather than pass

**Decision.** Underspecified, non-English, or non-English-script input returns
`analysis_status` reflecting insufficient evidence rather than a confident low
level.

**Why.** Silence is not evidence of absence of risk.

**Cost.** More UNKNOWN/abstain responses on multilingual input.
---
# Session decisions (2026-10-08, backend audit and repair)

Numbering restarts at D-001 because the entries above predate this session's
Rule 2 format and carry no identifiers. The eight prose entries above are
historical and are not edited; where this session reverses one, the reversing
entry names it.

Cross-reference: `reports/defect-register.md` uses the same D-numbers.

## Session scope

- Repository: shreshthgod/mental.ai, HEAD 2053855d51aaa5c9e06bd8c30f1c35d45c64716b
- Environment: Python 3.12.3, numpy 2.4.4, scikit-learn 1.8.0, xgboost 3.2.0,
  fastapi 0.142.2, pytest 9.1.1, Linux. Model artifacts unchanged (SHA-256 in
  handoff.md).
- No commits created. All work is uncommitted; every entry below therefore
  records "uncommitted" honestly per Rule 6.7.

### D-001: The urgency model flag is recorded evidence, never a routing decision
- Date / phase / commit: 2026-10-08, Phase C, uncommitted
- Context: D-01. `safety.evaluate()` let `urgency_flagged` raise NONE_DETECTED
  to NEEDS_CLARIFICATION. Running the 78-case seed corpus through the FULL
  request path produced 66/78 while the engine-only runner reported 78/78,
  because that runner hardcoded `urgency_flagged=False`. The 12 failures were
  every benign control the classifier fires on.
- Decision: the flag is recorded as evidence code only. It can never raise a
  level and can never lower one.
- Why: measured at the deployed 0.15 threshold, the classifier flags 67 of 78
  seed cases, including "I live on the tenth floor" (p=0.247), "This deadline is
  killing me" (p=0.669), "The program crashed; I need to kill the process"
  (p=0.466) and "Our suicide-prevention lesson" (p=0.755). It is trained on
  subreddit proxy labels and is not scope-aware.
- Alternatives considered: raise the threshold alone (rejected - the classifier
  fires on method vocabulary regardless of threshold); add a corroboration rule
  (rejected - a bare location noun still corroborates, so it fixed 6 of 12);
  keep it as a tiebreaker only (rejected - still a false-positive channel).
- Consequences: a disclosure phrased entirely outside the pattern set that the
  engine also reads as NONE_DETECTED now returns NONE_DETECTED. That residual
  risk is measured, not assumed: see D-040 and the holdout results.
- Files: Step 12 - Packaging/package/mental_health_screening/safety.py,
  tests/test_safety_contract.py
- What happens: benign text is no longer escalated by a classifier flag; every
  - HIGH/IMMEDIATE route comes from text evidence.
- How it happens: the `if urgency_flagged:` branch in `evaluate()` now only
  appends `URGENCY_MODEL_FLAGGED`.
- When it happens: 2026-10-08, Phase C, on the first repair of the day.
- Supersedes: the 2026-10-08 entry "Model evidence is additive and can never
  lower a level", to the extent it implied the flag could also raise a level.

### D-002: Corrected expectation for "I live on the tenth floor."
- Date / phase / commit: 2026-10-08, Phase C, uncommitted
- Context: `test_benign_floor_reference_is_not_treated_as_high_risk` asserted
  the level was NEEDS_CLARIFICATION or CONCERNING, with a docstring saying
  "must ask instead".
- Decision: assert NONE_DETECTED, `needs_clarification is False`, and that
  `URGENCY_MODEL_FLAGGED` is still present.
- Why: that expectation was taken from the implementation, not from the
  specification. Seed S037 classifies this text N - no automatic personal-crisis
  escalation. Accepting NEEDS_CLARIFICATION was weaker than the product
  requires, not stricter. Rule 17 forbids keeping a weaker expectation.
- Alternatives considered: leave it (rejected - it pins a false-positive
  behaviour D-001 deliberately removed).
- Consequences: none beyond D-001.
- Files: tests/test_safety.py
- What happens: the test now asserts the specified outcome.
- How it happens: expectation replaced, with the reason recorded inline.
- When it happens: 2026-10-08, Phase C.

### D-003: `immediacy` is restricted to the declared enum
- Date / phase / commit: 2026-10-08, Phase C, uncommitted
- Context: D-02. The assembly step rewrote `immediacy` to a fourth value,
  "immediate", which is outside the Literal the module declares and outside the
  - Part 4 contract (stated / not_stated / unclear).
- Decision: an IMMEDIATE route with `immediacy == "unclear"` becomes "stated".
- Why: a present-danger route is by definition an immediacy the text stated, so
  "stated" is both correct and in-contract.
- Alternatives considered: widen the enum to include "immediate" (rejected -
  the contract in Part 4 fixes three values).
- Consequences: consumers reading `immediacy` get a value they can enumerate.
- Files: Step 12 - Packaging/package/mental_health_screening/safety.py,
  tests/test_safety.py
- What happens: no response carries an undeclared `immediacy`.
- How it happens: one guard in the assembly block of `evaluate()`.
- When it happens: 2026-10-08, Phase C.

### D-004: `support_action()` reads its `region_known` parameter
- Date / phase / commit: 2026-10-08, Phase C, uncommitted
- Context: the function advertised `region_known: bool = False` and ignored it.
- Decision: HIGH now adds an optional location question when the region is
  unknown. No national hotline is named anywhere in the module.
- Why: Part 3.16 requires a usable generic local-emergency instruction plus an
  optional location question when the region is unknown, and forbids inferring a
  country. An unread parameter is a lie about the interface.
- Alternatives considered: delete the parameter (rejected - a verified-region
  implementation needs the seam).
- Consequences: none.
- Files: Step 12 - Packaging/package/mental_health_screening/safety.py,
  tests/test_safety_contract.py

### D-005: Whitespace-only input is a contract error, not a 500
- Date / phase / commit: 2026-10-08, Phase C, uncommitted
- Context: D-05. `PredictRequest.text` had `min_length=1`, which counts raw
  characters, so " " passed validation and then raised inside `screen()`, where
  the route's generic `except Exception` turned a caller mistake into HTTP 500
  "Prediction failed".
- Decision: a `field_validator` rejects text with no non-whitespace character
  with 422, before any model runs.
- Why: measured with a stubbed Supabase transport - " ", "   ", "\t", "\n",
  "\t\n " and "\xa0" all returned 500 before the fix.
- Alternatives considered: widen the except clause (rejected - hides real
  faults); strip in the validator (rejected - silently alters the caller's text).
- Consequences: the documented 500 no longer covers a caller mistake.
- Files: api/api.py, tests/test_api_contract.py
- Symptom: HTTP 500, `detail: "Prediction failed"`.
- Root cause: raw-length validation plus a catch-all handler.
- Regression test: `test_d05_whitespace_only_is_a_contract_error_not_a_500`.

### D-006: A failed model track reports "no signal", not a negative signal
- Date / phase / commit: 2026-10-08, Phase C, uncommitted
- Context: D-006. `inference.screen()` passed `urgency_flagged=bool(
  urgency_result["flagged"])`. On failure `flagged` is False because that is
  the API default for an absent value, so a dead urgency track was reported to
  the safety layer as "the model ran and found nothing": `analysis_status
  "complete"` with code `URGENCY_MODEL_NOT_FLAGGED`.
- Decision: pass `urgency_flagged=None` when the track's status is not
  "complete".
- Why: a missing signal and a negative signal are different facts and must not
  share a value. Part 4 requires unknown/unavailable/degraded to be reported
  honestly.
- Alternatives considered: leave it (rejected - it misreports a fault as a
  negative finding).
- Consequences: a failed urgency track now sets `analysis_status: "degraded"`
  and emits `URGENCY_MODEL_UNAVAILABLE`.
- Files: Step 12 - Packaging/package/mental_health_screening/inference.py,
  tests/test_api_contract.py
- Symptom: `analysis_status == "complete"` while the urgency track was down.
- Root cause: reuse of an absent-value default as a real observation.
- Regression test: `test_d06_urgency_model_failure_still_returns_a_safety_route`.

### D-007: /health verifies artifacts and /ready runs a real inference
- Date / phase / commit: 2026-10-08, Phase C, uncommitted
- Context: D-07. `/health` filled every artifact entry with the literal "ok"
  whenever the screener object existed; `/ready` returned ready for the same
  reason. Both reported INITIALIZATION, not working inference. A deleted
  artifact or a model that raises on every input still read healthy.
- Decision: `/health` stats each artifact resolved from the live config and
  reports missing/empty honestly, and also reports the result of a real
  inference probe. `/ready` returns 503 unless both the files and a real
  screening succeed, and reports `inference_checked`.
- Why: audit target Part 2.9(i). A readiness signal that only proves an object
  exists cannot be used to gate a rollout.
- Alternatives considered: probe on every /ready call (rejected - unbounded
  per-request cost); cache the probe (rejected - a cached "ok" is the same lie).
- Consequences: /health and /ready now cost one inference each.
- Files: api/api.py, tests/test_api_contract.py

### D-008: Advertised runtime settings are honoured, or removed
- Date / phase / commit: 2026-10-08, Phase C, uncommitted
- Context: D-08. `.env.example` advertised `MAX_TEXT_LENGTH` and
  `URGENCY_THRESHOLD`. Neither string was read anywhere in the backend.
  - Verified: with `URGENCY_THRESHOLD=0.99`, `decision_threshold_used` stayed 0.15.
- Decision: `MAX_TEXT_LENGTH` is read by `api.api.max_text_length()`, validated
  to 1000..100000 with a fallback to 10000 and a warning; it is also passed to
  `MentalHealthScreener` so an accepted request cannot then be rejected by the
  model layer. `URGENCY_THRESHOLD` is read by
  `MentalHealthScreener._configured_urgency_threshold()`, validated to (0, 1],
  and raises at construction if invalid.
- Why: a threshold that is not the one an operator asked for is worse than no
  threshold; silently ignoring a documented control is worse than either.
- Alternatives considered: delete both lines from .env.example (rejected - the
  controls are genuinely wanted, and a safety-relevant threshold should be
  operable); fail startup on a bad `MAX_TEXT_LENGTH` (rejected - a typo in a
  length limit should not take the service down).
- Consequences: `.env.example` documents the real bounds. The default threshold
  is unchanged at 0.15.
- Files: api/api.py, .env.example,
  Step 12 - Packaging/package/mental_health_screening/inference.py,
  tests/test_api_contract.py

### D-009 to D-025: Vocabulary and context repairs found by the expanded corpus
These are one class of defect - the rule set recognised one phrasing per
construct - found by growing the corpus from 78 to 321 cases. Each entry names
the construct, the verified cause and the guard that keeps the addition from
over-matching.

### D-009: Self-harm, method, medical, violence, abuse and fiction vocabulary gaps
- Context: the seed corpus held one phrasing per family. Common phrasings of
  the same construct routed to NONE_DETECTED.
- Decision: add the missing constructions with a near-miss control beside each.
- Why: measured misses included "I want to slit my wrists", "I want to walk
  into traffic and end it", "I want to step off the roof tonight", "I tried to
  hang myself last week", "I overdosed two days ago", "I took a whole packet of
  pills and I cannot stop vomiting", "I collapsed and I am not waking up
  properly", "I want to kill the person who wronged me", "My partner is hitting
  me right now", "Something in my head keeps telling me to end it", and the
  - Hinglish and Devanagari equivalents.
- Alternatives considered: a single broad keyword list (rejected - Part 1.7;
  each addition carries a minimal-pair control).
- Consequences: benign FP rate measured at 0/73 on the regression corpus and
  1/131 including holdouts.
- Files: safety.py, tests/test_safety_contract.py
- Regression test: `test_d009_*` (33 cases).

### D-009a: A bare "poem|song" alternative corrupted the subject field
- Context: the fiction detector ended in `|poem|song`, so any clause mentioning
  a song or poem reported `subject=fictional_or_quoted`. "I like that song a
  lot" was mis-attributed.
- Decision: every alternative now requires an explicit creative frame or a
  named work.
- Why: `subject` is a contract field consumers read.
- Files: safety.py, tests/test_safety_contract.py

### D-009b: A location word in an acquisition context is not a method statement
- Context: "I want to get a rooftop apartment" routed HIGH.
- Decision: a bare location noun (`rooftop`, `balcony`, `bridge`, `ledge`,
  `cliff edge`) escalates only with a strong method verb, a present-position
  claim or a self-harm term; an acquisition or decorative context blocks it.
- Why: measured false positive.
- Files: safety.py, tests/test_safety_contract.py

### D-009c: Presence at a fall edge with a present-time marker escalates
- Context: "I'm outside on the ledge right now" matched neither the location
  nor the present-position patterns.
- Decision: a present-position claim plus a location plus an explicit
  present-time marker routes HIGH, with code `PRESENT_POSITION_AT_EDGE`.
- Why: the specification requires adding verified present access not to lower
  priority. It does not claim the person intends to jump.
- Files: safety.py, tests/test_safety_contract.py

### D-009d: Negation binds to its own clause position
- Context: "I hurt myself earlier today and the bleeding has not stopped" was
  read as a denial and downgraded a reported act plus ongoing bleeding.
- Decision: a clause counts as negated for a given pattern only when a negation
  marker appears BEFORE the evidence it would cancel.
- Why: Part 3.8 - negation must apply to its actual clause.
- Files: safety.py, tests/test_safety_contract.py

### D-009e: An educational frame is not a quotation
- Context: `lesson explains` sat in QUOTATION_WRAPPER, so seed S032 reported
  `subject=fictional_or_quoted` where the seed expects `unclear`.
- Decision: moved to EDUCATIONAL_FRAME.
- Files: safety.py

### D-010: A fiction container outranks a bare third-person pronoun
- Context: "My novel's main character says she wants to die" routed HIGH and was
  attributed to another person.
- Decision: an explicit creative container (`fiction_container`) outranks a
  third-person pronoun, but not an explicit self-assertion.
- Files: safety.py, tests/test_safety_contract.py

### D-011: Latin script is not English
- Context: German, French, Spanish, Dutch and Indonesian use Latin script, so the
  script check reported them supported; no pattern matched; "Ich möchte heute
  sterben" returned NONE_DETECTED - a false all-clear on an explicit statement.
- Decision: Latin-script text is also checked for English function words, with
  a Hinglish carve-out. Below 4 word tokens the check abstains.
- Why: measured. "Ich möchte heute sterben", "Je veux mourir ce soir",
  "Yo quiero morirme hoy", "Meine katze ist auf dem Dach" now abstain, while
  - Hinglish and short English still read as supported.
- Alternatives considered: a language-detection dependency (rejected - this
  module imports only the standard library by design, so routing survives a
  missing dependency).
- Consequences: a long non-English Latin text abstains to UNKNOWN rather than
  guessing. Residual gap: a short foreign fragment may still be read as English
  (measured: holdout-2 K064).
- Files: safety.py, tests/test_safety_contract.py

### D-012: Preparation and farewell evidence routes HIGH
- Context: the `out_of_vocabulary` corpus family exists to measure what D-001
  gave up. "I have made arrangements", "I have written the note", "I have said
  my goodbyes", "I will not be missing this world" all returned NONE_DETECTED.
- Decision: a bounded `FINAL_ARRANGEMENTS` pattern routes HIGH, never IMMEDIATE
  - nothing in it claims an act is underway.
- Why: measured false negatives on high-risk preparation language.
- Alternatives considered: reintroducing "made arrangements" unqualified
  (rejected - "I have made arrangements for the party" is ordinary English and
  was a measured false positive); "will not be here for the party" (rejected
  for the same reason).
- Files: safety.py, tests/test_safety_contract.py

### D-013 to D-025: Remaining vocabulary and context repairs
#### D-013: distress vocabulary (anhedonia, low mood, irritability, altered energy,
  - perceptual disturbance). Cause: seed corpus had one phrasing each.
#### D-014: the acquisition check must precede the present-access shortcut.
  - Cause: "I am at the balcony watering plants" was escalated to a question.
#### D-015: the anaphoric carry-over must not reach into a resolved context.
  - Cause: a fiction gate cleared a clause and the carry-over re-escalated it in
  - the same pass.
#### D-016: a quoted disclosure the author personally identifies with is a
  - self-disclosure. Cause: quotes were set aside regardless of personal
  - re-assertion.
#### D-017: an unstated object with a stated time is a question, not an inference.
#### D-018: a clean denial is a question; a denial plus distress is concern.
  - Cause: "I don't want to kill myself" routed CONCERNING.
#### D-019: a recovery marker anywhere caps a past-tense HIGH with no present-tense
  - marker. Cause: the recovery sentence was in a different clause than the
  - disclosure.
#### D-020: bounded typo tolerance for a closed list of risk words plus one
  - adjacent transposition. Cause: "i wna to kill myslef".
#### D-021: leet expansion must skip digit-leading tokens. Cause: "10th" became
  - "ioth", silently breaking the floor-number alternative; the leading-digit
  - exclusion was documented in a comment but never implemented.
#### D-022: passive wishes phrased without a wish verb.
#### D-023: distress forms the earlier additions missed by one token.
#### D-024: `NEGATIVE_WISH` participates in the D-018 decision. Cause: "I hurt
  - myself again but I do not want to die" routed to a question.
#### D-025: `NEGATIVE_WISH` was Devanagari-only. Cause: the commonest English
  - statement of intent not to die had no pattern at all.
- Files for D-013..D-025: safety.py, tests/test_safety_contract.py

### D-026: A probability outside [0, 1] fails its track
- Date / phase / commit: 2026-10-08, Phase C, uncommitted
- Context: the guards checked NaN and negative values but not values above 1.
  Observed: a corrupted primary model returned 7.5 as a class probability and it
  was published verbatim; a corrupted urgency model returned
  `suicide_probability: 5.0`, `predicted_class: "suicide"`, `flagged: true`,
  `status: "complete"`.
- Decision: `_assert_valid_probabilities()` rejects non-finite, negative and
  above-1 values; the track then reports `status: unavailable` with nulls.
- Why: Part 4 requires invalid probability ranges to be validated. A value
  outside [0,1] is not a small inaccuracy, it is a broken model.
- Files: inference.py, tests/test_metamorphic.py
- Symptom: `suicide_probability: 5.0` in an HTTP 200 response.
- Root cause: incomplete range validation.
- Regression test: `test_f3_out_of_range_probability_is_rejected`,
  `test_f3b_out_of_range_primary_probability_is_rejected`.

### D-027 to D-034: Systematic gaps exposed by the first sealed holdout
#### D-027: tense coverage. The act patterns matched base and -ing forms only, so
  - "I killed myself" matched nothing. Cause: pattern construction, not vocabulary.
#### D-028: present-position coverage: sitting, out on, climbed; plus fire escape.
#### D-029: remaining acute medical presentations: cannot get up, chest tightness,
  - vision going, blood everywhere.
#### D-030: violence and abuse verbs: break his jaw, shouting and pushing me.
#### D-031: third-party risk: posted about ending their life, stopping her tablets.
#### D-032: a past-tense self-harm verb is itself the report of a completed act.
#### D-033: Indic coverage: khud ko khatam kar dunga, chhoot jayega, इस दुनिया से छुट.
#### D-034: shorthand coverage: gona, bulcony.
- Files: safety.py, tests/test_safety_contract.py

### D-035: Two false-positive regressions introduced during repair were removed
- Date / phase / commit: 2026-10-08, Phase C, uncommitted
- Context: the D-030 abuse addition made "Nobody is pushing me toward anything"
  route IMMEDIATE, and the D-029 medical addition made "I would not mind not
  waking up" route IMMEDIATE. Both were regressions introduced by this session.
- Decision: a negated/hypothetical subject and the "pushing me aside/away/
  toward" sense are excluded from ABUSE_THREAT; the medical reading of "not
  waking up" now requires a clinical anchor ("I am not waking up", "still not
  waking", "cannot wake").
- Why: an over-reaction to a benign sentence is a safety defect too, and these
  two were introduced here rather than inherited.
- Files: safety.py, tests/test_safety_contract.py

### D-036: The corpus runner must execute the layer that ships
- Date / phase / commit: 2026-10-08, Phase C, uncommitted
- Context: `scripts/run_safety_corpus.py` hardcoded `urgency_flagged=False`, so
  it executed a path the service never takes. It reported 78/78 while the real
  request path produced 66/78. It also accepted "unclear" for every expected
  subject, which made the subject assertion unenforceable, and contained two
  no-op assertion blocks that could never fail.
- Decision: two layers, `--layer engine|pipeline|both`; the subject assertion is
  exact, with one explicitly counted exception; prohibited-behaviour checks are
  real; raw model output and final policy output are recorded separately.
- Why: a regression suite that cannot fail is worse than none.
- Files: scripts/run_safety_corpus.py, tests/safety_corpus/expansion.json

### D-037: Expectations are authored from the specification, mechanically
- Date / phase / commit: 2026-10-08, Phase B, uncommitted
- Context: hand-authoring hundreds of cases drifts toward whatever the engine
  happens to do. Batch authoring had also defaulted every subject to `self`,
  which was simply wrong for "The cat jumped onto the counter".
- Decision: `scripts/generate_corpus_expansion.py` authors expectations from the
  Part 5 oracle and derives subject mechanically, with a documented override
  table for cases where the text is genuinely two-sided. A normalised duplicate
  is rejected unless it declares the same paraphrase group.
- Consequences: 321 regression cases, 311 distinct paraphrase groups; near-
  duplicate variants cannot masquerade as independent samples.
- Files: scripts/generate_corpus_expansion.py, tests/safety_corpus/expansion.json

### D-038: Expectations I authored were corrected, with the reason recorded
- Date / phase / commit: 2026-10-08, Phase B, uncommitted
- Context: six of my own expectations were wrong and were corrected rather than
  satisfied by changing the engine: "I have decided that I will not be here for
  the party" and "Tonight is the night" (idiomatic or contextless; must not
  escalate), "The poem is about the sea" (subject is cosmetic at
  - NONE_DETECTED), "I will never jump off anything", "The poem is about the sea".
- Decision: correct the expectation, record the reasoning in the case
  `rationale`, and keep the original behaviour unchanged.
- Why: Rule 17 forbids weakening a correct expectation, and equally forbids
  leaving an incorrect one in place to justify a code change.
- Files: scripts/generate_corpus_expansion.py, tests/safety_corpus/expansion.json

### D-039: The historical test split stays historical
- Date / phase / commit: 2026-10-08, Phase D, uncommitted
- Context: `Step 10 - Evaluation/code/evaluate_test.py::eval_urgency()` selects
  the deployed threshold by calling `precision_recall_curve(y_test_bin, proba)`
  on the test split, so that split is not an untouched final evaluation set.
- Decision: its reported macro-F1 is preserved as a historical figure and is not
  re-presented as a fresh result. New generalisation claims come from the sealed
  holdouts only.
- Why: Part 7.
- Files: none changed; recorded in handoff.md and the final report.

### D-040: Two sealed holdouts, run once each, reported as found
- Date / phase / commit: 2026-10-08, Phase D, uncommitted
- Context: Part 7 forbids tuning on a test set and then calling it untouched.
- Decision: `tests/safety_corpus/holdout.json` (96 cases) was built, run once,
  and CONSUMED: it exposed the systematic gaps in D-027..D-034, which were then
  repaired. `tests/safety_corpus/holdout2.json` (83 cases) was built on surface
  forms not used during repair and run once for the post-fix evaluation. The
  regression runner excludes both unless `--include-holdout` is passed.
- Why: after holdout-1 was repaired against, re-running it would measure a
  system fitted to it.
- Consequences, and these are the most important numbers in this session:
  on holdout-1, 25 of 35 urgent cases routed urgent; on holdout-2, 15 of 30.
  The rule layer does NOT generalise to unseen phrasings. No further holdout is
  claimed.
- Alternatives considered: continuing to add patterns until holdout-2 passed
  (rejected - that is the "one hardcoded phrase at a time" trap in Part 1.7, and
  it would destroy the only unbiased estimate available).
- Files: scripts/build_holdout.py, scripts/build_holdout2.py,
  tests/safety_corpus/holdout.json, tests/safety_corpus/holdout2.json

### D-041: The echoed preprocessed text is retained, and the requirement is recorded
- Date / phase / commit: 2026-10-08, Phase E, uncommitted
- Context: `PredictResponse.cleaned_text` and `lemmatized_text` echo the
  caller's own submitted text. They are declared in
  `web/src/lib/api.ts` and are not rendered by any component.
- Decision: keep them, because removing them would break a declared contract;
  assert the response content type is JSON; record the consumer requirement
  ("render as text, never as markup") in handoff.md.
- Why: it is not a leak - it returns only to the authenticated caller who sent
  it and is stored against that caller's own record. It IS a stored-XSS surface
  if a consumer ever renders it as HTML.
- Alternatives considered: drop the fields (rejected - contract break for no
  security gain, since the caller already has the text).
- Files: tests/test_api_contract.py

### D-042: Frontend is not changed in this phase
- Date / phase / commit: 2026-10-08, Phase E, uncommitted
- Context: `web/src/lib/api.ts` `PredictResponse` has no `safety` field,
  `PrimaryResult.predicted_class` is typed non-nullable while the backend can
  now return null, and `web/src/pages/Screen.tsx` renders
  `primary.predicted_class` as the headline and prints "No elevated urgency
  signal detected" whenever `urgency.flagged` is false - including when the
  urgency track was unavailable.
- Decision: change no frontend file. Record every required consumer change and
  the end-to-end release blocker.
- Why: Part 4.6 and Part 1.2.
- Files: none changed; requirements recorded in handoff.md.

#### D-043: The audit task specification is preserved in the repository
- Date / phase / commit: 2026-10-08, Phase F, uncommitted
- Context: the requirements this work is held to existed only as a chat prompt.
  A reviewer could not check a decision, a test or a metric against the
  requirement that produced it without the transcript.
- Decision: `AUDIT-SPEC.md` in the repository root holds the specification, all
  ten parts, with Part 5 seed cases as tables. It is a specification, not a
  report, and states what must be true rather than what was done.
- Why: traceability. Every defect ID in `reports/defect-register.md` and every
  entry here should be checkable against a numbered requirement.
- Alternatives considered: a link to the chat (rejected - not durable); a
  summary (rejected - a summary cannot be checked against).
- Consequences: one new root file. The file follows the repository convention of
  no em-dashes in documentation; the only alteration to the source text is that
  punctuation, which is disclosed at the top of the file. No requirement,
  expectation code, seed case or acceptance gate was changed, removed or
  reordered.
- Files: AUDIT-SPEC.md, decisions.md, flow.md
- What happens: `AUDIT-SPEC.md` is read as the source of requirements; actual
  compliance status lives in `handoff.md`.
- How it happens: a plain Markdown file at the repository root, next to
  `decisions.md`, `flow.md` and `handoff.md`.
- When it happens: 2026-10-08, Phase F, at the owner's request.

#### D-044: Documentation convention restored in this session's own files
- Date / phase / commit: 2026-10-08, Phase F, uncommitted
- Context: commit `116c945` ("remove em-dashes from all documentation and
  source") is a live convention: every tracked doc and source file at HEAD
  contains zero em-dashes. `handoff.md` and `reports/defect-register.md`, written
  in this session, contained 11, because the convention was not read before
  writing.
- Decision: all 11 replaced with a colon or hyphen. Verified: zero em-dashes in
  both files.
- Why: a new file that breaks a documented repository convention makes the
  convention unenforceable and is visible in any diff review.
- Alternatives considered: leave them (rejected - inconsistent output from a
  single session).
- Consequences: none. No requirement, number or test reference changed.
- Files: handoff.md, reports/defect-register.md
- What happens: prose reads with colons and hyphens instead of em-dashes.
- How it happens: targeted replacement; verified by re-counting.
- When it happens: 2026-10-08, Phase F.

#### D-045: Six compliance gaps against AUDIT-SPEC.md recorded, not closed
- Date / phase / commit: 2026-10-08, Phase F, uncommitted
- Context: after writing the specification, the work was re-checked against it.
  Six gaps were confirmed by inspection, not guessed.
- Decision: record all six in `AUDIT-SPEC.md` section "Current compliance status"
  and in `handoff.md`. Close none of them in this session.
- Why, per item:
  1. **Part 7 rule 1 (Rule 7 of Part 1) is substantially violated.** The
     evidence vocabulary is now 415 alternatives across 34 patterns; roughly
     150-200 were added this session, plus a 40-word Hinglish marker list and a
     ~120-word English function-word list. Each addition carried a minimal-pair
     control and was measured, and the holdouts then showed the approach does
     not generalize (25/35 and 15/30). The rule warned against exactly this and
     the measurement vindicates the warning. This is the most important open
     item, and more of the same would make it worse.
  2. **Rule 6.1 violated.** `decisions.md` and `flow.md` were written once at the
     end rather than in the same step as each code change, so the decision log's
     ordering does not reflect when work happened.
  3. **Part 8 case-record gap.** `expected_temporal_context` is absent from all
     78 seed cases in `tests/safety_corpus/cases.json`; it is present in the 243
     expansion cases.
  4. **Part 8.2, 8.7 and Part 3.1 artifacts missing.** There is no standalone
     coverage-matrix document, no standalone documented safety/API contract, and
     no standalone written routing specification. `AUDIT-SPEC.md` records the
     requirements; the contract itself is scattered across `flow.md` and
     `decisions.md`.
  5. **Part 8 defect template not followed.** `reports/defect-register.md` uses a
     table plus prose, not the 13-field template.
  6. **Part 6 and Part 7 gaps.** No CORS tests, no `/predict` rate limiting, no
     request-cancellation tests, no explicit homoglyph test, and no confidence
     intervals. Verified by grep across `tests/`, `scripts/` and the reports.
- Alternatives considered: closing all six now (rejected for item 1, which needs
  a design decision rather than more work; not rejected for items 2-6, which are
  outstanding and cheap).
- Consequences: the deliverable is honestly incomplete. Presenting checklist
  completion as progress on the real risk would misrepresent it.
- Files: AUDIT-SPEC.md, handoff.md, reports/defect-register.md
- What happens: `handoff.md` section 9 carries the same six items as unfinished
  work.
- How it happens: recorded as decision text, not as a status field, so it cannot
  be silently dropped.
- When it happens: 2026-10-08, Phase F.

### D-046: Reproduce the dirty checkout and enforce the runner's missing assertions
- Date / phase / commit: 2026-10-08, Phase A, uncommitted
- Context: Required source exists, but HEAD alone does not identify it. The runner recorded null actual temporal context and regenerated pipeline support instead of inspecting it.
- Decision: preserve the baseline file manifest and artifact hashes; assert temporal metadata where present, returned pipeline action, and unavailable handling. Add controlled mutations and a nonzero-exit check.
- Why: inspection of run_layer/check_case confirmed unchecked fields. Baseline 314 tests and 321/321 per corpus layer passed without those assertions. Minimal TestClient stalls in the sandbox but 314 tests passed outside it in 12.87s.
- Alternatives considered: accept old green totals (rejected: hidden failures); change routing first (rejected: the measuring tool must be trustworthy).
- Consequences: previously hidden temporal and pipeline-support defects now fail; original datasets and historical reports remain unchanged. Missing seed temporal annotations remain a visible gap.
- Files: scripts/run_safety_corpus.py, tests/test_corpus_runner.py, reports/recovery-baseline.json, reports/recovery-original-baseline.json, reports/requirements-evidence.md, decisions.md, flow.md
- What happens: wrong level, subject, temporal context, empty urgent action, reassurance and unavailable no-concern results are rejected.
- How it happens: run_layer reads actual temporal context and pipeline support_action; check_case checks them; main returns 1 for required failures.
- When it happens: on each engineering corpus execution, before Phase B repairs.
- Symptom: green corpus despite unchecked temporal results and substituted support actions.
- Root cause: actual_temporal_context was hardcoded null; support_action was recomputed outside the pipeline.
- Regression test: tests/test_corpus_runner.py::test_oracle_rejects_wrong_behavior, test_pipeline_checks_returned_action_and_temporal_context, test_required_failure_exits_nonzero.

Historical correction: D-045 admits documentation was written at the former session end. This entry does not retroactively claim contemporaneous documentation for D-001..D-045.

### D-047: Evaluate safety before optional lossy processing and return support from the pipeline
- Date / phase / commit: 2026-10-08, Phase B, uncommitted
- Context: clean_and_lemmatize, handcrafted extraction and feature assembly ran before safety or outside the primary catch. Package import eagerly imported inference, so safety depended on NLTK indirectly. Urgent support branches ignored another_person.
- Decision: lazy package/processing imports; evaluate raw safety first; catch preprocessing separately and feature extraction inside the primary track; carry actual support text in screen results. Address third-party urgent support to the affected person before self-directed branches.
- Why: tests/test_recovery_failures.py reproduces each escape and optional import dependency. The strengthened runner exposes missing pipeline support.
- Alternatives considered: enlarge regex vocabulary (rejected: measured architecture limit); wrap the entire screen call (rejected: loses useful independent outputs); rewrite models (rejected: honest raw outputs must stay).
- Consequences: optional processing failures report null raw outputs and degraded safety; no added packages or downloads. Existing rule semantics/generalization limitations remain. Semantic routing is still unvalidated.
- Files: docs/ROUTING-POLICY.md, Step 12 - Packaging/package/mental_health_screening/__init__.py, Step 12 - Packaging/package/mental_health_screening/inference.py, Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_recovery_failures.py, api/api.py, flow.md, decisions.md
- What happens: reliable HIGH evidence and subject-appropriate support survive optional failures.
- How it happens: screen evaluates raw text before clean_and_lemmatize; preprocessing failure disables both raw tracks; feature failure disables primary only. support_action selects third-party text first.
- When it happens: each screen call after input validation and before optional processing, 2026-10-08.
- Symptom: preprocessing/feature exceptions abort screening; third-person HIGH gets harming-yourself copy.
- Root cause: unguarded optional calls and level branches preceding subject check.
- Regression test: tests/test_recovery_failures.py::test_optional_processing_failure_preserves_high, test_safety_module_import_does_not_import_optional_packages, test_feature_vector_failure_does_not_abort_safety_or_urgency, test_support_addresses_affected_person.

### D-048: Current intent and past-event time are independent of routing priority
- Date / phase / commit: 2026-10-08, Phase B, uncommitted
- Context: Strengthened runner reveals 123 temporal mismatches. Original sentence returned HIGH but temporal unclear; recent acts were labelled current and an adolescent attempt was not historical.
- Decision: record explicit past-event anchors as historical/recent before route-related temporal evidence; present non-negated intention with act/method/passive evidence is current. Advance policy to safety-policy-2026.10.08.3.
- Why: six focused temporal regressions failed before change; HIGH does not require stated immediacy, and urgent support after a recent act does not turn its event time into current.
- Alternatives considered: change dataset expectations (rejected without semantic review); add danger vocabulary (rejected); infer immediacy from level (rejected).
- Consequences: narrow event-time correction; generic distress, multilingual and disputed annotation cases remain unresolved and visible in reports. No generalization claim.
- Files: Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_temporal_recovery.py, docs/ROUTING-POLICY.md, decisions.md, flow.md
- What happens: current intention remains current with unstated immediacy; explicit recent/historical act anchors retain their time independently of support urgency.
- How it happens: temporal vote selection tests explicit event anchors before the existing historical/planned/act branches.
- When it happens: per minimally normalized clause during evaluate, before route assembly.
- Symptom: original case temporal unclear; recent harm current; past adolescent attempt current.
- Root cause: temporal votes used planned/present/recent route flags and omitted intent and event anchors.
- Regression test: tests/test_temporal_recovery.py::test_temporal_event_is_independent_of_route and test_current_intent_does_not_invent_immediacy.

### D-049: Add a disabled semantic boundary without pretending a candidate was validated
- Date / phase / commit: 2026-10-08, Phase B, uncommitted
- Context: Repository has only legacy TF-IDF models and a transformer handoff script. Step 5/output and Step 9/output are absent; torch, transformers and sentence_transformers are not installed; no local semantic weights were found.
- Decision: add a standard-library structured adapter with explicit disabled/unavailable states and shape validation. Keep it outside production routing until candidate evidence is supplied.
- Why: a fabricated or unvalidated model cannot meet the semantic comparison requirement. Runtime has 16 logical CPUs and about 32 GB host memory, but no candidate artifact/license/reviewed labels established.
- Alternatives considered: MentalBERT handoff (no weights or runtime); train on synthetic regressions (rejected as candidate proof); use raw urgency as semantic (rejected: proxy model lacks scope); new hosted service (not authorized).
- Consequences: candidate comparison and production semantic fusion remain BLOCKED on a suitable licensed artifact and independently reviewed development/validation labels. Adapter tests prove failure/shape handling only, not language understanding. Synchronous deadlines require bounded execution by a future caller.
- Files: Step 12 - Packaging/package/mental_health_screening/semantic.py, tests/test_semantic_adapter.py, docs/ROUTING-POLICY.md, flow.md, decisions.md
- What happens: disabled adapter emits no assessment; malformed or failing evaluators return unavailable; valid structured output retains subject and time.
- How it happens: assess invokes only an explicitly supplied local callable and checks exact fields and enums; no network or model load is added.
- When it happens: isolated adapter evaluation only; not called by production screen.

### D-050: Fingerprint every new corpus run and expose missing temporal coverage
- Date / phase / commit: 2026-10-08, Phase A evidence follow-through, uncommitted
- Context: Old reports identify only uncommitted, silently skip absent corpus files, omit actual model hashes and temporal coverage, and divide urgency flags by unavailable cases too.
- Decision: add a source/config/corpus manifest fingerprint and artifact hashes to each report; fail if a required corpus is absent; report duplicate inputs, missing temporal annotations, temporal errors and assessment statuses; use available urgency denominator; check diagnostic assertions in support text.
- Why: dirty checkout must be reproducible; 78 seeds lack temporal metadata; 83 regression cases opt out of subject checking (not the one exception previously claimed in runner prose).
- Alternatives considered: HEAD alone (insufficient); hash .env or raw datasets (rejected: privacy); regenerate historical reports (rejected: preserve evidence).
- Consequences: report/handoff/docs excluded from the repeatable source hash to avoid self-reference; artifact/config/corpus contents included. Existing consumed reports untouched. No confidence intervals on dependent synthetic cases are presented as clinical evidence.
- Files: scripts/source_fingerprint.py, scripts/run_safety_corpus.py, decisions.md, flow.md
- What happens: runs identify exact source and artifacts and explicitly count missing assertion coverage.
- How it happens: allowlisted source files are SHA-256 hashed; build_report includes the manifest and diagnostics.
- When it happens: report creation after each run; corpus absence fails before inference.

### D-051: Failed optional analysis without reliable evidence abstains
- Date / phase / commit: 2026-10-08, Phase B, uncommitted
- Context: D-047 preserved explicit HIGH under preprocessing failure but an unmatched statement still returned NONE_DETECTED when neither raw track ran.
- Decision: when both legacy tracks are unavailable and independent evidence returned NONE_DETECTED, return UNKNOWN with clarification/review and an insufficient-assessment code.
- Why: tests/test_recovery_failures.py::test_processing_failure_without_reliable_evidence_is_unknown fails before repair; missing observations cannot become confident absence of concern.
- Alternatives considered: fabricate negative model outputs (rejected); lower a reliable HIGH (rejected); apply UNKNOWN to every input (rejected).
- Consequences: known HIGH remains HIGH/degraded. Healthy legacy outputs still do not establish semantic understanding; comprehensive no-match semantics remain open under D-049.
- Files: Step 12 - Packaging/package/mental_health_screening/inference.py, tests/test_recovery_failures.py, decisions.md, flow.md
- What happens: unmatched disclosures with unavailable optional assessment abstain honestly.
- How it happens: post-track availability guard changes only NONE_DETECTED to UNKNOWN, sets clarification/review and preserves null raw outputs.
- When it happens: after raw safety and legacy tracks, before support text and serialization.
- Symptom: preprocessing failure produced NONE_DETECTED without any model observation.
- Root cause: fallback no-match result was returned unchanged after both optional tracks failed.
- Regression test: tests/test_recovery_failures.py::test_processing_failure_without_reliable_evidence_is_unknown.

### D-052: Add seed temporal annotations separately from the preserved corpus
- Date / phase / commit: 2026-10-08, Phase A/B coverage, uncommitted
- Context: All 78 mandatory seeds lacked temporal expectations, so even the corrected runner could not assert their event time.
- Decision: add versioned temporal-seeds-v1.json overlay, preserving original seed inputs, IDs, routes and historical reports. Annotate concern-event time, not an invented imminent action; mark developer review explicitly.
- Why: D-045 item 3 and current requirement 9 demand asserted temporal expectations. Current disclosure is distinct from known immediacy. Historical/recovery and combined transcript seeds retain their documented context.
- Alternatives considered: overwrite original dataset (rejected: provenance); copy current engine outputs (rejected: independent oracle); leave missing coverage (rejected).
- Consequences: newly exposed seed temporal failures remain failures; annotations have no clinical review. Some expansion annotations describe general statement time, while this overlay describes concern-event time; disputed cases need versioned semantic review, not automatic relabeling.
- Files: tests/safety_corpus/temporal-seeds-v1.json, scripts/run_safety_corpus.py, decisions.md, flow.md
- What happens: every mandatory seed has an asserted event-time expectation.
- How it happens: load_corpus merges the separate versioned overlay by case_id and reports its version.
- When it happens: corpus loading before engine/pipeline evaluation.

### D-053: Publish a diagnostic contract map without claiming Phase C freeze
- Date / phase / commit: 2026-10-08, Phase A/B documentation checkpoint, uncommitted
- Context: Current contract was scattered; persistence and browser omit authoritative safety, and later gates remain unfulfilled.
- Decision: document actual field production/validation/storage/consumption and defects in API-CONTRACT-CURRENT.md; append full-field recovery defects; preserve prior handoff separately before updating continuation state.
- Why: static inspection confirms missing schema version/persistence state, string enums, raw presentation and omitted safety storage. Docker command is unavailable. No local semantic weights or reviewed data establish a candidate.
- Alternatives considered: describe proposed frozen schema as existing (rejected); edit frontend before gate (rejected); erase historical handoff (rejected).
- Consequences: Phase C and frontend integration are still not complete; unstarted local work is NOT_STARTED, not disguised as an external blocker.
- Files: docs/API-CONTRACT-CURRENT.md, docs/ROUTING-POLICY.md, reports/defect-register.md, reports/recovery-report.md, reports/requirements-evidence.md, reports/handoff-pre-recovery.md, handoff.md, decisions.md, flow.md
- What happens: reviewers can distinguish this repair batch from unresolved integration/runtime work.
- How it happens: repository-relative field map, current evidence matrix and a fingerprinted local checkpoint, no commit/push/deploy.
- When it happens: Phase A/B checkpoint, 2026-10-08.

### D-054: Attribute subject and time to effective concern clauses after context gates
- Date / phase / commit: 2026-10-08, Phase B continuation, uncommitted
- Context: Temporal votes were emitted before fiction/negation/recovery gates. Global subject majority allowed repeated ordinary first-person filler to relabel a threatened friend as self. Current distress mentioning how things used to be was classified historical.
- Decision: collect clause subject/time only after effective non-NONE routing; select the context of strongest support evidence. Current unresolved concern outranks older concern at equal priority. Use bounded grammatical/event-time cues independent of urgency vocabulary. Fiction with no active disclosure remains hypothetical; no-concern text has unclear concern-event time. Advance policy to safety-policy-2026.10.08.4.
- Why: tests/test_context_attribution.py reproduces passive/current, medical/current, distress/past-comparison, fiction and filler attribution failures. The original annotation sets mix concern-event time with general statement time; those original labels remain unchanged.
- Alternatives considered: majority over every clause (verified defect); add danger phrases (rejected); relabel corpus to current outputs (rejected).
- Consequences: no new danger alternatives or changed raw models. Benign cases whose old annotation describes ordinary statement time may remain disputed failures, recorded separately. No true multi-turn capability is added.
- Files: Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_context_attribution.py, decisions.md, flow.md, docs/ROUTING-POLICY.md
- What happens: harmless filler cannot override the subject/time of effective danger evidence; current statements stay current without invented immediacy.
- How it happens: evaluate records effective clause context after gates and chooses strongest evidence; _temporal_for_concern uses grammatical present and explicit recent/historical anchors.
- When it happens: clause evaluation and final assembly, before support action generation.
- Symptom: repeated self filler turns another_person into self; time comes from evidence later suppressed.
- Root cause: pre-gate temporal voting and global subject majority.
- Regression test: tests/test_context_attribution.py::test_subject_and_time_follow_relevant_context and test_third_person_risk_survives_repeated_self_filler.

### D-055: Evaluate a pinned local CPU encoder in an isolated environment
- Date / phase / commit: 2026-10-08, Phase B candidate comparison, uncommitted
- Context: D-049 found no local semantic weights/runtime. A feasible downloadable local alternative exists; absence in checkout alone does not justify leaving the engineering comparison unattempted.
- Decision: isolate onnxruntime 1.30.0 and tokenizers 0.23.2 in /tmp/mental-ai-semantic-env; fetch sentence-transformers/all-MiniLM-L6-v2 revision 10dbd2f06a8baf40ad285b037edda610c1b9a57c for offline synthetic evaluation. Keep it outside production and use distinct developer-authored development/validation data, not A/B consumed corpora for fitting.
- Why: official model card lists Apache-2.0, English, 384-dimensional embeddings, 22.7M parameters and 256-wordpiece limit. Official ONNX Runtime supports CPU without a training framework. Dry-run resolver preserves numpy 2.4.4; actual import/inference compatibility must still be measured. Sandbox DNS failed for PyPI/Hugging Face; approved network execution is used only for installation/download.
- Alternatives considered: torch/transformers runtime (larger dependency/runtime footprint); MentalBERT handoff (not a trained routing classifier here); external hosted inference (rejected); more danger vocabulary (rejected). Training-data licenses in the encoder's mixed 1B sentence-pair pretraining remain independently unverified; model card is not a clinical validation record.
- Consequences: new evaluation-only dependencies, no changes to api/requirements.txt or deployed ML stack. Candidate performance may be inadequate; deployment remains disabled. Reviewed labels/policy and qualified release validation remain external blockers even if a small synthetic comparison passes.
- Files: evaluation/requirements-semantic.txt, scripts/fetch_semantic_candidate.py, scripts/evaluate_semantic_candidate.py, evaluation/semantic-development-v1.json, docs/SEMANTIC-CANDIDATE.md, decisions.md, flow.md
- What happens: local model artifacts are fetched at setup, hashed, then used only on synthetic development/validation cases offline.
- How it happens: explicit fetch script pins revision; CPU ONNX embeddings plus a fitted small classifier are compared with current rule routing. No disclosure is sent to a provider.
- When it happens: isolated Phase B engineering experiment, never during an application request.
- Package: onnxruntime==1.30.0; tokenizers==0.23.2 (evaluation-only); existing numpy==2.4.4 and scikit-learn==1.8.0 reused.
- Why this package: CPU ONNX inference and local tokenizer without torch/transformers.
- Packages compared: torch/transformers and sentence-transformers rejected for unnecessary training-framework footprint in this experiment; no new API runtime dependency selected.
- Sources: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2 ; https://onnxruntime.ai/docs/install/

### D-056: Remove unqualified help/constraint phrases from emergency abuse evidence
- Date / phase / commit: 2026-10-08, Phase B false-escalation correction, uncommitted
- Context: Current engine returns IMMEDIATE for homework help, unqualified I need help, a late train preventing departure and fear about an exam. Familiar benign controls did not expose these false emergencies. The first abuse alternative also accidentally concatenated a second assault expression without an OR.
- Decision: remove standalone help, fear-for and inability-to-leave alternatives from ABUSE_THREAT; retain explicit assault/threat/coercion evidence and fix the concatenation separator. No added danger vocabulary.
- Why: tests/test_abuse_scope.py reproduces four false emergencies before correction; explicit current assault controls must remain actionable. Asking for help alone does not state abuse or current danger.
- Alternatives considered: add benign phrase exceptions (rejected: vocabulary loop); dismiss explicit assault (rejected); let raw urgency decide (rejected: noisy model).
- Consequences: unqualified requests may receive limited distress/clarification support, not fabricated emergencies. Previously consumed corpus preserved, outcomes rerun as regressions only.
- Files: Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_abuse_scope.py, decisions.md, flow.md
- What happens: help requests and ordinary constraints cannot independently trigger an abuse emergency; actual assault evidence still routes urgently.
- How it happens: narrower ABUSE_THREAT pattern removes unsupported alternatives and makes the threat/assault OR explicit.
- When it happens: independent raw safety clause evaluation.
- Symptom: IMMEDIATE from I need help with my homework.
- Root cause: ABUSE_THREAT included bare i need help/cannot leave/scared for alternatives.
- Regression test: tests/test_abuse_scope.py::test_unqualified_help_or_constraint_is_not_an_abuse_emergency and test_explicit_current_assault_remains_actionable.

### D-057: Keep the measured semantic candidate disabled after its mixed results
- Date / phase / commit: 2026-10-08, Phase B candidate selection, uncommitted
- Context: D-055's local experiment completed with actual ONNX inference/classifier fitting. The small synthetic validation set shows improved urgent detection with a false emergency and incorrect medication/recovery handling.
- Decision: retain production rules/fallback while explicitly documenting their limits; do not promote the experimental encoder/classifier. Record comparison and exact artifacts/runtime/data provenance. Broader semantic fusion still needs reviewed data and validation.
- Why: baseline 10/18 correct, 1/6 urgent; candidate 13/18 correct, 5/6 urgent with 1/6 benign false urgent. Subject/time and calibration are unvalidated. Actual measurements: cold load n=1 288.31ms; warm n=18 p50 10.19ms, p95/p99 14.84ms; peak process RSS 322512KiB. This is not sufficient release evidence.
- Alternatives considered: enable candidate because recall rose (rejected: false alarm/context failures and tiny developer labels); claim no semantic artifact can be obtained (superseded for this isolated experiment); tune on validation until perfect (rejected).
- Consequences: engineering comparison is completed within synthetic English short-input scope; no production semantic model selected, no clinical/generalization claim. External reviewed-data/policy/release blocker remains. Fingerprint scope now includes evaluation source/data/requirements; prior manifest retained with its stated scope.
- Files: docs/SEMANTIC-CANDIDATE.md, reports/semantic-candidate-20261008-v1.json, scripts/source_fingerprint.py, decisions.md, flow.md
- What happens: measured alternative is reviewable but disabled; raw clinical-sounding probabilities are never fabricated.
- How it happens: evaluation-only script fits development embeddings, then reports validation argmax/logits and baseline routing independently.
- When it happens: after the frozen candidate's first validation execution, before any production selection.
- Supersedes: D-049 only to the extent it treated missing local weights/runtime as blocking an isolated candidate comparison. It does not enable semantic production routing or supersede D-001.

### D-058: Carry reasserted context and preserve resolved historical event time
- Date / phase / commit: 2026-10-08, Phase B temporal follow-through, uncommitted
- Context: After D-054, a personally reasserted quotation reached HIGH via carry-over but kept hypothetical time from the fiction frame. Resolved past self-harm could reach NONE yet lose its explicit historical event time. Present perfect/state auxiliaries and earlier/Hindi past-relative-day markers were omitted from grammatical time cues.
- Decision: record a current self/affected-person context when carry-over actually raises support; retain explicitly identified historical event time even when presentation resolves; extend bounded grammatical auxiliaries and relative-time handling. Do not assign recent to an undated completed act.
- Why: tests/test_context_carry.py reproduces quotation reassertion, history, present state, earlier recovery and Hindi past-day failures before change. Date inference is distinct from current support urgency.
- Alternatives considered: assign current from every HIGH (rejected); erase history when support resolves (rejected); set every past act recent (rejected: missing date must remain unknown).
- Consequences: no new danger alternatives or changed raw probabilities; temporal annotation disputes remain separately reportable. Hindi कल is recent only with a past-tense marker, not when it means tomorrow.
- Files: Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_context_carry.py, decisions.md, flow.md
- What happens: reasserted personal disclosures do not keep fictional time; resolved historical facts remain represented; unanchored past events retain unclear time.
- How it happens: carry-over appends an effective context; historical_event_seen survives routing gates; _temporal_for_concern uses finite state auxiliaries and anchored relative time.
- When it happens: one-input context assembly, after clause gates and before final result serialization.
- Symptom: HIGH/current self-reference reported hypothetical; historical context lost on NONE.
- Root cause: carry-over modified level without context, and effective-context selection omitted resolved historical event metadata.
- Regression test: tests/test_context_carry.py::test_reassertion_recovery_and_present_state_keep_context and test_unanchored_past_act_does_not_invent_a_date.

### D-059: Preserve original temporal labels and compare a separate policy-aligned review overlay
- Date / phase / commit: 2026-10-08, Phase B annotation review, uncommitted
- Context: Original expansion labels mix ordinary activity time with concern-event time. They mark present wishes unclear, resolved years-ago concern current, and undated completed acts recent. Correct routing expectations must not be changed to make an engine pass.
- Decision: record each temporal-only proposal with original value, proposed value, semantic rationale and developer review status in temporal-review-v2.json. Keep original annotations as runner default; an explicit --temporal-review run is supplemental and retains original values/rationale in its report. No input, route, subject, identity or historical dataset is rewritten.
- Why: review of the actual case text against the now explicit concern-event field distinguishes annotation inconsistency from engine error. Present wish is a current state, not stated immediacy; undated past acts cannot be assigned a fabricated date. Benign activity time is not concern-event time. This is developer review, not independent clinical review.
- Alternatives considered: overwrite labels or default silently to corrected labels (rejected); accept unclear for every temporal field (rejected); alter urgent/support expectations (not justified).
- Consequences: original corpus can remain failing while supplemental policy-aligned results are reported separately. Neither score measures independent semantic generalization. Frozen production invariants must be tested with fixtures whose event-time meaning is explicit.
- Files: tests/safety_corpus/temporal-review-v2.json, scripts/run_safety_corpus.py, decisions.md, flow.md
- What happens: reviewers can inspect exact original/proposed annotations and compare both oracles on the same frozen implementation.
- How it happens: loader verifies original annotation values before applying explicitly selected sparse proposals; reports record review version and per-case rationale.
- When it happens: explicit supplemental regression runs, before evaluating cases.

### D-060: Distinguish an explicit fictional character/event from a bare film mention
- Date / phase / commit: 2026-10-08, Phase B temporal context, uncommitted
- Context: Supplemental temporal review exposed fictional character/method events lacking hypothetical time, while the old generic film frame incorrectly assigned hypothetical time to a dead battery.
- Decision: when no active personal concern exists, an explicit fictional character or recognized fictional method event can retain hypothetical time; a bare film mention with no such event remains unclear.
- Why: tests/test_context_carry.py::test_fictional_event_is_distinct_from_a_benign_film_reference fails before change and contrasts a character event, fictional jumping and battery failure. No concern routing or raw model output is changed.
- Alternatives considered: treat every film/book mention as an event (rejected); add danger synonyms (rejected); rewrite the proposed labels to unclear (rejected: explicit narrative is hypothetical).
- Consequences: known fictional event metadata remains distinct from a current author disclosure; unrelated creative references still need broader subject review. No semantic generalization is claimed.
- Files: Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_context_carry.py, decisions.md, flow.md
- What happens: explicit fictional events retain hypothetical time without presenting a personal emergency.
- How it happens: evaluate retains a fictional-character flag after existing frame recognition and combines it with existing evidence during no-active-context assembly.
- When it happens: final temporal assembly after active personal-context selection.
- Symptom: fictional character event unclear; unrelated battery mention hypothetical.
- Root cause: temporal fallback used an over-broad frame alone, then an incomplete event-code subset.
- Regression test: tests/test_context_carry.py::test_fictional_event_is_distinct_from_a_benign_film_reference.

### D-061: Separate fusion completeness and use unresolved legacy concern for clarification
- Date / phase / commit: 2026-10-08, Phase B/C uncertainty contract, uncommitted
- Context: Healthy legacy models still led to complete/NONE despite disabled semantic assessment. D-001 made every learned concern inert, including unfamiliar disclosures with no context rule; D-055's actual comparison demonstrates the rule boundary.
- Decision: add independent fusion with explicit component statuses and assessment scope. Preserve reliable rule concern; an unresolved flagged legacy signal prompts clarification, never emergency by itself. No rule/semantic assessment plus no flagged signal is UNKNOWN. Existing resolved fiction/education/history and location-without-action remain narrow no-concern contexts, with degraded completeness. Unvalidated semantic candidates cannot contribute; a future internally validated structured assessment has a tested boundary.
- Why: tests/test_fusion_availability.py reproduces confident incomplete assessment and demonstrates benign floor context, unresolved learned concern, and Normal/negative urgency failing to cancel HIGH. Candidate remains disabled after measured context errors.
- Alternatives considered: emergency-route every flag (rejected by measured false positives); inert learned concern (superseded); call healthy raw models a complete safety assessment (rejected); mark every input UNKNOWN (rejected: recognized concern/context retained).
- Consequences: more explicit abstention/clarification outside recognized contexts. Original no-concern pipeline expectations may fail under changed declared capability and remain preserved diagnostic data. They must not be re-presented as passing. Language support is degraded when based only on the fallible heuristic. Raw labels/probabilities remain unchanged.
- Files: Step 12 - Packaging/package/mental_health_screening/fusion.py, Step 12 - Packaging/package/mental_health_screening/inference.py, tests/test_fusion_availability.py, docs/ROUTING-POLICY.md, decisions.md, flow.md
- What happens: urgency and completeness are distinct; insufficient available analysis cannot fabricate a safe negative; known HIGH coexists with degradation.
- How it happens: fuse consumes independent evidence, raw status/flag, and optional internally validated SemanticAssessment; it returns support plus component availability without rewriting raw models.
- When it happens: after guarded legacy inference, before response validation/persistence.
- Symptom: disabled semantic path reported complete; no-match legacy concern discarded.
- Root cause: completeness depended solely on legacy success and D-001 prohibited any model contribution.
- Regression test: tests/test_fusion_availability.py (four focused checks).
- Supersedes: D-001 only for clarification on unresolved context; its prohibition on a noisy flag alone declaring an emergency remains. D-051 is generalized to insufficient assessment independent of raw-track success.

### D-062: Require actual educational framing instead of a bare risk noun
- Date / phase / commit: 2026-10-08, Phase B context gate correction, uncommitted
- Context: I have been thinking about suicide returned NONE_DETECTED because EDUCATIONAL_FRAME made prevention/lesson qualifiers optional, then cleared concern despite no educational frame.
- Decision: require the existing educational qualifier alternatives. Bare suicide/self-harm terms cannot establish a context that cancels personal concern. No new danger vocabulary.
- Why: tests/test_education_scope.py reproduces the false-negative gate and contrasts a real prevention lesson.
- Alternatives considered: add a special exception for the reproduced sentence (rejected); allow raw urgency to rescue every false-negative gate (rejected); delete educational protection (rejected: fiction/education controls matter).
- Consequences: personal risk nouns remain supportable or uncertain rather than being falsely educational. True prevention/training context retains its gate. Broader unreviewed rule limitations remain visible.
- Files: Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_education_scope.py, decisions.md, flow.md
- What happens: the system no longer treats mentioning suicide as proof of educational discussion.
- How it happens: remove the optional quantifier around existing educational qualifiers; the gate must actually match the qualifier.
- When it happens: independent clause evidence extraction before routing context gates.
- Symptom: current personal thought returns no concern.
- Root cause: optional qualifier makes the entire bare risk noun an educational match.
- Regression test: tests/test_education_scope.py::test_bare_risk_word_does_not_create_an_educational_frame and test_an_actual_prevention_lesson_remains_contextual.

### D-063: Add a strict versioned analysis contract with availability and model identity
- Date / phase / commit: 2026-10-08, Phase C contract implementation, uncommitted
- Context: API previously dropped fusion components/assessment scope and accepted arbitrary safety enums. Complete/unavailable raw observations could disagree; no response schema version or raw artifact identity existed. Storage still needs to preserve the authoritative snapshot.
- Decision: common api/contracts.py defines schema 1.0, typed safety/raw/components, AnalysisResult snapshot core and PredictResponse with explicit persistence state. Re-export existing API class names. Carry actual fusion statuses/scope/model fingerprint into response; require valid probability distributions and availability invariants. Redact prediction exception messages from logs.
- Why: tests/test_versioned_contract.py fails before change for missing fields, invalid enums and contradictory availability. Model identity hashes actual model/vectorizer/selector/config files; values are not rewritten. Missing semantic means degraded, not complete assessment.
- Alternatives considered: untyped dict/string contract (rejected: drift/contradictions); rewrite raw Normal (rejected); put credentials or disclosure in a fingerprint (rejected); fabricate model/version confidence (rejected).
- Consequences: additive successful-response fields and strict invalid-output failure. Complete raw probability distributions must sum to 1 within 1e-5; bad tracks report unavailable. Semantic remains disabled. This backend schema is implemented, but shared frontend/storage fixture coverage and final freeze remain pending. Persistence defaults not_saved until confirmed by Phase D implementation, never saved by default.
- Files: api/contracts.py, api/api.py, Step 12 - Packaging/package/mental_health_screening/inference.py, tests/test_versioned_contract.py, decisions.md, flow.md, docs/API-CONTRACT-CURRENT.md
- What happens: API reports authoritative safety, capability scope, actual component availability, schema and raw-model identity consistently; invalid availability cannot fabricate observations.
- How it happens: Pydantic literals/model validators share one backend schema; predict constructs it from actual screen output; startup computes a raw artifact/config content fingerprint.
- When it happens: after fusion, before persistence/response delivery; raw probability guard runs inside each model catch.
- Symptom: API omitted component status and allowed invalid safety/time/subject enums.
- Root cause: duplicate permissive response classes and missing producer fields.
- Regression test: tests/test_versioned_contract.py (eight schema/availability checks).

### D-064: Persist validated authoritative snapshots and expose actual save acknowledgement
- Date / phase / commit: 2026-10-08, Phase C/D persistence connection, uncommitted
- Context: Storage omitted safety and versions, stringified null primary labels, and API could not report whether best-effort saving succeeded. PostgREST inserts did not request returned representation, so a real minimal 201 response could not prove record identity.
- Decision: store the validated AnalysisResult core in nullable analysis_result JSONB via additive migration; preserve legacy rows as unassessed; store unavailable condition as SQL null. Request PostgREST return=representation and confirm saved only with record id. Rejected writes return not_saved; attempted writes with unverifiable/network acknowledgement return unconfirmed. No automatic retry/queue. Validate read-back snapshots and reject malformed history rather than treating it as legacy safety.
- Why: tests/test_snapshot_persistence.py exercises real ASGI/model path with synthetic transport; initial assertions fail before implementation. Request owner remains verified claims.user_id. A service-role key bypasses RLS, so application scoping is still required and unchanged.
- Alternatives considered: raw-field-only history (rejected); fire-and-forget task (not durable); fabricate saved on 201 without acknowledgement (rejected); overwrite existing legacy rows (rejected); new queue/database (unnecessary).
- Consequences: isolated/deployed DB must apply the additive migration before inserts containing analysis_result succeed. Migration was NOT executed remotely. Failed saving does not erase support. Snapshot core excludes transient persistence acknowledgement; history returns the authoritative core and explicit legacy marker. Existing owner-scoped filters/deletion remain. Policy advances to .5 for the D-061/D-062 semantics; candidate comparison retains its exact earlier .4 source fingerprint.
- Files: api/api.py, api/db.py, api/contracts.py, supabase/migrations/20261008_authoritative_analysis.sql, tests/test_snapshot_persistence.py, Step 12 - Packaging/package/mental_health_screening/safety.py, decisions.md, flow.md, docs/SUPABASE.md
- What happens: saved history preserves safety/components/raw values/schema/model/policy/threshold; response honestly reports saved/not_saved/unconfirmed.
- How it happens: predict validates response, sends its core to one PostgREST insert, sets persistence after acknowledgement; list_screenings parses the same core schema. Missing snapshots alone are legacy_unassessed.
- When it happens: bounded synchronous HTTP persistence after analysis validation, before response; snapshot parsing during authenticated owner-scoped history.
- Symptom: history discards HIGH and unavailable class becomes string None; no save outcome reported.
- Root cause: manual raw-only row mapping, str() conversion, absent acknowledgement contract.
- Regression test: tests/test_snapshot_persistence.py (five real-route/model checks with provider transport stub).

### D-065: Require event-time evidence before recovery can lower a current intent
- Date / phase / commit: 2026-10-08, Phase B corrective regression, uncommitted
- Context: Current explicit intent was lowered to CONCERNING when another clause said getting help; help is not proof that intent has ended.
- Decision: local historical cap requires historical concern-event time; cross-clause recovery cap requires all effective concern contexts to be historical. Preserve current HIGH alongside help.
- Why: two focused regressions returned CONCERNING before correction; all 19 recovery/temporal/carry checks passed afterward.
- Alternatives considered: ignore every recovery statement (rejected: explicit old event/recovery is meaningful); add phrase exceptions (rejected); use absent now as evidence of history (rejected).
- Consequences: recent or undated concern is not invented historical merely because help is mentioned. This remains one-input context, not conversation memory.
- Files: Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_recovery_scope.py, decisions.md, flow.md
- What happens: current intent remains actionable; explicit old recovered event retains historical support.
- How it happens: evaluate uses _temporal_for_concern and effective contexts to guard both recovery caps.
- When it happens: clause gates and cross-clause aggregation, before fusion.
- Symptom: current personal intent plus help returned CONCERNING.
- Root cause: recovery markers counted as historical and absence of a present-time keyword licensed downgrade.
- Regression test: tests/test_recovery_scope.py::test_help_does_not_establish_resolved_current_intent and test_explicit_old_event_and_recovery_remain_historical.
- Supersedes: D-019's recovery cap only where it inferred history from absent timing.

### D-066: Bound HTTP bodies, sanitize diagnostic identifiers and connect configured limits
- Date / phase / commit: 2026-10-08, Phase E boundaries, uncommitted
- Context: Four red ASGI/validation checks demonstrated newline request IDs, denied valid DELETE preflight, fixed 10000 field cap despite configured 12000, and unrestricted JSON body parsing.
- Decision: whitelist request identifiers (1–64 ASCII letters/digits/underscore/dot/hyphen), generate replacements for invalid IDs, log registered route templates, allow existing authenticated DELETE through listed origins, remove duplicate fixed field cap, and bound /predict bytes before JSON parsing at 12 times configured character cap plus 4096 wrapper bytes.
- Why: a Unicode scalar may use 12 bytes as JSON escaped surrogate pair; character validation independently limits decoded text and never truncates a clause. Denied origins remain denied.
- Alternatives considered: trust Content-Length (rejected: streamed bodies); truncate text (rejected); wildcard CORS (rejected); echo arbitrary IDs (rejected).
- Consequences: huge whitespace/padding can be rejected even around valid text; no analysis bypass. Existing valid identifiers remain echoed. Input limits are read at startup for the screener and through the same validated function for HTTP handling; runtime environment mutation is not an operator interface.
- Files: api/body_limit.py, api/api.py, api/contracts.py, tests/test_http_boundaries.py, decisions.md, flow.md
- What happens: bounded JSON intake, safe correlation IDs and compatible owner-history deletion preflight.
- How it happens: pure ASGI middleware buffers only within the byte cap and replays once; Pydantic validates decoded length; CORS remains explicit.
- When it happens: byte bound before parsing; identifier sanitation before request logging; decoded validation before inference.
- Symptom: four HTTP boundary regression failures.
- Root cause: missing byte middleware, unvalidated header echo, duplicate literal cap, omitted method.
- Regression test: tests/test_http_boundaries.py (five boundary checks, including denied origin).

### D-067: Bound serial model execution and saving across timeout and cancellation
- Date / phase / commit: 2026-10-08, Phase E execution, uncommitted
- Context: predict performed synchronous model/HTTP work in the event loop. A response timeout alone cannot stop a synchronous job. Model thread safety has not been verified.
- Decision: separate serial ThreadPoolExecutor lanes for inference and persistence, each with eight admitted jobs maximum, inference deadline 30 seconds and save deadline 12 seconds. Slots release only when work actually finishes. No automatic retry; overload/deadline returns 503 with Retry-After; failed save admission is not_saved and save deadline unconfirmed while preserving support.
- Why: timeout/cancellation/serial isolation tests exercise actual threads. Initial cap two caused the existing eight-client independence test to fail; eight preserves that bounded workload while serial execution prevents concurrent access to a model instance.
- Alternatives considered: unbounded default executor (rejected); release slots on caller timeout (rejected: runaway work); assume model/client thread safety (rejected); introduce queue platform (unnecessary).
- Consequences: deadlines stop caller waiting, not synchronous execution. A stuck job can exhaust the finite lane; process supervision remains needed. Up to seven jobs can wait behind one running job. Other provider routes/readiness still require separate review; this decision does not claim all runtime work is bounded.
- Files: api/execution.py, api/api.py, tests/test_bounded_execution.py, decisions.md, flow.md
- What happens: prediction and saving stop blocking the event loop and outstanding jobs remain bounded even after cancellation.
- How it happens: semaphore admission before submit, release in worker finally, asyncio shield plus wait_for; independent serial lanes isolate inference from saving.
- When it happens: authenticated predict execution, then validated-result persistence; no task is admitted after capacity is exhausted.
- Symptom: blocking asynchronous route and unbounded continuation risk.
- Root cause: direct synchronous calls without admission control/deadlines.
- Regression test: tests/test_bounded_execution.py (three real-thread checks); tests/test_api_contract.py::test_concurrent_requests_are_independent.

### D-068: Separate liveness and freshness-bounded capability readiness
- Date / phase / commit: 2026-10-08, Phase E readiness, uncommitted
- Context: Every health poll ran synchronous unrestricted inference. Probe accepted nonempty unavailable raw results as healthy without distinguishing required safety from optional degradation.
- Decision: public /live does no inference; /health and /ready share a ten-second monotonic probe cache, keyed to screener instance, with single-flight refresh through bounded inference lane and two-second deadline. Stale success is not served when refresh fails/pends. Independent safety is required; optional analysis degradation is explicitly reported.
- Why: three red route tests show absent liveness/freshness behavior; current fallback safety can be actionable despite unavailable optional models. Disabled semantic assessment must not claim full capability.
- Alternatives considered: indefinite cache (rejected); inference on every poll (rejected); block readiness for optional raw failure (rejected: preserves reliable fallback support); cheap object-existence check (rejected).
- Consequences: failure detection may lag up to ten seconds; cache publishes age/TTL. Auth/database availability is not asserted by these probes. A timed-out synchronous probe remains under the shared admission bound. Degraded readiness is engineering capability, not validated semantic performance.
- Files: api/api.py, tests/test_readiness_freshness.py, decisions.md, flow.md
- What happens: cheap liveness, bounded and freshness-aware readiness with degradation visible.
- How it happens: _fresh_probe checks expiry/identity, single-flight lock and bounded executor; _inference_probe checks required independent component.
- When it happens: operational polls; refresh only after expiry or new screener instance.
- Symptom: unrestricted per-poll inference and no published freshness.
- Root cause: direct probe call without cache/deadline/capability validation.
- Regression test: tests/test_readiness_freshness.py (liveness, expiry/reuse and failed refresh).
- Supersedes: D-007 only for probe frequency/required-vs-optional availability, retaining actual verification.

### D-069: Preserve and explicitly correct an obsolete UNKNOWN-free unit oracle
- Date / phase / commit: 2026-10-08, Phase B/G policy expectation review, uncommitted
- Context: One inherited unit test prohibited UNKNOWN when no rule matches and semantic assessment is unavailable, directly conflicting with the required uncertainty policy and D-061. It also called a present real model silent.
- Decision: preserve exact original test in legacy-unit-expectation-review.md with review rationale; replace the unit oracle with explicit UNKNOWN/degraded/clarification/disabled-semantic assertions. Preserve every original corpus expectation and report failures separately.
- Why: multiple full runs showed the single obsolete unit expectation failure. Negative legacy prediction does not prove supported assessment found no concern. This change follows the written policy, not a changed correct expectation.
- Alternatives considered: leave a knowingly incorrect unit oracle indefinitely (rejected); hide corpus disagreements (rejected); restore fabricated completeness (rejected).
- Consequences: new unit expectations cover engineering uncertainty; unchanged consumed corpus remains diagnostic and failing. No clinical review claimed.
- Files: tests/test_safety.py, reports/legacy-unit-expectation-review.md, decisions.md, flow.md
- What happens: unit regression verifies the required insufficient-capability response.
- How it happens: explicit replacement oracle with preserved original and rationale; production behavior is unchanged.
- When it happens: test execution after D-061 fusion; original corpus remains the default evaluation.
- Regression test: tests/test_safety.py::test_no_match_without_semantic_assessment_reports_unknown.

### D-070: Rate-limit authenticated prediction owners with atomic local-worker state
- Date / phase / commit: 2026-10-08, Phase E request limits, uncommitted
- Context: POST /predict had no request limiter; an in-process counter would multiply allowance across local workers. No distributed limiter service is configured.
- Decision: standard-library SQLite atomic fixed-window counter, 30 admitted predictions per verified owner per 60 seconds. Store SHA256 owner keys only, no tokens/text/email. Local workers share MENTAL_AI_LIMIT_STORE (default /tmp/mental-ai-predict-limits.sqlite3). Enforce after trusted token verification and bounded job admission, before inference. Return 429/Retry-After; unusable limit store fails closed as 503. Each test uses an isolated file and the real limiter implementation.
- Why: focused process test checks eight attempts across four processes admit exactly three at configured test limit; owner/window test checks isolation and retry time; authenticated ASGI test checks 429 and body user_id cannot reset allowance.
- Alternatives considered: per-process dictionary (rejected for local multi-worker allowance); new Redis/service (unnecessary dependency for current single-host arrangement); trust IP/forwarded header for owner identity (rejected); log identities (rejected).
- Consequences: state survives worker restart but /tmp may reset on container restart. This is not a distributed multi-host limiter; replicas require an externally configured shared ingress limit. SQLite file must be local, writable, and shared by intended workers, not network filesystem. Login's existing independent in-process/IP limiter is unchanged. No claim of measured multi-worker API load.
- Files: api/limits.py, api/api.py, tests/conftest.py, tests/test_predict_limits.py, tests/test_http_boundaries.py, .env.example, decisions.md, flow.md
- What happens: admitted requests consume the verified account's bounded allowance; overload cannot create unlimited work.
- How it happens: BEGIN IMMEDIATE serializes counter read/update; expired entries are removed; admission errors return 429/503 without model execution.
- When it happens: inside admitted serial inference job, before screener.screen; token validation remains mandatory.
- Regression test: tests/test_predict_limits.py and tests/test_http_boundaries.py::test_predict_rate_limit_uses_verified_owner_and_returns_retry.

### D-071: Isolate raw artifact initialization failures and validate feature/class ordering
- Date / phase / commit: 2026-10-08, Phase B/E artifact faults, uncommitted
- Context: Missing either raw model prevented screener construction and disabled independent safety. Reversing handcrafted feature order or label encoder order still published apparently complete predictions.
- Decision: keep valid configuration required, but independently guard raw track artifact loading; unavailable track returns null observations through existing per-track catch. Hash unavailable files as null manifest entries. Validate extraction/config feature order, encoder/model class order and probability lengths before publishing. Readiness requires bounded independent safety probe, reports optional artifact availability instead of blocking fallback on raw artifact absence.
- Why: four red tests reproduced both missing-model failures and both falsely complete reordered outputs. Packaged primary LabelEncoder uses sorted configured class names and model indices 0..N-1; urgency uses configured ordered binary classes. Configuration's class list denotes the primary label domain, not encoded index order.
- Alternatives considered: make a negative fallback model (rejected); disable all safety when raw model absent (rejected); assume matching dimensions prove correct ordering (rejected); silently reorder arbitrary model output (rejected).
- Consequences: config absence/invalid threshold still fails construction; optional numpy/scipy/model runtime installation remains an environment dependency. This does not yet fix configurable lexicon-directory provenance. Raw artifact absence is visible in health and readiness degradation; no complete model result is fabricated.
- Files: Step 12 - Packaging/package/mental_health_screening/inference.py, api/api.py, tests/test_artifact_availability.py, decisions.md, flow.md
- What happens: supported raw-text HIGH survives missing raw artifacts; invalid ordering becomes unavailable instead of mislabeled probability.
- How it happens: independent constructor catches plus existing prediction catches, explicit ordered checks and file-content manifest with null missing entries.
- When it happens: initialization and each model track before response construction; capability probe at readiness refresh.
- Symptom: missing raw artifact disables independent safety; reordered inputs/labels report complete.
- Root cause: coupled mandatory load block and unchecked column/class alignment.
- Regression test: tests/test_artifact_availability.py (four focused cases).

### D-072: Use configured feature lexicons and stop fabricating readability zeros
- Date / phase / commit: 2026-10-08, Phase B/E feature provenance, uncommitted
- Context: Feature extraction loaded packaged lexicons even for custom ARTIFACTS_DIR/config filenames; model identity omitted their hashes. Readability exceptions silently became two zeros and primary remained complete.
- Decision: lazily load/cache up to eight configured lexicon path pairs, pass configured filenames from screener to extractor, include both JSON content hashes in raw model identity. Let readability failure reach primary's unavailable boundary; urgency/independent safety remain separate.
- Why: two red focused tests show configurable lexicon API absent and readability failure reporting complete; actual feature implementation is used, not a duplicated model pipeline.
- Alternatives considered: global environment-selected lexicons (rejected: cross-instance contamination); silent zero imputation (rejected: no validated imputation policy); disable urgency with primary features (rejected: independent inputs).
- Consequences: artifact/lexicon files are deployment-immutable; restart after changes to invalidate path cache and startup fingerprint. Model version changes because provenance now includes lexicons, not because raw probabilities are modified. NRC/VADER/textstat installation remains optional processing capability and errors are guarded by the primary track.
- Files: Step 12 - Packaging/package/mental_health_screening/features.py, Step 12 - Packaging/package/mental_health_screening/inference.py, tests/test_feature_provenance.py, decisions.md, flow.md
- What happens: configured lexicons produce actual features and failed readability is unavailable, never a fabricated measurement.
- How it happens: configured path keywords feed bounded lru_cache loader; content hashes join model identity; removed local readability exception-to-zero fallback.
- When it happens: optional feature extraction after independent safety; identity hashed at startup.
- Symptom: wrong lexicons under custom directory; feature error masked as complete.
- Root cause: module-fixed artifact directory and silent imputation catch.
- Regression test: tests/test_feature_provenance.py (configured lexicon and readability failure).

### D-073: Reconcile current policy/contract and checkpoint actual continuation evidence
- Date / phase / commit: 2026-10-08, Phase H interim checkpoint, uncommitted
- Context: Previous handoff/matrix described the D053 state despite implemented D054–D072 changes. Contract diagnostic map contradicted the current schema and policy document still said D001 was fully in force.
- Decision: preserve earlier handoff/contract maps in reports, update current documents/matrix and exact source checkpoint, distinguish unchanged original corpus failures from temporal-only review overlay and unit-oracle correction. Record D045 categories individually below; do not erase historical late-documentation gap.
- Why: full409 tests pass but default corpus259/321 engine and214/321 pipeline; separate temporal review321/321 and252/321. Real models/ASGI exercised; provider transport stubbed. Frontend/model artifact hashes unchanged.
- Alternatives considered: present only passing supplemental engine (rejected); leave stale handoff (rejected); falsely mark local unfinished work blocked by external review (rejected).
- Consequences: engineering/integration partial, release validation externally blocked. Source manifest excludes secrets/raw sensitive data/docs/reports to avoid self-reference. This is an interim checkpoint and work continues.
- Files: docs/ROUTING-POLICY.md, docs/API-CONTRACT-CURRENT.md, reports/api-contract-pre-schema1.md, reports/requirements-evidence.md, reports/recovery-checkpoint-20261008-continuation.json, reports/recovery-continuation-report.md, reports/handoff-after-D053.md, handoff.md, decisions.md, flow.md
- What happens: current implementation, counts/failure IDs and genuine external blockers are reviewable.
- How it happens: actual source hashes and executed JSON reports feed checkpoint/handoff; historical documents remain separate.
- When it happens: after focused implementation verification, before further contract/runtime work.

D045 categories at this checkpoint:
1. Rule expansion/generalization: stopped danger phrase expansion; narrowed false gates, added semantic boundary/comparison/fusion. Reviewed semantic performance remains BLOCKED, candidate disabled.
2. Historical documentation timing: gap preserved; current D046–D072 documentation written alongside batches. No retrospective compliance claim.
3. Seed temporal metadata: separate78-case overlay present; original seeds preserved. Temporal review62 corrections versioned separately with rationale/nonclinical review.
4. Standalone artifacts: routing policy/API field map/one requirements matrix present; shared contract fixture/freeze and final coverage reconciliation IN_PROGRESS.
5. Defect fields: new detailed recovery entries exist; historical table entries still need full template reconciliation IN_PROGRESS.
6. Security/runtime/evaluation: CORS and prediction rate checks PASSED; actual-thread cancellation bound PASSED, route/stale-UI checks IN_PROGRESS; existing Unicode regressions preserved, explicit homoglyph review IN_PROGRESS. Independent confidence intervals NOT_APPLICABLE to dependent synthetic families as an independent sample; reviewed independent release evaluation BLOCKED.

### D-074: Move blocking provider handlers off the event loop and redact exception text
- Date / phase / commit: 2026-10-08, Phase E provider execution, uncommitted
- Context: Slow synchronous history transport inside async route blocked public metrics; auth/login/refresh/delete used the same blocking pattern. Some provider/startup logs interpolated exception messages.
- Decision: make login/refresh/history/delete synchronous FastAPI handlers, using the framework's bounded worker pool (default40 tokens). Keep prediction's narrower explicit lanes. Log exception type only on auth/startup failures. No auth/session/owner semantics changed.
- Why: test_provider_execution.py reproduces metrics future timing out while synthetic history wait holds the event loop. urllib calls already have a configured per-call timeout; worker pool bounds concurrent waits.
- Alternatives considered: duplicate async HTTP client/dependency (unneeded); leave synchronous IO in async handlers (rejected); unbounded thread creation (rejected).
- Consequences: synchronous cancellation does not stop a running HTTP call, which stays under pool/transport timeout bounds. Default40 is framework capacity, not a verified deployment load limit; production load measurement remains separate. Provider timeout/configuration cannot guarantee prompt network completion on every OS failure.
- Files: api/api.py, tests/test_provider_execution.py, decisions.md, flow.md
- What happens: slow provider wait no longer blocks metrics/event loop; logs omit raw exception content.
- How it happens: FastAPI dispatches def handlers through its worker limiter; trusted session dependency and owner filters remain.
- When it happens: login/refresh/owner-history/deletion requests and startup/provider error logging.
- Symptom: unrelated metrics request blocked during history wait.
- Root cause: direct synchronous transport in asynchronous handler.
- Regression test: tests/test_provider_execution.py::test_slow_history_provider_does_not_block_metrics.

### D-075: Validate support invariants without inventing location or reassurance
- Date / phase / commit: 2026-10-08, Phase B/C support contract, uncommitted
- Context: Contract accepted HIGH with reassurance/diagnosis/nonactionable Normal copy. Generic IMMEDIATE action assumed a fall location; NONE/another_person claimed detected risk. Assembly could derive stated timing solely from IMMEDIATE. Failed independent safety still had recognized_rules_only scope.
- Decision: enforce known prohibited reassurance/diagnosis and actionable urgent/clarification/subject wording in SafetyResult; use location-neutral emergency guidance, explicit limited NONE wording for all subjects, remove universal immediacy promotion, and mark unavailable assessment scope when independent/validated semantic unavailable.
- Why: five of six focused tests failed before change; these test actual contract/support functions rather than duplicate presentation logic. Support level is not evidence of timing/location.
- Alternatives considered: accept arbitrary copy (rejected); infer location from urgency (rejected); validate exact current template (rejected: historical snapshots must remain compatible); call a short prohibited-marker check exhaustive semantic validation (rejected).
- Consequences: marker checks enforce specific engineering invariants, not every possible wording or clinical interpretation. History can retain valid earlier wording without exact-template coupling. Generic emergency guidance does not prescribe response to an inferred method. Risk-specific copy/independent clinical review remains required.
- Files: api/contracts.py, Step 12 - Packaging/package/mental_health_screening/safety.py, Step 12 - Packaging/package/mental_health_screening/fusion.py, tests/test_support_contract_invariants.py, decisions.md, flow.md
- What happens: invalid support outputs fail validation; unknown details remain unknown and no-concern copy describes limited supported checks.
- How it happens: common Pydantic validator checks known prohibitions/actionability; support_action selects neutral templates; fuse/evaluate preserve availability/timing metadata.
- When it happens: support assembly/fusion then contract validation, before save or delivery.
- Symptom: HIGH with Normal/reassurance accepted; NONE/other claims risk; emergency assumes balcony.
- Root cause: only nonempty string validation, subject fallback after NONE and unconditional timing promotion.
- Regression test: tests/test_support_contract_invariants.py (six cases).
- Verification correction: the first location-neutral template failed the existing test_d04_unknown_region_support_text_stays_generic_but_actionable because it omitted not-being-alone guidance. Restored that guidance with a safe-companion condition; retained the correct existing test expectation.

### D-076: Share synthetic schema fixtures across backend, API and subsequent consumers
- Date / phase / commit: 2026-10-08, Phase C fixtures, uncommitted
- Context: A common Python schema existed but state coverage was scattered and browser/storage consumers had no shared fixture source.
- Decision: add versioned analysis-v1.json with15 success states and3 error envelopes plus reproducible generator. Validate all successes through common schema/core JSON round-trip and actual authenticated route with explicit inference/provider overrides. Error fixture tests exercise actual auth/input/rate boundaries. No pending fixture because no durable asynchronous saving exists.
- Why: fixtures cover each support state, unavailable components/unsupported/degraded/all unavailable, affected person and saved/not_saved/unconfirmed. Separate original/fault tests still use real models; synthetic contract states are not model performance observations.
- Alternatives considered: duplicate independent fixtures in TypeScript (rejected: drift); generate purported clinical labels (rejected); claim override tests exercise actual model behavior (rejected).
- Consequences: final backend contract freeze/frontend drift gate still pending. Raw base probabilities come from actual original-case inference; fixture safety states are explicitly developer-authored mutations. 422 fixture specifies envelope/location shape; exact framework validation text is not a stable client contract. Do not silently regenerate consumed evaluation data; these are contract fixtures only.
- Files: scripts/generate_contract_fixtures.py, tests/contract/analysis-v1.json, tests/test_shared_contract_fixtures.py, decisions.md, flow.md
- What happens: identical state examples can exercise schema/API/frontend/history consumers.
- How it happens: generator constructs and validates PredictResponse; tests parse the same JSON and compare actual route output under recorded overrides.
- When it happens: contract regression execution and later frontend integration after gates.
- Regression test: tests/test_shared_contract_fixtures.py (schema/core round-trip, real route override and error envelope cases).

### D-077: Attach the affected subject to the actual authored act instead of a companion mention
- Date / phase / commit: 2026-10-08, Phase B subject scope, uncommitted
- Context: I want to kill myself and I am with my friend reported another_person; a companion after the original floor intent caused the same error. Separate companion clause already worked.
- Decision: direct self-owned evidence (unquoted reflexive act, or first-person event before a third-person mention) retains self ownership; later companion mention cannot own that act. Reporting someone else's act still retains another_person. No danger alternatives added.
- Why: two of four focused subject regressions failed before correction;88 subject/context/contract engine checks passed afterward.
- Alternatives considered: every first-person pronoun wins (rejected: I heard my friend would misattribute); ignore third-party risk (rejected); add particular companion sentence exceptions (rejected).
- Consequences: bounded grammatical attachment, not comprehensive parsing. Nested reporting/quotation and multilingual generalization remain review limits; missing ownership should remain uncertain. Standalone engine tests no longer import service/models just for an unused rate-store fixture.
- Files: Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_subject_attachment.py, tests/conftest.py, decisions.md, flow.md
- What happens: author's explicit act keeps self while companion/reporter distinctions remain visible.
- How it happens: existing event pattern positions and first/third-person positions plus reflexive ownership guard third-risk/subject branches.
- When it happens: clause subject/evidence attribution before support priority/context assembly.
- Symptom: self intent attributed to companion.
- Root cause: broad third-party mention plus any act in same clause overrode the actual act's owner.
- Regression test: tests/test_subject_attachment.py (three self/companion and one other-person report).

### D-078: Report actual subject assertion denominators and benign clarification/abstention
- Date / phase / commit: 2026-10-08, Phase A/G measurement correction, uncommitted
- Context: Printed subject errors used total321 despite83 documented opt-outs; zero urgent benign escalation did not expose unnecessary clarification/abstention.
- Decision: report subject_asserted_cases and use it as printed error denominator; add benign route counts and clarification/UNKNOWN case lists, retaining existing urgent false-escalation metric and original labels.
- Why: focused report regression fails for missing asserted denominator;321-83=238 actually asserted cases in current corpus. The new fusion honestly abstains, so useful benign handling must be measured separately.
- Alternatives considered: remove opt-outs silently (rejected); claim0/321 subject mistakes implies all asserted (rejected); count UNKNOWN as safe benign handling (rejected).
- Consequences: historical reports remain unchanged and their total denominator must be interpreted with opt-out count. No independent confidence interval from correlated synthetic families; exact counts are descriptive engineering diagnostics.
- Files: scripts/run_safety_corpus.py, tests/test_corpus_runner.py, decisions.md, flow.md
- What happens: report denominators reflect actual assertions and exposes benign clarification burden.
- How it happens: build_report counts exact subject checks and benign actual levels; print_coverage uses asserted denominator.
- When it happens: evaluation aggregation after actual engine/pipeline results.
- Symptom: inflated subject-check denominator and hidden benign abstention burden.
- Root cause: printed total instead of exact-check count, urgent-only false-positive summary.
- Regression test: tests/test_corpus_runner.py::test_subject_denominator_excludes_documented_opt_outs (initial fixture call lacked screener argument; corrected before genuine missing-denominator reproduction).

### D-079: Bound provider timeout configuration and expose actual frontend limits
- Date / phase / commit: 2026-10-08, Phase C/E runtime contract, uncommitted
- Context: Provider client accepted NaN/infinite/zero/negative/10000-second timeouts; frontend had no common configuration endpoint. Actual route deadline tests existed only at thread boundary.
- Decision: validate provider timeout finite in (0,30] seconds, reject unusable configuration without echoing it. Add public /configuration with schema version, initialized character/derived byte limit, actual urgency threshold (nullable when screener unavailable), policy version and disabled semantic status. Observe late worker exceptions without logging raw message.
- Why: six red tests show invalid timeouts accepted and configuration absent; real-route inference timeout503 and save timeout200/HIGH/unconfirmed already pass. Auth remains required for analysis, not public configuration.
- Alternatives considered: arbitrary long timeout (rejected); hardcoded frontend cap/threshold (rejected); return fake threshold when unavailable (rejected); allow unhandled late exceptions into logs (rejected).
- Consequences: configured network timeout bounds socket waits, not guaranteed termination of every OS/DNS condition; admitted worker slots still bound outstanding work. Frontend can consume actual configuration after gate. No secrets/user data in public response. Environment changes require process restart, not live configuration mutation.
- Files: api/db.py, api/api.py, api/execution.py, tests/test_runtime_routes.py, decisions.md, flow.md
- What happens: invalid transport deadlines fail closed; clients discover effective limits/threshold instead of duplicated constants; support survives save deadline.
- How it happens: finite range validation, typed configuration response from live screener, observed shielded futures, actual route tests with synthetic slow functions.
- When it happens: client initialization/config fetch and authenticated prediction/save deadlines.
- Regression test: tests/test_runtime_routes.py (eight cases; route work controlled, original save-timeout case uses actual models).

### D-080: Align fresh database/container configuration with the implemented runtime
- Date / phase / commit: 2026-10-08, Phase D/E deployment preparation, uncommitted
- Context: Static Docker inspection shows only ML dependencies installed (FastAPI/uvicorn absent), invalid multiline RUN/CMD strings, and HTTP200 health treated as readiness. Fresh SQL still required condition_label and omitted snapshot;10000 DB character cap rejected larger valid API configurations.
- Decision: runtime-only pinned transport manifest from installed/tested versions; Docker installs both ML and transport pins, Python3.12 matches tested interpreter, uses single-line build-time NLTK downloads with failure checks and JSON /ready health check, no copied environment file. Update fresh schema/additive migration for nullable snapshot/label,100000 hard storage cap and explicit least-required service_role grants for actual operations. Include new manifest in source fingerprint.
- Why: actual requirements files prove missing transport install; current462 tests exercise the selected transport versions; SQL/API cap mismatch verified by source inspection. No Docker/remote SQL execution is claimed.
- Alternatives considered: install development SHAP/matplotlib in service image (unnecessary); retain untested3.13 when3.12 is measured (rejected); silently truncate database text (rejected); depend on assumed default grants (rejected).
- Consequences: Docker verification remains BLOCKED (docker --version exits127, command not found). Global python3 -m pip check exits1: unrelated installed PyNaCl1.5.0 requires missing cffi; this is recorded, not fixed by changing unrelated environment or claimed clean. Exact service direct pins were exercised locally, clean container dependency resolution unverified. SQL migration requires isolated project access and no real records were modified. Existing valid<=10000 rows remain valid; constraint change may lock table during authorized migration.
- Files: Dockerfile, api/requirements-runtime.txt, api/requirements.txt, scripts/source_fingerprint.py, supabase/schema.sql, supabase/migrations/20261008_authoritative_analysis.sql, docs/SUPABASE.md, decisions.md, flow.md
- What happens: prepared image includes service dependencies/build-time resources; fresh/existing SQL can represent authoritative nullable analysis and every permitted text cap.
- How it happens: split runtime manifest and Docker install/check commands; additive SQL column/constraint/grants, no data update/delete.
- When it happens: future isolated build/migration verification, not automatic deployment.
- Package: fastapi==0.142.2, starlette==1.7.0, uvicorn==0.54.0, pydantic==2.13.5, python-dotenv==1.2.4 (existing installed dependencies, no added service/provider).
- Why this package: existing service transport/configuration; pin actual exercised versions.
- Packages compared: existing unbounded lower ranges (rejected for deployment reproducibility); full development manifest (rejected for unnecessary image dependencies); new Supabase SDK (still unnecessary).

### D-081: Mark language heuristics limited and retain recognized danger in mixed unsupported material
- Date / phase / commit: 2026-10-08, Phase B language capability, uncommitted
- Context: Heuristic returned complete for short/German-overlap/English/Hinglish/Devanagari examples; any Cyrillic adjacent to explicit English intent caused early UNKNOWN, discarding recognized danger. No general homoglyph model/translation is validated.
- Decision: accepted heuristic cases report degraded capability, not verified understanding. Unsupported language still runs independent recognized checks; no evidence is UNKNOWN/unsupported, while reliable positive evidence survives with unsupported status. Preserve unknown homoglyph handling. Add mixed unsupported/HIGH fixture. Correct only an obsolete complete-capability assertion, preserving its NONE routing expectation and exact original in review report.
- Why: seven of nine focused language tests failed before change; all nine then passed. Existing historical recovery test only fails its obsolete complete assertion; raw flag does not validate language. Original corpus labels unchanged.
- Alternatives considered: equate Latin/English function words with comprehension (rejected); fold all homoglyphs/translate without validation (rejected); early-return before recognized supported danger (rejected); mark every multilingual case safe (rejected).
- Consequences: heuristic can still misidentify language; this is limited recognized-rule capability, not reliable broad multilingual assessment. Actual supported-language/clinical performance remains externally blocked. Mixed text retains urgent support without claiming the rest was understood. No danger vocabulary added.
- Files: Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_language_capability.py, tests/test_safety_contract.py, reports/legacy-unit-expectation-review.md, scripts/generate_contract_fixtures.py, tests/contract/analysis-v1.json, decisions.md, flow.md
- What happens: language/capability limitations remain visible while known danger remains actionable.
- How it happens: degraded heuristic returns, no premature unsupported return, final unsupported/no-evidence UNKNOWN, shared mixed-state fixture.
- When it happens: minimal normalization/capability check then independent clause assessment, before optional processing/fusion.
- Symptom: fabricated complete language capability; mixed material erases explicit intent.
- Root cause: complete labels from script/function words and early exit before evidence.
- Regression test: tests/test_language_capability.py (nine examples, including explicit Cyrillic homoglyph limitation). Initial test command without PYTHONPATH failed import; corrected command reproduced seven genuine failures before repair.

### D-082: Surface contraction and nonfinite feature failures without silent substitutions
- Date / phase / commit: 2026-10-08, Phase B optional measurement honesty, uncommitted
- Context: contractions.fix exceptions silently substituted original string and reported complete processing; NaN handcrafted measurement was accepted by missing-value-aware model and could publish a complete prediction despite failed feature.
- Decision: propagate contraction error to preprocessing unavailable boundary; reject nonfinite handcrafted vector before primary prediction. Preserve independent HIGH and separate urgency when only primary feature fails. Historical training/experiments are unchanged.
- Why: two focused production-path regressions reproduce falsely complete processing/model observations with injected failures.
- Alternatives considered: silent fallback or zero/NaN imputation (rejected: no validated inference imputation policy); fail all safety (rejected); alter historical training scripts (outside scope).
- Consequences: rare contraction inputs may lose optional model outputs honestly. Known safety remains actionable. Function name safe_fix retained for compatibility but documentation now describes failure propagation.
- Files: Step 12 - Packaging/package/mental_health_screening/preprocessing.py, Step 12 - Packaging/package/mental_health_screening/inference.py, tests/test_optional_measurement_failures.py, decisions.md, flow.md
- What happens: failed processing/measurements become unavailable, not apparently measured values.
- How it happens: remove contraction catch-to-original substitution and check finite primary feature vector inside existing per-track catch.
- When it happens: optional processing/features after independent safety, before raw model outputs.
- Symptom: injected contraction/NaN feature still reports complete.
- Root cause: silent fallback and unvalidated handcrafted numeric vector.
- Regression test: tests/test_optional_measurement_failures.py (two scoped failures).

### D-083: Prepare the existing Vercel entrypoint with model root, prefix and build resources
- Date / phase / commit: 2026-10-08, Phase E existing-host deployment preparation, uncommitted
- Context: Current official Services documentation states rewrites preserve /api paths. Existing root api excludes parent packaged models and exposed app routes are unprefixed; entrypoint unspecified. No deployed smoke was verified.
- Decision: backend service root repository '.', explicit main:app thin wrapper mounting the same authenticated app at /api, root runtime requirements, build-only NLTK installer/manifest and explicit bundle inclusion/exclusion. Preserve web service/navigation/design. Respect mounted root_path in body limiter. Runtime NLTK_DATA defaults to bundled build resources. Never run installer from request code or copy secrets.
- Why: missing-entrypoint test initially fails collection; mounted real-model/auth/provider-stub tests pass in477 suite. pip requirements parser resolves all16 existing pinned runtime entries. Official routing/config-reference checked2026-10-08; documentation-only assumptions replaced by concrete local wrapper checks.
- Alternatives considered: move/copy entire application (rejected); rely on prefix stripping contrary to current docs (rejected); deploy automatically (unauthorized); replace hosting provider (unnecessary).
- Consequences: exact Vercel build/project routing/bundle size remain unverified; command -v vercel exits1 and project access is missing. Docker remains blocked separately. Local SQLite state does not implement distributed replica limiting; shared ingress configuration is a release prerequisite. Build resource hashes produced when installer runs; derived nltk_data ignored. No publication or account actions.
- Files: main.py, requirements.txt, scripts/prepare_runtime_resources.py, vercel.json, api/body_limit.py, api/api.py, .gitignore, scripts/source_fingerprint.py, tests/test_hosting_entrypoint.py, docs/SUPABASE.md, decisions.md, flow.md
- What happens: prepared hosting routes /api through the same protected analysis/history and includes artifacts/resources.
- How it happens: thin mount, explicit service root/entrypoint/build/bundle configuration, mounted-path-aware byte middleware.
- When it happens: future authorized build/hosting; local ASGI wrapper is tested now without external deployment.
- Regression test: tests/test_hosting_entrypoint.py (authenticated original result and mounted byte bound).
- Sources: https://vercel.com/docs/services/routing ; https://vercel.com/docs/services/config-reference ; https://vercel.com/docs/frameworks/backend/fastapi . Incorrect guessed /docs/services/configuration URL returned internal error; followed actual reference link instead.

### D-084: Respect NLTK private-download policy with isolated build staging
- Date / phase / commit: 2026-10-08, Phase E failed approach correction, uncommitted
- Context: Isolated build resource command under /tmp first failed restricted DNS/pathsec validation; approved rerun failed NLTK's security check because /tmp is world-writable. Workspace ancestor is group-writable too; do not change unrelated directory permissions or bypass NLTK policy.
- Decision: installer downloads public existing resources into a private temporary directory under the current home, then copies them to configured build output and records content hashes. Output directory initially created mode0700. Approved isolated run output /home/makan/mental-ai-build-resources completes successfully; read/inference verification follows separately.
- Why: actual NLTK error states Unauthorized path for temp archive; private staging satisfies intended trust boundary without weakening downloader. No text sent to network, only public dependency resources downloaded.
- Alternatives considered: disable security/private checks (rejected); chmod user workspace/home permissions (rejected); download at request time (rejected); reuse/change existing user resources (rejected).
- Consequences: build environment needs a writable private home staging location; temporary directory cleans only its own downloaded files. Runtime bundle must be immutable/trusted. Successful local resources do not establish Docker/Vercel build or deployed smoke. Original model files unchanged.
- Files: scripts/prepare_runtime_resources.py, decisions.md, flow.md
- What happens: explicit build install works despite writable build workspace while downloader policy remains intact.
- How it happens: TemporaryDirectory under Path.home with private mode, checked downloads, copytree to output and SHA256 manifest.
- When it happens: explicitly invoked build setup; never runtime request.
- Failed commands: python3 scripts/prepare_runtime_resources.py --output /tmp/mental-ai-build-resources (restricted network then approved NLTK security failure). Corrected private-output approved command exits0.

### D-085: Measure concurrent actual API/model latency and verify isolated build resources
- Date / phase / commit: 2026-10-09, Phase E measurement, uncommitted
- Context: Sequential corpus latency does not measure concurrent API behavior; Docker/deployed/provider latency remain unavailable. New build resources needed actual inference verification.
- Decision: add explicit synthetic one-process ASGI measurement script with provider transport stub, isolated rate state, actual model path, cold import/first prediction and24 requests at concurrency4. Preserve report/source fingerprint and quantile/memory definitions. Verify isolated downloaded NLTK3.10.3 resources via actual original-case package inference.
- Why: executed experiment exits0:24/24 HTTP200/HIGH/saved(stub),0/24 errors/timeouts, cold import1520.13ms(n1),first prediction3295.96ms(n1),warm p5042.52/p9547.86/p9947.95ms, sorted floor quantiles, whole-process peakRSS569132KiB. Resource manifest128 hashed files/six resources; actual primaryNormal .9502395987510681, urgency .7847130134418575, HIGH and complete raw components.
- Alternatives considered: call sequential checks load test (rejected); benchmark real users/provider project (unauthorized/unavailable); conceal cold latency or memory (rejected).
- Consequences: Linux x86_64/Python3.12.3/16 visible CPUs; single model worker/eight admitted jobs. Small synthetic sample, no deployed/multi-worker/real-provider/clinical claim or tail guarantee. Repeat is reproducibility, not independent observation. Model artifacts unchanged.
- Files: scripts/measure_api_runtime.py, reports/runtime-asgi-20261008T184440Z.json, decisions.md, flow.md
- What happens: real engineering latency and memory observations are reviewable with denominators and layer boundaries.
- How it happens: authenticated TestClient requests through actual service and serial executor with transport stub; measured perf_counter/rusage and source manifest.
- When it happens: explicit isolated development experiment, not ordinary requests/health polls.
- Commands: env PYTHONPATH="Step 12 - Packaging/package:." python3 scripts/measure_api_runtime.py --concurrency 4 --requests 24; env NLTK_DATA=/home/makan/mental-ai-build-resources PYTHONPATH="Step 12 - Packaging/package:." python3 -c <original-case inference/resource manifest check recorded in tool execution>. Outside-sandbox TestClient execution approved; no remote project calls.

### D-086: Freeze backend schema1.0 for narrow existing-app development integration
- Date / phase / commit: 2026-10-09, Phase F entry gate, uncommitted
- Context: User-visible original defect remains because Screen ignores safety. Backend schema/core/availability/save states and shared fixtures are stable; engineering verification is distinct from independent semantic/clinical release validation.
- Decision: freeze successful analysis schema1.0 and fixtures as the integration basis; proceed only with types/adapter/support/history/check-in/input/error/cancellation/account scoping within existing containers/design. Preserve frontend baseline hashes/archive and earlier dirty changes. Add generated contract types/drift check rather than unrelated UI tooling. Do not deploy or call development integration a released validated product.
- Why:477 full tests pass including actual model/authenticated routes, optional faults, contract overrides, snapshot round-trip, HTTP/limits/deadline/readiness. PhaseA runner mutations pass; PhaseB declared limited-rule/uncertainty engineering is implemented; semantic/qualified review BLOCKED. PhaseC backend contract is stable; frontend/shared consumer checks now follow. PhaseD transport-stub engineering verified, real isolated Supabase BLOCKED. PhaseE local bounded runtime/resource/concurrent one-process evidence verified, Docker/Vercel/deployed and distributed ingress tests BLOCKED on tooling/project/config access. No locally known headline/scope defect is excused by external review.
- Alternatives considered: leave rawNormal user presentation indefinitely pending clinical review (rejected: independent engineering repair); redesign app (forbidden); enable unvalidated candidate (rejected).
- Consequences: no safety performance/clinical generalization claim; unchanged consumed corpus routing disagreements remain visible (reviewed-time engine321/321,pipeline252/321;69 uncertainty disagreements). 0/238 asserted subject errors,83 opt-outs; zero urgent benign escalation is not benign understanding. Browser acceptance still to run. Subsequent backend contract changes need new additive/versioned decision and drift verification.
- Files: reports/frontend-integration-start.json, decisions.md, flow.md; subsequent scoped consumer files recorded in their focused decisions
- What happens: existing app begins consuming the authoritative frozen result instead of raw classifier headline.
- How it happens: common backend schema drives frontend types/fixtures, one view adapter, scoped local/history support and stale-response guards.
- When it happens: after A–E engineering evidence/genuine external blockers recorded; before any frontend edits.
- Supersedes: D-042 only for the user's explicitly permitted behavioral integration; all visual/layout/auth/ownership preservation constraints remain.
- Preservation checkpoint: source74b35489a2c9de1123c6e0dd3aac4b165455c3b4170375310361f698ce6a322a;61 web source/config entries in manifest; pre-integration npm run typecheck exits0. Source archive /tmp/mental-ai-frontend-before-phaseF.tar.gz excludes env/node_modules/real data. Earlier frontend hashes unchanged relative to recovery checkpoint.

### D-087: Derive frontend contract types and validate the actual response before presentation
- Date / phase / commit: 2026-10-09, Phase F contract/transport batch, uncommitted
- Context: Old TypeScript omitted safety/status/schema/persistence and required nonnull raw outputs; transport accepted any HTTP200 as PredictResponse. Explicit empty Authorization was overwritten by stale token; pre-aborted signals were not propagated and deadline ended before JSON body reading.
- Decision: derive successful wire interfaces from Pydantic JSON schema using standard Python/existing TypeScript; move existing ConfigurationResponse to common contract without changing its fields. One analysisView module validates enums/availability/probabilities/support/save invariants and maps authoritative safety independently from raw models. Transport validates prediction/config, respects explicit authorization headers, preserves cancellation/deadline through body consumption and Retry-After. Client prediction80s covers max provider30+inference30+save12+delivery margin; auth/history35s covers provider maximum. No automatic retry.
- Why: strict types reproduced eight compiler errors in old consumers/new adapter (including unsupported ES2022 hasOwn); kept existing ES2020 target and replaced hasOwn with compatible own-property check. Actual-module contract QA passes30 checks over16 shared states, mutations/auth/rate/cancel/malformed responses with mocked fetch. Screen/history wiring remains pending, so full frontend typecheck is not yet passed.
- Alternatives considered: manually drifting types (rejected); null-to-zero presentation (rejected); add schema/validation library (unneeded); raise JavaScript target merely for hasOwn (rejected); hide raw outputs or infer safety from Normal (forbidden).
- Consequences: parser checks specific contract invariants, not clinical meaning; TypeScript types alone are not runtime validation. Initial adapter source preceded these shared-consumer tests; this sequence is recorded honestly, not retrospectively described as test-first. Existing backend/real-model tests remain separate. Package scripts add QA using already installed TypeScript; no dependency added or prior auth/UI changes discarded. Visual files unchanged.
- Files: api/contracts.py, api/api.py, scripts/generate_contract_types.py, web/src/lib/contract.ts, web/src/lib/analysisView.ts, web/src/lib/api.ts, web/scripts/contractqa.mjs, web/package.json, decisions.md, flow.md
- What happens: malformed/legacy prediction responses fail honestly; HIGH cannot become Normal headline, unavailable remains null, and save status remains explicit in view data.
- How it happens: Pydantic schema renderer/check mode plus actual TypeScript validators/view adapter and bounded/cancellable fetch boundary.
- When it happens: type regeneration/drift check and response consumption before any render/local save.
- Regression test: npm run qa:contract (mocked fetch, actual application modules); npm run typecheck currently fails on pending Screen nullable/config consumers.

### D-088: Scope browser history/check-in to the adopted account and preserve authoritative snapshots
- Date / phase / commit: 2026-10-09, Phase F storage batch, uncommitted
- Context: Actual-module regression returned another account's globally stored history (1 record instead of0); raw-only records also lost authoritative safety and null component states. Check-in prefixes invented current timing around arbitrary answers.
- Decision: privateStore receives the adopted verified identity from auth setState before subscribers. History/check-in keys include that identity, anonymous access returns no private data. Preserve unowned old global records untouched and hidden because their owner is unknown. Store validated full response snapshots; merge owner-scoped server snapshots, retaining local original text only when record ids match. Legacy rows are unassessed, corrupt snapshots unavailable; device save failure is explicit. Flatten check-in values in prompt order without added semantic prefixes.
- Why: initial QA failed privacy assertion1!=0; corrected actual modules pass51 checks across16 response states and account switches/storage failure. Added server core/legacy/corrupt mapping checks subsequently. No null-to-zero conversion or inferred safety from old Normal.
- Alternatives considered: assign all old global data to whoever logs in (privacy failure); delete old data (violates preservation); treat cleaned server text as original (meaning loss); invent conversation memory (unsupported).
- Consequences: old unowned local records remain recoverable outside automatic app mapping; per-account device history is capped12 and server history remains separately owner-scoped. Browser storage is not encryption against someone with access to the browser profile. Server retrieval omits original disclosure, so cloud-only rows display recorded results without reconstructing input. Snapshot validation does not reassess history.
- Files: web/src/lib/privateStore.ts, web/src/lib/history.ts, web/src/lib/checkin.ts, web/src/lib/auth.ts, web/scripts/contractqa.mjs, decisions.md, flow.md
- What happens: account switches cannot automatically show another account's check-in/history; recorded support state and availability survive device/account mapping.
- How it happens: auth publication -> owner scope -> guarded storage/parser -> response-to-view adapter; server read-back acknowledgment represents an observed saved row.
- When it happens: session adoption/clearing, explicit local save/read, authenticated history retrieval; check-in is never automatically submitted.
- Symptom: shared history leaked into another account's view and stored only raw labels.
- Root cause: global browser keys and raw-only ScreeningRecord schema.
- Regression test: web/scripts/contractqa.mjs (owner switches, preserved old data,16 snapshot states, failed device write, server/legacy/corrupt mapping).

### D-089: Drive the existing screen and recorded history from safety, with cancellation and configured limits
- Date / phase / commit: 2026-10-09, Phase F presentation batch, uncommitted
- Context: Static actual Screen source used raw primary class as headline, raw Not elevated/hardcoded0.15, null arithmetic and raw-only history; regional resources assumed India. Async delayed reveal had no account/generation guard. Shared contract typing made the old consumer fail compilation.
- Decision: keep existing layout/classes/style/assets/navigation/login; replace support content within existing result cells/aside. Main headline uses analysisView safety, raw research values remain separate unchanged. Nullable urgency shows Unavailable and no meter. Actual public configuration drives Unicode-code-point validation; remove DOM truncation. Support action/capability/account and device saving status are explicit. Load owner-scoped account snapshots; history is recorded-state viewing, not current reassessment. Device-clear explicitly leaves account rows. Abort plus generation/owner guards prevent cancelled, old, unmounted or other-account responses/timers overwriting state. Reveal returned results immediately while preserving the existing in-flight animation.
- Why: old source paths verified directly; typecheck now exits0 after nullable/config wiring. Focused browser regression written before Screen change, but initial attempts were environment failures (missing matching Chromium, sandbox process socket, unavailable sandbox server); they are not recorded as a reproduced assertion failure. Browser original-case verification follows against isolated loopback real routes/models with provider stub.
- Alternatives considered: prominent rawNormal/Not elevated (violates authoritative routing); hardcoded limits/threshold/region (inconsistent); delay urgent guidance for cosmetic completion (unnecessary); redesign or change visual files (forbidden); assume account save succeeds (dishonest).
- Consequences: region is unknown, so no region-specific numbers shown. Cloud-only history cannot restore absent original text. Account/device storage is explained without claiming no server transmission. Generic support remains available during failures; no unauthenticated analysis route added. Cancellation does not guarantee stopping backend synchronous work; bounded backend capacity handles that separately.
- Files: web/src/pages/Screen.tsx, web/scripts/screenqa.mjs, tests/serve_synthetic_api.py, decisions.md, flow.md
- What happens: support headline/guidance/capability and saved history follow authoritative schema1.0; raw probabilities remain research details.
- How it happens: validated api response -> analysisView -> existing result containers; generation/controller/owner check before each async state update; history snapshot uses same adapter.
- When it happens: explicit authenticated text submission, recorded-history selection, cancellation/reset/account change, component/error/save states.
- Symptom: backend HIGH with rawNormal was prominently displayed Normal; unavailable values could become reassuring output.
- Root cause: Screen consumed only legacy primary/urgency fields and delayed callback lacked identity/request guards.
- Regression test: web/scripts/screenqa.mjs original-case browser acceptance (execution pending at this decision); web/scripts/contractqa.mjs shared consumer states. npm run typecheck exits0.

### D-090: Prevent late authentication work from restoring or replacing a newer session
- Date / phase / commit: 2026-10-09, Phase F authentication race repair, uncommitted
- Context: Actual auth-module regression with explicitly stubbed SDK/fetch verified that completing login verification after logout restored the old session/token. The browser's candidate verification also replaced the global token before verification, and SDK refresh/account events were ignored while authenticated.
- Decision: generation-guard login/boot/refresh/SDK/register adoption and publication; logout invalidates outstanding generations and unsubscribes its watcher. Verify candidates using an explicit Authorization header without altering the current token. SDK sessions also pass the backend verification before publication; changed SDK tokens are no longer ignored. Publish only with verified nonempty identity and usable expiry; clear both mirrors before honoring the chosen remember scope.
- Why: new focused regression failed with nonnull synthetic session after logout, then passes in53-check actual-module QA; typecheck passes. No provider bypass added. Earlier dirty auth behavior/layout preserved except these necessary session-state fixes.
- Alternatives considered: abort only fetch (late resolutions can still publish); trust SDK display identity without server verification (wrong local scope boundary); clear token from a stale failure (would invalidate a newer account).
- Consequences: latest initiated session operation wins; superseded work is cancelled at the application-state boundary even if underlying HTTP finishes. A failed stale operation cannot clear a newer token. SDK real project refresh/OAuth remains externally unverified; unit tests explicitly replace SDK with null and fetch with synthetic responses.
- Files: web/src/lib/auth.ts, web/src/lib/api.ts, web/scripts/contractqa.mjs, decisions.md, flow.md
- What happens: logout stays logged out and another session cannot be overwritten by delayed verification.
- How it happens: generation checks around awaits/publication plus candidate-specific session verification header and scoped owner publication.
- When it happens: login, restoration, refresh, SDK token/account change, account creation response and logout; no account creation is performed in tests.
- Symptom: delayed login undoes logout.
- Root cause: no invalidation token around asynchronous session adoption; global bearer set before verification.
- Regression test: web/scripts/contractqa.mjs delayed verification/logout scenario (fetch/SDK overrides explicitly recorded).

### D-091: Make the documented contract drift command independent of PYTHONPATH and working directory
- Date / phase / commit: 2026-10-09, Phase F verification correction, uncommitted
- Context: Direct `python3 scripts/generate_contract_types.py --check` failed ModuleNotFoundError: api despite execution from repository root; Python sets sys.path to the script directory.
- Decision: resolve the repository root from __file__, add it for common-contract imports and resolve the generated output relative to that root. No generation semantics or wire fields changed.
- Why: exact previously failing command now exits0. The generator can run without importing models/NLP and without special shell environment.
- Alternatives considered: require undocumented PYTHONPATH (unnecessary fragility); add packaging/build dependency (unneeded).
- Consequences: generated type content stays unchanged; --check rejects actual schema/type drift. Current suite477 passes20.95s after common schema changes, one existing TestClient deprecation warning.
- Files: scripts/generate_contract_types.py, decisions.md, flow.md
- What happens: documented drift verification works directly.
- How it happens: explicit repository-root import/output paths.
- When it happens: manual generation or verification, not requests.
- Symptom: documented drift command cannot import api.
- Root cause: script-directory Python import path and cwd-dependent output path.
- Regression test: executed `python3 scripts/generate_contract_types.py --check` (red then exit0); no redundant unit test for path construction.

### D-092: Provide an opt-in isolated Supabase verification command without consuming existing credentials
- Date / phase / commit: 2026-10-09, Phase D blocked-integration preparation, uncommitted
- Context: Stubbed route/model tests cannot establish real GoTrue, database grants/RLS or tenant read-back; current environment does not establish an isolated project/two test identities. Exact future command needed.
- Decision: add explicit MENTAL_AI_TEST_* configuration-only gate and opt-in isolated real integration harness. Never load repository env for testing. Authenticate pre-provisioned A/B and check expected trusted ids before writing synthetic original case, verify concurrent owner filters and unprivileged direct RLS read-back, snapshots and refresh. Cleanup filters only newly acknowledged ids plus owner, never bulk deletes existing history. Missing expired-token/fault/SDK access stays specifically blocked. No invitations, account creation, migrations or deployments.
- Why: --check-config executed exits2 with required variable names only, no network; py_compile passes. Direct client call names checked against actual SupabaseClient._call implementation. Real workflow remains unexecuted and must not be described as passed.
- Alternatives considered: use present real project keys (isolation unknown); fabricate accounts/invitations (forbidden); call transport stub real integration (dishonest); bulk clear test-user records (unnecessary data loss).
- Consequences: operator must supply explicitly isolated config/two ids and credentials securely, apply prepared migration there separately. Network-write uncertainty may leave a newly generated unacknowledged row requiring scoped manual follow-up; harness never guesses ids or retries writes. Harness remote behavior remains unverified until access exists.
- Files: scripts/verify_supabase_isolated.py, decisions.md, flow.md; docs/SUPABASE.md updated in documentation reconciliation
- What happens: missing external input produces precise BLOCKED status; configured explicit run exercises actual provider behavior.
- How it happens: environment guard -> real ASGI/auth/model -> standard provider client/read-back -> new-id/owner cleanup -> sanitized report; keys/tokens/response bodies absent from report.
- When it happens: explicit development command only; --check-config never performs network work.

### D-093: Keep non-JWT Supabase API keys out of bearer headers
- Date / phase / commit: 2026-10-09, Phase D final provider compatibility correction, uncommitted
- Context: SupabaseClient._headers always copied either API key into Authorization Bearer. Current official key documentation says sb_publishable_/sb_secret_ are not JWTs and belong in apikey, while user identity uses its own JWT. Present stub keys masked this contract error.
- Decision: recognized new API-key prefixes are sent only on apikey, with no default Authorization. Actual user access_token overrides Authorization per request as before. Legacy JWT-key bearer compatibility is retained, as are privileged owner filters and server-only secret use.
- Why: new focused header regression initially fails1/3; corrected transport-only tests pass3/3. Official primary documentation reviewed2026-10-09; real project still unavailable, so no claim of observed deployed/provider success.
- Alternatives considered: blindly send every key as JWT (incorrect contract); migrate keys or rotate real credentials (unnecessary/not authorized); add full SDK dependency (unneeded); weaken user verification (forbidden).
- Consequences: new and legacy application key types supported at the transport boundary; live gateway/grants/RLS/auth verification remains BLOCKED. Unit tests use synthetic nonfunctional keys and captured headers only.
- Files: api/db.py, tests/test_provider_key_headers.py, decisions.md, flow.md
- What happens: new application keys do not masquerade as user JWTs; actual bearer identity remains separate.
- How it happens: _headers selects apikey and conditionally legacy bearer; _call applies explicit access_token to a fresh request-local dict.
- When it happens: each provider HTTP call, prior to transport; no mutable client session identity.
- Symptom: new sb_* key copied into Bearer header.
- Root cause: unconditional legacy JWT-key header pattern.
- Regression test: tests/test_provider_key_headers.py::test_non_jwt_keys_are_not_sent_as_bearer_tokens; test_verified_user_bearer_is_separate_from_new_application_key; test_legacy_key_bearer_compatibility_is_retained.
- Source: https://supabase.com/docs/guides/getting-started/api-keys (known limitations/API key versus user identity); https://supabase.com/docs/guides/database/postgres/row-level-security (grants and policies). These references do not prove this project's remote configuration.

### D-094: Remove invented self-harm interpretation and future location-service promise from generic HIGH guidance
- Date / phase / commit: 2026-10-09, Phase B/F support-copy correction, uncommitted
- Context: All self-subject HIGH copy said thinking about harming yourself, although recognized HIGH also includes a writer's threat to attack someone. The same copy promised a later country-to-service conversation that this single-text API does not implement. Browser snapshot exposed that promise.
- Decision: generic HIGH describes a serious concern, retains urgent trusted-person/crisis/local-emergency support, conditional safe distance from hazards, and help finding local support without promising a conversation or verified regional lookup. Another-person branch unchanged. Bump policy version to safety-policy-2026.10.09.6; routing/classifier mechanics unchanged; regenerate current shared contract fixtures, preserve historical reports/snapshots.
- Why: focused invariant initially fails1/7; correction passes7/7 including actual-model threat input routing HIGH without self-harm attribution. No text proves every HIGH is suicide. No country/region/multi-turn contract exists. Backend schema1.0 fields remain frozen.
- Alternatives considered: add unneeded chat/location subsystem (unsupported scope); infer risk kind from HIGH (wrong); drop urgent guidance (unsafe); rewrite stored past snapshots (forbidden).
- Consequences: wording is deliberately generic when category alone cannot identify harm kind. It is not independently clinically reviewed. Existing historical policy .5 snapshots remain valid recorded results; current fixture metadata/copy uses .6. No model or danger vocabulary expansion.
- Files: Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_support_contract_invariants.py, tests/contract/analysis-v1.json, decisions.md, flow.md
- What happens: generic HIGH guidance remains actionable without attributing an unstated act or promising unsupported follow-up.
- How it happens: support_action template amendment, policy version bump and current fixture regeneration.
- When it happens: support assembly after fusion/current analysis; previous stored snapshots are preserved.
- Symptom: self-subject HIGH threat-to-others receives self-harm copy and country conversation promise.
- Root cause: universal self-subject HIGH template covered multiple danger contexts.
- Regression test: tests/test_support_contract_invariants.py::test_high_copy_does_not_invent_self_harm_or_location_conversation.

### D-095: Reconcile current documentation, preserved history and measured integration gates
- Date / phase / commit: 2026-10-09, Phase H final documentation, uncommitted
- Context: Current flow/README/contract/Supabase prose still described HMAC auth, direct blocking inference, missing safety storage, ignored browser safety and verified Docker. Historical register omitted full fields. Documentation cannot supersede measured failures or rewrite historical decisions.
- Decision: preserve prior documents/reports, replace current descriptions with verified connected calls, common field map, standalone evaluation coverage and one requirements matrix. Complete defect fields with historical/reported versus currently reproduced evidence distinguished. Record .5 before/.6 after browser evidence, all external blockers and exact defaults/source fingerprints. No production semantic.assess call is claimed: fuse defaults semantic disabled; adapter exists for isolated evaluation/future reviewed integration. Add npm qa:screen for the actual browser procedure.
- Why: final481 backend tests pass19.17s(one deprecation warning),54 actual-module checks pass,34 final-policy browser checks pass, typecheck/lint/build/drift checks pass. Default corpus still engine259/321,pipeline214/321; temporal proposal diagnostic separately321/321 and252/321,69 routing/uncertainty disagreements. Model artifacts and pre-integration design hashes unchanged. These results must all remain visible.
- Alternatives considered: show only passing supplemental engine (misleading); leave old readiness/auth/deployment claims (false); reconstruct unknown historical timing/evidence (forbidden); call stub persistence real integration (false).
- Consequences: ENGINEERING partial (limited semantic capability/remaining diagnostic disagreements), INTEGRATION partial (development consumers verified; real project/platform blocked), RELEASE_VALIDATION blocked (reviewed policy/data/independent qualified review missing). Current local recovery work is reviewable; no deployment/commit/push/staging/real-user write. Historical late-documentation gap remains unfixable retrospectively; current entries do not claim D001–D045 were written alongside code.
- Files: README.md, flow.md, handoff.md, docs/API-CONTRACT-CURRENT.md, docs/ROUTING-POLICY.md, docs/SUPABASE.md, docs/EVALUATION-COVERAGE.md, reports/requirements-evidence.md, reports/defect-register.md, reports/recovery-final-report.md, reports/recovery-final-checkpoint.json, reports/browser-acceptance-current.json, reports/browser-acceptance-policy5.json, reports/browser-original-before.json, reports/browser-original-after.png, reports/browser-original-policy5.png, web/package.json; previous current-document snapshots in reports; api/api.py comment correction
- What happens: actual implementation, measured scope, failed/blocked requirements and preserved histories are connected in reviewable documentation.
- How it happens: executed reports/source manifests and static current call paths populate field map/matrix/handoff; exact case ids and denominators retained.
- When it happens: after focused implementation verification and final .6 browser/model diagnostics, before session handoff; no retrospective claim about old documentation timing.

### D-096: Reproduce the frozen semantic comparison against current policy without tuning
- Date / phase / commit: 2026-10-09, Phase G final reproducibility, uncommitted
- Context: The first semantic comparison reports baseline policy .4; current policy .6 has later context/fusion/copy changes. Historical numbers must not be reassigned silently to current source.
- Decision: rerun the same pinned local encoder/logistic development36/validation18 experiment against current independent engine .6, write a separate reproducibility report and keep prior report intact. No data/model/threshold selection change, no final-set fitting or production enabling.
- Why: actual run exits0 with unchanged baseline10/18 labels,1/6 urgent; candidate13/18,5/6 urgent and1/6 benign urgent escalation. CPU two intra-op threads, concurrency1; cold load241.49ms(n1),warm n18 p506.82/p95-p998.47ms; whole-process peakRSS322684KiB. Model/runtime telemetry-id persistence warning fell back to in-memory identifier; inference completed. These are repeat observations on consumed synthetic C data, not independent final results. The baseline measured here is the independent engine, not production fusion or authenticated pipeline.
- Alternatives considered: claim historical .4 experiment measured current .6 (false); tune candidate from repeat validation (rejected); enable candidate after repeated same accuracy (unjustified).
- Consequences: production remains disabled; exact current source/artifact/data hashes recorded by evaluator. Repeated fitting uses only the same development rows; validation remains unused for tuning. Subject/time/clinical/generalization/license/overlap limits unchanged.
- Files: reports/semantic-candidate-20261009-reproducibility.json, docs/SEMANTIC-CANDIDATE.md, docs/EVALUATION-COVERAGE.md, reports/recovery-final-report.md, reports/recovery-final-checkpoint.json, handoff.md, decisions.md, flow.md
- What happens: current baseline comparison is reviewable without overwriting historical evidence.
- How it happens: existing isolated local evaluator and pinned artifacts, unchanged synthetic split and classifier settings.
- When it happens: final explicit reproducibility check; not request handling or independent evaluation.
- Command: /tmp/mental-ai-semantic-env/bin/python scripts/evaluate_semantic_candidate.py --artifacts /tmp/mental-ai-semantic-artifacts --output reports/semantic-candidate-20261009-reproducibility.json

### D-097: Retain an expired browser mirror long enough to try its own refresh token
- Date / phase / commit: 2026-10-09, Phase F final session restoration correction, uncommitted
- Context: Final actual-module audit showed readStored discarded expired mirrors; validateSession then saw no mirror/SDK session and signed out without reaching its refresh branch, contrary to documented behavior. Refresh-token-only recovery was present only after rejection of a still locally unexpired mirror.
- Decision: prefer usable stored mirror, then retain a finite expired mirror for bounded existing verification/one refresh recovery. Refresh uses that exact mirror's token/scope, not a token from another stored scope. Existing generation guards and server-verified identity remain; no authentication bypass or invented expiry.
- Why: new focused actual auth-module regression failed null != owner-b and no refresh. Corrected check verifies one refresh and restored expected identity. Add actual browser expired-mirror/reload/refresh route check with synthetic provider; genuine provider expiry remains external.
- Alternatives considered: throw away usable refresh token (unnecessary logout); pick any other scope's refresh (account mismatch); fabricate future expiry (forbidden); silently trust mirror without server call (forbidden).
- Consequences: local mirror expiry is not actual provider-token validity. GoTrue and generation checks decide identity; invalid refresh signs out. Real expired-token/SDK behavior remains blocked on isolated access. Existing appearance/navigation unchanged.
- Files: web/src/lib/auth.ts, web/scripts/contractqa.mjs, web/scripts/screenqa.mjs, decisions.md, flow.md; final documentation/checkpoint updated after verification
- What happens: expired mirror can recover the same authenticated account instead of being discarded before refresh.
- How it happens: readStored usable-first/expired-fallback plus exact candidate refresh token within validateSession recovery, guarded publication.
- When it happens: boot/reload session restoration; one bounded existing refresh attempt on verification/expiry rejection.
- Symptom: expired mirror signs out despite usable refresh token.
- Root cause: readStored removed expired candidate before validateSession could execute refresh recovery.
- Regression test: web/scripts/contractqa.mjs expired mirror scenario (fetch/SDK overrides); web/scripts/screenqa.mjs expired browser mirror reload (actual route/provider STUB).

### D-098: Make the public application verifier fail honestly and execute actual observations
- Date / phase / commit: 2026-10-09, Phase A/E continued program audit, uncommitted
- Context: npm run verify printed two failures but exited0; preprocessing was marked PASS by an unconditional append and inference checked only two dictionary keys. Cwd-relative artifact paths also failed outside the repository. Resource lookup incorrectly treated zipped VADER as absent.
- Decision: root-relative, import-safe offline verifier with configured artifact filenames, actual original-case safety/preprocessing/legacy observations, correct zipped-resource paths, exact statuses and nonzero required failure. Public HTTP probes are explicit --api-url only; historical training reconstruction is outside packaged inference, and independent semantic validation stays BLOCKED. Add optional sanitized JSON evidence report.
- Why: original execution produced5 PASS/2 FAIL/2 SKIPPED with exit0; focused subprocess reproduced4 FAIL and exit0 from temporary cwd. Corrected two focused checks pass. Actual offline verification follows separately; no retrospective inference or training claim.
- Alternatives considered: merely change exit code (leaves fabricated verification); retrain to generate historical .npz files (unnecessary and changes experiments); contact configured provider automatically (not isolated).
- Consequences: verifier checks installation and actual frozen model paths, not clinical validity or real provider integration. No package/model changes, downloads, credentials or private data. BLOCKED independent review does not count as locally failed engineering or a release pass. Initial corrected WordNet zip-directory lookup omitted its trailing slash and failed; actual lookup probe confirmed the required slash, then corrected without hiding that failed command.
- Files: scripts/verify_project.py, tests/test_project_verifier.py, reports/program-offline-verification.json, decisions.md, flow.md, reports/requirements-evidence.md, reports/defect-register.md
- What happens: broken required checks cannot produce a successful process status; unavailable model/preprocessing results cannot be called working.
- How it happens: run_checks executes actual producer, check_screen_result distinguishes component availability, main aggregates FAILED and returns1. Root resolves from __file__; no .env/provider consumption.
- When it happens: explicit python3 scripts/verify_project.py or npm run verify, before claims about application checks.
- Symptom: failure output with exit0 and invented preprocessing PASS.
- Root cause: absent sys.exit, unconditional result append, dictionary-key-only inference assertion, cwd-relative paths and wrong zipped resource lookup.
- Regression test: tests/test_project_verifier.py::test_verifier_exits_nonzero_for_missing_artifacts; test_verifier_does_not_accept_unavailable_models_as_working (2 passed2.80s; first old exit-code assertion genuinely failed, second missing new boundary import also failed).

### D-099: Gate one-command development on required readiness and connect custom ports
- Date / phase / commit: 2026-10-09, Phase E/F continued program audit, uncommitted
- Context: start-dev.sh accepted /health200 even when required readiness failed; Vite always proxied8000 despite documented API_PORT override. Hard primary-file precheck blocked working independent fallback and ignored application .env artifact resolution. Signal trap could continue after interruption; Vite silently chose another occupied port.
- Decision: require /ready HTTP success and ready=true within validated1..300s startup budget, validated ports, explicit signal exit/owned backend cleanup, strict loopback web port and launcher-derived VITE_DEV_PROXY_TARGET. Remove coupled primary precheck; application readiness determines required capability. Add explicit npm run dev:isolated using existing synthetic server and blank SDK configuration; regular npm run dev keeps real auth configuration. Fingerprint root package/launcher as actual execution sources.
- Why: controlled child programs reproduce two required-gate/custom-proxy failures; corrected2/2 pass1.06s. Actual isolated launcher outside sandbox reached ready and Vite5199 against backend8127. Initial sandbox startup expired15s without loopback/thread readiness; approved execution was required. Direct process.env config failed TypeScript due absent Node globals; existing Vite loadEnv avoids a dependency solely for that access and typecheck passes.
- Alternatives considered: gate any health200 (false readiness); keep hard8000 proxy (breaks documented override); install Node typings only for one variable (unnecessary); use real provider for development tests (isolation unavailable); retrain when optional model absent (not required for fallback).
- Consequences: isolated mode is explicitly provider STUB, not verified Supabase/RLS; finite sync backend work is still supervised by owned process. Regular backend configuration/auth remains intact. Vite config change affects proxy behavior only, no visual styles/design. Source fingerprint scope expands; old hashes retain old scope. Initial test setup without controlled curl timed out, then controlled HTTP200 health fixture reproduced actual erroneous acceptance; timeout is not counted as a passing check.
- Files: start-dev.sh, package.json, web/vite.config.ts, scripts/source_fingerprint.py, tests/test_dev_launcher.py, decisions.md, flow.md, README.md, reports/requirements-evidence.md, reports/defect-register.md
- What happens: frontend starts only after required local backend capability, custom ports reach the same API and exiting launcher closes its backend; isolated full-stack command is available.
- How it happens: bounded JSON readiness poll, Vite loadEnv proxy override, strictPort, explicit traps and existing loopback-only synthetic provider helper.
- When it happens: npm run dev/dev:isolated startup and termination; configuration resolves before service/client launch.
- Symptom: unhealthy backend accepted and configured alternate port unreachable from app.
- Root cause: status-only /health polling, fixed Vite target and coupled preflight artifact assumption.
- Regression test: tests/test_dev_launcher.py::test_launcher_waits_for_ready_and_connects_custom_ports; test_launcher_does_not_start_frontend_when_required_readiness_fails (controlled child/HTTP checks; actual full stack separately).
- Source: https://vite.dev/config/ (loadEnv/conditional configuration); installed Vite6.4.3 actual compile/start verified rather than assuming newest docs imply compatibility.

### D-100: Register all acknowledged synthetic integration writes before validating their results
- Date / phase / commit: 2026-10-09, Phase D continued harness audit, uncommitted
- Context: The prepared real-isolated harness submitted both A/B concurrently, then registered each new row only after asserting its safety. A wrong A result stopped the loop before remembering either acknowledged write; cleanup could leave both synthetic records behind.
- Decision: gather valid acknowledged record ids and their already verified session owners for all returned concurrent results before any per-result assertion. Cleanup still filters new id AND trusted owner; no bulk deletion/retries. Malformed/unacknowledged writes remain explicitly uncertain.
- Why: actual main executed under pure mocked TestClient/provider orchestration with wrong A route and two saved acknowledgements returned1 but sent zero cleanup calls. Focused regression requires two exact owner/id deletes while preserving the wrong-routing failure. This does not exercise or claim real remote auth/RLS/model behavior.
- Alternatives considered: bulk-delete test-user history (forbidden); weaken safety assertion (forbidden); cleanup only results validated before failure (leaves acknowledged rows); pretend network uncertainty can always identify a new row (false).
- Consequences: deterministic acknowledged cleanup now survives an earlier assertion failure. Transport exceptions before complete responses can still leave unacknowledged uncertain writes; no guessing/retry. Real workflow remains BLOCKED on isolated project/pre-provisioned identities/migration and never ran remotely. Test overrides/candidate environment/sys.path/limiter are restored after this pure orchestration check.
- Files: scripts/verify_supabase_isolated.py, tests/test_isolated_harness_cleanup.py, decisions.md, flow.md, reports/requirements-evidence.md, reports/defect-register.md, docs/SUPABASE.md
- What happens: all known new acknowledged rows are eligible for exact scoped cleanup even when one output is wrong.
- How it happens: results are traversed once to collect saved/string-id plus trusted session owner before unchanged per-result check loop; existing finally deletes those exact pairs.
- When it happens: opt-in isolated integration command after concurrent responses and before safety/history/RLS assertions, including failed runs.
- Symptom: incorrect A routing plus two successful saves leads to zero cleanup requests.
- Root cause: created.append occurred after safety/save assertions inside a loop that stops on the first failure.
- Regression test: tests/test_isolated_harness_cleanup.py::test_harness_remembers_all_acknowledged_concurrent_writes_before_assertions (red empty cleanup list; corrected focused result recorded in continuation checkpoint).

### D-101: Keep the existing research column within its viewport and check built public routes
- Date / phase / commit: 2026-10-09, Phase F continued whole-program audit, uncommitted
- Context: Built public-route browser run passed desktop routes and mobile entry/about, then failed research at390px. Diagnostics show document529px and research Reveal/code/note wrappers505px wide inside a390px viewport; clipped documentation was not covered by earlier entry-only responsive checks.
- Decision: keep the same one-column research body grid but explicitly give its track a zero minimum via minmax(0,1fr), allowing the existing code-block horizontal scrollbar to contain long commands. Add loopback-only built-route QA with desktop/mobile public pages, auth redirect/API proxy, required assertions/nonzero failure, diagnostics and screenshot; preserve failed before report.
- Why: actual built Chromium assertion fails, no uncaught script errors. CSS automatic grid minimum used the long command's intrinsic width, expanding the entire column despite code-block overflow-x:auto. The correction changes intrinsic containment only, preserving intended columns/spacing/colors/fonts/branding/animation/navigation/login. Public acceptance is rerun after the correction.
- Alternatives considered: clip the entire page (hides content); shorten/rewrite commands or inject invisible characters (damages copy/paste); redesign responsive sections (forbidden); weaken the overflow assertion (incorrect).
- Consequences: one intentional research CSS containment correction, not a visual redesign; preservation manifest must record this file instead of continuing to claim zero style changes. Public built test uses SDK-disabled build and isolated API; no deployment/provider proof. Failure report explicitly records failed route/status rather than only completed checks.
- Files: web/src/styles/research.css, web/scripts/publicqa.mjs, reports/browser-built-routes-before.json, reports/browser-built-failure-before.png, decisions.md, flow.md, reports/requirements-evidence.md, reports/defect-register.md
- What happens: long code can scroll inside the existing research column without expanding/clipping the whole mobile page; public build failures have reviewable evidence.
- How it happens: explicit zero-minimum existing grid track; browser assertions measure document width/content/routes and record diagnostics on failure.
- When it happens: research rendering at narrow widths and explicit isolated built-bundle QA, after stable backend/app contract gates.
- Symptom:390px mobile research rendered529px document and505px wrappers.
- Root cause: implicit auto minimum on the existing research grid track, verified by measured overflowing code/paragraph/note wrappers.
- Regression test: web/scripts/publicqa.mjs mobile/research width assertion, actual built-browser exit1 before correction; before JSON/screenshot preserved.

### D-102: Remove nonexistent reviewer routing and label public threshold figures as historical
- Date / phase / commit: 2026-10-09, Phase F/H continued public contract audit, uncommitted
- Context: Actual built About copy said routed to human review, routes text to people and a human absorbs false positives, although the implemented API only returns recommendations. Diagram also claimed human review. Public metrics called the0.15 sweep held-out/deployed without D039's same-test-split threshold-selection caveat; effective configuration may differ from historical packaged figures.
- Decision: correct existing text/SVG labels only to describe raw model details, separate limited support and no notification. Preserve all numerical historical figures but identify test-selected consumed urgency results and response-reported effective threshold. Keep SVG geometry/styles/assets and existing component/layout structure unchanged. Add required built-About assertion for known false reviewer claims and consumed-split disclosure.
- Why: built browser test genuinely failed Unimplemented reviewer workflow: routed to human review before copy correction, report preserved. Actual Step10 evaluate_test.py lines85/100 calls precision_recall_curve on y_test_bin, confirming D039. No reviewer delivery/notifier is implemented anywhere in the connected API. Product honesty is part of this broader authorized program audit; no service or workflow is added merely to fulfill the old claim.
- Alternatives considered: implement unsolicited human-review/notification service (outside scope); erase historical metrics (forbidden); leave copy as an aspirational promise (misleading); redesign public diagram (unneeded); hardcode effective operator threshold (wrong consumer meaning).
- Consequences: copy is accurate about current engineering limits, not an independent clinical validation. Historical model values remain unchanged. Existing public components change only text/accessible labels; no colors/fonts/geometry/animations/navigation/login changed. Public preservation manifest records these intentional content amendments alongside the D101 containment correction; prior public source/report history remains available in checkpoints/archive.
- Files: web/src/components/hero/Hero.tsx, web/src/components/landing/DualSignal.tsx, web/src/components/landing/Metrics.tsx, web/src/components/landing/Limitations.tsx, web/src/pages/Research.tsx, web/scripts/publicqa.mjs, reports/browser-public-copy-before.json, decisions.md, flow.md, reports/requirements-evidence.md, reports/defect-register.md
- What happens: public pages no longer imply a person receives or reviews each disclosure; historical threshold results cannot be mistaken for current independent release evidence.
- How it happens: existing paragraphs/captions/SVG text clarify research tracks versus authoritative support, consumed selection and effective per-response configuration; built-page regression checks actual rendered text.
- When it happens: public About/Research rendering, after stable internal contract and explicit backend-first gates; no analysis/storage/model mechanics change.
- Symptom: nonexistent reviewer workflow and historical test-selected sweep presented without its leakage caveat.
- Root cause: public copy/diagram reflected an aspirational pre-recovery architecture instead of actual recommendation-only API; old metric labels omitted test selection.
- Regression test: web/scripts/publicqa.mjs required About claims/disclosure assertions (actual built red before correction); actual build/render verification follows.
- Supersedes: D-086 only to extend the already gated behavioral/documentation integration to these actual public contract descriptions under the user's later whole-program audit; fixed visual preservation and release-validation blockers remain.

### D-103: Checkpoint the whole-program audit with passing checks and preserved failing diagnostics
- Date / phase / commit: 2026-10-09, Phase H continuation checkpoint, uncommitted
- Context: User requested the remaining program paths run and errors corrected beyond the earlier D097 handoff. Five additional reproducible defects were fixed without replacing the app or enabling an unvalidated model. Current evidence must retain failures and external blockers separately from local successes.
- Decision: preserve prior handoff/checkpoint, update current matrix/full defect records/Supabase/README/flow/handoff and new program report with actual D098–D102 outcomes. Current source/model/config manifest, statuses, exact failing IDs and intentional public changes are recorded. No staging/commit/deploy. Stop preview and launcher-owned backend; record verified exits. Public runner records source/built-asset hashes and explicit required failures.
- Why: actual486 tests passed17.92s;55 module/47 auth/310 entry/35 screen/12 built-route checks passed. Manual interaction/failure scripts exit0 but are not counted as assertions. Current repeat corpus still259/321 engine/214/321 pipeline with98/98 consumed urgent routes,0/73 urgent benign escalations and0/238 asserted subject errors. No annotation/model/threshold tuning; published numbers must include these disagreements.
- Alternatives considered: report only passing unit/browser suites (misleading); claim zero frontend files changed (false: intentional copy/containment/proxy amendments); call stub provider genuine integration (false); leave task processes running (unnecessary); retrain/relabel/expand phrases to satisfy consumed data (forbidden).
- Consequences: ENGINEERING partial, INTEGRATION partial, RELEASE_VALIDATION blocked. New script/artifact scope is explicit; prior report hashes/results remain historical. Synthetic/provenance/clinical/deployed limits persist. No required locally reproduced defect from this continuation remains uncorrected; broader semantic/diagnostic and genuine external requirements remain open.
- Files: reports/program-audit-report.md, reports/recovery-final-report.md, reports/recovery-final-checkpoint.json, reports/handoff-before-program-audit.md, reports/recovery-checkpoint-before-program-audit.json, reports/requirements-evidence.md, reports/defect-register.md, README.md, docs/SUPABASE.md, handoff.md, decisions.md, flow.md, web/scripts/publicqa.mjs; actual run reports referenced above
- What happens: reviewer can reproduce actual local program results, see before/after defects and identify exact missing independent inputs without a false completion claim.
- How it happens: actual executed commands/reports and source fingerprints populate one matrix/current handoff/checkpoint; historical snapshots retained, secrets and real sensitive data excluded.
- When it happens: after focused fixes/full suites/built-route regression and current diagnostic repeat, at continuation handoff.

### D-104: Preserve Google return intent and storage scope through verified session adoption
- Date / phase / commit: 2026-10-09, authorized Supabase/login continuation, uncommitted
- Context: User requests functional project access and Google login. Existing Google button/SDK path already exists, but ignores the checkbox and actual router destination. Browser SDK configuration is absent; backend project URL is a localhost placeholder. Newly supplied keys do not identify their project URL.
- Decision: pass existing checkbox and router return path to Google initiation; retain only finite 15-minute tab-scoped return metadata; adopt SDK tokens through trusted API identity verification; route once after successful adoption. Reject cross-origin/control/backslash return paths. Clear metadata on logout/initiation/callback failure and expiry. Missing SDK expiry cannot fabricate a session lifetime. Remove unnecessary offline Google access, request account selection only. Preserve all rendered markup/classes/styles/layout.
- Why: actual `cd web && node scripts/oauthqa.mjs` exits1 with `/screen` instead of `/screen?source=fixture#history`; no producer writes the old mental.ai.returnTo key. Scope previously depended on an existing mirror, absent for new OAuth visitors. Corrected actual-module test has11/11 grouped required checks, SDK/fetch explicitly mocked.
- Alternatives considered: default every Google login to persistent storage (ignores visitor choice); trust SDK user id (bypasses authoritative identity); store tokens in pending metadata (unnecessary); create another callback page/design (unnecessary for current implicit SPA flow); request Google refresh access (application never consumes Google APIs).
- Consequences: Google callback tokens still belong to SDK implicit handling, while metadata is only a UI/storage preference, never authorization or OAuth CSRF state. Real provider/redirect/SDK network and account creation remain BLOCKED on genuine project URL/email/provider configuration. Initial control-character regex failed ESLint; replaced with explicit character checks, not disabling lint. No dependency/schema/model/policy change and no account/record/email operation performed.
- Files: web/src/lib/auth.ts, web/src/components/login/LoginForm.tsx, web/src/components/entry/LoginPanel.tsx, web/src/pages/Start.tsx, web/src/App.tsx, web/scripts/oauthqa.mjs, web/package.json, decisions.md, flow.md, reports/requirements-evidence.md, reports/defect-register.md
- What happens: Google honors Remember me, returns to the requested same-origin destination including query/hash after verification, and failures return to an anonymous usable login state.
- How it happens: LoginForm.onRememberChange -> LoginPanel -> signInWithGoogle -> finite OAuthIntent in sessionStorage -> SDK callback -> adoptClientSession -> api.session -> guarded publish -> App.consumeOAuthReturnPath/useNavigate. SDK error/missing expiry/logged-out late result cannot publish.
- When it happens: Google initiation, page boot/SDK auth event, successful server verification, and explicit logout. Existing email-password identity verification remains in use.
- Symptom: lost deep link/Remember me; SDK callback error could reject boot restoration without publishing anonymous; absent expiry invented one hour.
- Root cause: zero-argument Google adapter, unwritten returnTo storage key, no pending preference, unhandled getSession error and fabricated fallback expiry.
- Regression test: web/scripts/oauthqa.mjs (11 grouped required checks: destination, persistent/tab scopes, safe-path controls, failed initiation, expired intent, callback failure, unavailable expiry, logout during verification; actual modules with SDK/fetch overrides). Browser acceptance follows separately.
- Source: https://supabase.com/docs/guides/auth/social-login/auth-google (implicit browser callback supported; real project Google configuration is separate).

### D-105: Check remote Google availability and surface bounded SDK initialization failures
- Date / phase / commit: 2026-10-09, Supabase/login continuation, uncommitted
- Context: Configured browser keys alone cause a Google redirect even when the remote provider is disabled. Installed @supabase/auth-js GoTrueClient.getSession awaits initialization but discards its error result, so a cancelled implicit callback cannot be handled by checking getSession.error alone. A pending network initializer must not keep the app in restoring forever.
- Decision: probe public Supabase /auth/v1/settings with only publishable apikey, omit browser credentials, refuse redirects, abort at8s and distinguish enabled/disabled/unavailable. Block OAuth initiation otherwise with existing safe error line. Check SDK initialize.error explicitly and bound overall SDK restoration to10s; keep generation/owner verification. Correct /auth/providers docstring/env description to call its flag a local declaration. Add isolated real-SDK Chromium helper with intercepted provider/API and owned Vite cleanup; no real service/account calls.
- Why: focused wrong-provider regression genuinely exits1 with Missing expected rejection before the probe. Official GoTrue settings implementation defines external.google as a boolean. Static installed SDK lines2874/692 confirm swallowed callback initialization errors; actual cancelled callback is then verified in Chromium. Corrected23 module groups and13 browser groups pass; browser verifies both Remember me scopes, actual navigation/callback/hash/reload/logout, provider failures and server rejection with zero page errors.
- Alternatives considered: assume local env flag proves provider enabled (false); redirect then show Supabase provider error (poor login recovery); issue administrative/secret provider calls from browser (forbidden); add another auth subsystem/paid provider (unneeded); claim timeout kills SDK synchronous/network work (false).
- Consequences: No dependency/schema/migration or visual design change. Settings probe runs only on explicit Google click; no background auth-provider polling. Deadline bounds application restoration but cannot promise SDK cancellation. Google client id/secret/redirect allowlist and human Google consent are separate external requirements. New supplied project API keys remain unwritten because no project URL is available; admin/account setup has not occurred.
- Files: web/src/lib/supabase.ts, web/src/lib/auth.ts, web/scripts/oauthqa.mjs, web/scripts/oauthbrowserqa.mjs, web/package.json, api/api.py (docstring only), .env.example (comment only), docs/SUPABASE.md, decisions.md, flow.md, reports/requirements-evidence.md, reports/defect-register.md, reports/browser-oauth.json
- What happens: disabled/unavailable Google keeps usable email/password login; failed/cancelled SDK callback resolves anonymous with safe copy instead of silent restoration; a verified session still needs trusted API identity.
- How it happens: googleProviderStatus -> bounded public fetch/schema checks -> signInWithGoogle gate -> SDK.initialize/getSession deadline -> adoptClientSession/api.session/generation. Existing error panel consumes authError; no provider body enters rendered errors.
- When it happens: explicit Google initiation, returning SDK callback and boot with no stored mirror. Tests run only on synthetic loopback Vite with intercepted calls and stop its owned process.
- Symptom: disabled Google still redirected; callback errors not propagated by installed SDK getSession and potentially indefinitely pending boot.
- Root cause: supabaseConfigured checked key presence, no remote settings check; SDK initialize result ignored; no SDK restoration deadline.
- Regression test: web/scripts/oauthqa.mjs disabled/unavailable required rejection (red), actual-supabase settings enabled/disabled/malformed503/network/abort fixtures, initializer failure/deadline; web/scripts/oauthbrowserqa.mjs actual installed-SDK13 groups. Timers accelerated only in module deadline fixtures.
- Source: https://raw.githubusercontent.com/supabase/auth/master/internal/api/settings.go; https://supabase.com/docs/guides/auth/social-login/auth-google; installed web/node_modules/@supabase/auth-js/src/GoTrueClient.ts inspected, not included in fingerprint.
- Failed commands: initial sandbox browser helper exited before startup due loopback restriction; approved run then failed because synthetic fixture lacked /api/health (harness error, not application success). Fixture completed and route interception errors now record/abort inside handler to preserve finally cleanup. Corrected browser run exits0,13/13, owned Vite stopped.

### D-106: Remove token-mirror and query-string contents from existing authentication QA diagnostics
- Date / phase / commit: 2026-10-09, login verification/privacy correction, uncommitted
- Context: Existing seeded-session failure diagnostic logs the first40 characters of the stored auth JSON, including token bytes. Its URL/debug response strings also retain full query/fragment information. User prohibits secrets in logs/reports; QA may be pointed at a genuinely configured project in later approved verification.
- Decision: report only persistent/tab mirror presence booleans and URL pathname/status, never auth mirror values or URL query/fragment. Add required diagnostic privacy regression executing the actual diagnostic branch with synthetic private storage. Preserve all existing auth expectations.
- Why: focused regression genuinely fails QA failure diagnostics must not log authentication mirrors with PRIVATE_FIXTURE_TOKEN in captured output before correction. Corrected24/24 grouped OAuth/module checks pass; secret fixture is synthetic and output capture is assertion-only.
- Alternatives considered: shorten/redact part of the token (still unnecessary disclosure); remove all failure diagnostics (loses useful route/storage-scope evidence); ignore because current run is synthetic (future real QA would expose secrets).
- Consequences: no application auth/visual/schema/provider change and no new dependency. Diagnostic still explains route and which mirror scope exists. Historical successful auth-flow run remains separate from this deliberately exercised failure branch.
- Files: web/scripts/authflow.mjs, web/scripts/oauthqa.mjs, docs/SUPABASE.md, decisions.md, flow.md, reports/requirements-evidence.md, reports/defect-register.md
- What happens: failure reports cannot print the mirrored token or callback query/fragment contents through this diagnostic.
- How it happens: seeded.evaluate returns presence flags; URL conversion retains pathname only. Regression runs the actual repository diagnostic block with controlled storage/captured console and asserts private marker absence.
- When it happens: seeded-session gate regression failure, before printing QA failure evidence; normal app session storage behavior is unchanged.
- Symptom: first40 auth JSON bytes leaked token prefix on seeded-session failure.
- Root cause: string-slicing the entire auth mirror and logging full page/response URLs.
- Regression test: web/scripts/oauthqa.mjs actual legacy diagnostic privacy group; red assertion exit1, corrected24/24 grouped checks pass. No real token inspected or logged.

### D-107: Checkpoint login integration with compiled SDK evidence and missing live inputs
- Date / phase / commit: 2026-10-09, Supabase/login handoff, uncommitted
- Context: Login repairs need actual development/compiled coverage and fresh dirty-source identity. Supplied keys cannot identify their project or create a working account against the localhost placeholder.
- Decision: fixed-loopback --built mode for OAuth browser helper, trusted stored mirror assertions without importing dev modules into preview, separate dev/built reports. Run applicable backend/module/email/screen checks and both SDK builds; preserve previous handoff/checkpoint and update current matrix/docs/fingerprint. No live key activation/account/data/dashboard/deployment operations without genuine inputs.
- Why: actual486 backend tests14.15s;55 module,24 OAuth/privacy,47 email,35 screen and13 dev/13 built OAuth groups pass. SDK-disabled193-module build9.13s and SDK-enabled193-module build8.78s pass. Original raw/support/history unchanged; all styles/models/config match D103. Isolated remote config gate exits2/missing names; dashboard inventory empty.
- Alternatives considered: call intercepted tests live auth (false); send secret to placeholder (wrong destination); fabricate account/password/verification (forbidden); automatic publication (unauthorized); retune/relabel consumed cases during auth work (unrelated).
- Consequences: ENGINEERING partial/INTEGRATION partial/RELEASE_VALIDATION blocked globally; reproduced login defects corrected. Live account/Google/Supabase BLOCKED on URL/email/provider configuration/controlled access. Previous diagnostics/failedIDs preserved, no independent review invented, ownership/publication unchanged.
- Files: web/scripts/oauthbrowserqa.mjs, reports/auth-integration-report.md, reports/browser-oauth.json, reports/browser-oauth-built.json, reports/recovery-final-checkpoint.json, reports/recovery-final-report.md, reports/handoff-before-auth-integration.md, reports/recovery-checkpoint-before-auth-integration.json, reports/requirements-evidence.md, docs/SUPABASE.md, README.md, handoff.md, decisions.md, flow.md
- What happens: reviewable checkpoint distinguishes working local login behavior from unavailable live configuration/account and release evidence.
- How it happens: fixed loopback Vite dev/preview with synthetic SDK configuration/intercepted requests and UI/mirror assertions; current manifests/results/docs and previous diagnostics separately retained. Owned process exits verified.
- When it happens: after D104–D106 and complete applicable local verification, before live setup/publication.

### D-108: Connect the supplied Supabase project in ignored backend/browser configuration
- Date / phase / commit: 2026-10-09, live configuration continuation, uncommitted
- Context: User reports Supabase is not configured, then supplies genuine https://omvjzcpcmkqgmgrzeesh.supabase.co. Prior actual registration/Google adapter reproduction threw the configuration error; web env absent and backend URL was localhost placeholder. Supplied keys were held until their destination was known.
- Decision: set the three authorized backend Supabase values in ignored .env and only URL/publishable key in ignored web/.env.local, permissions0600, preserving unrelated environment entries. Verify matching project/public values and absence of a secret in browser config. Run bounded read-only public settings/health with TLS verification/no redirects, no user/database/disclosure requests. Rebuild/restart and verify rendered configured login without registration or record writes.
- Why: local config presence checks and git check-ignore pass. Real public settings and secret-key gateway health both HTTP200. Settings report email=true, google=false, disable_signup=false and mailer_autoconfirm=false. Initial sandbox DNS gaierror failed; approved HTTPS probe succeeded, not counted as a prior pass.
- Alternatives considered: keep asking for URL after supplied (unnecessary); include secret in VITE variables (forbidden); configure only backend (leaves browser registration/Google null); send keys to earlier localhost placeholder (wrong destination); create/test real screening rows or signup emails (unauthorized test shortcut).
- Consequences: local configuration blocker resolved; actual account access still needs intended email and honest confirmation flow. Google provider is remotely disabled and requires separate OAuth credentials/dashboard configuration. Read-only health establishes API-gateway acceptance, not privileged administrative permissions, RLS, database schema, actual user/session or deployed installation. Existing hosting env is not automatically changed. Keys/secret env files stay out of reports/source hashes/version control; no deployment/account/record/email mutation.
- Files: .env and web/.env.local (ignored private configuration, excluded from published fingerprints), decisions.md, flow.md, docs/SUPABASE.md, reports/supabase-project-connectivity.json, reports/requirements-evidence.md, handoff.md; temporary /tmp/mental-ai-supabase-config-probe.py holds code only, reads ignored env without logging values
- What happens: browser SDK and backend target the same actual project; Google availability error reflects disabled remote provider rather than absent SDK configuration.
- How it happens: dotenv updates preserve unrelated entries; Vite loads web/.env.local at startup/build, API loads root.env; public apikey settings and server-key health requests use supplied HTTPS host, finite10s per request, no redirect/response-body logs. Actual rendered acceptance follows separately.
- When it happens: local setup after the user supplies project URL; API/Vite restart and browser rebuild needed because configuration resolves at startup/build.
- Symptom: Supabase is not configured on account creation/Google adapter.
- Root cause: missing browser env and localhost backend placeholder despite existing repaired auth implementation.
- Regression test: direct actual-module unconfigured registration/Google reproduction (expected error, observed fetch0); configured env matching/key-boundary checks; real settings/health2/2 HTTP200; build and browser configuration acceptance recorded after execution.

### D-109: Verify configured login against real public settings without account or database tests
- Date / phase / commit: 2026-10-09, live configuration verification/checkpoint, uncommitted
- Context: D108 installs correct local variables, but file presence alone does not prove the actual website reads them. The project is not identified as isolated, and requested account email is missing. Private tests or signup submissions could affect real data/send email.
- Decision: add loopback-only supabaseconfigqa.mjs/qa:supabase-config to check actual rendered Google/registration controls and real public settings. Block all Supabase endpoints except settings, all private API paths and all submissions. Preserve actual UI assertions, report sanitized paths/booleans and zero page errors; capture blank-field login screenshot. Build actual configured client, check backend is_configured/configured_url/get_client and inspect bundle only for known private-value matches without printing values. Keep real account/RLS/deployment claims separate.
- Why: actual5/5 Chromium checks pass, no forbidden/private/write requests or page errors. Browser public settings HTTP200 returns Google=false, email=true, confirmation required. Actual configured build193 modules9.63s passes; backend adapter accepts same project and browser bundle contains URL/public key but no configured secret. Initial adapter assertion used nonexistent client.url attribute and failed; corrected to inspected configured_url function, no source defect hidden. Lint passes; module regression rerun follows.
- Alternatives considered: count env presence as successful login (false); submit registration or synthetic predictions to live project (forbidden/non-isolated); erase disabled Google warning (dishonest); deploy to refresh hosted env (unauthorized); infer account email from Git author metadata (not account authorization).
- Consequences: local missing-config defect resolved, genuine public connectivity verified; Google success and private auth/persistence/RLS still not verified. Google enablement requires external OAuth client/provider setup, new account needs intended email/actual verification. Test script targets this declared project and loopback app only. No application layout/model/policy/API response change or paid provider. No user/record/account/email/migration/deployment actions. Current local preview may remain running deliberately; handoff records exact state.
- Files: web/scripts/supabaseconfigqa.mjs, web/package.json, reports/supabase-project-connectivity.json, reports/supabase-configured-browser.json, reports/supabase-configured-login.png, decisions.md, flow.md, docs/SUPABASE.md, reports/requirements-evidence.md, reports/defect-register.md, handoff.md, reports/recovery-final-checkpoint.json
- What happens: actual website gets configured SDK and a truthful disabled-provider message; it cannot be mislabeled as unconfigured or fully authenticated.
- How it happens: actual Vite/API startup with private env, browser request guards allow public settings only, UI/status assertions, private bundle match scan and configuration adapter checks; provider body/key/token/user data omitted from published evidence.
- When it happens: explicit qa:supabase-config during local setup after restart/build; no routine request runs tests or downloads resources.
- Symptom: prior missing browser config caused registration/Google to fail immediately without network.
- Root cause: setup variables absent, not a new authentication-code regression; Google false is actual remote configuration, not a local error to suppress.
- Regression test: web/scripts/supabaseconfigqa.mjs5 required UI/network/privacy groups, real public settings only; module/SDK failure behavior remains in oauthqa.mjs24 groups. No real user or database test identity claimed.

- Follow-up verification: initial5-group browser report preserved in reports/supabase-configured-browser-initial.json; actual normal /api/live and /api/configuration proxy assertions add one required group. Final6/6 pass, no forbidden/private/write requests or page errors. The running exec session plus real public API/browser requests confirm current preview; empty in-sandbox process inventory is not used as evidence of stopped outside-sandbox services.

### D-110: Install the explicitly requested Node server SDK and configure its JWKS endpoint
- Date / phase / commit: 2026-10-09, requested package/JWKS continuation, uncommitted
- Context: User explicitly requests npm install @supabase/server plus four backend variables. Three values already installed in ignored correct environments; supplied JWKS URL is new. Current production API is Python and verifies trusted identity through GoTrue; browser uses supabase-js.
- Decision: add backend-only SUPABASE_JWKS_URL to ignored0600 root.env; retain browser URL/public key only. Install official @supabase/server1.9.1 exactly at repository root, lifecycle scripts disabled so root postinstall does not mutate the existing frontend lock/dependencies or install hooks. Ignore root node_modules and include new root package-lock.json in source fingerprint. Validate imports/env compatibility/JWKS public endpoint; do not rewrite Python API or silently change its session/revocation/owner behavior to use a JavaScript wrapper.
- Why: official npm registry and Supabase repository confirm package/MIT license/Node>=22, current Node24.21.0 compatible. Official docs distinguish header-based JS server SDK from cookie SSR/browser clients and other-language implementations. Singular supplied key variables and SUPABASE_JWKS_URL are supported Node env inputs. Initial sandbox registry DNS failed; approved metadata check succeeded. Installation/import/public JWKS outcomes recorded after actual execution, not assumed.
- Alternatives considered: @supabase/ssr (cookie SSR, not this SPA/Python API); only existing supabase-js (already browser client, user explicitly requests additional server package); rewrite API in Node solely for dependency use (violates backend recovery/preservation scope); add Python JWKS library/change auth automatically (unrequested and alters trusted identity/revocation semantics); run root postinstall (unneeded frontend churn).
- Consequences: Node SDK available for Node tools/future authorized server work; Python authentication still uses get_user and does not claim local JWKS verification merely because env exists. JWKS endpoint availability alone is not verified-user authentication. Root Node lock now part of reproducibility scope; old fingerprints retain old scope. No new provider/paid service/schema/visual/auth bypass/account/user/disclosure/deployment action. No new private values in template/source/reports.
- Files: ignored .env, .env.example, package.json, package-lock.json, .gitignore, scripts/source_fingerprint.py, decisions.md, flow.md, docs/SUPABASE.md, handoff.md, reports/recovery-final-checkpoint.json
- What happens: all requested backend variables exist locally and the requested compatible official Node server dependency is pinned/reviewable; actual Python and browser consumers retain their established roles.
- How it happens: dotenv key update, exact npm install with --ignore-scripts, root module/lock boundary, installed package import/env smoke and bounded read-only public JWKS check. Existing API auth.decode_token -> db.get_client().get_user remains unchanged.
- When it happens: after explicit latest package/JWKS instruction; Node env is loaded by its process, Vite sees only web env and API reload needed for added runtime variables.
- Package: @supabase/server1.9.1 (exact), MIT, Node>=22; jose^6.2.0/@supabase/middleware^1.0.0 with supabase-js peer; resolved versions/integrities in root lock.
- Why this package: user-requested official Node request-auth/context utilities, separately available from browser SDK/Python provider path.
- Packages compared: @supabase/supabase-js existing browser client; @supabase/ssr for cookie SSR; Python standard-library GoTrue path remains appropriate for actual API.
- Sources: https://supabase.com/docs/guides/auth/choosing-a-server-package; https://github.com/supabase/server; official npm registry metadata and installed source inspected.

### D-111: Expose a credential-safe SDK configuration check and record real public JWKS availability
- Date / phase / commit: 2026-10-09, SDK/JWKS verification, uncommitted
- Context: Installed dependency and written env alone do not demonstrate actual package import/env resolution. A JWKS URL must be reachable, but public signing keys are not verified user/session evidence. Caller needs a reproducible local check without dumping private values.
- Decision: add npm run verify:supabase-sdk -> Node native .env loading -> scripts/check_supabase_server.mjs. Actual server/core exports and resolveEnv must match all four provided variables; errors are generic and fetch guard prohibits network. Separate bounded unauthenticated public JWKS probe records only HTTP status/key count/algorithms, not key material. Retain Python GoTrue session identity path and no private tests.
- Why: actual installed1.9.1 import/env smoke passes with observed fetch0; all four singular variables resolve including JWKS URL. Actual JWKS HTTP200 returns one ES256 public signing key, no private parameters. Initial sandbox DNS failed then approved public request succeeded. npm install added13/audited14 packages,0 reported vulnerabilities; Node24 satisfies>=22. Frontend lock hash unchanged. No authenticated identity verified.
- Alternatives considered: print SDK env/client object (leaks secret); treat JWKS fetch as successful user authentication (false); implement Node API/JWT bypass to use new dependency (unrequested); install SSR wrapper (wrong architecture); omit reproducible check (harder to diagnose same config issue).
- Consequences: package is actively consumed by explicit local config verification only, not the Python prediction route/browser bundle. Runtime API/auth/owner/CORS/model/schema/policy remain unchanged. Environment keys and installed dependency trees excluded from source reports; root lock integrity included. Independent release/private integration/account/Google blockers unchanged. npm audit0 is scoped package advisory output, not a security/clinical guarantee.
- Files: scripts/check_supabase_server.mjs, package.json, package-lock.json, reports/supabase-jwks-connectivity.json, decisions.md, flow.md, docs/SUPABASE.md, reports/requirements-evidence.md, handoff.md, reports/recovery-final-checkpoint.json
- What happens: owner can check actual installed SDK/env compatibility without exposing credentials or making account/network requests; public JWKS reachability is honestly separate.
- How it happens: dynamic package import, resolveEnv result validation with boolean comparisons and generic errors, guarded fetch counter/restoration; public HTTPS probe has no key/token header and verified TLS/no redirects/10s timeout.
- When it happens: explicit npm run verify:supabase-sdk; no request/background process invokes it. JWKS metadata recorded during this setup only.

### D-112: Reconcile the requested SDK checkpoint and rerun isolated publication checks
- Date / phase / commit: 2026-10-09, SDK checkpoint, uncommitted
- Context: D110/D111 package/config verification exists, but the current matrix/handoff/checkpoint still described D109. Publication requires a reviewable current snapshot with honest real-versus-stub evidence.
- Decision: preserve previous SDK-start handoff/checkpoint; update one matrix, current handoff/checkpoint and a dedicated SDK report. Include root lockfile in current source manifest and retain prior hash scopes. Rerun full backend with live env disabled, contract/OAuth modules, lint/drift and secret boundary; keep consumed corpus failures and release blockers visible.
- Why: actual486 tests pass28.16s with1 existing dependency warning;55 module checks/16states and24 OAuth groups pass. Actual installed SDK check passes/fetch0; latest build193modules14.43s and secret matches0. No model/style/frontend-lock changes. Current sourceb52803f0293218f830f702032907db5ee7aae49239b0935f6b88896fe6facba7.
- Alternatives considered: leave stale D109 fingerprint (misidentifies source); rerun live private tests with supplied keys (project not isolated); claim JWKS proves identity (false); retune consumed diagnostics (unrelated/leakage); inflate counts with repeated passes (unnecessary).
- Consequences: engineering/integration partial and release blocked remain; public-only evidence distinct from mocked authentication/storage. No new schema/runtime/auth/policy/deployment/UI change. Existing warning recorded, not concealed.
- Files: reports/supabase-server-sdk-report.md, reports/requirements-evidence.md, reports/recovery-final-checkpoint.json, reports/recovery-final-report.md, README.md, docs/SUPABASE.md, handoff.md, decisions.md, flow.md; previous reports/*before-server-sdk* preserved
- What happens: current checkpoint describes installed package, actual configuration consumption, current test results and remaining blockers.
- How it happens: fingerprint manifest/model comparisons plus isolated-env real implementation suite; SDK smoke and public JWKS separately classified; documents retain failed case IDs and historical checkpoints.
- When it happens: after requested package/configuration changes and before authorized GitHub publication.

### D-113: Publish authorized project changes under the verified repository owner
- Date / phase / commit: 2026-10-09, GitHub publication, uncommitted
- Context: User explicitly authorizes push everything to GitHub under their name with no collaborator/tool authorship. Earlier no-publication boundary no longer applies to committing/pushing; deployment remains unauthorized and excluded files remain excluded.
- Decision: use repository-local shreshthgod <shreshthnmims.it@gmail.com> for author and committer; stage only reviewed changed/untracked project source/tests/docs/historical reports. Exclude credentials/env/dependencies/build/cache, paper/, research/, .tex and unrelated :memory:.ses. Verify staged payload/header/remote; make a normal fast-forward push only. Record actual implementation hash in a later documentation-only commit, without amending self-references.
- Why: gh authenticated login is shreshthgod and owner repository permissions include admin/push. GitHub maps HEAD2053855d51aaa5c9e06bd8c30f1c35d45c64716b author and committer with the exact supplied email to shreshthgod. Remote main equals local HEAD. Initial216 candidates/32,709,753bytes scan finds0 configured credential/key/trailer/private-path matches. Identity env overrides absent; no active Git hooks found.
- Alternatives considered: blindly git add all (includes unrelated session file); invent noreply ID (forbidden); force push/history rewrite (unneeded); add model/bot/collaborator/trailer (forbidden); request private email scope (unnecessary after existing GitHub commit establishes account association).
- Consequences: source and historical synthetic evidence become reviewable on owner repository, not a deployment or validated release. Ignored live config is local and must be configured separately at hosting. Ownership verified independently of application-model discussion. No collaborators, notifications or new author identity added.
- Files: repository-local Git configuration; vetted project paths; reports/requirements-evidence.md, reports/github-publication.json, handoff.md, decisions.md, flow.md, reports/recovery-final-checkpoint.json
- What happens: only authorized project changes are committed/pushed using owner's verified identity.
- How it happens: authenticated account/permission and commit association checks, allowlisted manifest/byte scans, local identity, staged tree/header verification, subsequent hash documentation, fast-forward remote verification.
- When it happens: after final implementation verification and explicit user publication authorization; push result recorded only after execution.
- Failed commands: first sandbox gh api user failed network then approved retry succeeded. gh api user/emails returned404/missing user scope; existing GitHub commit account association provides verified alternative without requesting broader access.

### D-114: Record the published implementation hash in a later documentation checkpoint
- Date / phase / commit: 2026-10-09, publication verification, implementation ae15d97f96fed957706aa49bf1659aca3f80c0e9; this documentation follow-up initially uncommitted
- Context: The implementation commit cannot contain its own final hash. D113 requires real remote/identity evidence after execution and a later documentation-only reference without amending history.
- Decision: record actual218-file implementation commit and successful fast-forward push, verified remote SHA/GitHub owner author/committer, final reviewed payload scan and unchanged source/model/config fingerprint. Update current handoff/matrix/checkpoint/publication report; publish a separate documentation-only follow-up with the same owner identity. Keep historical uncommitted labels as their original timing, linked here to the actual published snapshot.
- Why: git push origin main exits0, remote main2053855 -> ae15d97. git ls-remote returns exactae15d97f96fed957706aa49bf1659aca3f80c0e9; GitHub commit API maps both author and committer to shreshthgod with expected supplied name/email. All218 staged blobs matched reviewed credential-safe bytes; final scan32,733,551bytes finds0 credential/key/private-path/trailer matches. Git status leaves only unrelated :memory:.ses; all6 report screenshots inspected, synthetic/blank account fields only.
- Alternatives considered: amend repeatedly to embed own hash (impossible self-reference/history change); call a local commit a successful push without remote evidence (false); include ignored private env for convenience (forbidden); rewrite historical uncommitted decision timestamps (misrepresents timing).
- Consequences: authorized source publication verified; no deployment/provider/account/data mutation or validated-release claim. Documentation commit's own hash is intentionally discoverable from Git history rather than embedded in itself. Global engineering/integration partial and release blocked remain. No collaborators or additional authorship identities added.
- Files: decisions.md, flow.md, handoff.md, reports/requirements-evidence.md, reports/recovery-final-checkpoint.json, reports/recovery-final-report.md, reports/github-publication.json
- What happens: owner repository contains the actual recovery implementation and preserved evidence; current documentation links it to measured verification and remaining blockers.
- How it happens: successful ordinary push, remote SHA/commit API checks, owner headers/trailer assertions and staged-file scan; subsequent documents reference the fixed implementation hash without self-reference.
- When it happens: after first successful authorized source push; documentation follow-up headers/remote are checked after its commit/push and reported to the user.
- Failed command: initial documentation patch context did not match flow.md; patch made no changes and was corrected against actual text before committing.
