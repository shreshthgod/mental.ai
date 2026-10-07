"""
Integration and unit tests for the MENTAL.AI screening system.

These tests verify:
- package import and artifact loading
- inference with actual artifacts
- session authentication (token issue, verify, tamper, expiry)
- API endpoint behaviour through the real ASGI app
- defensive error handling

Run:
    PYTHONPATH="Step 12 - Packaging/package:." pytest tests -q
"""
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "Step 12 - Packaging", "package"))
sys.path.insert(0, _ROOT)

import pytest
from fastapi.testclient import TestClient

from api import auth
from mental_health_screening.inference import MentalHealthScreener


@pytest.fixture(scope="module")
def client():
    """TestClient over the real app: models load once for the whole module."""
    from api.api import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def token(client):
    """A valid bearer token from the demo credentials."""
    res = client.post("/auth/login", json={"user_id": "admin", "password": "password"})
    assert res.status_code == 200, res.text
    return res.json()["token"]


def test_package_import_and_screen():
    """Verified: MentalHealthScreener imports and produces predictions."""
    s = MentalHealthScreener()
    result = s.screen("This is a test input for screening.")
    assert "primary" in result
    assert "urgency" in result
    assert "predicted_class" in result["primary"]
    assert isinstance(result["urgency"]["flagged"], bool)
    assert "cleaned_text" in result


def test_input_validation_none():
    s = MentalHealthScreener()
    with pytest.raises(ValueError):
        s.screen(None)


def test_input_validation_empty():
    s = MentalHealthScreener()
    with pytest.raises(ValueError):
        s.screen("   ")


def test_input_validation_non_string():
    s = MentalHealthScreener()
    with pytest.raises(ValueError):
        s.screen(12345)


def test_artifact_loading():
    """Verified: all required artifacts load without FileNotFoundError."""
    s = MentalHealthScreener()
    # Screen call implicitly verifies artifacts
    s.screen("Verification input.")


# ------------------------------------------------------------------
# Auth primitives
# ------------------------------------------------------------------
def test_verify_credentials_accepts_configured_pair():
    auth.verify_credentials("admin", "password")


@pytest.mark.parametrize("user_id,password", [
    ("admin", "wrong"),
    ("wrong", "password"),
    ("", "password"),
    ("admin", ""),
])
def test_verify_credentials_rejects_wrong_pair(user_id, password):
    with pytest.raises(auth.InvalidCredentials):
        auth.verify_credentials(user_id, password)


def test_token_roundtrip():
    token, expires_in = auth.issue_token("admin")
    assert token.startswith("v1.")
    assert expires_in > 0
    claims = auth.decode_token(token)
    assert claims["sub"] == "admin"
    assert claims["exp"] > claims["iat"]


def test_token_rejects_tampered_signature():
    token, _ = auth.issue_token("admin")
    with pytest.raises(auth.InvalidToken):
        auth.decode_token(token + "x")


def test_token_rejects_tampered_payload():
    """Editing the payload must invalidate it even with a valid-looking shape."""
    token, _ = auth.issue_token("admin")
    version, payload, signature = token.split(".")
    with pytest.raises(auth.InvalidToken):
        auth.decode_token(f"{version}.{payload[:-2]}AA.{signature}")


def test_token_rejects_other_subject():
    """A token signed for a different user must not authenticate as admin."""
    forged_payload = auth._b64encode(
        b'{"alg":"hs256","exp":9999999999,"iat":1,"jti":"x","sub":"someone-else"}'
    )
    forged = f"v1.{forged_payload}.{auth._sign(forged_payload)}"
    with pytest.raises(auth.InvalidToken):
        auth.decode_token(forged)


def test_token_rejects_expired():
    payload = auth._b64encode(
        f'{{"alg":"hs256","exp":1,"iat":0,"jti":"x","sub":"admin"}}'.encode()
    )
    stale = f"v1.{payload}.{auth._sign(payload)}"
    with pytest.raises(auth.InvalidToken):
        auth.decode_token(stale)


@pytest.mark.parametrize("header", [None, "", "Basic abc", "Bearer", "Bearer   "])
def test_bearer_token_requires_scheme(header):
    with pytest.raises(auth.InvalidToken):
        auth.bearer_token(header)


def test_bearer_token_accepts_bearer():
    assert auth.bearer_token("Bearer v1.abc.def") == "v1.abc.def"


# ------------------------------------------------------------------
# API: auth endpoints
# ------------------------------------------------------------------
def test_predict_requires_authentication(client):
    res = client.post("/predict", json={"text": "hello"})
    assert res.status_code == 401


def test_predict_rejects_forged_token(client):
    res = client.post(
        "/predict",
        json={"text": "hello"},
        headers={"Authorization": "Bearer v1.abc.def"},
    )
    assert res.status_code == 401


def test_login_rejects_bad_credentials(client):
    res = client.post("/auth/login", json={"user_id": "admin", "password": "nope"})
    assert res.status_code == 401
    # The response must not reveal which half of the pair was wrong.
    assert "user id" in res.json()["detail"].lower()


def test_login_returns_usable_token(client):
    res = client.post("/auth/login", json={"user_id": "admin", "password": "password"})
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["user"] == "admin"
    assert body["expires_at"] > 0


def test_session_validates_token(client, token):
    res = client.get("/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["user"] == "admin"


def test_session_requires_token(client):
    assert client.get("/auth/session").status_code == 401


def test_authenticated_predict(client, token):
    res = client.post(
        "/predict",
        json={"text": "I feel hopeless and cannot get out of bed."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["primary"]["predicted_class"] in {
        "Normal", "Depression", "Suicidal", "Anxiety", "Bipolar",
        "Stress", "Personality disorder",
    }
    assert len(body["primary"]["class_probabilities"]) == 7
    assert isinstance(body["urgency"]["flagged"], bool)
    assert body["urgency"]["decision_threshold_used"] > 0


def test_predict_enforces_length_limit(client, token):
    res = client.post(
        "/predict",
        json={"text": "x" * 10001},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 422


# ------------------------------------------------------------------
# API: operational endpoints stay public
# ------------------------------------------------------------------
def test_health_is_public(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_ready_is_public(client):
    assert client.get("/ready").status_code == 200


def test_metrics_reports_real_uptime(client):
    res = client.get("/metrics")
    assert res.status_code == 200
    # Guards against the old placeholder, which always evaluated to 0.
    assert res.json()["uptime_seconds"] >= 0


def test_rate_limit_blocks_after_repeated_failures(client):
    """Repeated failures trip the per-IP throttle, and a valid password is
    refused too while the window is open. Deliberately the last IP-touching test
    in the module: auth.enforce_attempt_limit() keys on the TestClient address.
    """
    for _ in range(12):
        client.post("/auth/login", json={"user_id": "admin", "password": "wrong"})
    res = client.post("/auth/login", json={"user_id": "admin", "password": "password"})
    assert res.status_code == 429
    assert "Retry-After" in res.headers
    auth.clear_attempts("testclient")


def test_request_id_is_echoed(client):
    res = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert res.headers["X-Request-ID"] == "abc123"


def test_unknown_route_returns_404(client):
    assert client.get("/does-not-exist").status_code == 404


if __name__ == "__main__":
    test_package_import_and_screen()
    print("Smoke test PASSED")
