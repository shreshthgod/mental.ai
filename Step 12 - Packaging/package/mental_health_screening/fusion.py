"""Support fusion and assessment availability, separate from raw classifiers.

The production semantic adapter is disabled. A validated structured adapter may
be supplied by an internal caller in future; user input cannot enable it.
"""
from .semantic import SemanticAssessment
from .safety import LEVEL_ORDER, support_action


def fuse(rule: dict, primary: dict, urgency: dict, *, preprocessing_available: bool,
         semantic: SemanticAssessment | None = None, semantic_validated: bool = False) -> tuple[dict, dict]:
    result = dict(rule)
    codes = set(rule["evidence_codes"])
    codes.difference_update({"URGENCY_MODEL_UNAVAILABLE", "URGENCY_MODEL_NOT_FLAGGED", "URGENCY_MODEL_FLAGGED"})
    urgency_available = urgency["status"] == "complete"
    codes.add("URGENCY_MODEL_FLAGGED" if urgency_available and urgency["flagged"] else
              "URGENCY_MODEL_NOT_FLAGGED" if urgency_available else "URGENCY_MODEL_UNAVAILABLE")
    independent_available = "SAFETY_EVALUATION_FAILED" not in codes
    semantic = semantic or SemanticAssessment(status="disabled")
    semantic_available = semantic_validated and semantic.status == "complete"
    components = {
        "independent_safety": "complete" if independent_available else "unavailable",
        "semantic": "complete" if semantic_available else
                    "unavailable" if semantic.status == "unavailable" else "disabled",
        "preprocessing": "complete" if preprocessing_available else "unavailable",
        "primary": primary["status"], "urgency": urgency["status"],
    }
    # A negative primary/urgency result cannot cancel existing concern.
    if semantic_available and independent_available:
        candidate = {"none_detected": "NONE_DETECTED", "ambiguous": "NEEDS_CLARIFICATION",
                     "concerning": "CONCERNING", "urgent": "HIGH"}[semantic.concern]
        codes.add("VALIDATED_SEMANTIC_ASSESSMENT")
        if result["level"] in {"NONE_DETECTED", "UNKNOWN"} or (
            candidate != "NONE_DETECTED" and LEVEL_ORDER[candidate] > LEVEL_ORDER[result["level"]]
        ):
            result.update(level=candidate, subject=semantic.subject,
                          temporal_context=semantic.temporal_context, immediacy="not_stated")
    elif independent_available and result["level"] == "NONE_DETECTED":
        # Existing context gates and a location named without an action provide
        # narrow supported benign contexts. Absence of every rule does not.
        resolved = bool(codes & {"FICTION_FRAME", "EDUCATIONAL_FRAME", "HISTORICAL_CONTEXT"})
        location_without_action = "METHOD_OR_LOCATION" in codes and not codes & {
            "INTENT_VERB", "SELF_HARM_ACT", "EXPLICIT_DIE_INTENT", "PLANNED_ACTION", "PRESENT_ACCESS"}
        if not (resolved or location_without_action):
            if urgency_available and urgency["flagged"]:
                result.update(level="NEEDS_CLARIFICATION", needs_clarification=True,
                              review_recommended=True,
                              summary="A legacy concern signal has unresolved context; clarification is needed.")
                codes.add("LEGACY_CONCERN_UNRESOLVED_CONTEXT")
            else:
                result.update(level="UNKNOWN", needs_clarification=True, review_recommended=True,
                              summary="Available checks cannot establish a sufficiently complete assessment.")
                codes.add("INSUFFICIENT_AVAILABLE_ASSESSMENT")
    if result["analysis_status"] not in {"unsupported", "unavailable"}:
        result["analysis_status"] = (
            "complete" if semantic_available and all(s == "complete" for s in components.values())
            else "degraded")
    result["assessment_scope"] = ("validated_semantic_and_rules" if semantic_available else
                                  "recognized_rules_only" if independent_available else "unavailable")
    if result["language_support"] == "complete" and not semantic_available:
        result["language_support"] = "degraded"  # heuristic, not established comprehension
    result["needs_clarification"] = result["needs_clarification"] or result["level"] in {"UNKNOWN", "NEEDS_CLARIFICATION"}
    result["evidence_codes"] = sorted(codes)
    result["support_action"] = support_action(result["level"], subject=result["subject"])
    return result, components
