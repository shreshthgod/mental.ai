import pytest
from mental_health_screening.safety import evaluate


@pytest.mark.parametrize('text', [
    'I want to kill myself and I am with my friend.',
    'I want to kill myself. My friend is supporting me.',
    'I wanna jump from the 10th floor with my friend nearby.',
])
def test_companion_is_not_the_subject_of_authors_intent(text):
    result=evaluate(text)
    assert result.level=='HIGH'
    assert result.subject=='self'
    assert result.temporal_context=='current'


def test_reporting_another_persons_intent_retains_that_person():
    result=evaluate('My friend told me he wants to kill himself.')
    assert result.level=='HIGH'
    assert result.subject=='another_person'
