"""Recovery context cannot erase a still-current stated intent."""
import pytest
from mental_health_screening.safety import evaluate


@pytest.mark.parametrize('text', [
    'I want to kill myself. I am getting help.',
    'I want to kill myself and I am getting help.',
])
def test_help_does_not_establish_resolved_current_intent(text):
    result = evaluate(text)
    assert result.level == 'HIGH'
    assert result.temporal_context == 'current'
    assert result.immediacy == 'not_stated'


def test_explicit_old_event_and_recovery_remain_historical():
    result = evaluate('I tried to kill myself as a teenager. I am safe now.')
    assert result.level == 'CONCERNING'
    assert result.temporal_context == 'historical'
