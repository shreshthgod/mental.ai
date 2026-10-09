"""Schema invariants independent of socket/provider behavior."""
import copy
import pytest
from pydantic import ValidationError
from api.api import PredictResponse
from mental_health_screening.inference import MentalHealthScreener


@pytest.fixture(scope="module")
def payload():
    out = MentalHealthScreener().screen("i wanna jump from 10th floor")
    return {**out, "request_id": "synthetic-request", "service_version": "0.1.0"}


def test_version_and_component_status_survive_response_validation(payload):
    result = PredictResponse.model_validate(payload).model_dump()
    assert result["schema_version"] == "1.0"
    assert result["components"]["semantic"] == "disabled"
    assert result["safety"]["assessment_scope"] == "recognized_rules_only"
    assert result["model_version"]


@pytest.mark.parametrize("field,value", [
    ("level", "safe"), ("subject", "everyone"), ("temporal_context", "imminent"),
    ("immediacy", "immediate"), ("analysis_status", "perfect"),
])
def test_invalid_safety_enums_are_rejected(payload, field, value):
    broken = copy.deepcopy(payload)
    broken["safety"][field] = value
    with pytest.raises(ValidationError):
        PredictResponse.model_validate(broken)


def test_disabled_semantic_cannot_claim_complete_assessment(payload):
    broken = copy.deepcopy(payload)
    broken["safety"]["analysis_status"] = "complete"
    with pytest.raises(ValidationError):
        PredictResponse.model_validate(broken)


def test_unavailable_primary_cannot_retain_a_prediction(payload):
    broken = copy.deepcopy(payload)
    broken["primary"]["status"] = "unavailable"
    with pytest.raises(ValidationError):
        PredictResponse.model_validate(broken)
