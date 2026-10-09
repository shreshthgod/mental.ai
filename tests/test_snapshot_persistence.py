"""Actual ASGI/model path, synthetic GoTrue/PostgREST transport only."""
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from api import db
from api.api import app

sys.path.insert(0, str(Path(__file__).parent))
from _supabase_stub import StubSupabase, install


@pytest.fixture
def session():
    stub = StubSupabase()
    install(stub)
    with TestClient(app) as client:
        token = client.post('/auth/login', json={'user_id':'alice@example.com','password':'alice-pass'}).json()['token']
        yield client, {'Authorization':'Bearer '+token}, stub
    db.reset_client()


def test_saved_snapshot_round_trips_authoritative_result(session):
    client, headers, stub = session
    result = client.post('/predict', headers=headers, json={'text':'i wanna jump from 10th floor'}).json()
    assert result['persistence']['status'] == 'saved'
    stored = next(iter(stub.screenings.values()))
    core = {k:v for k,v in result.items() if k != 'persistence'}
    assert stored['analysis_result'] == core
    history = client.get('/screenings', headers=headers).json()['screenings'][0]
    assert history['analysis_result'] == core
    assert history['assessment_kind'] == 'authoritative'
    assert core['safety']['level'] == 'HIGH'


def test_rejected_write_preserves_support_and_reports_not_saved(session):
    client, headers, stub = session
    stub.rest_status['/rest/v1/screenings'] = 500
    response = client.post('/predict', headers=headers, json={'text':'i wanna jump from 10th floor'})
    assert response.status_code == 200
    assert response.json()['safety']['level'] == 'HIGH'
    assert response.json()['persistence']['status'] == 'not_saved'
    assert not stub.screenings


def test_uncertain_write_acknowledgement_is_not_claimed_saved(session, monkeypatch):
    client, headers, _ = session
    def fail(**kwargs):
        raise db.SupabaseError('synthetic transport failure')
    monkeypatch.setattr(db.get_client(), 'record_screening', fail)
    result = client.post('/predict', headers=headers, json={'text':'i wanna jump from 10th floor'}).json()
    assert result['safety']['level'] == 'HIGH'
    assert result['persistence']['status'] == 'unconfirmed'
    assert result['persistence']['record_id'] is None


def test_legacy_history_is_explicitly_unassessed(session):
    client, headers, stub = session
    stub.screenings['legacy-row'] = dict(user_id='uuid-alice', text='synthetic old record',
        condition_label='Normal', condition_probabilities={}, urgency_flagged=False)
    row = client.get('/screenings', headers=headers).json()['screenings'][0]
    assert row['analysis_result'] is None
    assert row['assessment_kind'] == 'legacy_unassessed'


def test_null_primary_is_stored_as_null_not_a_label(session, monkeypatch):
    from api import api as service
    client, headers, stub = session
    def fail(*args): raise RuntimeError('synthetic primary failure')
    monkeypatch.setattr(service.screener._primary_model, 'predict_proba', fail)
    result = client.post('/predict', headers=headers, json={'text':'i wanna jump from 10th floor'}).json()
    row = next(iter(stub.screenings.values()))
    assert row['condition_label'] is None
    assert row['analysis_result']['primary']['predicted_class'] is None
    assert result['persistence']['status'] == 'saved'
