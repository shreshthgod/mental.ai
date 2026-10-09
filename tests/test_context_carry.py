import pytest
from mental_health_screening.safety import evaluate


@pytest.mark.parametrize("text,temporal", [
    ("A quote says 'I want to die.' It describes how I feel right now.", "current"),
    ("I used to self-harm. I have no current urge and I have support.", "historical"),
    ("I have already harmed myself and need help.", "current"),
    ("Life has been good lately but I still think about ending it some nights.", "current"),
    ("Something in my head keeps telling me to end it.", "current"),
    ("I wanted to hurt myself earlier. I am now away from danger and with a trusted person.", "recent"),
    ("मैंने कल खुद को नुकसान पहुँचाया।", "recent"),
])
def test_reassertion_recovery_and_present_state_keep_context(text, temporal):
    assert evaluate(text).temporal_context == temporal


def test_unanchored_past_act_does_not_invent_a_date():
    assert evaluate("I cut my arm because I could not handle it.").temporal_context == "unclear"


def test_fictional_event_is_distinct_from_a_benign_film_reference():
    assert evaluate("The book I am reading has a character who kills himself.").temporal_context == "hypothetical"
    assert evaluate("The play ends with the protagonist jumping off a tower.").temporal_context == "hypothetical"
    assert evaluate("The battery died halfway through the film.").temporal_context == "unclear"
