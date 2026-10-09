# System Flow

How a screening request is served, and where safety sits in it. Every name in
this file is from the inspected code at revision
2053855d51aaa5c9e06bd8c30f1c35d45c64716b plus this session's changes.

## 1. Verified Current Flows

### 1.1 Request path: POST /predict

```
existing browser -> POST /predict
  -> add_request_id() middleware            api/api.py (currently unvalidated header)
  -> require_session()                     api/api.py
     -> auth.decode_token() -> db.get_client().get_user()
        trusted identity from GoTrue; test transport is stubbed
  -> PredictRequest validation              whitespace/character limit
  -> predict() -> MentalHealthScreener.screen(raw_text)
     -> input validation
     -> evaluate_safety(raw_text)            safety.py: evaluate
        minimally normalized rules, subject/context gates and temporal votes
        failure -> UNKNOWN/unavailable
     -> clean_and_lemmatize()                optional lazy processing import
        failure -> cleaned/lemmatized null, both raw tracks unavailable
     -> primary track try block
        extract_handcrafted_features -> _build_primary_features -> predict_proba
        probability validation -> raw result; failure -> null/unavailable
     -> urgency track try block
        TF-IDF -> predict_proba -> threshold; failure -> null/unavailable
     -> retain safety, add honest urgency availability evidence
        optional failure -> degraded, not a lost HIGH
        both raw tracks unavailable plus no concern -> UNKNOWN/clarification
     -> support_action(level, subject)       actual support returned by screen
  -> PredictResponse validation              api/api.py (not yet frozen/versioned)
  -> _persist_screening()                    bounded HTTP timeout, synchronous
     -> db.record_screening()                verified user_id, privileged PostgREST
        CURRENT DEFECT: row omits safety; write outcome absent from response
  -> JSON -> web/src/lib/api.ts -> Screen.tsx
     CURRENT DEFECT: safety ignored, primary headline; history also loses safety
```

The raw safety check precedes optional processing after screen input validation.
The async route still calls synchronous inference and storage directly; outstanding work
and cancellation are not bounded by a worker strategy yet. Processing never downloads
packages/resources. The semantic adapter is disabled and not in this production flow.
Authenticated owner-scoped history is `list_screenings()` -> `db.list_screenings(claims.user_id)`;
local browser history uses `web/src/lib/history.ts` and currently stores only raw signals.


### 1.2 Health and readiness

```
GET /health                     api/api.py: health()
  -> _verify_artifacts()        stats every artifact resolved from config.json
  -> _inference_probe()         one real screener.screen("hello")   [D-007]
  -> healthy only if both pass

GET /ready                      api/api.py: ready()
  -> _verify_artifacts() and _inference_probe()
  -> 503 unless both pass; reports inference_checked
```

### 1.3 Safety levels

| level | meaning | action |
| --- | --- | --- |
| `IMMEDIATE` | in-progress act, or stated position with a stated action | act now |
| `HIGH` | explicit self-directed intent, or preparation and farewell | reach someone now |
| `CONCERNING` | passive wish, distress, self-harm without intent, historical | check in, follow up |
| `NEEDS_CLARIFICATION` | ambiguous, unread, or an action with an unstated object | ask |
| `NONE_DETECTED` | no evidence code matched | limited no-concern result |
| `UNKNOWN` | unsupported language, or the safety layer failed | treat as needing review |

Ordering is `UNKNOWN(0) < NONE_DETECTED(1) < NEEDS_CLARIFICATION(2) <
CONCERNING(3) < HIGH(4) < IMMEDIATE(5)` in `safety.LEVEL_ORDER`.

Model evidence cannot move a level under current D-001. Clause aggregation applies only within one disclosure; recovery can change present routing. UNKNOWN is not a lower danger despite the legacy internal ordering.

## 2. What a consumer must do

Read `safety` first. `primary.predicted_class` is a proxy-label topic guess and
is **not** evidence that someone is safe. For "i wanna jump from 10th floor",
`primary` reads `Normal` at p=0.950 while `safety.level` reads `HIGH`. Both are
reported honestly; only one is a support decision.

`cleaned_text` and `lemmatized_text` echo the caller's own text back and must be
rendered as text, never as markup (D-041).

## 3. Corpus and evaluation flows

```
python3 scripts/generate_corpus_expansion.py
  -> tests/safety_corpus/expansion.json      243 regression cases
     (expects Part 5 oracle + mechanical subject derivation)

python3 scripts/run_safety_corpus.py --layer engine|pipeline|both
  -> loads cases.json + expansion.json ONLY
  -> per case: safety.evaluate(), or screener.screen() for pipeline
  -> asserts level, subject, annotated temporal context, actual pipeline support, prohibited behaviour
  -> reports/safety-run-<utc>.json  + coverage + metrics with denominators
  -> exits 1 on any required failure

python3 scripts/run_safety_corpus.py --layer engine --include-holdout
  -> additionally loads holdout.json and holdout2.json  (EVALUATION ONLY)  [D-040]
```

## Changes in this session (Phase A-F backend audit and repair)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| safety policy | Urgency model flag demoted to evidence; it no longer escalates | `safety.py` | uncommitted | D-001 |
| safety policy | `immediacy` restricted to the declared enum | `safety.py` | uncommitted | D-003 |
| safety policy | `support_action()` reads `region_known`; no country is ever named | `safety.py` | uncommitted | D-004 |
| safety policy | Unreachable farewell alternative in `PASSIVE_DEATH_WISH` fixed (`\\s` inside a raw string) | `safety.py` | uncommitted | D-003 (test D-03) |
| safety vocabulary | Self-harm, method, medical, violence, abuse, fiction and Indic gaps | `safety.py` | uncommitted | D-009, D-013, D-027 |
| safety context | Fiction container priority; negation clause scope; acquisition guard; anaphora guard; recovery cap | `safety.py` | uncommitted | D-010, D-009d, D-009b, D-015, D-019 |
| safety capability | Latin script is not English: function-word check plus Hinglish carve-out | `safety.py` | uncommitted | D-011 |
| safety vocabulary | Preparation/farewell evidence (`FINAL_ARRANGEMENTS`) | `safety.py` | uncommitted | D-012 |
| safety normalization | Bounded typo map; leet skips digit-leading tokens | `safety.py` | uncommitted | D-020, D-021 |
| safety regression | Two false-positive regressions introduced in repair removed | `safety.py` | uncommitted | D-035 |
| inference | Failed urgency track passes `None`, not `False` | `inference.py` | uncommitted | D-006 |
| inference | Probability range validation for both tracks | `inference.py` | uncommitted | D-026 |
| inference | `URGENCY_THRESHOLD` honoured and validated; `max_text_length` parameterised | `inference.py` | uncommitted | D-008 |
| API | Whitespace-only text returns 422, not 500 | `api/api.py` | uncommitted | D-005 |
| API | `MAX_TEXT_LENGTH` honoured with validated fallback | `api/api.py`, `.env.example` | uncommitted | D-008 |
| API | Supabase outage during token verification returns 503, not 500 | `api/api.py` | uncommitted | D-006 |
| API | `/health` verifies artifacts and runs an inference probe | `api/api.py` | uncommitted | D-007 |
| API | `/ready` returns 503 unless a real screening succeeds | `api/api.py` | uncommitted | D-007 |
| corpus | Expansion corpus: 243 cases, oracle-derived, dedup by paraphrase group | `scripts/generate_corpus_expansion.py`, `tests/safety_corpus/expansion.json` | uncommitted | D-037 |
| corpus | Runner executes the shipped layer; exact subject assertion; real prohibited checks | `scripts/run_safety_corpus.py` | uncommitted | D-036 |
| evaluation | Two sealed holdouts, run once each, reported as found | `scripts/build_holdout.py`, `scripts/build_holdout2.py`, `tests/safety_corpus/holdout*.json` | uncommitted | D-040 |
| tests | Safety contract regressions (75), API contract/security (125), metamorphic + fault (33) | `tests/test_safety_contract.py`, `tests/test_api_contract.py`, `tests/test_metamorphic.py`, `tests/_supabase_stub.py` | uncommitted | D-001..D-035 |
| tests | Corrected two prior expectations that encoded the old behaviour | `tests/test_safety.py` | uncommitted | D-002, D-003 |
| documentation | Task specification preserved in the repository root | `AUDIT-SPEC.md` | uncommitted | D-043 |
| documentation | Documentation convention (no em-dashes) restored in this session's own files | `handoff.md`, `reports/defect-register.md` | uncommitted | D-044 |
| documentation | Six compliance gaps against the specification recorded rather than closed | `AUDIT-SPEC.md`, `handoff.md`, `reports/defect-register.md` | uncommitted | D-045 |
| documentation | This file, `decisions.md`, `handoff.md`, `reports/defect-register.md` | `flow.md`, `decisions.md`, `handoff.md`, `reports/defect-register.md` | uncommitted | none |

No previous session section existed; this is the first.
## Changes in this session (Phase A recovery)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Baseline | Dirty-source manifest and model hashes, original synthetic API reproduction | reports/recovery-baseline.json, reports/recovery-original-baseline.json | uncommitted | D-046 |
| Evaluation | Check temporal context and actual pipeline support; reject controlled wrong outputs | scripts/run_safety_corpus.py, tests/test_corpus_runner.py | uncommitted | D-046 |

## Changes in this session (Phase B recovery)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Safety execution | Raw evidence precedes optional processing; failures isolated by track; actual support returned | mental_health_screening/inference.py, mental_health_screening/__init__.py, api/api.py | uncommitted | D-047 |
| Support | Urgent guidance addresses another person where appropriate | mental_health_screening/safety.py | uncommitted | D-047 |
| Policy | Standalone routing meanings, unknown semantics and fusion requirements | docs/ROUTING-POLICY.md | uncommitted | D-047 |

## Changes in this session (Phase B temporal correction)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Temporal context | Explicit recent/historical event anchors precede route flags; present intent can establish current context without immediacy | mental_health_screening/safety.py, tests/test_temporal_recovery.py | uncommitted | D-048 |

## Changes in this session (Phase B semantic boundary)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Semantic adapter | Disabled local boundary with shape and failure checks, evaluation only; no production fusion | mental_health_screening/semantic.py, tests/test_semantic_adapter.py | uncommitted | D-049 |

`semantic.assess(text, evaluator=None)` returns disabled. Explicit test/evaluation callables can exercise the shape boundary. This is not connected to production `screen()`; no validated semantic artifact exists here. Do not read this boundary as a deployed layered semantic system.

## Changes in this session (Phase A evidence provenance)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Reports | Source/config/corpus fingerprints, artifact hashes, temporal coverage/errors, duplicates, available-model denominator | scripts/source_fingerprint.py, scripts/run_safety_corpus.py | uncommitted | D-050 |

Runner assertions are exact for cases marked `subject_check=exact`. The existing regression corpus has 83 explicit subject opt-outs; the earlier description of one exception was inaccurate. The report now retains and counts those opt-outs. Missing seed temporal annotations are reported explicitly, not treated as passing assertions.

## Changes in this session (Phase B insufficient assessment)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Uncertainty | Both raw tracks unavailable plus no reliable fallback evidence returns UNKNOWN/clarification; HIGH retained | mental_health_screening/inference.py, tests/test_recovery_failures.py | uncommitted | D-051 |

## Changes in this session (Phase A/B seed annotations)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Corpus metadata | Separate temporal overlay for all 78 seeds, original dataset preserved | tests/safety_corpus/temporal-seeds-v1.json, scripts/run_safety_corpus.py | uncommitted | D-052 |

## Changes in this session (Phase A/B checkpoint documents)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Current contract | Diagnostic field map; no claim of versioned contract freeze | docs/API-CONTRACT-CURRENT.md | uncommitted | D-053 |
| Evidence/handoff | Full recovery defect entries, current matrix, preserved prior handoff and continuation report | reports/defect-register.md, reports/requirements-evidence.md, reports/handoff-pre-recovery.md, reports/recovery-report.md, handoff.md | uncommitted | D-053 |

## Changes in this session (Phase B continuation: effective context)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Context attribution | Gate each clause, then attach subject/time to effective support evidence; strongest evidence determines context | Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_context_attribution.py | uncommitted | D-054 |

`evaluate` no longer determines concern-event time from unrelated clauses. It collects effective contexts after fiction/education/negation gates, chooses the highest support priority, then resolves subject/time among that evidence. `_temporal_for_concern` reads finite grammatical state and event-time anchors. A no-concern result has no known concern-event time; fictional-only text is hypothetical. This is one-input attribution, not conversation memory.

## Changes in this session (Phase B isolated semantic experiment)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Evaluation candidate | Explicit pinned artifact setup and CPU-only experiment environment; no production enablement | evaluation/requirements-semantic.txt, scripts/fetch_semantic_candidate.py, scripts/evaluate_semantic_candidate.py, evaluation/semantic-development-v1.json, docs/SEMANTIC-CANDIDATE.md | uncommitted | D-055 |

`fetch_semantic_candidate.py --output /tmp/mental-ai-semantic-artifacts` downloads only public model files from a pinned revision and writes hashes. `evaluate_semantic_candidate.py` performs local encoding/classifier fitting on developer synthetic development rows, then comparison on separate synthetic validation rows. This path does not import credentials or use application data and is not part of `screen()`.

## Changes in this session (Phase B abuse evidence scope)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| False escalation | Unqualified help/constraint/fear no longer count as abuse emergency evidence; explicit threats/assaults retained | Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_abuse_scope.py | uncommitted | D-056 |

## Changes in this session (Phase B candidate decision)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Semantic comparison | Actual local encoder/classifier comparison recorded; candidate remains disabled after context/false-alarm failures | docs/SEMANTIC-CANDIDATE.md, reports/semantic-candidate-20261008-v1.json | uncommitted | D-057 |
| Provenance | Evaluation code/data/requirements added to source fingerprint scope | scripts/source_fingerprint.py | uncommitted | D-057 |

## Changes in this session (Phase B temporal carry-over)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Temporal context | Actual reassertion adds current context; resolved history retains event time; undated past remains unclear | Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_context_carry.py | uncommitted | D-058 |

## Changes in this session (Phase B temporal annotation review)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Temporal review | Separate sparse policy-aligned temporal proposals; original labels remain the default | tests/safety_corpus/temporal-review-v2.json, scripts/run_safety_corpus.py | uncommitted | D-059 |

`--temporal-review` applies the separate developer-reviewed temporal overlay after validating that original values still match. Each affected row records its original expectation and rationale; original input/route/subject data is preserved. The default run still tests the original oracle. Supplemental passes cannot be described as independent clinical validation or as a passing original corpus.

## Changes in this session (Phase B fictional event time)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Temporal fiction | Preserve hypothetical time for explicit fictional character/method events; bare film reference remains unclear | Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_context_carry.py | uncommitted | D-060 |

## Changes in this session (Phase B/C fusion availability)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Fusion | Independent fuse returns assessment scope and honest component statuses; unresolved raw flag clarifies, insufficient no-match abstains | Step 12 - Packaging/package/mental_health_screening/fusion.py, Step 12 - Packaging/package/mental_health_screening/inference.py, tests/test_fusion_availability.py | uncommitted | D-061 |

`screen` calls `fusion.fuse` after both raw tracks. Fusion retains reliable raw-text support, records raw availability, marks semantic disabled and heuristic language degraded. An unresolved legacy flag cannot declare an emergency. Outside recognized context, no available validated semantic assessment means clarification/UNKNOWN. These fields must pass through the common API contract and storage in Phase C/D.

## Changes in this session (Phase B educational context scope)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Education gate | Require actual existing prevention/lesson/training framing; bare risk nouns cannot clear concern | Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_education_scope.py | uncommitted | D-062 |

## Changes in this session (Phase C versioned contract)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Contract | Common schema 1.0 with strict enums, raw availability, component/scope and model identity; API uses actual producer fields | api/contracts.py, api/api.py, Step 12 - Packaging/package/mental_health_screening/inference.py, tests/test_versioned_contract.py | uncommitted | D-063 |

`predict` validates the actual fusion result using `PredictResponse` from `api/contracts.py`. `AnalysisResult` is the shared core intended for immutable stored snapshots. Persistence outcome is separate and defaults not_saved, never saved by implication. Source artifact identity is computed once per screener initialization from actual raw-model files/config. Invalid probability distributions fail the affected track before response validation. Raw exception messages are omitted from prediction logs.

## Changes in this session (Phase C/D authoritative snapshots)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Persistence | Store validated core JSONB; report confirmed/rejected/unconfirmed acknowledgement; no retries | api/api.py, api/db.py, supabase/migrations/20261008_authoritative_analysis.sql, tests/test_snapshot_persistence.py | uncommitted | D-064 |
| History | Parse common snapshot schema; absent snapshot is legacy_unassessed, malformed snapshot is unavailable | api/api.py, api/contracts.py | uncommitted | D-064 |

`predict` validates `PredictResponse`, then `_persist_screening` sends its `AnalysisResult` core plus existing row fields. `record_screening` requests returned record id. Confirmed id sets saved; rejection sets not_saved; uncertain transport/acknowledgement sets unconfirmed. No in-process background save or retry is used. The privileged insert uses verified claims.user_id. `list_screenings` reads analysis_result under the same owner filter and validates it; NULL snapshots retain legacy raw values without a fabricated safety assessment. Additive migration is prepared, not applied to a remote project.

## Changes in this session (Phase B recovery scope correction)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Recovery gates | Require historical concern-event evidence before lowering support; help alone cannot cancel current intent | Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_recovery_scope.py | uncommitted | D-065 |

Within `evaluate`, the clause historical gate now checks `_temporal_for_concern`; cross-clause recovery checks every effective concern context. Current or unknown-time intent survives a separate help statement. An explicitly old event still retains historical context and support. Output then enters the unchanged fusion/contract/storage flow.

## Changes in this session (Phase E HTTP boundaries)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| HTTP validation | Bound streamed body bytes; use configured decoded character cap; sanitize request ID; permit existing DELETE preflight | api/body_limit.py, api/api.py, api/contracts.py, tests/test_http_boundaries.py | uncommitted | D-066 |

`BodyLimitMiddleware` bounds `/predict` POST intake before JSON parsing, without trusting Content-Length or truncating text. Request middleware selects a safe ID and logs the registered route. `PredictRequest._check_text` uses `max_text_length`, also supplied to the screener at initialization. Authentication remains required for private analysis/history/deletion. Explicit CORS origins permit GET/POST/DELETE with Authorization; unlisted origins receive no grant.

## Changes in this session (Phase E bounded prediction work)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Execution | Serial inference/save lanes, eight admitted jobs each; deadline/cancellation do not release running slots | api/execution.py, api/api.py, tests/test_bounded_execution.py | uncommitted | D-067 |

Authenticated `predict` awaits `inference_executor.run(screener.screen, ...)` with a 30-second deadline. One worker serializes model access; eight slots bound running plus queued work. Capacity/deadline failure yields 503/Retry-After. The validated core then enters an independent serial persistence lane with a 12-second caller deadline. Unadmitted saving is not_saved; timed-out saving is unconfirmed. Support survives save failure. A cancelled/timed-out caller cannot stop synchronous work; its slot remains occupied until worker completion. Readiness and other provider routes are not covered by this lane yet.

## Changes in this session (Phase E capability freshness)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Operations | Add cheap /live; share ten-second fresh probe cache with bounded refresh and published age/TTL | api/api.py, tests/test_readiness_freshness.py | uncommitted | D-068 |

`/live` reports process liveness without inference. `/health` and `/ready` stat artifacts and await `_fresh_probe`. Fresh cached inference can be reused for ten seconds; expired success cannot satisfy readiness if refresh fails or is pending. Refresh uses the existing bounded serial inference lane with a two-second caller deadline. `_inference_probe` requires complete independent safety and reports optional degradation. Authentication/database and independent semantic validation remain outside the probe's claimed coverage.

## Changes in this session (Phase G expectation review)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Unit oracle | Preserve obsolete UNKNOWN-free assertion and explicitly test required insufficient-capability response | tests/test_safety.py, reports/legacy-unit-expectation-review.md | uncommitted | D-069 |

No production flow changes in D-069. Original corpus routing expectations remain untouched and evaluated as consumed diagnostics; one obsolete unit expectation is preserved with its policy review.

## Changes in this session (Phase E owner request limit)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Prediction limits | Atomic local-worker counter; 30/60s per trusted owner; isolated test state | api/limits.py, api/api.py, tests/conftest.py, tests/test_predict_limits.py, tests/test_http_boundaries.py, .env.example | uncommitted | D-070 |

`predict` authenticates and validates input, then admits `_screen_with_limit` through the bounded inference lane. `PredictLimiter.check` hashes verified claims.user_id, executes a SQLite transaction and consumes a 60-second allowance before `screen`. Rate exhaustion returns 429 with Retry-After; inaccessible/locked limit store returns 503. A caller-supplied user_id is never used. Workers on one host must share the configured local file. Distributed replicas need shared ingress limits; no such deployment is asserted verified.

## Changes in this session (Phase B/E artifact and ordering faults)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Raw initialization | Isolate track load failures; validate extraction/class order and probability length | Step 12 - Packaging/package/mental_health_screening/inference.py, tests/test_artifact_availability.py | uncommitted | D-071 |
| Readiness | Required independent safety can remain ready/degraded despite optional artifact absence | api/api.py | uncommitted | D-071 |

`MentalHealthScreener.__init__` still requires valid configuration, then loads each raw track independently. A failed raw load leaves that model unavailable; raw safety can still run. Each inference track checks feature/class/probability alignment before publishing values. Missing-file entries in model fingerprint manifest are null. `/health` reports artifact failure; `/ready` can report bounded independent fallback ready with optional_artifacts_ok false. Configurable lexicon directory remains a separate open defect.

## Changes in this session (Phase B/E feature provenance)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Features | Use configured lexicon files with bounded lazy cache; propagate readability failure; hash lexicons | Step 12 - Packaging/package/mental_health_screening/features.py, Step 12 - Packaging/package/mental_health_screening/inference.py, tests/test_feature_provenance.py | uncommitted | D-072 |

Constructor records lexicon paths from the same configuration/artifact directory as models and includes their hashes in model identity. `screen` runs independent safety, optional cleaning, then passes these paths into guarded primary feature extraction. `_load_lexicons` caches eight immutable deployment path pairs. Readability exceptions reach primary unavailable; they do not become zero-valued observations or erase independent/urgency output. Restart is required after artifact/lexicon changes. This closes the configurable-lexicon defect left open under D-071.

## Changes in this session (Phase H interim evidence checkpoint)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Evidence/docs | Reconcile current contract/policy/matrix/handoff; preserve prior maps; record actual source and failed IDs | docs/ROUTING-POLICY.md, docs/API-CONTRACT-CURRENT.md, reports/recovery-continuation-report.md, reports/requirements-evidence.md, reports/recovery-checkpoint-20261008-continuation.json, handoff.md | uncommitted | D-073 |

No production behavior changes in D073. Interim checkpoint explicitly leaves shared contract freeze, broader context/language review, remaining runtime/provider checks and gated browser integration unfinished. Actual models/ASGI are distinguished from stubbed provider transport; real external validation remains blocked on named missing inputs.

## Changes in this session (Phase E provider execution)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Provider IO | Synchronous FastAPI worker dispatch for login/refresh/history/delete; error type redaction | api/api.py, tests/test_provider_execution.py | uncommitted | D-074 |

Login/refresh and owner-scoped history/deletion execute in FastAPI's bounded worker pool instead of blocking the event loop. Existing urllib timeout bounds each provider call. Trusted token checks and owner filters are unchanged. Prediction retains its explicit serial inference/save lanes. Running synchronous work survives caller cancellation under its own pool/transport bounds. Error logs contain types and sanitized identifiers, not exception messages.

## Changes in this session (Phase B/C support invariants)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Support/schema | Known prohibition/actionability checks; location-neutral urgent guidance; explicit limited NONE; honest timing/scope | api/contracts.py, Step 12 - Packaging/package/mental_health_screening/safety.py, Step 12 - Packaging/package/mental_health_screening/fusion.py, tests/test_support_contract_invariants.py | uncommitted | D-075 |

`evaluate` retains missing immediacy rather than deriving it from IMMEDIATE. `fuse` reports unavailable scope if assessment components are unavailable. `support_action` uses conditional hazard/emergency guidance without inventing a balcony and explains limited no-concern assessment for NONE. Common `SafetyResult` checks known prohibited reassurance/diagnosis, urgent actionability, a clarification question and correct person before persistence/response. This is specific invariant validation, not complete semantic or clinical validation, and avoids exact-template coupling for history.

## Changes in this session (Phase C shared contract examples)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Fixtures | Versioned15 success states/3 errors, shared schema/API/core round-trip with explicit overrides | scripts/generate_contract_fixtures.py, tests/contract/analysis-v1.json, tests/test_shared_contract_fixtures.py | uncommitted | D-076 |

Fixture tests load one JSON source. Common Pydantic schema validates each success and AnalysisResult round-trips its core. Real authenticated API consumes the same states under explicit inference and provider transport overrides; separate original/fault tests exercise actual models. Auth/input/rate errors exercise real boundaries. Frontend/history fixture consumption and final freeze remain pending. No pending saving mechanism is invented.

## Changes in this session (Phase B affected subject attachment)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Subject | Preserve direct authored act ownership despite a later companion; retain reports of others | Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_subject_attachment.py, tests/conftest.py | uncommitted | D-077 |

Clause attribution uses existing event positions/direct reflexive ownership before generic third-party mention. A companion does not acquire ownership of the author's act; reports of the other's own intent remain another_person. This occurs before context fusion and subject-aware support. Standalone engine tests do not load API/models solely for unused rate isolation.

## Changes in this session (Phase A/G measurement denominators)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Evaluation | Report exact subject assertion denominator and benign clarification/abstention separately | scripts/run_safety_corpus.py, tests/test_corpus_runner.py | uncommitted | D-078 |

`build_report` aggregates actual outputs, preserving original labels/rows. `print_coverage` uses subject_asserted_cases rather than all inputs. Benign actual-route counts and clarification/UNKNOWN IDs accompany urgent false escalations; UNKNOWN is not counted as successful benign understanding. Historical reports remain preserved with their earlier formatting.

## Changes in this session (Phase C/E deadline/configuration contract)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Runtime config | Validate provider deadline; expose actual character/byte/threshold/policy/schema config; observe late exceptions | api/db.py, api/api.py, api/execution.py, tests/test_runtime_routes.py | uncommitted | D-079 |

`SupabaseClient.__init__` rejects nonfinite/out-of-range timeout configuration. Public `/configuration` returns the initialized input cap and actual nullable urgency threshold, schema/policy and semantic disabled status without private analysis. Prediction/save deadlines preserve existing 503 versus200/unconfirmed behavior; late thread exceptions are observed without raw exception logging. Actual slow-function route tests distinguish inference timeout from uncertain save acknowledgement.

## Changes in this session (Phase D/E deployment preparation)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Container | Install tested transport pins with ML pins, Python3.12, checked build-time resources and readiness JSON; no env file copied | Dockerfile, api/requirements-runtime.txt, api/requirements.txt | uncommitted | D-080 |
| Database | Fresh/additive nullable snapshot/condition,100000 hard cap, explicit server operation grants | supabase/schema.sql, supabase/migrations/20261008_authoritative_analysis.sql, docs/SUPABASE.md | uncommitted | D-080 |

Future image build installs runtime dependencies and NLTK resources before serving; no request downloads resources. Healthcheck consumes /ready JSON instead of treating every /health200 as healthy. Build is not executed: Docker tooling missing. Isolated SQL application must precede authoritative inserts; API effective cap<=100000 and storage hard bound100000 preserve full text. Server key bypasses RLS, so owner scoping remains required despite explicit grants. Fresh schema alone does not migrate existing tables. No migration/deployment ran.

## Changes in this session (Phase B limited language capability)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Language | Heuristic reports degraded; recognized supported danger survives mixed unsupported text; explicit homoglyph limitation | Step 12 - Packaging/package/mental_health_screening/safety.py, tests/test_language_capability.py, tests/test_safety_contract.py, scripts/generate_contract_fixtures.py, tests/contract/analysis-v1.json | uncommitted | D-081 |

After minimal normalization, `detect_language_support` supplies fallible degraded/unsupported capability. Unsupported material no longer returns before independent checks. Recognized supported danger retains its level/subject with unsupported assessment; no recognized concern becomes UNKNOWN/unsupported. Optional models/fusion follow without claiming complete comprehension. Original recovered-context NONE expectation remains; its obsolete complete-capability assertion is preserved/reviewed separately and corrected to degraded. No broad folding/translation or conversation memory is added.

## Changes in this session (Phase B optional measurements)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Processing | Propagate contraction faults; reject nonfinite primary measurements; preserve independent/urgency scopes | Step 12 - Packaging/package/mental_health_screening/preprocessing.py, Step 12 - Packaging/package/mental_health_screening/inference.py, tests/test_optional_measurement_failures.py | uncommitted | D-082 |

`safe_fix` now propagates failure to guarded preprocessing; failed expansion gives null cleaned/lemmatized observations and unavailable optional tracks. Primary feature construction rejects nonfinite measurements under its own catch; urgency remains independent when preprocessing succeeded. No historical training/consumed results are rewritten.

## Changes in this session (Phase E existing-host entrypoint)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Hosting | Explicit repository-root backend/main:app, same app at/api, checked build resources and bundle paths | main.py, requirements.txt, scripts/prepare_runtime_resources.py, vercel.json, api/body_limit.py, api/api.py, .gitignore, scripts/source_fingerprint.py, tests/test_hosting_entrypoint.py, docs/SUPABASE.md | uncommitted | D-083 |

Vercel's prepared service configuration routes original /api paths to `main.app`, mounting the same `api.api.app` with its authentication/contracts/storage. Body byte middleware accounts for mounted root_path. Build script installs NLTK resources and records content hashes before deployment; request code only reads them. Backend root contains actual model package, explicit bundle excludes sensitive environment/development/research paths. Web service remains unchanged. Local mount tests use actual model/ASGI and synthetic provider transport; Vercel/Docker/deployed smoke not claimed. No deployment ran.

## Changes in this session (Phase E resource staging correction)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Build resources | Private home staging satisfies NLTK download security; copy public files and hash output | scripts/prepare_runtime_resources.py | uncommitted | D-084 |

Explicit installer creates a private home staging directory, checks downloads, copies resource data to build output and records hashes. No NLTK security bypass or workspace permission change occurs. An approved isolated private-output installation completed; container/platform build remains unrun. Serving never imports/invokes the installer.

## Changes in this session (Phase E runtime measurements)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Measurement | Explicit concurrent authenticated ASGI/model experiment with stubbed provider and isolated limit state | scripts/measure_api_runtime.py, reports/runtime-asgi-20261008T184440Z.json | uncommitted | D-085 |

The measurement script explicitly installs synthetic provider transport, initializes the real service, measures one cold inference and24 warm requests with concurrency4 through the actual authenticated route. It records status/safety/save acknowledgements, source hashes, quantile method and peak process memory. Runtime request implementation is unchanged. Isolated NLTK resource inference separately retains original raw values/HIGH. This is single-process local evidence, not container/deployed/provider/clinical validation.

## Changes in this session (Phase F entry gate)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Integration boundary | Freeze backend schema1.0/fixtures, preserve frontend source checkpoint and allow narrowly scoped behavioral wiring | reports/frontend-integration-start.json, decisions.md, flow.md | uncommitted | D-086 |

PhaseF development now connects existing app to the stable backend contract; visual/navigation/login design remains unchanged. Backend response -> generated types -> one support view adapter -> current result/history is the permitted next flow. Actual browser consumer remains unmodified at this gate and acceptance is pending. Real external Supabase/container/platform/distributed ingress/qualified validation blockers remain explicit. No release/deployment is authorized or claimed.

## Changes in this session (Phase F contract/transport boundary)

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Types/adapter | Pydantic-derived wire types, runtime invariant parser and one safety/capability/save view adapter | api/contracts.py, api/api.py, scripts/generate_contract_types.py, web/src/lib/contract.ts, web/src/lib/analysisView.ts | uncommitted | D-087 |
| Transport/QA | Validate success/config; respect empty auth; retain body deadline/cancellation/Retry-After; shared state tests | web/src/lib/api.ts, web/scripts/contractqa.mjs, web/package.json | uncommitted | D-087 |

`api.predict` awaits bounded/cancellable `doRequest`, parses schema1.0 and availability/support invariants, then supplies `analysisView`. Raw observations remain unchanged. Invalid HTTP200 is unavailable, never legacy-safe. `api.configuration` validates the actual service cap/threshold. Explicit empty auth headers stay empty for login/refresh. Deadline covers response JSON reading and signal listeners detach on completion; caller cancellation remains distinct from timeout. Shared fixtures exercise actual modules with mocked fetch; Screen/history still need connection and their compiler errors remain visible. Existing ES2020 target/style files retained.

## Changes in this session (Phase F account storage)

Auth `setState` sets `privateStore.setPrivateOwner` before notifying consumers. `history.loadHistory` / `checkin.loadCheckIn` read only identity-qualified keys; anonymous reads return empty. Previous unowned global keys stay untouched and are never guessed to belong to a new visitor. Explicit analysis save validates the full response, stores the authoritative snapshot and returns device-write success separately from account persistence. `mergeAccountHistory` merges the authenticated server core snapshot by row id, preserving local original text when available; cloud-only original text is unknown, legacy rows unassessed, invalid snapshots unavailable. `historyTitle` uses the same `analysisView` adapter as current results. `checkInToText` joins the user's ordered values without inventing subject or current timing; still one manually submitted text field, not conversation memory. Account-switch UI clearing and guarded async retrieval are connected in the following Screen batch.

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Browser private storage | Identity-qualified data, full snapshots, legacy mapping and exact check-in flattening | web/src/lib/privateStore.ts, web/src/lib/history.ts, web/src/lib/checkin.ts, web/src/lib/auth.ts, web/scripts/contractqa.mjs | uncommitted | D-088 |

## Changes in this session (Phase F existing screen)

The unchanged navigation/login routes lead to authenticated `Screen`. It fetches public `api.configuration` for the actual input cap and authenticated `api.screenings` for owner-filtered snapshots. Check-in values prefill only after explicit completion; text is submitted manually. Code-point input length matches Python, excess text is rejected intact rather than truncated. `analyze` captures owner/text/generation, uses cancellable `api.predict`, checks the active owner/generation after completion, then renders `analysisView` safety in the existing result cells and support aside. Raw primary probabilities and urgency probability/actual threshold remain research details, nullable observations show Unavailable. Capability, account acknowledgment and independent device-write status remain visible. No regional resource is guessed from language. Returned guidance is not delayed for animation; in-flight animation is cosmetic. Cancel/reset/unmount/account changes invalidate outstanding state updates. `showRecord` displays the authoritative recorded snapshot/date, restoring exact original local text only if known; it does not reassess or invent current state. Explicit device history clear does not delete server records; that distinction is shown. Failed account retrieval leaves available scoped device history with an honest message. Text/metadata render through React text nodes, never inserted as HTML.

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Existing Screen integration | Authoritative support, nullable/raw details, configured limits, save/history/error and stale/cancel guards | web/src/pages/Screen.tsx, web/scripts/screenqa.mjs, tests/serve_synthetic_api.py | uncommitted | D-089 |

## Changes in this session (Phase F session lifecycle)

Session operations capture an auth generation. `adoptFromApi` sends the candidate token explicitly to `api.session` while the current bearer remains unchanged; only a current, verified identity publishes. SDK sessions use the same backend verification. Publication clears old mirrors, honors remember scope, installs the token and identity-qualified private-store owner before subscribers. Logout invalidates generations, clears mirrors/token/owner and unsubscribes the watcher. Late verification/refresh cannot publish or clear another session. Backend token verification still occurs independently on every private API request.

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Session lifecycle | Guard delayed adoption/logout/refresh and verify candidate without global token mutation | web/src/lib/auth.ts, web/src/lib/api.ts, web/scripts/contractqa.mjs | uncommitted | D-090 |

## Changes in this session (Phase F contract CLI)

`generate_contract_types.py` resolves its root from its own location before importing `api.contracts`; generation/check writes or compares the repository's `web/src/lib/contract.ts` regardless of invocation directory. It imports no inference model or optional NLP path. Direct documented --check is now verified.

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Contract tooling | Resolve repository import/output paths in direct drift command | scripts/generate_contract_types.py | uncommitted | D-091 |

## Changes in this session (Phase D real-integration preparation)

`scripts/verify_supabase_isolated.py --check-config` checks only explicit MENTAL_AI_TEST_* names and isolation assertion. Missing config exits2 with BLOCKED, without importing service or network. A separately invoked configured run verifies pre-provisioned expected identities, then real synthetic authenticated API/model saves/read-back plus direct unprivileged PostgREST RLS and refresh. Cleanup uses only newly acknowledged id/owner pairs; no existing history is bulk-deleted, no migration/account/email operation performed. Real remote execution remains BLOCKED; preparation and configuration checking are not connectivity evidence.

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Isolated integration harness | Explicit external-input gate and scoped real-provider procedure | scripts/verify_supabase_isolated.py | uncommitted | D-092 |

## Changes in this session (Phase D provider key compatibility)

`SupabaseClient._headers` puts new sb_publishable_/sb_secret_ keys only in apikey, preserving bearer fallback for legacy JWT keys. `_call(access_token=...)` installs the verified user's bearer in a new local header dict; client reuse does not mutate a shared session token. Privileged data calls still require explicit application owner filters because secret keys bypass RLS. Transport-only captured header tests pass; actual remote behavior remains blocked.

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| Provider headers | Separate new non-JWT application keys from user/legacy bearer tokens | api/db.py, tests/test_provider_key_headers.py | uncommitted | D-093 |

## Changes in this session (Phase B/F generic support)

Current `support_action` HIGH copy describes serious concern without inferring self-harm from the route alone. It gives urgent trusted-person/local-emergency guidance and help locating support without promising a country conversation. Policy version .6 identifies this copy change; no classifier/routing vocabulary changed. Historic .5 snapshots remain authoritative for their recorded time. Current shared fixture generation uses the new template.

| Area | Change | Files | Commit | Decision |
|---|---|---|---|---|
| HIGH support | Remove invented harm-kind attribution and unimplemented country conversation promise | mental_health_screening/safety.py, tests/test_support_contract_invariants.py, tests/contract/analysis-v1.json | uncommitted | D-094 |
