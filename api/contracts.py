"""Versioned internal analysis contract used by API and stored snapshots.

Model probabilities remain raw research outputs. Unavailable is explicit and
never becomes a fabricated label/probability. No clinical validity is implied.
"""
import math
from typing import Literal
from pydantic import BaseModel, Field, model_validator

SCHEMA_VERSION = "1.0"
Status = Literal["complete", "unavailable"]


class Components(BaseModel):
    independent_safety: Status
    semantic: Literal["complete", "disabled", "unavailable"]
    preprocessing: Status
    primary: Status
    urgency: Status


class PrimaryResult(BaseModel):
    predicted_class: str | None = None
    class_probabilities: dict[str, float] = Field(default_factory=dict)
    status: Status = "complete"

    @model_validator(mode="after")
    def validate_observation(self):
        if self.status == "unavailable":
            if self.predicted_class is not None or self.class_probabilities:
                raise ValueError("Unavailable primary must not contain observations")
        else:
            p = self.class_probabilities
            if self.predicted_class not in p or not p:
                raise ValueError("Complete primary requires a predicted class and distribution")
            if any(not math.isfinite(v) or not 0 <= v <= 1 for v in p.values()) or abs(sum(p.values())-1) > 1e-5:
                raise ValueError("Invalid primary probability distribution")
        return self


class UrgencyResult(BaseModel):
    predicted_class: Literal["suicide", "non-suicide"] | None = None
    suicide_probability: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    decision_threshold_used: float = Field(gt=0, le=1, allow_inf_nan=False)
    flagged: bool = False
    status: Status = "complete"

    @model_validator(mode="after")
    def validate_observation(self):
        if self.status == "unavailable":
            if self.predicted_class is not None or self.suicide_probability is not None or self.flagged:
                raise ValueError("Unavailable urgency must not contain observations")
        else:
            if self.predicted_class is None or self.suicide_probability is None:
                raise ValueError("Complete urgency requires observations")
            expected = self.suicide_probability >= self.decision_threshold_used
            if self.flagged != expected or (self.predicted_class == "suicide") != expected:
                raise ValueError("Urgency label/flag disagree with actual threshold")
        return self


class SafetyResult(BaseModel):
    level: Literal["NONE_DETECTED", "NEEDS_CLARIFICATION", "CONCERNING", "HIGH", "IMMEDIATE", "UNKNOWN"]
    subject: Literal["self", "another_person", "fictional_or_quoted", "unclear"]
    temporal_context: Literal["current", "recent", "historical", "hypothetical", "unclear"]
    immediacy: Literal["stated", "not_stated", "unclear"]
    evidence_codes: list[str]
    summary: str
    needs_clarification: bool
    review_recommended: bool
    analysis_status: Literal["complete", "degraded", "unavailable", "unsupported"]
    policy_version: str
    language_support: Literal["complete", "degraded", "unavailable", "unsupported", "unknown"] = "unknown"
    assessment_scope: Literal["recognized_rules_only", "validated_semantic_and_rules", "unavailable"]
    support_action: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_support_state(self):
        action = self.support_action.lower()
        if any(marker in action for marker in ("nothing to worry", "you're fine", "all clear", "no risk",
                 "you have depression", "you are bipolar", "you have schizophrenia", "clinically normal", "you are suicidal")):
            raise ValueError("Support action contains prohibited reassurance or diagnosis")
        if self.level in {"HIGH", "IMMEDIATE"} and not any(marker in action for marker in ("emergency", "crisis", "trusted", "trust", "urgent")):
            raise ValueError("Urgent support requires actionable guidance")
        if self.level == "NEEDS_CLARIFICATION" and "?" not in action:
            raise ValueError("Clarification support requires a question")
        if self.subject == "another_person" and self.level != "NONE_DETECTED" and any(marker in action for marker in ("harming yourself", "harm yourself", "you are suicidal")):
            raise ValueError("Support addresses the wrong affected person")
        if self.level in {"UNKNOWN", "NEEDS_CLARIFICATION"} and not self.needs_clarification:
            raise ValueError("Uncertain state must require clarification")
        if self.level == "NONE_DETECTED" and self.analysis_status in {"unavailable", "unsupported"}:
            raise ValueError("Unavailable assessment cannot report no concern")
        if self.level in {"HIGH", "IMMEDIATE"} and not self.review_recommended:
            raise ValueError("Urgent support must recommend review, without claiming notification")
        return self


class AnalysisResult(BaseModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    request_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    safety: SafetyResult
    components: Components
    primary: PrimaryResult
    urgency: UrgencyResult
    model_version: str
    cleaned_text: str | None = None
    lemmatized_text: str | None = None
    provenance_caveat: str | None = None
    service_version: str

    @model_validator(mode="after")
    def validate_availability(self):
        if self.components.primary != self.primary.status or self.components.urgency != self.urgency.status:
            raise ValueError("Component statuses disagree with raw observations")
        if self.safety.analysis_status == "complete" and any(
            value != "complete" for value in self.components.model_dump().values()
        ):
            raise ValueError("Incomplete components cannot claim complete assessment")
        return self


class PersistenceResult(BaseModel):
    status: Literal["saved", "not_saved", "unconfirmed"] = "not_saved"
    record_id: str | None = None

    @model_validator(mode="after")
    def validate_save_state(self):
        if (self.status == "saved") != (self.record_id is not None):
            raise ValueError("Only confirmed saved results carry a record identifier")
        return self


class PredictResponse(AnalysisResult):
    persistence: PersistenceResult = Field(default_factory=PersistenceResult)


class ConfigurationResponse(BaseModel):
    schema_version: Literal['1.0'] = SCHEMA_VERSION
    max_text_length: int
    max_body_bytes: int
    urgency_threshold: float | None
    policy_version: str | None
    semantic_status: Literal['disabled']
