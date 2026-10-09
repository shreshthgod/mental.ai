import pytest
from mental_health_screening.safety import evaluate


@pytest.mark.parametrize("text,temporal", [
    ("i wanna jump from 10th floor", "current"),
    ("I want to kill myself", "current"),
    ("I plan to hang myself this weekend", "current"),
    ("I cut myself again last night", "recent"),
    ("I hurt myself earlier today and the bleeding has not stopped", "recent"),
    ("I tried to kill myself as a teenager. I am safe now.", "historical"),
])
def test_temporal_event_is_independent_of_route(text, temporal):
    assert evaluate(text).temporal_context == temporal


def test_current_intent_does_not_invent_immediacy():
    result = evaluate("i wanna jump from 10th floor")
    assert result.level == "HIGH"
    assert result.immediacy == "not_stated"
