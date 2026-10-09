"""Real ASGI boundary, authentication transport stub only."""
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from api import api as service, db
sys.path.insert(0, str(Path(__file__).parent))
from _supabase_stub import StubSupabase, install


@pytest.fixture
def client():
    install(StubSupabase())
    with TestClient(service.app) as client:
        yield client
    db.reset_client()


def test_request_id_rejects_log_control_characters(client):
    supplied = 'unsafe\nforged-log'
    response = client.get('/metrics', headers={'X-Request-ID':supplied})
    assert response.status_code == 200
    assert response.headers['X-Request-ID'] != supplied
    assert '\n' not in response.headers['X-Request-ID']


def test_allowed_origin_can_delete_owner_history(client):
    response = client.options('/screenings', headers={
        'Origin':'http://localhost:5173', 'Access-Control-Request-Method':'DELETE',
        'Access-Control-Request-Headers':'Authorization'})
    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == 'http://localhost:5173'


def test_denied_origin_is_not_given_permission(client):
    response = client.options('/predict', headers={
        'Origin':'https://untrusted.example', 'Access-Control-Request-Method':'POST',
        'Access-Control-Request-Headers':'Authorization'})
    assert response.status_code == 400
    assert 'access-control-allow-origin' not in response.headers


def test_one_configured_character_limit_above_default(monkeypatch):
    monkeypatch.setenv('MAX_TEXT_LENGTH', '12000')
    # This is validation, not model inference on a repeated synthetic word.
    assert len(service.PredictRequest(text='x'*11000).text) == 11000


def test_oversized_body_rejected_before_json_validation(client):
    response = client.post('/predict', content=b' '*500001,
                           headers={'Content-Type':'application/json'})
    assert response.status_code == 413


def test_predict_rate_limit_uses_verified_owner_and_returns_retry(client, monkeypatch, tmp_path):
    from api.limits import PredictLimiter
    monkeypatch.setattr(service, 'predict_limiter', PredictLimiter(str(tmp_path/'route-limits.sqlite3'), maximum=1))
    token = client.post('/auth/login', json={'user_id':'alice@example.com','password':'alice-pass'}).json()['token']
    headers = {'Authorization':'Bearer '+token}
    assert client.post('/predict', headers=headers, json={'text':'synthetic test'}).status_code == 200
    rejected = client.post('/predict', headers=headers, json={'text':'synthetic test', 'user_id':'other'})
    assert rejected.status_code == 429
    assert int(rejected.headers['Retry-After']) > 0
