"""Same fixtures intended for Python/API/frontend/history consumption.

API fixture tests stub inference and provider transport explicitly. Real model
fault/original-case tests are separate; fixtures are contract state coverage.
"""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from api import api as service, db
from api.contracts import PredictResponse, AnalysisResult
from _supabase_stub import StubSupabase, install

DOC = json.loads((Path(__file__).parent/'contract/analysis-v1.json').read_text())


@pytest.mark.parametrize('case', DOC['success_cases'], ids=lambda c:c['name'])
def test_fixture_validates_and_snapshot_round_trip_preserves_core(case):
    response=PredictResponse.model_validate(case['response'])
    core=response.model_dump(exclude={'persistence'})
    assert AnalysisResult.model_validate_json(json.dumps(core)).model_dump() == core


@pytest.mark.parametrize('case', DOC['success_cases'], ids=lambda c:c['name'])
def test_real_route_preserves_fixture_with_explicit_inference_override(case, monkeypatch):
    stub=StubSupabase()
    install(stub)
    expected=case['response']
    monkeypatch.setattr(service.screener, 'screen', lambda text: expected)
    desired=expected['persistence']['status']
    if desired=='not_saved':
        stub.rest_status['/rest/v1/screenings']=500
    elif desired=='saved':
        monkeypatch.setattr(db.get_client(), 'record_screening', lambda **kwargs:'synthetic-record')
    else:
        def fail(**kwargs): raise db.WriteUnconfirmed('synthetic acknowledgement fault')
        monkeypatch.setattr(db.get_client(), 'record_screening', fail)
    try:
        with TestClient(service.app) as client:
            token=client.post('/auth/login', json={'user_id':'alice@example.com','password':'alice-pass'}).json()['token']
            response=client.post('/predict', json={'text':'synthetic fixture'}, headers={
                'Authorization':'Bearer '+token, 'X-Request-ID':expected['request_id']})
            assert response.status_code==200
            assert response.json()==expected
    finally:
        db.reset_client()


@pytest.mark.parametrize('case', DOC['error_cases'], ids=lambda c:c['name'])
def test_error_fixture_envelope_through_real_route(case, monkeypatch, tmp_path):
    from api.limits import PredictLimiter
    install(StubSupabase())
    monkeypatch.setattr(service, 'predict_limiter', PredictLimiter(str(tmp_path/'error-limits.sqlite3'), maximum=1))
    # Controlled inference is irrelevant to auth/validation/rate errors.
    monkeypatch.setattr(service.screener, 'screen', lambda text:DOC['success_cases'][0]['response'])
    try:
        with TestClient(service.app) as client:
            headers={}
            text='synthetic fixture'
            if case['name']!='authentication_failure':
                token=client.post('/auth/login', json={'user_id':'alice@example.com','password':'alice-pass'}).json()['token']
                headers={'Authorization':'Bearer '+token}
            if case['name']=='invalid_input': text=' '
            if case['name']=='rate_limit':
                assert client.post('/predict', headers=headers, json={'text':text}).status_code==200
            response=client.post('/predict', headers=headers, json={'text':text})
            assert response.status_code==case['status']
            if isinstance(case['response']['detail'], list):
                assert isinstance(response.json()['detail'], list)
                assert response.json()['detail'][0]['loc']==case['response']['detail'][0]['loc']
            else:
                assert response.json()==case['response']
            if case['name']=='rate_limit': assert int(response.headers['Retry-After']) > 0
    finally:
        db.reset_client()
