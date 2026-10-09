# Defect register: backend audit, 2026-10-08

Severity is about safety impact on this product's routing, not software
quality. The original table below is preserved historical reporting, not proof of current behavior. Current reproductions, superseding decisions and full fields follow; unknown historical evidence is explicitly unknown. Decision IDs match decisions.md.

Reproduce the whole suite with:

```
PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q
PYTHONPATH="Step 12 - Packaging/package:." python3 scripts/run_safety_corpus.py --layer both
```

| ID | Sev | Defect | Verified cause | Fix | Regression |
|---|---|---|---|---|---|
| D-001 | Critical | The urgency model flag escalated benign controls: "I live on the tenth floor" (p=0.247) became NEEDS_CLARIFICATION. Corpus reported 78/78 while the shipped path gave 66/78. | `evaluate()` used the flag as a routing decision; the runner hardcoded `urgency_flagged=False`, so the shipped path was never executed | Flag recorded as evidence code only | `test_d01_model_flag_alone_does_not_escalate_benign_text` (12 cases) |
| D-002 | Med | `immediacy` emitted a fourth undeclared value `"immediate"` | Assembly step rewrote the field outside the declared Literal | IMMEDIATE + `immediacy=="unclear"` becomes `"stated"` | `test_d02_immediacy_stays_inside_the_declared_enum` |
| D-003 | Med | A farewell alternative in `PASSIVE_DEATH_WISH` could never match | `me\\s+again` inside a raw string is a literal backslash then "s" | Single-escaped; plus a structural guard over all patterns | `test_d03_farewell_pattern_is_live_not_dead`, `test_d009_no_pattern_contains_a_double_escape` |
| D-004 | Low | `support_action()` ignored its advertised `region_known` parameter | Parameter never read | Read; HIGH adds an optional location question when region unknown | `test_d04_*` |
| D-005 | Med | Whitespace-only input returned HTTP 500 "Prediction failed" | `min_length=1` counts raw chars; generic `except Exception` mapped a caller error to 500 | `field_validator` rejects non-whitespace-free text with 422 | `test_d05_whitespace_only_is_a_contract_error_not_a_500` (8 cases) |
| D-006 | High | A failed urgency track reported `analysis_status:"complete"` and `URGENCY_MODEL_NOT_FLAGGED` | `inference.screen()` passed `bool(urgency_result["flagged"])`, and `flagged` is False by default when absent: a missing signal reported as a negative one | Pass `None` unless the track's status is "complete" | `test_d06_urgency_model_failure_still_returns_a_safety_route` |
| D-006b | High | Supabase outage during token verification returned HTTP 500 | `require_session` caught `InvalidToken` and `AuthUnavailable` but not the base `db.SupabaseError` raised when unreachable | Added `db.SupabaseError` → 503, matching the documented contract | `test_auth_provider_outage_is_503_not_401` |
| D-007 | Med | `/health` and `/ready` reported initialization, not working inference | `/health` filled every artifact with the literal "ok" whenever the screener existed | `/health` stats real files and probes; `/ready` requires both | `test_d07_*` |
| D-008 | High | `MAX_TEXT_LENGTH` and `URGENCY_THRESHOLD` were advertised in `.env.example` and read nowhere; `URGENCY_THRESHOLD=0.99` still produced 0.15 | No reader existed for either string | Both read and validated; screener limit parameterised | `test_d08_*` |
| D-009a | Med | Any text mentioning a song or poem reported `subject=fictional_or_quoted` | Bare `\|poem\|song` alternative in the fiction detector | Every alternative needs an explicit creative frame | `test_d009a_*` |
| D-009b | High | "I want to get a rooftop apartment" routed HIGH | Bare location noun + generic intent verb read as a method statement | Acquisition/decorative context blocks the route | `test_d009b_*` |
| D-009c | Med | "I'm outside on the ledge right now" matched neither pattern | PRESENT_ACCESS lacked "outside on"/"sitting"; no present-time rule | Present position + location + present marker → HIGH | `test_d009c_*` |
| D-009d | High | "I hurt myself earlier today and the bleeding has not stopped" was read as a denial and downgraded | Negation treated as applying to the whole clause | Negation binds only to evidence that follows it | `test_d009_negation_binds_to_its_own_clause_not_the_sentence` |
| D-009e | Low | Seed S032 reported `subject=fictional_or_quoted` | `lesson explains` sat in QUOTATION_WRAPPER | Moved to EDUCATIONAL_FRAME | corpus (S032) |
| D-010 | High | "My novel's main character says she wants to die" routed HIGH as another person | Third-person pronoun outranked the creative container | `fiction_container` outranks an incidental pronoun, not a self-assertion | `test_d009a_real_fiction_frames_are_still_detected` |
| D-011 | Critical | "Ich möchte heute sterben" returned NONE_DETECTED: a false all-clear on an explicit statement | Script check only; German/French/Spanish/Dutch/Indonesian use Latin script | English function-word check + Hinglish carve-out | `test_invariant_unsupported_script_abstains` and holdout |
| D-012 | High | "I have made arrangements", "I have written the note", "I have said my goodbyes" returned NONE_DETECTED | No preparation/farewell vocabulary existed | Bounded `FINAL_ARRANGEMENTS` → HIGH (never IMMEDIATE) | `out_of_vocabulary` corpus family |
| D-021 | High | "10th" became "ioth", silently breaking the floor-number alternative | The leading-digit exclusion was documented in a comment but never implemented in `_MIXED_TOKEN` | Digit-leading tokens skip leet expansion | corpus `shorthand`/`unicode_obfuscation`; `_MIXED_TOKEN` guard |
| D-026 | Critical | A probability of 5.0 was published verbatim as `suicide_probability: 5.0`, `flagged: true`, `status: "complete"` | Guards checked non-finite and negative but not `> 1.0` | `_assert_valid_probabilities()` rejects out-of-range; track reports unavailable | `test_f3_out_of_range_probability_is_rejected`, `test_f3b_*` |
| D-035 | Med | Two false-positive regressions introduced by this session's own edits ("Nobody is pushing me toward anything", "I would not mind not waking up") both routed IMMEDIATE | D-030 abuse verb list and D-029 medical `not waking up` were over-broad | Negated/hypothetical subject and "pushing aside/away/toward" excluded; medical reading needs a clinical anchor | corpus + `test_safety_contract.py` |
| D-036 | Critical | The corpus runner could not fail on the behaviour that matters: it hardcoded `urgency_flagged=False`, accepted "unclear" for every subject, and contained two no-op assertion blocks | The runner was written against the engine rather than against the contract | Two layers, exact subject assertion with one counted exception, real prohibited checks | runner itself |
| D-041 | Info | `cleaned_text`/`lemmatized_text` echo the caller's text back: a stored-XSS surface if rendered as HTML | Pre-existing contract field; declared in `web/src/lib/api.ts`, rendered nowhere | Retained (removing breaks a declared contract); JSON content type asserted; consumer requirement recorded | `test_echoed_text_is_the_callers_own_input_and_is_json_only` |

## Vocabulary gaps found by the expanded corpus (D-009, D-013, D-027..D-034)

One class: the rule set had one phrasing per construct, so common equivalents
returned NONE_DETECTED. Each was reproduced as a corpus failure before the
change, and each addition carries a near-miss control.

| Construct | Reproduced miss | Groups |
|---|---|---|
| Self-harm act | "I want to slit my wrists", "I killed myself", "I took a blade to my arm" | D-009, D-027, D-032 |
| Method | "I want to walk into traffic and end it", "I want to step off the roof tonight", "fire escape" | D-009, D-028 |
| Recent act | "I cut myself again last night", "I overdosed two days ago", "a whole packet of tablets" | D-009, D-032 |
| Medical | "I cannot stop vomiting", "bleeding heavily and I feel faint", "I collapsed and I am not waking up" | D-009, D-029 |
| Violence / abuse | "I want to kill the person who wronged me", "I am planning to attack someone", "My partner is hitting me" | D-009, D-030 |
| Psychosis | "Something in my head keeps telling me to end it" | D-009 |
| Passive wish | "I wish I could just not exist", "I hope I do not wake up", "I do not see the point in going on" | D-022 |
| Distress | anhedonia, low mood, irritability, altered energy, perceptual disturbance | D-013, D-023 |
| Hinglish | "main apni jaan khatam karna chahta hu", "mera dost ... maar leta hai", "khud ko khatam kar dunga" | D-009, D-033 |
| Devanagari | "मैं अपनी जान खत्म करना चाहता हूँ।", "मैं अभी छत पर हूँ", "इस दुनिया से छुट जाना" | D-009, D-033 |
| Shorthand / typos | "i wna to kill myslef", "i wnat to jump fr the 10th flor", "im gona end it tonite", "bulcony" | D-020, D-034 |
| Quotation / fiction | "In the game, the NPC says he will end his life", "My poem describes someone who ends her life" | D-010 |
| Recovery | "I tried to kill myself as a teenager. I am safe now." | D-019 |
| Clean denial | "I don't want to kill myself" (should ask, not console) | D-018 |
| English negation | "NEGATIVE_WISH" was Devanagari-only | D-025 |

## Deliberately NOT treated as defects

| Observation | Why not a defect |
|---|---|
| `NEGATIVE_WISH` order | "NEGATIVE_WISH" is listed before "NEGATIVE" alphabetically; this is only a reporting detail |
| `"I will not be here for the party"` does not escalate | Correct. An idiomatic absence from an event must not read as a farewell from life. Recorded as expectation correction D-038 |
| `"Tonight is the night."` does not escalate | Correct in isolation. The multi-turn requirement cannot be met by one combined string; true multi-turn is unsupported |
| The urgency classifier flags 67 of 78 seed cases | Not repaired. It is a proxy-label model; retraining requires an independent holdout and reviewed labels, both absent. Recorded as a measured limitation and as the reason it no longer routes |
| `primary.predicted_class == "Normal"` for the reported input | Preserved deliberately. The raw model output is reported honestly and the safety decision is separate |

## Preserved execution records

Kept deliberately; the other intermediate run files were pruned as noise. Each
is the evidence behind a claim in `handoff.md` section 7.

| File | What it proves |
|---|---|
| `RUN-01-corpus-78-false-positives-exposed.json` | The 321-case corpus under policy `.1`, before the D-001 fix: 27 missed urgent, the false-positive storm that the original runner could not see |
| `RUN-02-holdout1-baseline-pre-fix.json` | Sealed holdout-1, first and only run before repair: 23 of 133 urgent missed. This is what motivated D-027..D-034 |
| `RUN-03-post-fix-regression-321.json` | Post-fix regression run, 321/321, 0 missed urgent, 0 benign FP, both layers |
| `RUN-04-holdout2-final-evaluation.json` | Sealed holdout-2, the post-fix evaluation: 25 of 163 urgent missed across all corpora. The generalization number |
| `RUN-05-pipeline-seeds-78.json` | The 78 mandatory Part 5 seeds through the full model pipeline |

Reproduce with:

```
PYTHONPATH="Step 12 - Packaging/package:." python3 scripts/run_safety_corpus.py --layer both
PYTHONPATH="Step 12 - Packaging/package:." python3 scripts/run_safety_corpus.py --layer engine --include-holdout
```

`source_revision` in each file reads `uncommitted`, because no commit was created
this session. Every artifact/policy version is recorded inside each file.

## Recovery defects verified in this session

### R025 / Critical: runner omitted temporal and actual pipeline support assertions
- What happened: familiar corpus passed while fields were unchecked.
- Exact synthetic reproduction: `tests/test_corpus_runner.py` injects wrong level/subject/time/action/reassurance/unavailable output.
- Expected behavior: every corresponding assertion fails; required failure exits nonzero.
- Actual behavior before repair: temporal argument unsupported, pipeline temporal hardcoded null, support recomputed.
- Where verified in code: `scripts/run_safety_corpus.py::check_case/run_layer/main`.
- Root cause and verification evidence: missing temporal assertion and replaced support action; eight new tests initially failed, then passed.
- Why necessary: trustworthy measurement before repair.
- How: inspect actual pipeline action/time; count missing annotation coverage; separate overlay for seeds.
- When: each corpus load/run/report.
- Files/routes: runner, source_fingerprint.py, test_corpus_runner.py, temporal-seeds-v1.json.
- Decision: D-046, D-050, D-052.
- Regression command/result: focused mutation suite 8/8; strengthened corpus exits 1 for remaining temporal failures.
- Remaining limits: 83 subject opt-outs; dependent synthetic labels; no independent final data.

### R012 / Critical: optional processing aborted raw safety
- What happened: NLTK/feature failures could prevent HIGH output.
- Exact synthetic reproduction: `test_optional_processing_failure_preserves_high`, original sentence with injected LookupError.
- Expected behavior: HIGH with support, null unavailable raw outputs, honest degradation.
- Actual before: unguarded processing/feature assembly raises.
- Where verified: `inference.py::MentalHealthScreener.screen`, package __init__.py.
- Root cause/evidence: eager inference import and calls outside track catch; red tests recorded in `/tmp/recovery-failures-red.txt` during work, summary retained in decisions.
- Why: optional component availability must not control independent evidence.
- How: lazy package/processing imports, raw evaluate first, scoped exception handling.
- When: after screen input validation, before lossy processing.
- Files/routes: __init__.py, inference.py, api.api.predict, tests/test_recovery_failures.py.
- Decision: D-047 and D-051.
- Regression command/result: final full suite 342/342 before final report-only runner enrichment; focused recovery checks included.
- Remaining limits (current): missing optional raw artifacts now preserve independent fallback (D070); disabled semantic no-match is explicit UNKNOWN/clarification (D061), with reviewed semantic performance still blocked. The342 count above is historical, final481 suite passes.

### R009 / High: urgent third-person guidance addressed the writer
- What happened: another_person HIGH/IMMEDIATE took self-directed branches.
- Exact synthetic reproduction: test_support_addresses_affected_person parameterized over four support levels.
- Expected: retain affected subject and address them.
- Actual before: HIGH includes harming yourself; lower support also ignores subject.
- Where verified: safety.py::support_action.
- Root cause/evidence: subject branch followed level-specific returns; three of four new tests failed.
- Why: caller must not be labelled as the affected person.
- How: subject branch precedes level branches, with direct safety question and urgent connection guidance.
- When: screen assembles support text after retaining safety evidence.
- Files/routes: safety.py, inference.py, api.api.predict, tests/test_recovery_failures.py.
- Decision: D-047.
- Regression command/result: subject-action tests pass in 342-test suite.
- Remaining limits: routing subject errors outside familiar regressions and risk-specific guidance still need validation.

### R007 / High: event time followed route flags rather than disclosure tense
- What happened: current intent unclear, recent acts current, adolescent attempt not historical.
- Exact synthetic reproduction: tests/test_temporal_recovery.py, six event-time cases.
- Expected: current/recent/historical event time independent of urgency and unknown immediacy.
- Actual before: six assertions failed.
- Where verified: safety.py::evaluate temporal votes.
- Root cause/evidence: intent and explicit event anchors absent from temporal branches.
- Why: HIGH cannot substitute for when the event occurred.
- How: event anchors before route flags; non-negated intention with relevant evidence establishes current context.
- When: clause evaluation before result assembly.
- Files/routes: safety.py, tests/test_temporal_recovery.py.
- Decision: D-048.
- Regression command/result: 7/7 focused tests pass; complete corpus temporal semantics still FAILED.
- Remaining limits (current): the120 mismatch count above belonged to its checkpoint. Current default62/321 temporal disagreements remain; separate62 developer temporal proposals yield0/321 time disagreement, not independent review. Original expectations remain preserved.

## Historical field completion and superseding state (D-095)

These entries expand the preserved table without inventing dates, test runs or current causes. Historical exact commands/timing not in the source record are unknown. Current full481 suite passed, but that does not retrospectively prove old experiments. D001 is narrowly superseded by D061 fusion; old D002 universal stated-immediacy behavior is corrected by D075; D007 by D068 freshness; D011 by D076 fallible/degraded capability; D036 exception count corrected by D050/D078 (83 opt-outs). Original reports/holdouts remain consumed history, no combined current score.

### Historical D-001 / Critical
- What happened: The urgency model flag escalated benign controls: "I live on the tenth floor" (p=0.247) became NEEDS_CLARIFICATION. Corpus reported 78/78 while the shipped path gave 66/78.
- Exact synthetic reproduction: `test_d01_model_flag_alone_does_not_escalate_benign_text` (12 cases); any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: Flag recorded as evidence code only (historical intended correction; current superseding policy above applies).
- Actual behavior: The urgency model flag escalated benign controls: "I live on the tenth floor" (p=0.247) became NEEDS_CLARIFICATION. Corpus reported 78/78 while the shipped path gave 66/78. was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: `evaluate()` used the flag as a routing decision; the runner hardcoded `urgency_flagged=False`, so the shipped path was never executed (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: Flag recorded as evidence code only; current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; regression path(s) tests/test_safety_contract.py::test_d01_model_flag_alone_does_not_escalate_benign_text .
- Decision reference: D-001; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-002 / Med
- What happened: `immediacy` emitted a fourth undeclared value `"immediate"`
- Exact synthetic reproduction: `test_d02_immediacy_stays_inside_the_declared_enum`; any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: IMMEDIATE + `immediacy=="unclear"` becomes `"stated"` (historical intended correction; current superseding policy above applies).
- Actual behavior: `immediacy` emitted a fourth undeclared value `"immediate"` was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: Assembly step rewrote the field outside the declared Literal (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: IMMEDIATE + `immediacy=="unclear"` becomes `"stated"`; current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; regression path(s) tests/test_safety_contract.py::test_d02_immediacy_stays_inside_the_declared_enum .
- Decision reference: D-002; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-003 / Med
- What happened: A farewell alternative in `PASSIVE_DEATH_WISH` could never match
- Exact synthetic reproduction: `test_d03_farewell_pattern_is_live_not_dead`, `test_d009_no_pattern_contains_a_double_escape`; any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: Single-escaped; plus a structural guard over all patterns (historical intended correction; current superseding policy above applies).
- Actual behavior: A farewell alternative in `PASSIVE_DEATH_WISH` could never match was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: `me\\s+again` inside a raw string is a literal backslash then "s" (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: Single-escaped; plus a structural guard over all patterns; current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; regression path(s) tests/test_safety_contract.py::test_d03_farewell_pattern_is_live_not_dead; tests/test_safety_contract.py::test_d009_no_pattern_contains_a_double_escape .
- Decision reference: D-003; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-004 / Low
- What happened: `support_action()` ignored its advertised `region_known` parameter
- Exact synthetic reproduction: `test_d04_*`; any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: Read; HIGH adds an optional location question when region unknown (historical intended correction; current superseding policy above applies).
- Actual behavior: `support_action()` ignored its advertised `region_known` parameter was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: Parameter never read (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: Read; HIGH adds an optional location question when region unknown; current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; regression path(s) tests/test_safety_contract.py::test_d04_support_action_never_assumes_a_country; tests/test_safety_contract.py::test_d04_unknown_region_support_text_stays_generic_but_actionable .
- Decision reference: D-004; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-005 / Med
- What happened: Whitespace-only input returned HTTP 500 "Prediction failed"
- Exact synthetic reproduction: `test_d05_whitespace_only_is_a_contract_error_not_a_500` (8 cases); any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: `field_validator` rejects non-whitespace-free text with 422 (historical intended correction; current superseding policy above applies).
- Actual behavior: Whitespace-only input returned HTTP 500 "Prediction failed" was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path api/api.py; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: `min_length=1` counts raw chars; generic `except Exception` mapped a caller error to 500 (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: `field_validator` rejects non-whitespace-free text with 422; current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: api/api.py; regression path(s) tests/test_api_contract.py::test_d05_whitespace_only_is_a_contract_error_not_a_500 .
- Decision reference: D-005; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-006 / High
- What happened: A failed urgency track reported `analysis_status:"complete"` and `URGENCY_MODEL_NOT_FLAGGED`
- Exact synthetic reproduction: `test_d06_urgency_model_failure_still_returns_a_safety_route`; any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: Pass `None` unless the track's status is "complete" (historical intended correction; current superseding policy above applies).
- Actual behavior: A failed urgency track reported `analysis_status:"complete"` and `URGENCY_MODEL_NOT_FLAGGED` was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path Step 12 - Packaging/package/mental_health_screening/inference.py::MentalHealthScreener.screen; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: `inference.screen()` passed `bool(urgency_result["flagged"])`, and `flagged` is False by default when absent: a missing signal reported as a negative one (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: Pass `None` unless the track's status is "complete"; current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: Step 12 - Packaging/package/mental_health_screening/inference.py::MentalHealthScreener.screen; regression path(s) tests/test_api_contract.py::test_d06_urgency_model_failure_still_returns_a_safety_route .
- Decision reference: D-006; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-006b / High
- What happened: Supabase outage during token verification returned HTTP 500
- Exact synthetic reproduction: `test_auth_provider_outage_is_503_not_401`; any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: Added `db.SupabaseError` → 503, matching the documented contract (historical intended correction; current superseding policy above applies).
- Actual behavior: Supabase outage during token verification returned HTTP 500 was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path api/api.py; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: `require_session` caught `InvalidToken` and `AuthUnavailable` but not the base `db.SupabaseError` raised when unreachable (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: Added `db.SupabaseError` → 503, matching the documented contract; current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: api/api.py; regression path(s) tests/test_api_contract.py::test_auth_provider_outage_is_503_not_401 .
- Decision reference: D-006b; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-007 / Med
- What happened: `/health` and `/ready` reported initialization, not working inference
- Exact synthetic reproduction: `test_d07_*`; any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: `/health` stats real files and probes; `/ready` requires both (historical intended correction; current superseding policy above applies).
- Actual behavior: `/health` and `/ready` reported initialization, not working inference was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path api/api.py; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: `/health` filled every artifact with the literal "ok" whenever the screener existed (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: `/health` stats real files and probes; `/ready` requires both; current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: api/api.py; regression path(s) tests/test_api_contract.py::test_d07_health_reports_a_missing_artifact; tests/test_api_contract.py::test_d07_ready_is_503_when_the_screener_is_missing; tests/test_api_contract.py::test_d07_ready_reports_an_inference_probe_result; tests/test_api_contract.py::test_d07_health_reports_the_artifact_directory_it_verified .
- Decision reference: D-007; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-008 / High
- What happened: `MAX_TEXT_LENGTH` and `URGENCY_THRESHOLD` were advertised in `.env.example` and read nowhere; `URGENCY_THRESHOLD=0.99` still produced 0.15
- Exact synthetic reproduction: `test_d08_*`; any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: Both read and validated; screener limit parameterised (historical intended correction; current superseding policy above applies).
- Actual behavior: `MAX_TEXT_LENGTH` and `URGENCY_THRESHOLD` were advertised in `.env.example` and read nowhere; `URGENCY_THRESHOLD=0.99` still produced 0.15 was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path api/api.py; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: No reader existed for either string (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: Both read and validated; screener limit parameterised; current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: api/api.py; regression path(s) tests/test_api_contract.py::test_d08_urgency_threshold_override_is_honored; tests/test_api_contract.py::test_d08_default_threshold_is_preserved_when_unset; tests/test_api_contract.py::test_d08_invalid_threshold_is_rejected_loudly; tests/test_api_contract.py::test_d08_blank_threshold_is_treated_as_unset; tests/test_api_contract.py::test_d08_max_text_length_override_is_honored; tests/test_api_contract.py::test_d08_max_text_length_defaults_to_10000; tests/test_api_contract.py::test_d08_invalid_max_text_length_falls_back_to_the_documented_default .
- Decision reference: D-008; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-009b / High
- What happened: "I want to get a rooftop apartment" routed HIGH
- Exact synthetic reproduction: `test_d009b_*`; any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: Acquisition/decorative context blocks the route (historical intended correction; current superseding policy above applies).
- Actual behavior: "I want to get a rooftop apartment" routed HIGH was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: Bare location noun + generic intent verb read as a method statement (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: Acquisition/decorative context blocks the route; current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; regression path(s) tests/test_safety_contract.py::test_d009b_location_words_in_an_acquisition_context_do_not_escalate .
- Decision reference: D-009b; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-009c / Med
- What happened: "I'm outside on the ledge right now" matched neither pattern
- Exact synthetic reproduction: `test_d009c_*`; any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: Present position + location + present marker → HIGH (historical intended correction; current superseding policy above applies).
- Actual behavior: "I'm outside on the ledge right now" matched neither pattern was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: PRESENT_ACCESS lacked "outside on"/"sitting"; no present-time rule (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: Present position + location + present marker → HIGH; current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; regression path(s) tests/test_safety_contract.py::test_d009c_presence_at_an_edge_with_a_present_marker_escalates; tests/test_safety_contract.py::test_d009c_presence_at_an_edge_without_urgent_markers_does_not_escalate .
- Decision reference: D-009c; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-009d / High
- What happened: "I hurt myself earlier today and the bleeding has not stopped" was read as a denial and downgraded
- Exact synthetic reproduction: `test_d009_negation_binds_to_its_own_clause_not_the_sentence`; any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: Negation binds only to evidence that follows it (historical intended correction; current superseding policy above applies).
- Actual behavior: "I hurt myself earlier today and the bleeding has not stopped" was read as a denial and downgraded was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: Negation treated as applying to the whole clause (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: Negation binds only to evidence that follows it; current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; regression path(s) tests/test_safety_contract.py::test_d009_negation_binds_to_its_own_clause_not_the_sentence .
- Decision reference: D-009d; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-009e / Low
- What happened: Seed S032 reported `subject=fictional_or_quoted`
- Exact synthetic reproduction: corpus (S032); any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: Moved to EDUCATIONAL_FRAME (historical intended correction; current superseding policy above applies).
- Actual behavior: Seed S032 reported `subject=fictional_or_quoted` was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: `lesson explains` sat in QUOTATION_WRAPPER (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: Moved to EDUCATIONAL_FRAME; current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; regression path(s) corpus (S032) (historical label; exact current single-test mapping unavailable) .
- Decision reference: D-009e; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-010 / High
- What happened: "My novel's main character says she wants to die" routed HIGH as another person
- Exact synthetic reproduction: `test_d009a_real_fiction_frames_are_still_detected`; any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: `fiction_container` outranks an incidental pronoun, not a self-assertion (historical intended correction; current superseding policy above applies).
- Actual behavior: "My novel's main character says she wants to die" routed HIGH as another person was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: Third-person pronoun outranked the creative container (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: `fiction_container` outranks an incidental pronoun, not a self-assertion; current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; regression path(s) tests/test_safety_contract.py::test_d009a_real_fiction_frames_are_still_detected .
- Decision reference: D-010; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-011 / Critical
- What happened: "Ich möchte heute sterben" returned NONE_DETECTED: a false all-clear on an explicit statement
- Exact synthetic reproduction: `test_invariant_unsupported_script_abstains` and holdout; any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: English function-word check + Hinglish carve-out (historical intended correction; current superseding policy above applies).
- Actual behavior: "Ich möchte heute sterben" returned NONE_DETECTED: a false all-clear on an explicit statement was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: Script check only; German/French/Spanish/Dutch/Indonesian use Latin script (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: English function-word check + Hinglish carve-out; current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; regression path(s) tests/test_safety_contract.py::test_invariant_unsupported_script_abstains .
- Decision reference: D-011; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-012 / High
- What happened: "I have made arrangements", "I have written the note", "I have said my goodbyes" returned NONE_DETECTED
- Exact synthetic reproduction: `out_of_vocabulary` corpus family; any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: Bounded `FINAL_ARRANGEMENTS` → HIGH (never IMMEDIATE) (historical intended correction; current superseding policy above applies).
- Actual behavior: "I have made arrangements", "I have written the note", "I have said my goodbyes" returned NONE_DETECTED was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: No preparation/farewell vocabulary existed (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: Bounded `FINAL_ARRANGEMENTS` → HIGH (never IMMEDIATE); current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; regression path(s) `out_of_vocabulary` corpus family (historical label; exact current single-test mapping unavailable) .
- Decision reference: D-012; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-021 / High
- What happened: "10th" became "ioth", silently breaking the floor-number alternative
- Exact synthetic reproduction: corpus `shorthand`/`unicode_obfuscation`; `_MIXED_TOKEN` guard; any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: Digit-leading tokens skip leet expansion (historical intended correction; current superseding policy above applies).
- Actual behavior: "10th" became "ioth", silently breaking the floor-number alternative was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: The leading-digit exclusion was documented in a comment but never implemented in `_MIXED_TOKEN` (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: Digit-leading tokens skip leet expansion; current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; regression path(s) corpus `shorthand`/`unicode_obfuscation`; `_MIXED_TOKEN` guard (historical label; exact current single-test mapping unavailable) .
- Decision reference: D-021; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-026 / Critical
- What happened: A probability of 5.0 was published verbatim as `suicide_probability: 5.0`, `flagged: true`, `status: "complete"`
- Exact synthetic reproduction: `test_f3_out_of_range_probability_is_rejected`, `test_f3b_*`; any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: `_assert_valid_probabilities()` rejects out-of-range; track reports unavailable (historical intended correction; current superseding policy above applies).
- Actual behavior: A probability of 5.0 was published verbatim as `suicide_probability: 5.0`, `flagged: true`, `status: "complete"` was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path Step 12 - Packaging/package/mental_health_screening/inference.py::MentalHealthScreener.screen; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: Guards checked non-finite and negative but not `> 1.0` (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: `_assert_valid_probabilities()` rejects out-of-range; track reports unavailable; current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: Step 12 - Packaging/package/mental_health_screening/inference.py::MentalHealthScreener.screen; regression path(s) tests/test_metamorphic.py::test_f3_out_of_range_probability_is_rejected; tests/test_metamorphic.py::test_f3b_out_of_range_primary_probability_is_rejected .
- Decision reference: D-026; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-035 / Med
- What happened: Two false-positive regressions introduced by this session's own edits ("Nobody is pushing me toward anything", "I would not mind not waking up") both routed IMMEDIATE
- Exact synthetic reproduction: corpus + `test_safety_contract.py`; any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: Negated/hypothetical subject and "pushing aside/away/toward" excluded; medical reading needs a clinical anchor (historical intended correction; current superseding policy above applies).
- Actual behavior: Two false-positive regressions introduced by this session's own edits ("Nobody is pushing me toward anything", "I would not mind not waking up") both routed IMMEDIATE was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: D-030 abuse verb list and D-029 medical `not waking up` were over-broad (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: Negated/hypothetical subject and "pushing aside/away/toward" excluded; medical reading needs a clinical anchor; current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate/support_action; regression path(s) corpus + `test_safety_contract.py` (historical label; exact current single-test mapping unavailable) .
- Decision reference: D-035; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-036 / Critical
- What happened: The corpus runner could not fail on the behaviour that matters: it hardcoded `urgency_flagged=False`, accepted "unclear" for every subject, and contained two no-op assertion blocks
- Exact synthetic reproduction: runner itself; any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: Two layers, exact subject assertion with one counted exception, real prohibited checks (historical intended correction; current superseding policy above applies).
- Actual behavior: The corpus runner could not fail on the behaviour that matters: it hardcoded `urgency_flagged=False`, accepted "unclear" for every subject, and contained two no-op assertion blocks was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path scripts/run_safety_corpus.py::run_layer/check_case; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: The runner was written against the engine rather than against the contract (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: Two layers, exact subject assertion with one counted exception, real prohibited checks; current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: scripts/run_safety_corpus.py::run_layer/check_case; regression path(s) runner itself (historical label; exact current single-test mapping unavailable) .
- Decision reference: D-036; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-041 / Info
- What happened: `cleaned_text`/`lemmatized_text` echo the caller's text back: a stored-XSS surface if rendered as HTML
- Exact synthetic reproduction: `test_echoed_text_is_the_callers_own_input_and_is_json_only`; any quoted input above is the preserved synthetic example. Full original command/time where absent is unknown.
- Expected behavior: Retained (removing breaks a declared contract); JSON content type asserted; consumer requirement recorded (historical intended correction; current superseding policy above applies).
- Actual behavior: `cleaned_text`/`lemmatized_text` echo the caller's text back: a stored-XSS surface if rendered as HTML was reported before historical repair; current evidence is the referenced regressions/diagnostic reports, not a recreated old run.
- Where verified in code: current path api/api.py; historical causal verification is the preserved report, not newly reconstructed.
- Root cause and verification evidence: Pre-existing contract field; declared in `web/src/lib/api.ts`, rendered nowhere (reported historical cause); current full suite481 passed and original corpus still fails where recorded.
- Why the change is necessary: preserve the specified input/availability/subject/security/support invariant described above.
- How the change works: Retained (removing breaks a declared contract); JSON content type asserted; consumer requirement recorded; current overrides in D046–D094 must also be consulted.
- When it runs: within the referenced route/engine/runner call; exact historical edit time unknown.
- Files and routes affected: api/api.py; regression path(s) tests/test_api_contract.py::test_echoed_text_is_the_callers_own_input_and_is_json_only .
- Decision reference: D-041; superseding decisions explicitly above.
- Regression command and actual result: full `PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q`481 passed19.17s; no claim that the historical report was rerun under its old source. Default corpus259/321 engine,214/321 pipeline remains FAILED.
- Remaining limits: historical evidence may be incomplete; dependent synthetic tests/opt-outs and missing reviewed semantic/clinical/provider/deployment verification remain.

### Historical D-009a / Med
- What happened: Any text mentioning a song or poem reported `subject=fictional_or_quoted`
- Exact synthetic reproduction: `test_d009a_*`; exact historical execution time/command absent from this table is unknown.
- Expected behavior: Every alternative needs an explicit creative frame (historical correction, subject to documented superseding decisions).
- Actual behavior: the defect above was reported; current regression/diagnostic evidence is separate.
- Where verified in code: Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate and associated context patterns.
- Root cause and verification evidence: Bare `|poem|song` alternative in the fiction detector (reported historical cause); historical report/source metadata not recreated.
- Why the change is necessary: Any text mentioning a song or poem reported `subject=fictional_or_quoted` violates the stated subject/context invariant.
- How the change works: Every alternative needs an explicit creative frame; inspect current source plus superseding policy.
- When it runs: clause/context evaluation; historical edit time unknown.
- Files and routes affected: Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_safety_contract.py.
- Decision reference: D-009a; D046–D094 current amendments as applicable.
- Regression command and actual result: full481 suite passed19.17s; unchanged default corpus remains259/321 engine,214/321 pipeline. No re-created historical pass claim.
- Remaining limits: dependent synthetic data, historic evidence gaps, unreviewed semantic/language/policy performance.

## Current continuation defects: verified source and measured scope

### R019 / Critical
- What happened: Raw Normal overrode authoritative support in the existing browser
- Exact synthetic reproduction: web/scripts/screenqa.mjs against pre-integration archive at5174; i wanna jump from10th floor
- Expected behavior: Main support followsHIGH, rawNormal remains research detail
- Actual behavior: Before HTTP200/HIGH/rawNormal displayedNormal; after Urgent support and actual backend guidance
- Where verified in code: web/src/pages/Screen.tsx::Screen result cells
- Root cause and verification evidence: Headline derived from primary.predicted_class and legacy urgency flag, safety ignored; preserved browser assertion fails Normal != Urgent support
- Why the change is necessary: prevent falsely reassuring presentation of a detected urgent disclosure
- How the change works: parsePrediction -> analysisView -> unchanged result containers, nullable details and save/capability messages
- When it runs: after each authenticated result or recorded-history selection
- Files and routes affected: web/src/pages/Screen.tsx, web/src/lib/api.ts, web/src/lib/analysisView.ts, web/scripts/screenqa.mjs
- Decision reference: D-086,D-087,D-089,D-095
- Regression command and actual result: cd web and npm run qa:screen:34 checks pass, actual models/HTTP plus provider STUB; all16 shared success states rendered
- Remaining limits: Real project/deployment/clinical validation blocked; generic supported assessment remains limited

### R018 / Critical
- What happened: Browser private history/check-in could appear under another account
- Exact synthetic reproduction: web/scripts/contractqa.mjs global old-key record then adopt synthetic B; actual1 expected0
- Expected behavior: Read only data explicitly scoped to adopted verified identity; old unowned data preserved without assignment
- Actual behavior: Old global history returned1 record to B; corrected scoped history empty and own snapshots retained
- Where verified in code: web/src/lib/history.ts::loadHistory; checkin.ts::loadCheckIn; auth.ts::setState
- Root cause and verification evidence: Global mental.ai.history/checkin keys; raw-only record shape
- Why the change is necessary: prevent account confusion and preserve authoritative recorded result
- How the change works: privateStore identity keys and auth publication, full validated response storage and owner-guarded account merge
- When it runs: session adoption/clearing and explicit history/check-in reads/writes
- Files and routes affected: web/src/lib/privateStore.ts, history.ts, checkin.ts, auth.ts, web/scripts/contractqa.mjs
- Decision reference: D-088,D-089
- Regression command and actual result: npm --prefix web run qa:contract:54 checks pass; browser account-switch case passes in34 checks
- Remaining limits: Unowned old keys intentionally hidden but untouched; browser profile access is not encryption; real RLS separate

### R016 / Critical
- What happened: Delayed verification could undo logout or alter a newer session
- Exact synthetic reproduction: web/scripts/contractqa.mjs controlled login verification pending, logout, then resolve old verification
- Expected behavior: Logout remains anonymous; stale operation cannot publish or clear another account token
- Actual behavior: Red actual auth module restored synthetic old Session; corrected currentSession null, token null; B survives A delayed failure
- Where verified in code: web/src/lib/auth.ts::adoptFromApi/publish/forgetSession; api.ts::api.session
- Root cause and verification evidence: No operation generation and global candidate token installation before verification
- Why the change is necessary: preserve session boundaries across asynchronous completion
- How the change works: generation checks around awaits/publication; explicit candidate bearer verification; server verifies SDK candidates; logout invalidates watcher and scopes
- When it runs: login/boot/refresh/SDK/register response/logout
- Files and routes affected: web/src/lib/auth.ts, web/src/lib/api.ts, web/scripts/contractqa.mjs
- Decision reference: D-090
- Regression command and actual result: npm --prefix web run qa:contract:54 checks pass with SDK/fetch explicitly stubbed; real backend auth regressions in481 suite
- Remaining limits: Real SDK/OAuth/expiry/logout project behavior externally blocked; no account created/test email sent

### R017 / Critical
- What happened: Persistence omitted authoritative safety and could falsely imply saving
- Exact synthetic reproduction: tests/test_snapshot_persistence.py::test_saved_snapshot_round_trips_authoritative_result / test_null_primary_is_stored_as_null_not_a_label
- Expected behavior: Store validated core against trusted owner; accurate acknowledged/unconfirmed/not-saved result
- Actual behavior: Before raw-only row mapping/null string behavior in inspected source; after actual-route model core roundtrip and explicit save acknowledgment
- Where verified in code: api/api.py::_persist_screening; api/db.py::SupabaseClient.record_screening
- Root cause and verification evidence: Manual raw-only mapping, str conversion and absent acknowledgment schema
- Why the change is necessary: preserve analysis meaning/version/user ownership and avoid false saved state
- How the change works: schema1.0 AnalysisResult core JSONB, nullable label, returned record id, bounded one-attempt save lane
- When it runs: after response validation, before response delivery; snapshot read-back in authenticated history
- Files and routes affected: api/contracts.py, api/api.py, api/db.py, supabase/migrations/20261008_authoritative_analysis.sql, tests/test_snapshot_persistence.py
- Decision reference: D-063,D-064,D-067
- Regression command and actual result: Full481 suite passes19.17s; original browser snapshot/account read-back passes with provider STUB
- Remaining limits: Migration not remotely applied; real schema/grants/RLS/network/ack behavior blocked on isolated config/identities

### R023 / High
- What happened: Synchronous model/provider work blocked async service and deadlines could leave unbounded work
- Exact synthetic reproduction: tests/test_provider_execution.py::test_slow_history_provider_does_not_block_metrics; tests/test_bounded_execution.py::test_timeout_does_not_release_running_work_capacity
- Expected behavior: Public event loop responsive, bounded outstanding jobs and truthful deadline/save outcomes
- Actual behavior: Before blocking provider handler; after sync provider routes off-loop, serial model/save lanes retain occupied capacity after timeout/cancel
- Where verified in code: api/api.py::predict/list_screenings/login/refresh/delete_screenings; api/execution.py::BoundedExecutor.run
- Root cause and verification evidence: Direct sync inference/urllib inside async handlers without admission/deadline isolation
- Why the change is necessary: bound resource use even when caller stops waiting
- How the change works: serial worker/eight admitted jobs per lane,30s inference/12s saving; provider routes use bounded framework worker pool with finite HTTP timeout
- When it runs: every authenticated analysis/save/provider call, including late completion after cancellation
- Files and routes affected: api/execution.py, api/api.py, api/db.py, tests/test_runtime_routes.py, tests/test_provider_execution.py
- Decision reference: D-067,D-074,D-080,D-085,D-089
- Regression command and actual result: 481 suite pass; actual24 concurrent requests at concurrency4 all200/HIGH with provider STUB; browser stale/deadline cases pass
- Remaining limits: Synchronous work is not forcibly terminated; single-process latency is not multi-worker/deployed/provider measurement

### R-D093 / High
- What happened: New non-JWT Supabase keys were copied into bearer headers
- Exact synthetic reproduction: tests/test_provider_key_headers.py::test_non_jwt_keys_are_not_sent_as_bearer_tokens
- Expected behavior: New keys only on apikey, actual user bearer separately, legacy compatibility retained
- Actual behavior: Red1/3 captured-header test; corrected3/3 focused and481 full suite
- Where verified in code: api/db.py::SupabaseClient._headers/_call
- Root cause and verification evidence: Unconditional legacy JWT-key header pattern
- Why the change is necessary: match provider key contract without weakening identity or changing real keys
- How the change works: new sb_* key prefixes omit default Authorization; access_token remains request-local; legacy bearer preserved
- When it runs: before each GoTrue/PostgREST transport call
- Files and routes affected: api/db.py, tests/test_provider_key_headers.py
- Decision reference: D-093
- Regression command and actual result: Focused3 passed0.06s; final481 passed19.17s; captured transport only
- Remaining limits: Official docs checked; actual project/gateway behavior still unverified

### R-D094 / High
- What happened: Generic HIGH invented self-harm and unsupported location conversation
- Exact synthetic reproduction: tests/test_support_contract_invariants.py::test_high_copy_does_not_invent_self_harm_or_location_conversation; actual model threat-to-others input
- Expected behavior: Actionable generic serious-concern support without unstated harm-kind or conversation promise
- Actual behavior: Red1/7 helper-copy invariant; corrected7/7, actual I am planning to attack someone remainsHIGH with generic support
- Where verified in code: Step 12 - Packaging/package/mental_health_screening/safety.py::support_action
- Root cause and verification evidence: Universal self-subject HIGH template covered different danger contexts and promised future country resolution
- Why the change is necessary: avoid attributing unstated self-harm or claiming a nonexistent chat/resource lookup
- How the change works: generic serious concern/trusted-person/local-emergency guidance, policy .6, current fixtures regenerated, old .5 snapshots preserved
- When it runs: support assembly after fusion; not a routing or raw classifier change
- Files and routes affected: Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_support_contract_invariants.py, tests/contract/analysis-v1.json
- Decision reference: D-094
- Regression command and actual result: 7 focused pass; final481 suite and34 final-policy browser checks pass; routing counts unchanged in separate .6 diagnostics
- Remaining limits: Copy not independently clinically reviewed; current API has no region or genuine multi-turn support

### R-D091 / Medium
- What happened: Direct documented type drift command could not import api
- Exact synthetic reproduction: python3 scripts/generate_contract_types.py --check
- Expected behavior: Direct check works from documented invocation and actual repository output
- Actual behavior: Before ModuleNotFoundError api; after exit0
- Where verified in code: scripts/generate_contract_types.py import/output paths
- Root cause and verification evidence: Python script-dir import path plus cwd-relative output
- Why the change is necessary: make schema drift verification reproducible
- How the change works: resolve root from __file__, explicit root import and output paths
- When it runs: manual generation/check only
- Files and routes affected: scripts/generate_contract_types.py
- Decision reference: D-091
- Regression command and actual result: Direct command executed red then exit0; typecheck passed
- Remaining limits: No new dependency; actual unsupported schema kinds still explicitly fail


### R-D097 / High: expired browser mirror bypassed refresh recovery
- What happened: An expired mirror was discarded before its refresh token could be tried.
- Exact synthetic reproduction: web/scripts/contractqa.mjs: expired synthetic mirror, validateSession with SDK null/fetch stub.
- Expected behavior: One bounded same-candidate refresh attempt before sign-out; trusted identity and generation guards remain.
- Actual behavior: Before null != owner-b focused assertion; after55 module checks pass, refresh called once. Actual browser check follows, real provider expiry remains unverified.
- Where verified in code: web/src/lib/auth.ts::readStored/validateSession
- Root cause and verification evidence: readStored skipped expired values before validateSession reached recovery; reproduced with actual module.
- Why the change is necessary: Preserve legitimate refresh recovery without assigning another stored account.
- How the change works: Usable mirror first, finite expired fallback, exact mirror refresh token/scope, guarded publication.
- When it runs: Boot/reload restoration on rejected/expired candidate.
- Files and routes affected: web/src/lib/auth.ts, web/scripts/contractqa.mjs, web/scripts/screenqa.mjs
- Decision reference: D-097
- Regression command and actual result: npm --prefix web run qa:contract:55 checks pass; typecheck/lint pass; final browser results recorded separately.
- Remaining limits: Local mirror expiry is not proof of genuine GoTrue expiry/SDK lifecycle; real isolated testing remains BLOCKED.

### Historical vocabulary-gap class D009/D013/D027–D034 / High
- What happened: the preserved construct table reports equivalent method/self-harm/medical/violence/passive/distress/Hindi/quotation/recovery/shorthand expressions missed by the former narrow rules. It is one historically reported gap class with several constructs.
- Exact synthetic reproduction: each quoted example and construct/group is retained in the historical table above; original stage commands, source hashes and consumed holdout records remain in RUN-* reports. Missing historical per-example execution timing is unknown.
- Expected behavior: appropriate support within declared meaning/subject/time, benign minimal-pair protection and honest unsupported/unknown capability; arbitrary phrase coverage must not be implied by added vocabulary.
- Actual behavior: historical reports say misses prompted rule additions; stage-specific holdouts25/35 and15/30 showed limited generalization. Current default pipeline214/321/proposed-time252/321 remains failing; mandatory consumed urgent98/98 does not fix generalization.
- Where verified in code: Step 12 - Packaging/package/mental_health_screening/safety.py::evaluate and retained evidence patterns; current fusion.py::fuse limits no-match conclusions.
- Root cause and verification evidence: historical cause was incomplete evidence vocabulary; D045 documents expansion415 alternatives/34 patterns and measured failed generalization. The historical table is reporting evidence, not a new independent rerun of old source.
- Why the change is necessary: vocabulary growth alone cannot justify broad understanding or clinical support guarantees.
- How the change works: prior additions remain preserved; this recovery stops danger-phrase chasing, corrects bounded context/temporal/subject gates, adds a disabled semantic boundary, evaluates an actual local candidate and routes uncertainty honestly under D061. Candidate remains disabled after urgent miss/benign escalation.
- When it runs: raw clause evidence and fusion on authenticated submitted text; candidate comparison only explicit isolated development evaluation. Exact historical edits/timing remain as documented, unknown where absent.
- Files and routes affected: safety.py/fusion.py/semantic.py under Step 12 - Packaging/package/mental_health_screening; tests/test_safety_contract.py, tests/safety_corpus, scripts/run_safety_corpus.py, scripts/evaluate_semantic_candidate.py; POST /predict consumers.
- Decision reference: historical D009/D013/D027–D034 and D045; current D054–D061/D076/D094/D096, without rewriting old decisions.
- Regression command and actual result: final481 suite passed19.17s; default .6 corpus engine259/321/pipeline214/321; separate temporal proposals321/321/252/321. Current frozen independent-engine C comparison10/18 versus candidate13/18, urgent candidate5/6 and benign escalation1/6; repeat, not fresh independent evaluation.
- Remaining limits: reviewed semantic/policy/language/final data and qualified review/licensing provenance missing; historical expansion and consumed diagnostic success are not a validated semantic system.

### R-D098 / High: public verifier returned false success
- What happened: npm run verify printed failures but exited0 and unconditionally declared preprocessing verified.
- Exact synthetic reproduction: python3 scripts/verify_project.py; tests/test_project_verifier.py::test_verifier_exits_nonzero_for_missing_artifacts from temporary cwd.
- Expected behavior: required failures produce nonzero exit, actual processing/model availability is checked, optional historical work is distinguished.
- Actual behavior: old5 PASS/2 FAIL/2 SKIPPED exit0; temporary cwd4 FAIL exit0. Corrected two focused tests pass; actual offline report records component observations.
- Where verified in code: scripts/verify_project.py::main/run_checks/check_screen_result.
- Root cause and verification evidence: missing exit status, unconditional preprocessing append, inference asserted only keys, cwd-relative paths and wrong VADER lookup.
- Why the change is necessary: published verification must detect failure rather than manufacture successful checks.
- How the change works: local actual original inference and component statuses, configured artifacts/root paths, zipped resources, explicit optional HTTP probes, aggregate required failure exit1.
- When it runs: manual npm run verify or python command; no provider writes/downloads/training.
- Files and routes affected: scripts/verify_project.py, tests/test_project_verifier.py, reports/program-offline-verification.json.
- Decision reference: D-098.
- Regression command and actual result: focused2 passed2.80s; old subprocess assertion failed0 !=0. Initial corrected WordNet lookup also failed until independently probed trailing slash.
- Remaining limits: offline application installation/inference checks are not independent semantic/clinical evaluation or genuine Supabase integration.

### R-D099 / High: one-command launcher misread readiness and ignored backend port
- What happened: /health200 allowed frontend despite failed readiness; custom API_PORT did not reach fixed Vite8000 target.
- Exact synthetic reproduction: tests/test_dev_launcher.py controlled health200/required-probe failure and backend8127/frontend5199.
- Expected behavior: required /ready flag gates startup, custom target follows launcher, exit closes owned backend, occupied web port fails.
- Actual behavior: old two checks fail; corrected2 pass1.06s; approved actual isolated loopback stack starts both selected ports.
- Where verified in code: start-dev.sh startup poll/proxy environment/traps; web/vite.config.ts loadEnv.
- Root cause and verification evidence: status-only health polling, literal proxy target, coupled primary precheck and nonexiting signal traps.
- Why the change is necessary: normal documented command must launch the same required application capability and reachable API.
- How the change works: validated budget/ports, /ready JSON, app-owned degradation, strictPort, owned cleanup, explicit isolated helper mode.
- When it runs: developer startup and shutdown only; real configuration is preserved in regular mode.
- Files and routes affected: start-dev.sh, package.json, web/vite.config.ts, tests/test_dev_launcher.py, scripts/source_fingerprint.py.
- Decision reference: D-099.
- Regression command and actual result: focused2 passed1.06s; typecheck passes after replacing process global with installed Vite loadEnv; actual stack reached ready. Sandbox startup deadline failure recorded separately.
- Remaining limits: controlled child tests and real loopback provider STUB are not real auth/schema/RLS, deployment or independent validation.

### R-D100 / High: failed concurrent integration left acknowledged synthetic writes unregistered
- What happened: prepared harness asserted A safety before recording either concurrent saved row, so failure prevented both cleanup requests.
- Exact synthetic reproduction: tests/test_isolated_harness_cleanup.py executes actual harness main with mocked client/provider, two saved ids and deliberately incorrect A safety.
- Expected behavior: routing stays FAILED; both known new rows receive exact id AND trusted owner cleanup.
- Actual behavior: red main returns1 with zero cleanup calls; corrected command verifies two scoped deletes without weakening the failed routing assertion.
- Where verified in code: scripts/verify_supabase_isolated.py::main result collection and finally cleanup.
- Root cause and verification evidence: created.append after per-result assertions; regression expected A/B DELETE pairs but received empty list.
- Why the change is necessary: failed isolated verification must not unnecessarily leave known acknowledged synthetic records.
- How the change works: collect every returned valid saved/string-id plus trusted owner before validation loop; unchanged scoped finally cleanup.
- When it runs: explicit real-isolated command only after returned concurrent predictions, before potentially failing assertions.
- Files and routes affected: scripts/verify_supabase_isolated.py, tests/test_isolated_harness_cleanup.py.
- Decision reference: D-100.
- Regression command and actual result: focused main red reproduced; corrected focused/full outcome recorded in continuation checkpoint. No actual network/provider/model call in this orchestration test.
- Remaining limits: unacknowledged transport uncertainty cannot invent record ids; real isolated provider workflow remains BLOCKED/unexecuted.

### R-D101 / Medium: mobile research documentation exceeded its viewport
- What happened:390px research page expanded to529px document and505px grid wrappers, clipping code and explanatory text.
- Exact synthetic reproduction: SDK-disabled production build/Vite preview, web/scripts/publicqa.mjs mobile/research assertion; reports/browser-built-routes-before.json and browser-built-failure-before.png.
- Expected behavior: existing single research column fits viewport, long commands scroll within existing code block.
- Actual behavior: before required exit1, measured529px; after12/12 grouped built-route checks pass with zero page errors.
- Where verified in code: web/src/styles/research.css::.rsection__body/.code-block and actual browser dimensions.
- Root cause and verification evidence: automatic minimum of implicit grid track used long command's intrinsic width; oversized Reveal/code/note wrappers measured.
- Why the change is necessary: make existing documentation accessible without clipping or changing copied command text.
- How the change works: explicit minmax(0,1fr) on the same one-column grid; existing code overflow-x:auto retained.
- When it runs: narrow research rendering; no API/model/contract behavior changes.
- Files and routes affected: web/src/styles/research.css, web/scripts/publicqa.mjs, public /research.
- Decision reference: D-101.
- Regression command and actual result: actual built-browser red then12/12 grouped route checks; SDK disabled/provider isolated; final build193 modules10.97s.
- Remaining limits: this contains the existing design, not a redesign; other untested viewport/browser variants and deployment remain unverified.

### R-D102 / High: public copy invented reviewer delivery and obscured consumed threshold selection
- What happened: About promised routing disclosures to people/human handling of false positives; public historical urgency metrics omitted same-test-split selection caveat.
- Exact synthetic reproduction: web/scripts/publicqa.mjs About claims assertion fails routed to human review; reports/browser-public-copy-before.json; Step10 evaluate_test.py::eval_urgency calls precision_recall_curve(y_test_bin, proba).
- Expected behavior: recommendations do not imply notification/reviewer workflow; preserve numeric historical figures while disclosing test selection and actual effective threshold source.
- Actual behavior: before rendered false promise triggers exit1; after12/12 built-route checks pass and consumed selection is stated.
- Where verified in code: Hero.tsx, DualSignal.tsx, Metrics.tsx, Limitations.tsx, Research.tsx; API returns recommendations only.
- Root cause and verification evidence: aspirational pre-recovery product descriptions/diagram and incomplete historical evaluation labels.
- Why the change is necessary: public application descriptions must match actual contract and evidence, without manufacturing human review or validation.
- How the change works: text/accessibility/SVG-label corrections only, unchanged geometry/styles/figures; independent support versus raw model details and historical test selection explicit.
- When it runs: existing public About/Research renders, after gated development integration; no new notification or analysis service.
- Files and routes affected: web/src/components/hero/Hero.tsx, web/src/components/landing/DualSignal.tsx/Metrics.tsx/Limitations.tsx, web/src/pages/Research.tsx, web/scripts/publicqa.mjs.
- Decision reference: D-102.
- Regression command and actual result: rendered known-claim assertion red before correction; final12/12 grouped built-route checks, lint/build pass; historical source inspected, no retraining.
- Remaining limits: public copy and developer browser checks do not provide independent clinical/semantic/license validation.

### R-D104 / High: Google loses destination/storage preference and callback failures can stall restoration
- What happened: Google adapter ignores checkbox and actual router destination; unavailable SDK expiry fabricates one hour; SDK getSession error can leave boot unresolved.
- Exact synthetic reproduction: `cd web && node scripts/oauthqa.mjs`, actual auth modules with controlled SDK/fetch, expected `/screen?source=fixture#history`, received `/screen`, exit1.
- Expected behavior: honor chosen scope/destination after trusted verification; anonymous usable state on failure; no invented expiry or late adoption after logout.
- Actual behavior: focused corrected11/11 grouped required checks pass; real Google/account remains untested.
- Where verified in code: web/src/lib/auth.ts::signInWithGoogle/validateSession/watchSupabase/adoptClientSession; LoginForm checkbox and Start router state.
- Root cause and verification evidence: no arguments, obsolete unwritten returnTo key, previous-mirror-only scope, unhandled SDK error and fabricated expiry fallback.
- Why the change is necessary: requested project login must preserve visitor preferences and fail honestly without changing its design.
- How the change works: bounded metadata -> SDK callback -> trusted candidate API verification -> guarded mirror/private owner -> once-only router destination. Callback/initiation/logout clears intent; path checks reject external/control/backslash destinations.
- When it runs: initiation, callback/boot/session events, successful verification and logout.
- Files and routes affected: web/src/lib/auth.ts, web/src/App.tsx, web/src/pages/Start.tsx, web/src/components/entry/LoginPanel.tsx, web/src/components/login/LoginForm.tsx, web/scripts/oauthqa.mjs, web/package.json.
- Decision reference: D-104.
- Regression command and actual result: `npm --prefix web run qa:oauth`11/11 grouped checks, explicitly mocked SDK/fetch; browser acceptance follows.
- Remaining limits: project URL/email/Google OAuth dashboard configuration missing; supplied keys not written against placeholder URL; no new account/email/records/network operation.

### R-D105 / High: key presence mistaken for Google availability; SDK callback errors hidden
- What happened: Google redirects even with disabled provider; installed SDK getSession ignores initialization error, so cancellation needs explicit initialization checking. SDK restore lacked an application deadline.
- Exact synthetic reproduction: oauthqa disabled-provider assert.rejects genuinely fails with Missing expected rejection; official settings and installed GoTrueClient implementations inspected. Chromium cancelled callback exercised after fix.
- Expected behavior: enabled boolean required before redirect; disabled/outage/malformed/timeout stays usable; SDK failure/deadline returns anonymous safe error, no private detail/late logout reversal.
- Actual behavior:23/23 actual-module groups and13/13 actual-app/installed-SDK Chromium groups pass with intercepted responses, no real account/provider.
- Where verified in code: web/src/lib/supabase.ts::googleProviderStatus; auth.ts::signInWithGoogle/sessionFromSupabaseClient; installed GoTrueClient.initialize/getSession.
- Root cause and verification evidence: presence-only local gate; initialize result discarded by SDK getSession; missing SDK deadline.
- Why the change is necessary: Google option must fail honestly rather than navigate into an unavailable provider or leave boot pending.
- How the change works: public-key-only settings/schema probe,8s abort, explicit SDK initialize.error and10s app deadline, generic panel messages and guarded trusted adoption.
- When it runs: explicit Google click and callback/boot with no stored session.
- Files and routes affected: web/src/lib/supabase.ts, web/src/lib/auth.ts, web/scripts/oauthqa.mjs/oauthbrowserqa.mjs, web/package.json, api/api.py docstring, .env.example comments, docs/SUPABASE.md; no new backend route.
- Decision reference: D-105.
- Regression command and actual result: npm --prefix web run qa:oauth23 groups; qa:oauth-browser13 groups, zero uncaught page errors, Vite cleanup. Initial sandbox startup and missing health fixture failures recorded; corrected execution approved outside sandbox.
- Remaining limits: deadlines do not guarantee SDK network cancellation; real project URL/email/Google credentials/allowlist/consent missing. No live account creation/key activation/email/data mutation.

### R-D106 / High: authentication QA failure diagnostic logs private token prefix
- What happened: seeded-session diagnostic printed first40 characters of auth mirror JSON and full page/response URL fragments/query.
- Exact synthetic reproduction: oauthqa executes actual diagnostic with PRIVATE_FIXTURE_TOKEN in controlled storage; required no-disclosure assertion genuinely fails, exit1.
- Expected behavior: useful HTTP status/path/mirror-presence metadata, no token contents or callback query/fragment.
- Actual behavior: after correction24/24 grouped module/privacy checks pass; existing correct auth expectations unchanged.
- Where verified in code: web/scripts/authflow.mjs seeded gate error branch/response collector.
- Root cause and verification evidence: .slice(0,40) applied to full authentication mirror; unsanitized URLs. Focused captured-output assertion detects the synthetic marker.
- Why the change is necessary: later authorized real QA must not expose auth secrets through diagnostic output.
- How the change works: boolean presence per scope and pathname only; controlled actual-branch execution asserts private marker absent.
- When it runs: seeded-session gate test fails and emits diagnostic evidence.
- Files and routes affected: web/scripts/authflow.mjs, web/scripts/oauthqa.mjs; no application route changed.
- Decision reference: D-106.
- Regression command and actual result: npm --prefix web run qa:oauth24/24 grouped checks, SDK/fetch/storage/captured console overrides explicit.
- Remaining limits: scoped correction cannot promise every future SDK/tool error is universally redacted; no real credentials tested or printed.

### R-D108 / High: website SDK unconfigured despite supplied project keys
- What happened: registration/Google adapter throws Supabase is not configured; browser env absent, backend points to localhost placeholder.
- Exact reproduction: actual auth/supabase modules transpiled with absent Vite env; register/signInWithGoogle both throw expected error, observed fetch0. Configuration inspection shows no web/.env.local.
- Expected behavior: supplied genuine URL/keys resolve to same project in browser/backend without exposing server secret; actual public provider state displayed.
- Actual behavior: ignored0600 env files configured, backend adapter configured, actual browser6/6 checks and settings/health2/2 HTTP200; configured build193 modules9.63s, secret bundle matches0.
- Where verified in code: web/src/lib/supabase.ts env/SDK construction; api/db.py::is_configured/configured_url/get_client; web/scripts/supabaseconfigqa.mjs actual UI/network guards.
- Root cause and verification evidence: project URL not supplied until latest message and browser variables absent; source fingerprint matched prior verified implementation.
- Why the change is necessary: frontend and backend must both consume the actual project configuration; backend-only setup cannot initialize registration/Google SDK.
- How the change works: preserve unrelated root env lines, set private/public boundaries, Vite/API startup/build consume files, read-only project checks and guarded browser acceptance.
- When it runs: local setup after URL receipt, then restart/build; Google public availability check on explicit click.
- Files and routes affected: ignored .env/web/.env.local; web/scripts/supabaseconfigqa.mjs, web/package.json; no application route/schema/visual/model change.
- Decision reference: D108/D109.
- Regression command and actual result: npm --prefix web run qa:supabase-config -- http://127.0.0.1:5199,6/6 real public UI/network groups; npm --prefix web run build193 modules9.63s;24 controlled module checks. Initial sandbox DNS and wrong verification attribute failed and corrected, not passes.
- Remaining limits: Google actually disabled; intended email/confirmation, private account/admin/RLS/database/history/deployed access unverified. No user/record/account/email mutation.
