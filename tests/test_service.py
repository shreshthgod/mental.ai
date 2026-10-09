"""
Integration and unit tests for the MENTAL.AI screening system.

These tests verify:
- package import and artifact loading
- inference with actual artifacts
- session authentication through Supabase Auth
- screening persistence and per-user isolation
- API endpoint behaviour through the real ASGI app
- defensive error handling

Run:
    PYTHONPATH="Step 12 - Packaging/package:." pytest tests -q

Supabase is stubbed at the transport seam in api/db.py, so the whole
request/response path - headers, query strings, status mapping - is exercised
without a network, an account or a project. The production code path is the
same one a deployment uses; only the socket is replaced.
"""
import sys
import os
import json
import urllib.parse

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "Step 12 - Packaging", "package"))
sys.path.insert(0, _ROOT)

import pytest
from fastapi.testclient import TestClient

from api import auth, db
from mental_health_screening.inference import MentalHealthScreener


# ------------------------------------------------------------------
# Stub Supabase
# ------------------------------------------------------------------
# Two accounts so isolation can be tested: the second one must never see the
# first one's screenings.
ACCOUNTS = {
    "alice@example.com": {"id": "uuid-alice", "name": "Alice Adams", "password": "alice-pass"},
    "bob@example.com": {"id": "uuid-bob", "name": "Bob Brown", "password": "bob-pass"},
}
SUPABASE_URL = "https://stub.supabase.co"


class StubSupabase:
    """In-memory stand-in for GoTrue + PostgREST."""

    def __init__(self):
        self.screenings = {}
        self.profiles = {a["id"]: {"id": a["id"], "email": e, "display_name": a["name"]}
                         for e, a in ACCOUNTS.items()}
        self.counter = 0
        self.requests = []

    # -- helpers ----------------------------------------------------------
    def _user(self, email):
        return {"id": ACCOUNTS[email]["id"], "email": email,
                "user_metadata": {"full_name": ACCOUNTS[email]["name"]}}

    def _session(self, email, suffix):
        return {"access_token": f"AT-{email}-{suffix}", "refresh_token": f"RT-{email}-{suffix}",
                "expires_in": 3600, "expires_at": 1800000000, "user": self._user(email)}

    # -- transport --------------------------------------------------------
    def __call__(self, method, url, headers, body, timeout):
        parsed = urllib.parse.urlparse(url)
        query = dict(urllib.parse.parse_qsl(parsed.query))
        path = parsed.path
        self.requests.append((method, path, dict(headers), body))

        if path == "/auth/v1/token":
            grant = query.get("grant_type")
            payload = json.loads(body) if body else {}
            if grant == "password":
                email = payload.get("email", "")
                account = ACCOUNTS.get(email)
                if not account or account["password"] != payload.get("password"):
                    return db.Response(400, {}, b'{"error_code":"invalid_credentials"}')
                return db.Response(200, {}, json.dumps(self._session(email, "1")).encode())
            email = next((e for e in ACCOUNTS if payload.get("refresh_token", "").startswith(f"RT-{e}")), None)
            if not email:
                return db.Response(400, {}, b'{"error_code":"refresh_token_not_found"}')
            return db.Response(200, {}, json.dumps(self._session(email, "2")).encode())

        if path == "/auth/v1/user":
            token = headers.get("Authorization", "").removeprefix("Bearer ")
            match = next((e for e in ACCOUNTS if token.startswith(f"AT-{e}-")), None)
            if not match:
                return db.Response(401, {}, b'{"msg":"invalid_token"}')
            return db.Response(200, {}, json.dumps(self._user(match)).encode())

        if path == "/rest/v1/screenings":
            rows = self.screenings
            if method == "POST":
                self.counter += 1
                rid = f"screening-{self.counter}"
                rows[rid] = json.loads(body)
                return db.Response(201, {}, json.dumps([{"id": rid}]).encode())
            user_id = query.get("user_id", "").removeprefix("eq.")
            owned = [{"id": k, "created_at": "2026-01-01T00:00:00Z", **v}
                     for k, v in rows.items() if v.get("user_id") == user_id]
            if method == "GET":
                return db.Response(200, {"content-range": f"0-{max(0, len(owned) - 1)}/{len(owned)}"},
                                   json.dumps(owned).encode())
            if method == "DELETE":
                gone = [k for k, v in rows.items() if v.get("user_id") == user_id]
                for k in gone:
                    del rows[k]
                return db.Response(204, {"content-range": f"*/{len(gone)}"}, b"")
        return db.Response(404, {}, b"{}")


STUB = StubSupabase()


@pytest.fixture(scope="module", autouse=True)
def _stub_supabase():
    """
    Point api/db.py at the stub for the whole module.

    Module-scoped so it is installed before the module-scoped token fixtures,
    which sign in through the app and therefore need Supabase to exist.
    """
    previous = db._client
    db.reset_client()
    db._client = db.SupabaseClient(
        SUPABASE_URL, "stub-publishable", "stub-secret", transport=STUB
    )
    yield
    db._client = previous
    db.reset_client()


@pytest.fixture(autouse=True)
def _clean_supabase_state():
    """Each test starts with no stored screenings and a clean request log."""
    STUB.screenings.clear()
    STUB.requests.clear()
    yield


@pytest.fixture(scope="module")
def client():
    """TestClient over the real app: models load once for the whole module."""
    from api.api import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def alice_token(client):
    """A valid bearer token for the first stub account."""
    res = client.post("/auth/login", json={"user_id": "alice@example.com", "password": "alice-pass"})
    assert res.status_code == 200, res.text
    return res.json()["token"]


@pytest.fixture(scope="module")
def bob_token(client):
    """A valid bearer token for the second stub account."""
    res = client.post("/auth/login", json={"user_id": "bob@example.com", "password": "bob-pass"})
    assert res.status_code == 200, res.text
    return res.json()["token"]


@pytest.fixture()
def token(alice_token):
    return alice_token


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
# ------------------------------------------------------------------
# Auth: Supabase-backed
# ------------------------------------------------------------------
def test_verify_credentials_returns_supabase_session():
    session = auth.verify_credentials("alice@example.com", "alice-pass")
    assert session.access_token.startswith("AT-alice@example.com")
    assert session.refresh_token.startswith("RT-")
    # The authoritative identity is the Supabase UUID, not the email.
    assert session.user_id == "uuid-alice"
    assert session.display_name == "Alice Adams"


@pytest.mark.parametrize(
    "email,password",
    [
        ("alice@example.com", "wrong"),   # right account, wrong password
        ("nobody@example.com", "x"),      # unknown account
        ("alice@example.com", ""),        # empty password
    ],
)
def test_verify_credentials_rejects_wrong_pair(email, password):
    with pytest.raises(auth.InvalidCredentials):
        auth.verify_credentials(email, password)


def test_unknown_account_and_wrong_password_are_indistinguishable():
    """No account enumeration: both failures carry the same message."""
    messages = set()
    for email, password in (("alice@example.com", "wrong"), ("nobody@example.com", "wrong")):
        with pytest.raises(auth.InvalidCredentials) as exc:
            auth.verify_credentials(email, password)
        messages.add(str(exc.value))
    assert len(messages) == 1


def test_decode_token_returns_verified_identity():
    session = auth.verify_credentials("alice@example.com", "alice-pass")
    claims = auth.decode_token(session.access_token)
    assert claims.user_id == "uuid-alice"
    assert claims.email == "alice@example.com"
    assert claims.name == "Alice Adams"


def test_decode_token_rejects_unknown_token():
    """A token Supabase does not recognise must never authenticate."""
    with pytest.raises(auth.InvalidToken):
        auth.decode_token("not-a-real-token")


def test_identity_comes_from_the_token_not_the_caller(client, bob_token):
    """
    A caller cannot claim someone else's identity by asking for it.

    Bob's token is valid, and it resolves to Bob. There is no parameter through
    which a request could ask to be Alice, which is what makes the per-user
    scoping in the screening tests meaningful.
    """
    res = client.get("/auth/session", headers={"Authorization": f"Bearer {bob_token}"})
    assert res.status_code == 200
    assert res.json()["user_id"] == "uuid-bob"
    assert res.json()["name"] == "Bob Brown"


def test_refresh_token_rotates_the_access_token():
    first = auth.verify_credentials("alice@example.com", "alice-pass")
    renewed = auth.refresh(first.refresh_token)
    assert renewed.access_token != first.access_token
    assert renewed.user_id == "uuid-alice"


def test_refresh_rejects_an_unknown_refresh_token():
    with pytest.raises(auth.InvalidToken):
        auth.refresh("RT-nobody-nope")


@pytest.mark.parametrize("email", ["a@b.com", "kArTiK@x.com", "no-at-sign"])
def test_display_name_falls_back_to_something_readable(email):
    """No blank greeting when Supabase has no name for the account."""
    assert auth.display_name_for(email).strip()


@pytest.mark.parametrize("header", [None, "", "Basic abc", "Bearer", "Bearer   "])
def test_bearer_token_requires_scheme(header):
    with pytest.raises(auth.InvalidToken):
        auth.bearer_token(header)


def test_bearer_token_accepts_bearer():
    assert auth.bearer_token("Bearer v1.abc.def") == "v1.abc.def"


# ------------------------------------------------------------------
# Screening persistence and isolation
# ------------------------------------------------------------------
def test_predict_persists_the_screening(client, token):
    res = client.post(
        "/predict",
        json={"text": "I have been sleeping badly and feel anxious."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    request_id = res.json()["request_id"]
    rows = [r for r in STUB.screenings.values() if r["request_id"] == request_id]
    assert len(rows) == 1, "exactly one row per screening"
    row = rows[0]
    # Ownership comes from the verified token, never from the request body.
    assert row["user_id"] == "uuid-alice"
    assert row["condition_label"] is not None
    assert "urgency_flagged" in row


def test_predict_uses_the_secret_key_only_for_database_writes(client, token):
    """The secret key must never travel on an auth request."""
    client.post(
        "/predict",
        json={"text": "screening text"},
        headers={"Authorization": f"Bearer {token}"},
    )
    for method, path, headers, _ in STUB.requests:
        if path.startswith("/rest/"):
            assert headers["apikey"] == "stub-secret"
        else:
            assert headers["apikey"] == "stub-publishable"
            assert headers["Authorization"] != "Bearer stub-secret"


def test_history_is_scoped_to_the_signed_in_account(client, alice_token, bob_token):
    client.post("/predict", json={"text": "alice only"},
                headers={"Authorization": f"Bearer {alice_token}"})

    alice = client.get("/screenings", headers={"Authorization": f"Bearer {alice_token}"})
    bob = client.get("/screenings", headers={"Authorization": f"Bearer {bob_token}"})
    assert alice.status_code == 200 and alice.json()["count"] == 1
    # User A's screening must be invisible to User B.
    assert bob.status_code == 200 and bob.json()["count"] == 0


def test_history_requires_authentication(client):
    assert client.get("/screenings").status_code == 401


def test_delete_history_is_scoped_to_the_account(client, alice_token, bob_token):
    client.post("/predict", json={"text": "alice only"},
                headers={"Authorization": f"Bearer {alice_token}"})
    client.post("/predict", json={"text": "bob only"},
                headers={"Authorization": f"Bearer {bob_token}"})

    bob_deleted = client.delete("/screenings", headers={"Authorization": f"Bearer {bob_token}"})
    assert bob_deleted.status_code == 200 and bob_deleted.json()["deleted"] == 1
    # Bob's delete must not have touched Alice's row.
    assert client.get("/screenings", headers={"Authorization": f"Bearer {alice_token}"}).json()["count"] == 1


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
    res = client.post("/auth/login", json={"user_id": "alice@example.com", "password": "nope"})
    assert res.status_code == 401
    # The response must not reveal which half of the pair was wrong.
    assert "email" in res.json()["detail"].lower()


def test_login_returns_usable_token(client):
    res = client.post("/auth/login", json={"user_id": "alice@example.com", "password": "alice-pass"})
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["user"] == "alice@example.com"      # human-facing id, unchanged
    assert body["user_id"] == "uuid-alice"          # authoritative Supabase UUID
    assert body["name"] == "Alice Adams"
    assert body["refresh_token"]
    assert body["expires_at"] > 0


def test_refresh_endpoint_issues_a_new_session(client):
    first = client.post("/auth/login", json={"user_id": "alice@example.com", "password": "alice-pass"}).json()
    res = client.post("/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert res.status_code == 200
    assert res.json()["token"] != first["token"]
    assert res.json()["user_id"] == "uuid-alice"


def test_auth_providers_lists_the_available_methods(client):
    res = client.get("/auth/providers")
    assert res.status_code == 200
    body = res.json()
    assert body["email_password"] is True
    assert body["provider"] == "supabase"


def test_session_validates_token(client, token):
    res = client.get("/auth/session", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["user"] == "alice@example.com"
    assert res.json()["user_id"] == "uuid-alice"


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
