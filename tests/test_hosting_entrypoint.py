"""Local ASGI hosting wrapper; no deployed/Vercel execution claimed."""
from fastapi.testclient import TestClient
from api import db
from main import app
from _supabase_stub import StubSupabase, install


def test_prefixed_authenticated_route_uses_same_real_analysis():
    install(StubSupabase())
    try:
        with TestClient(app) as client:
            assert client.post('/api/predict',json={'text':'synthetic'}).status_code==401
            token=client.post('/api/auth/login',json={'user_id':'alice@example.com','password':'alice-pass'}).json()['token']
            result=client.post('/api/predict',headers={'Authorization':'Bearer '+token},
                               json={'text':'i wanna jump from 10th floor'})
            assert result.status_code==200
            assert result.json()['safety']['level']=='HIGH'
            assert result.json()['primary']['predicted_class']=='Normal'
            assert result.json()['persistence']['status']=='saved'
    finally:
        db.reset_client()


def test_prefixed_route_retains_byte_limit():
    with TestClient(app) as client:
        assert client.post('/api/predict',content=b' '*500001).status_code==413
