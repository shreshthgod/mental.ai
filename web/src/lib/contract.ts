// Contract types from api/contracts.py; refresh with scripts/generate_contract_types.py.
// Successful wire responses serialize defaults, so every declared field is present.

export interface AnalysisResult {
  schema_version: "1.0";
  request_id: string;
  safety: SafetyResult;
  components: Components;
  primary: PrimaryResult;
  urgency: UrgencyResult;
  model_version: string;
  cleaned_text: string | null;
  lemmatized_text: string | null;
  provenance_caveat: string | null;
  service_version: string;
}

export interface Components {
  independent_safety: "complete" | "unavailable";
  semantic: "complete" | "disabled" | "unavailable";
  preprocessing: "complete" | "unavailable";
  primary: "complete" | "unavailable";
  urgency: "complete" | "unavailable";
}

export interface ConfigurationResponse {
  schema_version: "1.0";
  max_text_length: number;
  max_body_bytes: number;
  urgency_threshold: number | null;
  policy_version: string | null;
  semantic_status: "disabled";
}

export interface PersistenceResult {
  status: "saved" | "not_saved" | "unconfirmed";
  record_id: string | null;
}

export interface PredictResponse {
  schema_version: "1.0";
  request_id: string;
  safety: SafetyResult;
  components: Components;
  primary: PrimaryResult;
  urgency: UrgencyResult;
  model_version: string;
  cleaned_text: string | null;
  lemmatized_text: string | null;
  provenance_caveat: string | null;
  service_version: string;
  persistence: PersistenceResult;
}

export interface PrimaryResult {
  predicted_class: string | null;
  class_probabilities: Record<string, number>;
  status: "complete" | "unavailable";
}

export interface SafetyResult {
  level: "NONE_DETECTED" | "NEEDS_CLARIFICATION" | "CONCERNING" | "HIGH" | "IMMEDIATE" | "UNKNOWN";
  subject: "self" | "another_person" | "fictional_or_quoted" | "unclear";
  temporal_context: "current" | "recent" | "historical" | "hypothetical" | "unclear";
  immediacy: "stated" | "not_stated" | "unclear";
  evidence_codes: Array<string>;
  summary: string;
  needs_clarification: boolean;
  review_recommended: boolean;
  analysis_status: "complete" | "degraded" | "unavailable" | "unsupported";
  policy_version: string;
  language_support: "complete" | "degraded" | "unavailable" | "unsupported" | "unknown";
  assessment_scope: "recognized_rules_only" | "validated_semantic_and_rules" | "unavailable";
  support_action: string;
}

export interface UrgencyResult {
  predicted_class: "suicide" | "non-suicide" | null;
  suicide_probability: number | null;
  decision_threshold_used: number;
  flagged: boolean;
  status: "complete" | "unavailable";
}
