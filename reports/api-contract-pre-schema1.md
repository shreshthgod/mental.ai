# Current API contract: diagnostic map

Inspected 2026-10-08. This documents the implementation, not a frozen Phase C contract. Current response lacks schema_version, explicit component/capability statuses, artifact/threshold fingerprints and persistence status. `SafetyResult` uses unrestricted strings. Those are open requirements.

`POST /predict` accepts one text field with bearer authentication. `PredictRequest._check_text` rejects whitespace and applies `max_text_length`; the Field still imposes a fixed 10,000 cap even when configuration is larger. Extra fields cannot override token identity. No conversation-memory schema exists.

| Field | Produced by | Validated by | Stored by | Consumed by | Failure behavior |
|---|---|---|---|---|---|
| request_id | api.api.add_request_id | no header validation yet | api.db.record_screening request_id | api.ts / Screen.tsx | supplied header currently accepted unchecked |
| safety | inference.MentalHealthScreener.screen / safety.evaluate | api.api.SafetyResult | NOT STORED (defect) | ignored by current frontend (defect) | engine error UNKNOWN/unavailable; optional error preserves known HIGH |
| safety.support_action | safety.support_action inside screen | optional str, no semantic invariant | NOT STORED | ignored by frontend | another_person receives guidance for them |
| primary | screen primary try block | api.api.PrimaryResult | raw label/probabilities, unavailable label currently str(None) (defect) | prominent condition headline (defect) | null class / empty probabilities / unavailable |
| urgency | screen urgency try block | api.api.UrgencyResult | urgency label/probability/flag/threshold | raw urgency presentation | null class/probability and unavailable; frontend currently treats false as Not elevated (defect) |
| cleaned_text / lemmatized_text | lazy optional preprocessing | optional strings | same columns | declared, not rendered | null on preprocessing failure; must only render as text |
| provenance_caveat | packaged config | optional string | same column | provenance block | no clinical validation claim |
| service_version | api.api.SERVICE_VERSION | string | same column | request metadata | default 0.1.0 |

Current storage uses privileged PostgREST calls. RLS does not constrain that key: application owner filters matter. `list_screenings` and `delete_screenings` explicitly use verified claims.user_id. Stub tests exercise these filters; actual RLS/network/schema/grants remain unverified.

No failed write status reaches the browser. `_persist_screening` logs provider failures, leaving support output intact, but the user cannot tell whether it was saved. This contract must change additively and persist a complete authoritative snapshot before frontend integration.

## Schema 1.0 implementation (D-063)

The response definitions now live in `api/contracts.py`, re-exported by `api/api.py`. Successful responses add schema_version=1.0, model_version (raw model/vectorizer/selector/config SHA-256 identity), components and safety.assessment_scope. Strict enums and availability/probability invariants apply. `AnalysisResult` defines the snapshot core; `PredictResponse` adds explicit persistence status saved/not_saved/unconfirmed. Phase D must connect real save acknowledgement and history; default is not_saved, never an implicit save claim. Frontend shared fixtures/drift and storage tests remain pending; this does not declare all contract gates complete.
