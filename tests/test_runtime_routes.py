"""Actual authenticated route deadlines with controlled slow work."""
import threading
import pytest
from fastapi.testclient import TestClient
from api import api as service, db
from _supabase_stub import StubSupabase, install


@pytest.fixture
def client():
    install(StubSupabase())
    with TestClient(service.app) as client:
        token=client.post('/auth/login', json={'user_id':'alice@example.com','password':'alice-pass'}).json()['token']
        yield client, {'Authorization':'Bearer '+token}
    db.reset_client()


def test_inference_deadline_is_503_and_does_not_start_saving(client, monkeypatch):
    browser, headers=client
    release=threading.Event()
    def slow(text):
        release.wait(2)
        raise RuntimeError('synthetic cancelled work')
    monkeypatch.setattr(service.screener,'screen',slow)
    monkeypatch.setattr(service,'INFERENCE_TIMEOUT_SECONDS',.02)
    try:
        response=browser.post('/predict',headers=headers,json={'text':'synthetic timeout'})
        assert response.status_code==503
        assert response.headers['Retry-After']=='5'
        assert 'safety' not in response.json()
    finally:
        release.set()


def test_save_deadline_preserves_actual_high_and_reports_unconfirmed(client, monkeypatch):
    browser, headers=client
    release=threading.Event()
    def slow(**kwargs):
        release.wait(2)
        return 'synthetic-late-record'
    monkeypatch.setattr(db.get_client(),'record_screening',slow)
    monkeypatch.setattr(service,'PERSISTENCE_TIMEOUT_SECONDS',.02)
    try:
        response=browser.post('/predict',headers=headers,json={'text':'i wanna jump from 10th floor'})
        assert response.status_code==200
        assert response.json()['safety']['level']=='HIGH'
        assert response.json()['persistence']=={'status':'unconfirmed','record_id':None}
    finally:
        release.set()


@pytest.mark.parametrize('timeout',[float('nan'),float('inf'),0,-1,10000])
def test_provider_timeout_must_be_finite_and_bounded(timeout):
    with pytest.raises(db.SupabaseError):
        db.SupabaseClient('https://synthetic.example','synthetic-public','synthetic-secret',timeout=timeout)


def test_public_configuration_matches_actual_initialized_service(client):
    browser,_=client
    response=browser.get('/configuration')
    assert response.status_code==200
    data=response.json()
    assert data['schema_version']=='1.0'
    assert data['max_text_length']==service.screener.max_text_length
    assert data['max_body_bytes']==service.screener.max_text_length*12+4096
    assert data['urgency_threshold']==service.screener._urgency_threshold
    assert data['semantic_status']=='disabled'
