"""Adapter shape/failure tests use synthetic functions, not a semantic model."""
from mental_health_screening.semantic import assess


def test_disabled_adapter_does_not_invent_a_negative_assessment():
    result = assess("synthetic")
    assert result.status == "disabled"
    assert result.concern is None


def test_semantic_timeout_is_unavailable():
    def timeout(text):
        raise TimeoutError()
    result = assess("synthetic", timeout)
    assert result.status == "unavailable"
    assert result.concern is None
    assert result.failure == "timeout"


def test_malformed_result_is_unavailable():
    assert assess("synthetic", lambda _: {"concern": "safe"}).failure == "malformed"


def test_validated_shape_retains_subject_and_time():
    result = assess("synthetic", lambda _: {
        "concern": "urgent", "subject": "another_person",
        "temporal_context": "current", "artifact_version": "test-only",
    })
    assert result.status == "complete"
    assert result.subject == "another_person"
