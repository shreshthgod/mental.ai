"""Provider wait must not block the ASGI event loop; transport is synthetic."""
import threading
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from api import api as service, db
from _supabase_stub import StubSupabase, install


def test_slow_history_provider_does_not_block_metrics(monkeypatch):
    install(StubSupabase())
    started, release = threading.Event(), threading.Event()
    def slow_history(*args, **kwargs):
        started.set()
        release.wait(2)
        return []
    monkeypatch.setattr(db.get_client(), 'list_screenings', slow_history)
    try:
        with TestClient(service.app) as client, ThreadPoolExecutor(max_workers=2) as pool:
            token = client.post('/auth/login', json={'user_id':'alice@example.com','password':'alice-pass'}).json()['token']
            history = pool.submit(client.get, '/screenings', headers={'Authorization':'Bearer '+token})
            assert started.wait(1)
            metrics = pool.submit(client.get, '/metrics')
            try:
                assert metrics.result(timeout=.5).status_code == 200
            finally:
                release.set()
            assert history.result(timeout=2).status_code == 200
    finally:
        release.set()
        db.reset_client()
