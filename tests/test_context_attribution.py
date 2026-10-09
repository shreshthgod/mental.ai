"""Context belongs to effective concern evidence, not unrelated filler."""
import pytest
from mental_health_screening.safety import evaluate


@pytest.mark.parametrize("text,subject,temporal", [
    ("I wish I would not wake up tomorrow.", "self", "current"),
    ("I took more medicine than prescribed and feel unwell.", "self", "current"),
    ("I do not enjoy things the way I used to.", "self", "current"),
    ("My brother wants to die.", "another_person", "current"),
    ("A character in my story says, 'I want to die.'", "fictional_or_quoted", "hypothetical"),
    ("I had a nice day. I enjoyed dinner. I am glad to be here. "
     "My brother says he wants to end his life tonight.", "another_person", "current"),
    ("I wanted to die years ago. I have no current urge and have support. "
     "I had a lovely lunch. I enjoy my job.", "self", "historical"),
    ("I wanted to die years ago. I plan to end my life tonight.", "self", "current"),
])
def test_subject_and_time_follow_relevant_context(text, subject, temporal):
    result = evaluate(text)
    assert result.subject == subject
    assert result.temporal_context == temporal


def test_third_person_risk_survives_repeated_self_filler():
    result = evaluate("I had a good day. " * 15 + "My friend is about to jump from a balcony.")
    assert result.level in {"HIGH", "IMMEDIATE"}
    assert result.subject == "another_person"
