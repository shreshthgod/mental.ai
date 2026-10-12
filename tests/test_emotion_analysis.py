"""Unit tests for emotion recognition task separation and multi-label cues."""
import pytest
from mental_health_screening.emotion import EmotionRecognizer, EMOTION_CATEGORIES


@pytest.fixture
def recognizer():
    return EmotionRecognizer()


def test_recognizes_multiple_simultaneous_cues(recognizer):
    text = "I feel so lonely and sad, but also terrified and anxious about what is coming next."
    result = recognizer.analyze(text)
    emotions = {c.emotion for c in result.cues_detected}
    assert "sadness" in emotions
    assert "loneliness" in emotions
    assert "fear" in emotions or "anxiety_related" in emotions
    assert result.is_self_reported is True


def test_distinguishes_first_person_self_report_from_third_person(recognizer):
    first_person = recognizer.analyze("I am feeling completely overwhelmed and miserable inside.")
    assert first_person.is_self_reported is True

    third_person = recognizer.analyze("He seemed really angry and furious about what happened to them.")
    assert third_person.is_third_person_or_external is True


def test_clinical_distinction_advisories(recognizer):
    sad_result = recognizer.analyze("I'm feeling very sad today.")
    assert "not clinical depression" in sad_result.distinction_advisory

    excited_result = recognizer.analyze("I am so excited and thrilled about my new project!")
    assert "not a bipolar manic symptom" in excited_result.distinction_advisory


def test_negation_suppresses_spurious_emotion(recognizer):
    negated = recognizer.analyze("I am not happy with how things turned out.")
    # 'happy' negated should not produce high happiness score
    happiness_cues = [c for c in negated.cues_detected if c.emotion == "happiness"]
    assert len(happiness_cues) == 0 or happiness_cues[0].score < 0.2


def test_handles_empty_and_neutral_text(recognizer):
    empty = recognizer.analyze("")
    assert len(empty.cues_detected) == 0
    assert len(empty.primary_emotions) == 0

    neutral = recognizer.analyze("The bus arrives at 4:30 pm at the station.")
    assert len(neutral.primary_emotions) == 0


def test_serializable_to_dict(recognizer):
    res = recognizer.analyze("I feel frustrated and angry at this delay.")
    d = res.to_dict()
    assert "cues_detected" in d
    assert "primary_emotions" in d
    assert "distinction_advisory" in d
    assert "raw_scores" in d
    assert isinstance(d["raw_scores"], dict)
