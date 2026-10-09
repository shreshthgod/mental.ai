import copy
import pytest
from pydantic import ValidationError
from api.contracts import PredictResponse
from mental_health_screening.inference import MentalHealthScreener
from mental_health_screening.safety import support_action


@pytest.mark.parametrize('action', ['', "You're fine; no risk.", 'You have depression.', 'Result: Normal.'])
def test_urgent_contract_rejects_empty_reassuring_or_nonactionable_copy(action):
    result = MentalHealthScreener().screen('i wanna jump from 10th floor')
    result.update(request_id='synthetic', service_version='0.1.0')
    result['safety']['support_action'] = action
    with pytest.raises(ValidationError):
        PredictResponse.model_validate(result)


def test_none_for_another_person_does_not_claim_detected_risk():
    assert 'may be at risk' not in support_action('NONE_DETECTED', subject='another_person')


def test_generic_immediate_guidance_does_not_invent_a_fall_location():
    action = support_action('IMMEDIATE', subject='self')
    assert 'balcony' not in action
    assert 'edge, ledge' not in action
    assert 'emergency' in action.lower()


def test_high_copy_does_not_invent_self_harm_or_location_conversation():
    result = MentalHealthScreener().screen('I am planning to attack someone')
    assert result['safety']['level'] == 'HIGH'
    assert 'thinking about harming yourself' not in result['safety']['support_action']
    action = support_action('HIGH', subject='self', region_known=False)
    assert 'thinking about harming yourself' not in action
    assert 'If you tell me your country I can point you' not in action
    assert 'local' in action.lower()
    assert 'trust' in action.lower()
