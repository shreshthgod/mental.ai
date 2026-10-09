"""Versioned synthetic contract states, not safety-performance labels.

The baseline raw probabilities come from one actual packaged-model inference on
the public original regression input. State mutations exercise the contract;
they do not claim those models produced the synthetic safety states.
"""
import copy
import json
from pathlib import Path
from api.contracts import PredictResponse
from mental_health_screening.inference import MentalHealthScreener
from mental_health_screening.safety import support_action


def generate():
    raw = MentalHealthScreener().screen('i wanna jump from 10th floor')
    base = PredictResponse.model_validate({**raw, 'request_id':'contract-fixture',
                                          'service_version':'0.1.0'}).model_dump()
    cases = []

    def add(name, level='HIGH', *, subject='self', primary=True, urgency=True,
            semantic='disabled', status='degraded', language='degraded', independent=True,
            persistence='not_saved'):
        result = copy.deepcopy(base)
        safety = result['safety']
        safety.update(level=level, subject=subject, analysis_status=status,
            language_support=language, needs_clarification=level in {'UNKNOWN','NEEDS_CLARIFICATION'},
            review_recommended=level not in {'NONE_DETECTED'},
            temporal_context='unclear' if level in {'UNKNOWN','NONE_DETECTED'} else 'current',
            immediacy='stated' if level=='IMMEDIATE' else 'not_stated',
            evidence_codes=['SYNTHETIC_CONTRACT_FIXTURE'],
            summary='Synthetic contract state; not an evaluated disclosure.',
            assessment_scope='recognized_rules_only' if independent else 'unavailable',
            support_action=support_action(level, subject=subject))
        result['components'].update(independent_safety='complete' if independent else 'unavailable', semantic=semantic)
        if not primary:
            result['primary'].update(predicted_class=None, class_probabilities={}, status='unavailable')
            result['components']['primary']='unavailable'
        if not urgency:
            result['urgency'].update(predicted_class=None, suicide_probability=None, flagged=False, status='unavailable')
            result['components']['urgency']='unavailable'
        if not independent:
            result['components']['preprocessing']='unavailable'
            result['cleaned_text']=result['lemmatized_text']=None
        result['persistence']={'status':persistence, 'record_id':'synthetic-record' if persistence=='saved' else None}
        cases.append({'name':name, 'response':PredictResponse.model_validate(result).model_dump()})

    add('high')
    add('immediate', 'IMMEDIATE')
    add('concerning', 'CONCERNING')
    add('clarification', 'NEEDS_CLARIFICATION')
    add('none_detected', 'NONE_DETECTED')
    add('unsupported', 'UNKNOWN', status='unsupported', language='unsupported')
    add('known_high_with_unsupported_material', status='unsupported', language='unsupported')
    add('degraded')
    add('primary_unavailable', primary=False)
    add('urgency_unavailable', urgency=False)
    add('semantic_unavailable', semantic='unavailable')
    add('all_safety_unavailable', 'UNKNOWN', independent=False, primary=False, urgency=False,
        semantic='unavailable', status='unavailable', language='unknown')
    add('another_person', subject='another_person')
    add('persistence_failure')
    add('persistence_unconfirmed', persistence='unconfirmed')
    add('saved', persistence='saved')
    return {'fixture_version':'contract-fixtures-1.0.1',
        'provenance':'Developer-authored synthetic contract states; not clinical/performance evaluation. Raw base from actual original-case inference.',
        'pending_persistence':'NOT_APPLICABLE: no durable async mechanism exists.',
        'success_cases':cases,
        'error_cases':[
            {'name':'authentication_failure','status':401,'response':{'detail':'Authentication required'}},
            {'name':'invalid_input','status':422,'response':{'detail':[{'loc':['body','text'],'msg':'Invalid input'}]}},
            {'name':'rate_limit','status':429,'response':{'detail':'Analysis request limit reached; please retry later'},'retry_after':'60'}]}


if __name__=='__main__':
    path = Path('tests/contract/analysis-v1.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(generate(), indent=2)+'\n')
