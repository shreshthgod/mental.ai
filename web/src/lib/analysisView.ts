import type { AnalysisResult, ConfigurationResponse, PredictResponse, SafetyResult } from "./contract";

function ensure(condition: unknown): asserts condition {
  if (!condition) throw new Error("Unsupported or inconsistent analysis contract");
}
function object(value: unknown): Record<string, unknown> {
  ensure(value !== null && typeof value === "object" && !Array.isArray(value));
  return value as Record<string, unknown>;
}
function probability(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1;
}
function oneOf(value: unknown, choices: string[]): boolean {
  return typeof value === "string" && choices.includes(value);
}

/** Validate the wire state; this does not classify or reinterpret disclosure text. */
export function parseAnalysis(value: unknown): AnalysisResult {
  const result = object(value);
  ensure(result.schema_version === "1.0");
  ensure(typeof result.request_id === "string" && /^[A-Za-z0-9_.-]{1,64}$/.test(result.request_id));
  for (const key of ["model_version", "service_version"]) ensure(typeof result[key] === "string" && result[key]);
  for (const key of ["cleaned_text", "lemmatized_text", "provenance_caveat"]) ensure(result[key] === null || typeof result[key] === "string");
  const safety = object(result.safety), components = object(result.components);
  const primary = object(result.primary), urgency = object(result.urgency);
  ensure(oneOf(safety.level, ["NONE_DETECTED", "NEEDS_CLARIFICATION", "CONCERNING", "HIGH", "IMMEDIATE", "UNKNOWN"]));
  ensure(oneOf(safety.subject, ["self", "another_person", "fictional_or_quoted", "unclear"]));
  ensure(oneOf(safety.temporal_context, ["current", "recent", "historical", "hypothetical", "unclear"]));
  ensure(oneOf(safety.immediacy, ["stated", "not_stated", "unclear"]));
  ensure(oneOf(safety.analysis_status, ["complete", "degraded", "unavailable", "unsupported"]));
  ensure(oneOf(safety.language_support, ["complete", "degraded", "unavailable", "unsupported", "unknown"]));
  ensure(oneOf(safety.assessment_scope, ["recognized_rules_only", "validated_semantic_and_rules", "unavailable"]));
  ensure(typeof safety.needs_clarification === "boolean" && typeof safety.review_recommended === "boolean");
  ensure(Array.isArray(safety.evidence_codes) && safety.evidence_codes.every(v => typeof v === "string"));
  ensure(typeof safety.summary === "string" && typeof safety.policy_version === "string" && safety.policy_version);
  ensure(typeof safety.support_action === "string" && safety.support_action.trim());
  const action = safety.support_action.toLowerCase();
  ensure(!["nothing to worry", "you're fine", "all clear", "no risk", "you have depression", "you are bipolar", "you have schizophrenia", "clinically normal", "you are suicidal"].some(v => action.includes(v)));
  if (["HIGH", "IMMEDIATE"].includes(String(safety.level))) {
    ensure(safety.review_recommended && ["emergency", "crisis", "trust", "urgent"].some(v => action.includes(v)));
  }
  if (["UNKNOWN", "NEEDS_CLARIFICATION"].includes(String(safety.level))) ensure(safety.needs_clarification);
  if (safety.level === "NEEDS_CLARIFICATION") ensure(action.includes("?"));
  if (safety.level === "NONE_DETECTED") ensure(!["unavailable", "unsupported"].includes(String(safety.analysis_status)));
  if (safety.subject === "another_person" && safety.level !== "NONE_DETECTED") ensure(!action.includes("harming yourself") && !action.includes("harm yourself"));
  for (const key of ["independent_safety", "preprocessing", "primary", "urgency"]) ensure(oneOf(components[key], ["complete", "unavailable"]));
  ensure(oneOf(components.semantic, ["complete", "disabled", "unavailable"]));
  ensure(primary.status === components.primary && urgency.status === components.urgency);
  if (safety.analysis_status === "complete") ensure(Object.values(components).every(v => v === "complete"));
  const probabilities = object(primary.class_probabilities);
  if (primary.status === "unavailable") ensure(primary.predicted_class === null && Object.keys(probabilities).length === 0);
  else {
    ensure(typeof primary.predicted_class === "string" && Object.prototype.hasOwnProperty.call(probabilities, primary.predicted_class));
    const values = Object.values(probabilities);
    ensure(values.length && values.every(probability));
    ensure(Math.abs(values.reduce<number>((sum, v) => sum + Number(v), 0) - 1) <= 1e-5);
  }
  const threshold = urgency.decision_threshold_used;
  ensure(probability(threshold) && threshold > 0 && typeof urgency.flagged === "boolean");
  if (urgency.status === "unavailable") ensure(urgency.predicted_class === null && urgency.suicide_probability === null && !urgency.flagged);
  else {
    ensure(probability(urgency.suicide_probability));
    const flag = urgency.suicide_probability >= threshold;
    ensure(urgency.flagged === flag && urgency.predicted_class === (flag ? "suicide" : "non-suicide"));
  }
  return value as AnalysisResult;
}

export function parsePrediction(value: unknown): PredictResponse {
  parseAnalysis(value);
  const persistence = object(object(value).persistence);
  ensure(oneOf(persistence.status, ["saved", "not_saved", "unconfirmed"]));
  ensure(persistence.record_id === null || (typeof persistence.record_id === "string" && persistence.record_id.length > 0));
  ensure((persistence.status === "saved") === (persistence.record_id !== null));
  return value as PredictResponse;
}

export function parseConfiguration(value: unknown): ConfigurationResponse {
  const data = object(value);
  ensure(data.schema_version === "1.0" && data.semantic_status === "disabled");
  ensure(typeof data.max_text_length === "number" && Number.isInteger(data.max_text_length) && data.max_text_length >= 1000 && data.max_text_length <= 100000);
  ensure(data.max_body_bytes === data.max_text_length * 12 + 4096);
  ensure(data.urgency_threshold === null || (probability(data.urgency_threshold) && data.urgency_threshold > 0));
  ensure(data.policy_version === null || typeof data.policy_version === "string");
  return value as ConfigurationResponse;
}

const TITLES: Record<SafetyResult["level"], string> = {
  NONE_DETECTED: "No concern detected", NEEDS_CLARIFICATION: "More information needed",
  CONCERNING: "Support recommended", HIGH: "Urgent support", IMMEDIATE: "Immediate support",
  UNKNOWN: "Assessment uncertain",
};

/** One authoritative response-to-view adapter for current and saved results. */
export function analysisView(result: AnalysisResult | PredictResponse) {
  const safety = result.safety;
  const capability = {
    complete: ["Assessment available", "This support state is a screening result, not a diagnosis or confirmation of safety."],
    degraded: ["Limited assessment", "This is a limited text assessment. It may miss meaning, context, or concern."],
    unsupported: ["Unsupported analysis", "Some text is outside supported language checks. Any detected concern still warrants the guidance shown."],
    unavailable: ["Analysis unavailable", "The text could not be assessed reliably. No safety conclusion is available."],
  }[safety.analysis_status];
  const persistence = "persistence" in result ? result.persistence : null;
  const saving = persistence === null ? null : {
    saved: "Saved to your account history.",
    not_saved: "Not saved to your account. This support result is still available here.",
    unconfirmed: "Saving could not be confirmed. Check your account history before submitting again.",
  }[persistence.status];
  return {
    title: TITLES[safety.level], level: safety.level,
    urgent: safety.level === "HIGH" || safety.level === "IMMEDIATE",
    subject: safety.subject, temporalContext: safety.temporal_context, immediacy: safety.immediacy,
    capabilityTitle: capability[0], capabilityMessage: capability[1],
    supportAction: safety.support_action, savingMessage: saving,
    primaryLabel: result.primary.status === "unavailable" ? "Unavailable" : result.primary.predicted_class,
    urgencyLabel: result.urgency.status === "unavailable" ? "Unavailable" : result.urgency.flagged ? "Flagged (raw model)" : "Not flagged (raw model)",
    urgencyProbability: result.urgency.suicide_probability,
    urgencyThreshold: result.urgency.decision_threshold_used,
  };
}

export function formatProbability(value: number | null): string {
  return value === null ? "Unavailable" : `${(value * 100).toFixed(1)}%`;
}

export function analysisErrorView(error: unknown): { title: string; body: string; meta?: string } {
  const data = error && typeof error === "object" ? error as Record<string, unknown> : {};
  const meta = typeof data.requestId === "string" ? `request ${data.requestId}` : undefined;
  if (data.name === "AbortError") return { title: "Analysis cancelled", body: "The request was cancelled before a result was returned." };
  if (data.kind === "unauthorized") return { title: "Session expired", body: "Sign in again to continue.", meta };
  if (data.kind === "throttled") return { title: "Please wait before trying again", body: typeof data.retryAfterSeconds === "number" ? `Try again in ${data.retryAfterSeconds} seconds.` : "The request limit was reached. Please try again later.", meta };
  if (data.kind === "validation") return { title: "Check the text", body: typeof data.message === "string" ? data.message : "The supplied text was rejected.", meta };
  if (data.kind === "timeout") return { title: "Analysis timed out", body: "No assessment result was returned. If anyone is in immediate danger, contact their local emergency service.", meta };
  return { title: "Analysis unavailable", body: "No assessment result is available. If anyone is in immediate danger, contact their local emergency service or someone they trust.", meta };
}
