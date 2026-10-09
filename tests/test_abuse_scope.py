import pytest
from mental_health_screening.safety import evaluate


@pytest.mark.parametrize("text", [
    "I need help with my homework.", "I need help.",
    "I cannot leave because the train is late.", "I am scared for my exam.",
])
def test_unqualified_help_or_constraint_is_not_an_abuse_emergency(text):
    assert evaluate(text).level not in {"HIGH", "IMMEDIATE"}


@pytest.mark.parametrize("text", [
    "Someone at home is threatening to hurt me right now.",
    "My partner is hitting me right now.",
    "Someone is choking me and I cannot get away.",
])
def test_explicit_current_assault_remains_actionable(text):
    assert evaluate(text).level in {"HIGH", "IMMEDIATE"}
