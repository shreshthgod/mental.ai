# Current internal API contract

Schema 1.0 is implemented in `api/contracts.py` and exposed by OpenAPI. The schema1.0 fields are frozen for existing-app development integration (D-086); shared Python/API/TypeScript/browser fixtures and type drift checks are implemented. No independent clinical validity is claimed. Prior diagnostic map is preserved in reports/api-contract-pre-schema1.md.

Authenticated `POST /predict` accepts one `text` string. `PredictRequest._check_text` rejects blank input and decoded text above `max_text_length()` (default 10000). The same configured cap initializes `MentalHealthScreener`. HTTP bytes are bounded before JSON parsing at 12 times the character cap plus 4096 wrapper bytes, accommodating escaped Unicode scalars. No text is truncated. Body user_id cannot override verified identity. No structured conversation memory exists.

| Field | Produced by | Validated by | Stored by | Consumed by | Failure behavior |
|---|---|---|---|---|---|
| schema_version | AnalysisResult default 1.0 | Literal 1.0 | analysis_result JSONB | API/OpenAPI/history; generated web/src/lib/contract.ts | Unsupported version rejected |
| request_id | api.api.add_request_id | ASCII whitelist and AnalysisResult pattern | row and snapshot | response/header/diagnostics | Invalid supplied ID replaced; no control characters logged |
| safety | safety.evaluate then fusion.fuse | SafetyResult enums/availability/review invariants | validated snapshot | web/src/lib/analysisView.ts -> Screen.tsx and history.ts | Rule failure UNKNOWN/unavailable; reliable HIGH survives optional failure |
| safety.support_action | safety.support_action inside fuse | Required nonempty/actionable string; specific prohibited wording checks (not complete semantic validation) | snapshot | analysisView/Screen/history | Subject-aware guidance; no notification claim |
| components | fusion.fuse | Components and AnalysisResult agreement | snapshot | diagnostics; analysisView/Screen/history | disabled/unavailable separate from negative observation |
| safety.assessment_scope | fusion.fuse | Literal | snapshot | diagnostics; analysisView/Screen/history | Production recognized_rules_only; semantic disabled |
| primary | guarded primary track | PrimaryResult finite distribution/sum/label/status | nullable raw label and snapshot | research details only | Null class, empty probabilities, unavailable; no str(None) |
| urgency | guarded urgency track | UrgencyResult probability/threshold/label/flag/status | raw fields and snapshot | nullable research details/actual threshold | Null class/probability, false compatibility flag, unavailable; false must not mean measured negative |
| model_version | startup content fingerprint | Required string | snapshot | diagnostics; analysisView/Screen/history | Hashes config, raw models/vectorizers/selector/configured lexicons; missing files null in manifest |
| safety.policy_version | safety.POLICY_VERSION | Required string | snapshot | diagnostics | Source fingerprints distinguish uncommitted intermediate states |
| cleaned_text / lemmatized_text | optional preprocessing | Nullable strings | columns and snapshot | Declared, not rendered | Null on failure; render only as text |
| provenance_caveat / service_version | actual config/API | Nullable/required strings | row and snapshot | provenance/metadata | No clinical diagnosis claim |
| persistence | _persist_screening and bounded save lane | PersistenceResult status/id invariant | Not in immutable core | analysisView/Screen/history | Returned id: saved; rejected/unadmitted: not_saved; uncertain/timeout: unconfirmed |

`AnalysisResult` defines the stored core; `PredictResponse` adds transient acknowledgement. `ScreeningSummary.analysis_result` validates the same core. NULL snapshot means legacy_unassessed; malformed snapshot makes history unavailable (503). Additive migration `supabase/migrations/20261008_authoritative_analysis.sql` is prepared, **not applied remotely**.

Privileged PostgREST operations may bypass RLS. Inserts use verified claims.user_id; history/deletion explicitly filter that owner. Real schema/grants/RLS/auth/network isolation remain BLOCKED on an isolated configured project and two provisioned identities. Tests use the real route/models and provider transport stubs.

Errors retain FastAPI's `detail` envelope: 401 authentication; 413 body bytes; 422 input; 429 owner limit with Retry-After; 503 auth/capacity/deadline/store/readiness unavailable; 500 invalid/unexpected prediction. No model result is fabricated for errors. Support survives rejected/unconfirmed saves as HTTP 200 with persistence state.

Prediction: one serial worker/eight admitted jobs/30-second caller deadline. Saving: separate serial worker/eight jobs/12-second deadline. Timeout/cancellation does not terminate synchronous work or release its slot early. Local workers share SQLite limits (30/60s); separate hosts require shared ingress limits. `/live` is cheap; `/ready` publishes ten-second probe age/TTL and optional degradation.

## Existing consumers and shared fixtures

`api/contracts.py` is the schema source. `scripts/generate_contract_types.py --check` detects generated type drift. `web/src/lib/analysisView.ts` validates wire enums, availability, probabilities, support and acknowledgment invariants before mapping all current/recorded states. `Screen` uses safety for the headline; Normal never supplies a safety conclusion. Nullable observations show Unavailable, never zero/Not elevated. Current support copy is policy .6; saved .5 snapshots retain their recorded meaning. Runtime validation checks known invariants, not every possible unsafe statement.

`tests/contract/analysis-v1.json` supplies16 success states and3 errors to Python/core storage, real route with explicit inference overrides, actual frontend modules and browser rendering. Pending save is NOT_APPLICABLE: there is no durable async mechanism. Current account reads reconstruct saved acknowledgment only for a returned stored row. Browser history stores the complete validated response, and cloud merging preserves local original text only by row id; unknown original text remains null. Legacy/unassessed and malformed/unavailable are distinct. Private browser keys follow verified identity, and generation guards prevent old analysis/auth work replacing a new session or result.

Prediction fetch deadline80s includes maximum auth/provider30s + inference30s + save12s and margin; auth/history35s, configuration/health8s. No client automatic retry. UI code-point limits derive from `/configuration`; excess text is kept intact and blocked. Account/device saving statuses and device-only clearing semantics are explicit. Generic failure guidance does not claim an assessment or unauthenticated analysis.
