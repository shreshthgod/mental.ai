"""Readiness tests use the actual route, with synthetic probes where stated."""
from fastapi.testclient import TestClient
from api import api as service


def test_live_does_not_call_inference(monkeypatch):
    def fail(): raise AssertionError('liveness must not probe')
    monkeypatch.setattr(service, '_inference_probe', fail)
    with TestClient(service.app) as client:
        assert client.get('/live').status_code == 200


def test_ready_reuses_only_fresh_probe_and_refreshes_expired(monkeypatch):
    calls = []
    clock = [100.0]
    monkeypatch.setattr(service, '_probe_cache', None)
    monkeypatch.setattr(service, '_probe_clock', lambda: clock[0])
    def probe():
        calls.append(1)
        return True, 'degraded'
    monkeypatch.setattr(service, '_inference_probe', probe)
    with TestClient(service.app) as client:
        first = client.get('/ready').json()
        assert first['probe_age_seconds'] == 0
        assert first['capability'] == 'degraded'
        assert client.get('/ready').status_code == 200
        assert len(calls) == 1
        clock[0] += service.PROBE_TTL_SECONDS + 1
        assert client.get('/ready').status_code == 200
        assert len(calls) == 2


def test_failed_expired_probe_cannot_reuse_old_success(monkeypatch):
    monkeypatch.setattr(service, '_probe_cache', None)
    monkeypatch.setattr(service, '_inference_probe', lambda: (False, 'required_safety_unavailable'))
    with TestClient(service.app) as client:
        assert client.get('/ready').status_code == 503
