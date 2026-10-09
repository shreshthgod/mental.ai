from mental_health_screening.safety import evaluate


def test_bare_risk_word_does_not_create_an_educational_frame():
    result = evaluate("I have been thinking about suicide.")
    assert result.level in {"CONCERNING", "NEEDS_CLARIFICATION"}
    assert "EDUCATIONAL_FRAME" not in result.evidence_codes


def test_an_actual_prevention_lesson_remains_contextual():
    result = evaluate("Our suicide-prevention lesson explains how to ask for help.")
    assert result.level == "NONE_DETECTED"
    assert "EDUCATIONAL_FRAME" in result.evidence_codes
