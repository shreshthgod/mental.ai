"""Pure harness orchestration: no provider/network, models or actual records."""
from types import SimpleNamespace


def test_harness_remembers_all_acknowledged_concurrent_writes_before_assertions(monkeypatch, tmp_path):
    from scripts import verify_supabase_isolated as harness
    from api import db
    from api import api as service  # Resolve before replacing harness report root.
    import fastapi.testclient

    monkeypatch.setattr(harness, "ROOT", tmp_path)
    monkeypatch.setattr(harness.sys, "path", list(harness.sys.path))
    monkeypatch.setattr(service, "predict_limiter", service.predict_limiter)
    (tmp_path / "reports").mkdir()
    monkeypatch.setattr(harness.sys, "argv", ["verify_supabase_isolated.py"])
    monkeypatch.setenv("MENTAL_AI_TEST_ISOLATED_PROJECT", "1")
    for name in harness.REQUIRED:
        monkeypatch.setenv("MENTAL_AI_TEST_" + name, "synthetic-" + name)
    for name in ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "SUPABASE_PUBLISHABLE_KEY", "MENTAL_AI_ENV_FILE"):
        monkeypatch.setenv(name, "synthetic-placeholder")  # Track/restore later main mutations.

    sessions = {owner: {"user_id": "synthetic-USER_" + owner + "_ID",
                        "token": "head.payload.signature-" + owner, "refresh_token": "synthetic-refresh"}
                for owner in ("A", "B")}
    calls = []
    class Provider:
        def _call(self, method, path, **options):
            calls.append((method, options["params"]))
            return SimpleNamespace(status=204)
    monkeypatch.setattr(db, "reset_client", lambda: None)
    monkeypatch.setattr(db, "get_client", lambda: Provider())

    class Reply:
        def __init__(self, status, value):
            self.status_code, self.value = status, value
        def json(self):
            return self.value
    class Client:
        def __init__(self, app):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, path, json, headers=None):
            if path == "/auth/login":
                owner = "A" if json["user_id"] == "synthetic-USER_A_EMAIL" else "B"
                return Reply(200, sessions[owner])
            owner = next((key for key in sessions if (headers or {}).get("Authorization") ==
                          "Bearer " + sessions[key]["token"]), None)
            if owner is None:
                return Reply(401, {})
            return Reply(200, {"safety": {"level": "NONE_DETECTED" if owner == "A" else "HIGH"},
                               "persistence": {"status": "saved", "record_id": "new-" + owner}})
    monkeypatch.setattr(fastapi.testclient, "TestClient", Client)
    assert harness.main() == 1  # Deliberately wrong A routing remains a failed assertion.
    assert calls == [
        ("DELETE", {"id": "eq.new-A", "user_id": "eq.synthetic-USER_A_ID"}),
        ("DELETE", {"id": "eq.new-B", "user_id": "eq.synthetic-USER_B_ID"}),
    ]
