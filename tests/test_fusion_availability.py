"""Fusion policy checks; classifier scores are injected, not clinically validated."""
import numpy as np
import pytest
from mental_health_screening.inference import MentalHealthScreener


@pytest.fixture(scope="module")
def screener():
    return MentalHealthScreener()


@pytest.mark.parametrize("probability,level", [(.9, "NEEDS_CLARIFICATION"), (.01, "UNKNOWN")])
def test_unrecognized_context_without_semantic_assessment_is_not_safe(screener, monkeypatch, probability, level):
    monkeypatch.setattr(screener._urgency_model, "predict_proba",
                        lambda _: np.array([[1-probability, probability]]))
    result = screener.screen("An unfamiliar synthetic disclosure")
    assert result["safety"]["level"] == level
    assert result["safety"]["analysis_status"] == "degraded"
    assert result["components"]["semantic"] == "disabled"
    assert result["safety"]["needs_clarification"] is True
    assert result["urgency"]["suicide_probability"] == probability


def test_credible_location_context_does_not_become_an_emergency(screener, monkeypatch):
    monkeypatch.setattr(screener._urgency_model, "predict_proba", lambda _: np.array([[.1,.9]]))
    result = screener.screen("I live on the tenth floor.")
    assert result["safety"]["level"] == "NONE_DETECTED"
    assert result["safety"]["analysis_status"] == "degraded"


def test_primary_normal_and_negative_urgency_cannot_cancel_explicit_danger(screener, monkeypatch):
    monkeypatch.setattr(screener._urgency_model, "predict_proba", lambda _: np.array([[.99,.01]]))
    result = screener.screen("i wanna jump from 10th floor")
    assert result["safety"]["level"] == "HIGH"
    assert result["safety"]["analysis_status"] == "degraded"
    assert result["primary"]["predicted_class"] == "Normal"
