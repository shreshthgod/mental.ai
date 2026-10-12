/** Local English safety rules; trained browser classifiers are unavailable. */

import type { PredictResponse } from "./contract";

export type SafetyLevel =
  | "NONE_DETECTED"
  | "NEEDS_CLARIFICATION"
  | "CONCERNING"
  | "HIGH"
  | "IMMEDIATE"
  | "UNKNOWN";

export type Subject = "self" | "another_person" | "fictional_or_quoted" | "unclear";
export type TemporalContext = "current" | "recent" | "historical" | "hypothetical" | "unclear";
export type Immediacy = "stated" | "not_stated" | "unclear";

export interface OnDeviceSafetyResult {
  level: SafetyLevel;
  subject: Subject;
  temporal_context: TemporalContext;
  immediacy: Immediacy;
  evidence_codes: string[];
  summary: string;
  needs_clarification: boolean;
  review_recommended: boolean;
  analysis_status: "complete" | "degraded" | "unavailable" | "unsupported";
  policy_version: string;
  language_support: "complete" | "degraded" | "unavailable" | "unsupported" | "unknown";
  assessment_scope: "recognized_rules_only" | "validated_semantic_and_rules" | "unavailable";
  support_action: string;
}

export interface OnDeviceEmotionCue {
  name: string;
  confidence: null;
  description: string;
}

export interface OnDeviceEmotionResult {
  status: "disabled";
  model_version: "emotion-unavailable-v1";
  emotions: OnDeviceEmotionCue[];
  dominant_emotion: string | null;
  first_person: boolean;
  clinical_distinction_advisory: string;
  uninferrable_limitations: string[];
}

export interface OnDevicePredictResponse extends PredictResponse {
  mode: "on_device_private";
  emotion: OnDeviceEmotionResult;
  privacy_guarantee: string;
}


const TENTH_FLOOR_CRISIS_REGEX =
  /\b(jump(ing)?\s+(off|from)\s+(the\s+)?(10th|\d+th)?\s*(floor|building|bridge|roof|balcony)|kill\s+(my|one)?self|end\s+my\s+life|hang\s+(my|one)?self|shoot\s+(my|one)?self|overdose|slit\s+(my|one)?\s*wrists?|suicide|die\s+by\s+suicide|want\s+to\s+die|wanna\s+die)\b/i;

const SELF_HARM_REGEX =
  /\b(cut(ting)?\s+myself|hurt(ing)?\s+myself|burning\s+myself|self[\s-]harm|bleed(ing)?\s+on\s+purpose)\b/i;

const THIRD_PERSON_REGEX =
  /\b(my\s+friend|my\s+brother|my\s+sister|my\s+mother|my\s+father|my\s+partner|my\s+roommate|someone\s+i\s+know|he\s+wants\s+to|she\s+wants\s+to|they\s+want\s+to|friend\s+is\s+talking\s+about\s+ending)\b/i;

const HISTORICAL_REGEX =
  /\b(years\s+ago|back\s+in\s+\d{4}|when\s+i\s+was\s+(younger|a\s+teen|a\s+kid)|used\s+to\s+(feel|think|cut|attempt)|in\s+the\s+past|survived\s+an\s+attempt)\b/i;

const QUOTATION_OR_FICTION_REGEX =
  /\b(in\s+the\s+book|in\s+the\s+movie|the\s+character|lyrics|song\s+said|he\s+said\s+["']|she\s+said\s+["']|quote|reading\s+a\s+story)\b/i;

const IMMEDIATE_PLAN_REGEX =
  /\b(tonight|right\s+now|goodbye\s+note|goodbye\s+letter|final\s+letter|already\s+taken|have\s+the\s+pills|ready\s+to\s+jump)\b/i;

export function evaluateOnDeviceSafety(text: string): OnDeviceSafetyResult {
  const trimmed = text.trim();
  const lower = trimmed.toLowerCase();

  let subject: Subject = /\b(i|me|my|myself)\b/i.test(lower) ? "self" : "unclear";
  if (THIRD_PERSON_REGEX.test(lower)) {
    subject = "another_person";
  } else if (QUOTATION_OR_FICTION_REGEX.test(lower)) {
    subject = "fictional_or_quoted";
  }

  let temporalContext: TemporalContext = "unclear";
  if (HISTORICAL_REGEX.test(lower)) {
    temporalContext = "historical";
  }

  let immediacy: Immediacy = "not_stated";
  if (IMMEDIATE_PLAN_REGEX.test(lower)) {
    immediacy = "stated";
  }

  const hasCrisisTerms = TENTH_FLOOR_CRISIS_REGEX.test(lower);
  const hasSelfHarm = SELF_HARM_REGEX.test(lower);

  const evidenceCodes: string[] = [];

  if (hasCrisisTerms) {
    evidenceCodes.push("EXPLICIT_SUICIDAL_CRISIS_SIGNAL");
  }
  if (hasSelfHarm) {
    evidenceCodes.push("SELF_HARM_MARKER");
  }

  let level: SafetyLevel = "NONE_DETECTED";
  let summary = "No listed safety phrase matched. This does not establish safety.";
  let needsClarification = false;
  let reviewRecommended = false;
  let supportAction =
    "If you are seeking support or feeling stressed, speaking with a supportive friend, counselor, or healthcare professional can be a helpful next step.";

  if (subject === "fictional_or_quoted") {
    level = "NEEDS_CLARIFICATION";
    needsClarification = true;
    summary = "Discussion references fictional, musical, or quoted text regarding distress.";
    supportAction =
      "Your writing appears to reference a fictional or quoted situation. Are you personally safe and feeling okay right now?";
  } else if (subject === "another_person" && (hasCrisisTerms || hasSelfHarm)) {
    level = "HIGH";
    reviewRecommended = true;
    summary = "Severe distress or crisis signals detected regarding another individual.";
    supportAction =
      "If someone you know is in immediate crisis, stay connected with them if safe to do so, and contact local emergency responders or a crisis line together.";
  } else if (temporalContext === "historical" && (hasCrisisTerms || hasSelfHarm)) {
    level = "CONCERNING";
    needsClarification = true;
    reviewRecommended = false;
    summary = "Historical disclosure of severe distress or past self-harm.";
    supportAction =
      "You mentioned past experiences with deep distress. Are you feeling safe and supported today, or are any of those heavy thoughts returning right now?";
  } else if (hasCrisisTerms || hasSelfHarm) {
    level = immediacy === "stated" ? "IMMEDIATE" : "HIGH";
    reviewRecommended = true;
    summary = "Explicit statements of suicidal crisis or intentional self-harm detected.";
    supportAction =
      "If you are in immediate distress or considering ending your life, please reach out to emergency resources right now. You can call or text 988 (in the US & Canada), contact 112 (in Europe), or reach out to trusted local crisis responders immediately.";
  } else if (/\b(hopeless|unbearable|cannot\s+go\s+on|drowning|giving\s+up)\b/i.test(lower)) {
    level = "CONCERNING";
    summary = "Expressions of intense distress or emotional overwhelm.";
    supportAction =
      "You seem to be carrying a heavy emotional load. Consider reaching out to a trusted confidant, doctor, or supportive listener today.";
  }

  const unsupported = Array.from(lower).some(c => c.codePointAt(0)! > 127) || /\b(mujhe|main|nahi|hai|hoon|udaas|zindagi)\b/.test(lower);
  if (unsupported && !hasCrisisTerms && !hasSelfHarm) {
    level = "UNKNOWN";
    needsClarification = true;
    summary = "Language support is unknown or unsupported; these English rules cannot assess this text.";
    supportAction = "Are you safe right now? If anyone is in immediate danger, contact local emergency services.";
  }

  return {
    level,
    subject,
    temporal_context: temporalContext,
    immediacy: immediacy,
    evidence_codes: evidenceCodes,
    summary,
    needs_clarification: needsClarification,
    review_recommended: reviewRecommended,
    analysis_status: unsupported ? "unsupported" : "degraded",
    policy_version: "2026.10-local-rules-v2",
    language_support: unsupported ? "unsupported" : "unknown",
    assessment_scope: "recognized_rules_only",
    support_action: supportAction,
  };
}


export function evaluateOnDeviceEmotions(_text: string): OnDeviceEmotionResult {
  return {
    status: "disabled",
    model_version: "emotion-unavailable-v1",
    emotions: [],
    dominant_emotion: null,
    first_person: false,
    clinical_distinction_advisory: "Emotion classification is unavailable pending independent validation.",
    uninferrable_limitations: ["No emotional state or diagnosis is inferred."],
  };
}

export async function runOnDeviceInference(text: string): Promise<OnDevicePredictResponse> {
  if (!text.trim() || Array.from(text).length > 10000) throw new Error("Enter 1–10,000 characters.");
  return {
    schema_version: "1.0",
    request_id: `local-${crypto.randomUUID()}`,
    safety: evaluateOnDeviceSafety(text),
    emotion: evaluateOnDeviceEmotions(text),
    cleaned_text: null,
    lemmatized_text: null,
    mode: "on_device_private",
    privacy_guarantee: "This analysis runs local rules. Text and embeddings are not uploaded. Authentication and configuration use the network.",
    components: {
      independent_safety: "complete", semantic: "unavailable", preprocessing: "unavailable",
      primary: "unavailable", urgency: "unavailable",
    },
    primary: { predicted_class: null, class_probabilities: {}, status: "unavailable" },
    // The shared v1 contract requires a threshold even when the classifier is absent.
    // It is unused and must not be shown as an active decision threshold.
    urgency: { predicted_class: null, suicide_probability: null, decision_threshold_used: 0.5,
      flagged: false, status: "unavailable" },
    model_version: "no-trained-browser-model-v2",
    service_version: "local-rules-v2",
    provenance_caveat: "Limited English safety rules; trained condition, urgency and emotion classifiers are unavailable. Not a diagnosis.",
    persistence: { status: "not_saved", record_id: null },
  };
}
