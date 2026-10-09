# Current internal API contract

Schema 1.0 is implemented in `api/contracts.py` and exposed by OpenAPI. Shared frontend fixtures and final contract freeze remain IN_PROGRESS. No independent clinical validity is claimed. Prior diagnostic map is preserved in reports/api-contract-pre-schema1.md.

Authenticated `POST /predict` accepts one `text` string. `PredictRequest._check_text` rejects blank input and decoded text above `max_text_length()` (default 10000). The same configured cap initializes `MentalHealthScreener`. HTTP bytes are bounded before JSON parsing at 12 times the character cap plus 4096 wrapper bytes, accommodating escaped Unicode scalars. No text is truncated. Body user_id cannot override verified identity. No structured conversation memory exists.

| Field | Produced by | Validated by | Stored by | Consumed by | Failure behavior |
|---|---|---|---|---|---|
| schema_version | AnalysisResult default 1.0 | Literal 1.0 | analysis_result JSONB | API/OpenAPI/history; frontend pending | Unsupported version rejected |
| request_id | api.api.add_request_id | ASCII whitelist and AnalysisResult pattern | row and snapshot | response/header/diagnostics | Invalid supplied ID replaced; no control characters logged |
| safety | safety.evaluate then fusion.fuse | SafetyResult enums/availability/review invariants | validated snapshot | API/history; Screen.tsx still ignores (open defect) | Rule failure UNKNOWN/unavailable; reliable HIGH survives optional failure |
| safety.support_action | safety.support_action inside fuse | Required nonempty string; semantic wording validation pending | snapshot | frontend pending | Subject-aware guidance; no notification claim |
| components | fusion.fuse | Components and AnalysisResult agreement | snapshot | diagnostics; frontend pending | disabled/unavailable separate from negative observation |
| safety.assessment_scope | fusion.fuse | Literal | snapshot | diagnostics; frontend pending | Production recognized_rules_only; semantic disabled |
| primary | guarded primary track | PrimaryResult finite distribution/sum/label/status | nullable raw label and snapshot | raw headline (open defect) | Null class, empty probabilities, unavailable; no str(None) |
| urgency | guarded urgency track | UrgencyResult probability/threshold/label/flag/status | raw fields and snapshot | raw urgency view (open defect) | Null class/probability, false compatibility flag, unavailable; false must not mean measured negative |
| model_version | startup content fingerprint | Required string | snapshot | diagnostics; frontend pending | Hashes config, raw models/vectorizers/selector/configured lexicons; missing files null in manifest |
| safety.policy_version | safety.POLICY_VERSION | Required string | snapshot | diagnostics | Source fingerprints distinguish uncommitted intermediate states |
| cleaned_text / lemmatized_text | optional preprocessing | Nullable strings | columns and snapshot | Declared, not rendered | Null on failure; render only as text |
| provenance_caveat / service_version | actual config/API | Nullable/required strings | row and snapshot | provenance/metadata | No clinical diagnosis claim |
| persistence | _persist_screening and bounded save lane | PersistenceResult status/id invariant | Not in immutable core | frontend pending | Returned id: saved; rejected/unadmitted: not_saved; uncertain/timeout: unconfirmed |

`AnalysisResult` defines the stored core; `PredictResponse` adds transient acknowledgement. `ScreeningSummary.analysis_result` validates the same core. NULL snapshot means legacy_unassessed; malformed snapshot makes history unavailable (503). Additive migration `supabase/migrations/20261008_authoritative_analysis.sql` is prepared, **not applied remotely**.

Privileged PostgREST operations may bypass RLS. Inserts use verified claims.user_id; history/deletion explicitly filter that owner. Real schema/grants/RLS/auth/network isolation remain BLOCKED on an isolated configured project and two provisioned identities. Tests use the real route/models and provider transport stubs.

Errors retain FastAPI's `detail` envelope: 401 authentication; 413 body bytes; 422 input; 429 owner limit with Retry-After; 503 auth/capacity/deadline/store/readiness unavailable; 500 invalid/unexpected prediction. No model result is fabricated for errors. Support survives rejected/unconfirmed saves as HTTP 200 with persistence state.

Prediction: one serial worker/eight admitted jobs/30-second caller deadline. Saving: separate serial worker/eight jobs/12-second deadline. Timeout/cancellation does not terminate synchronous work or release its slot early. Local workers share SQLite limits (30/60s); separate hosts require shared ingress limits. `/live` is cheap; `/ready` publishes ten-second probe age/TTL and optional degradation.
