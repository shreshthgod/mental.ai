"""Local semantic adapter boundary. No provider, model, or downloads enabled.

An evaluator must be validated separately before production selection. The
boundary rejects malformed output and records availability without fake scores.
The caller owns bounded scheduling: this adapter cannot cancel synchronous work.
"""
from dataclasses import dataclass
from typing import Callable, Literal


@dataclass(frozen=True)
class SemanticAssessment:
    status: Literal["complete", "disabled", "unavailable"]
    concern: Literal["none_detected", "ambiguous", "concerning", "urgent"] | None = None
    subject: str | None = None
    temporal_context: str | None = None
    artifact_version: str | None = None
    failure: Literal["timeout", "malformed", "component_error"] | None = None


def assess(text: str, evaluator: Callable[[str], dict] | None = None) -> SemanticAssessment:
    if evaluator is None:
        return SemanticAssessment(status="disabled")
    try:
        out = evaluator(text)
    except TimeoutError:
        return SemanticAssessment(status="unavailable", failure="timeout")
    except Exception:
        return SemanticAssessment(status="unavailable", failure="component_error")
    if not isinstance(out, dict) or set(out) != {
        "concern", "subject", "temporal_context", "artifact_version"
    } or out["concern"] not in {"none_detected", "ambiguous", "concerning", "urgent"} \
            or out["subject"] not in {"self", "another_person", "fictional_or_quoted", "unclear"} \
            or out["temporal_context"] not in {"current", "recent", "historical", "hypothetical", "unclear"} \
            or not isinstance(out["artifact_version"], str) or not out["artifact_version"]:
        return SemanticAssessment(status="unavailable", failure="malformed")
    return SemanticAssessment(status="complete", **out)
