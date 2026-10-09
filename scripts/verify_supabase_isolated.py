"""Opt-in real integration for an explicitly isolated project and existing test users.

Uses only MENTAL_AI_TEST_* environment values, never a repository .env.
No account creation/emails/migration/deployment. Cleanup deletes only new row ids.
Missing inputs exit2 without network. --check-config never contacts the provider.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "SUPABASE_PUBLISHABLE_KEY",
            "USER_A_EMAIL", "USER_A_PASSWORD", "USER_A_ID", "USER_B_EMAIL", "USER_B_PASSWORD", "USER_B_ID")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-config", action="store_true")
    args = parser.parse_args()
    missing = ["MENTAL_AI_TEST_" + k for k in REQUIRED if not os.environ.get("MENTAL_AI_TEST_" + k)]
    if os.environ.get("MENTAL_AI_TEST_ISOLATED_PROJECT") != "1":
        missing.append("MENTAL_AI_TEST_ISOLATED_PROJECT=1 (explicit isolated-project assertion)")
    if missing:
        print(json.dumps({"status": "BLOCKED", "missing_variable_names": missing}))
        return 2
    if args.check_config:
        print(json.dumps({"status": "PASSED", "scope": "configuration presence only; no network or validation"}))
        return 0
    if os.environ["MENTAL_AI_TEST_USER_A_ID"] == os.environ["MENTAL_AI_TEST_USER_B_ID"]:
        print(json.dumps({"status": "FAILED", "reason": "Test identities must be distinct"}))
        return 1
    for key in ("SUPABASE_URL", "SUPABASE_SECRET_KEY", "SUPABASE_PUBLISHABLE_KEY"):
        os.environ[key] = os.environ["MENTAL_AI_TEST_" + key]
    os.environ["MENTAL_AI_ENV_FILE"] = str(ROOT / "tests" / "absent-isolated.env")
    sys.path[:0] = [str(ROOT), str(ROOT / "Step 12 - Packaging/package")]
    from api import db
    db.reset_client()
    from api import api as service
    from api.limits import PredictLimiter
    from fastapi.testclient import TestClient
    from scripts.source_fingerprint import fingerprint
    report = {"run_utc": datetime.now(timezone.utc).isoformat(), "layer": "real isolated GoTrue/PostgREST + actual ASGI/model",
              "checks": [], "cleanup": [], "source_fingerprint": fingerprint(ROOT)}
    created = []
    def check(label, condition):
        report["checks"].append({"requirement": label, "status": "PASSED" if condition else "FAILED"})
        if not condition:
            raise AssertionError(label)
    def bearer(token):
        return {"Authorization": "Bearer " + token}
    try:
        with tempfile.TemporaryDirectory(prefix="mental-ai-real-integration-") as temp:
            service.predict_limiter = PredictLimiter(str(Path(temp) / "limits.sqlite3"))
            with TestClient(service.app) as client:
                sessions = {}
                for owner in ("A", "B"):
                    login = client.post("/auth/login", json={"user_id": os.environ[f"MENTAL_AI_TEST_USER_{owner}_EMAIL"],
                        "password": os.environ[f"MENTAL_AI_TEST_USER_{owner}_PASSWORD"]})
                    check(f"{owner}: pre-provisioned authentication", login.status_code == 200)
                    session = login.json()
                    check(f"{owner}: verified expected identity before any write", session["user_id"] == os.environ[f"MENTAL_AI_TEST_USER_{owner}_ID"])
                    sessions[owner] = session
                check("Missing token rejected", client.post("/predict", json={"text": "synthetic check"}).status_code == 401)
                check("Invalid token rejected", client.post("/predict", headers=bearer("synthetic-invalid-token"), json={"text": "synthetic check"}).status_code == 401)
                token_a = sessions["A"]["token"]
                # Change a signature character, leaving payload/claims unchanged.
                head, payload, signature = token_a.rsplit(".", 2)
                tampered = head + "." + payload + "." + ("A" if signature[0] != "A" else "B") + signature[1:]
                check("Tampered signature rejected", client.post("/predict", headers=bearer(tampered), json={"text": "synthetic check"}).status_code == 401)
                expired = os.environ.get("MENTAL_AI_TEST_EXPIRED_ACCESS_TOKEN")
                if expired:
                    check("Provided expired token rejected", client.post("/predict", headers=bearer(expired), json={"text": "synthetic check"}).status_code == 401)
                else:
                    report["checks"].append({"requirement": "Real expired token", "status": "BLOCKED", "missing": "MENTAL_AI_TEST_EXPIRED_ACCESS_TOKEN from isolated project"})
                def submit(owner):
                    response = client.post("/predict", headers=bearer(sessions[owner]["token"]),
                        json={"text": "i wanna jump from 10th floor", "user_id": sessions["B" if owner == "A" else "A"]["user_id"]})
                    return owner, response
                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(submit, ["A", "B"]))
                # Record EVERY acknowledged new write before any assertion can
                # abort the loop. A wrong A route must not leave A/B rows behind.
                for owner, response in results:
                    try:
                        ack = response.json().get("persistence", {})
                        rid = ack.get("record_id")
                        if (response.status_code == 200 and ack.get("status") == "saved"
                                and isinstance(rid, str) and rid.strip()):
                            created.append((rid, sessions[owner]["user_id"]))
                    except (ValueError, TypeError, AttributeError):
                        pass  # Malformed/unacknowledged writes remain uncertain.
                provider = db.get_client()
                for owner, response in results:
                    check(f"{owner}: actual concurrent prediction returns200", response.status_code == 200)
                    result = response.json()
                    check(f"{owner}: reliable original safety retained", result["safety"]["level"] == "HIGH")
                    check(f"{owner}: save acknowledged", result["persistence"]["status"] == "saved")
                    rid = result["persistence"]["record_id"]
                    uid = sessions[owner]["user_id"]
                    history = client.get("/screenings", headers=bearer(sessions[owner]["token"])).json()
                    rows = [r for r in history["screenings"] if r["id"] == rid]
                    core = {k: v for k, v in result.items() if k != "persistence"}
                    check(f"{owner}: authoritative snapshot round-trip", len(rows) == 1 and rows[0]["analysis_result"] == core)
                    other = "B" if owner == "A" else "A"
                    other_history = client.get("/screenings", headers=bearer(sessions[other]["token"])).json()
                    check(f"{owner}: application owner filter", all(r["id"] != rid for r in other_history["screenings"]))
                    # Unprivileged direct PostgREST tests RLS independently from privileged server scoping.
                    for viewer in (owner, other):
                        direct = provider._call("GET", "/rest/v1/screenings", privileged=False,
                            params={"id": "eq." + rid}, access_token=sessions[viewer]["token"])
                        check(f"{owner}: unprivileged {viewer} RLS", direct.status == 200 and len(json.loads(direct.body)) == (1 if viewer == owner else 0))
                renewal = client.post("/auth/refresh", json={"refresh_token": sessions["A"]["refresh_token"]})
                check("Refresh retains expected identity", renewal.status_code == 200 and renewal.json()["user_id"] == sessions["A"]["user_id"])
                report["checks"].append({"requirement": "Network outage/expired SDK/logout UI/retention/deployed behavior", "status": "BLOCKED", "missing": "Controlled isolated fault access, real expiry/SDK browser setup and retention policy; stub engineering coverage is separate"})
    except Exception as exc:
        report["failure"] = {"type": type(exc).__name__} # No response bodies, keys, tokens or internal details.
    finally:
        # Never bulk-delete existing records, even from a test identity.
        for rid, uid in created:
            try:
                provider = db.get_client()
                reply = provider._call("DELETE", "/rest/v1/screenings", privileged=True,
                    params={"id": "eq." + rid, "user_id": "eq." + uid})
                report["cleanup"].append({"status": "PASSED" if reply.status in (200, 204) else "FAILED"})
            except Exception:
                report["cleanup"].append({"status": "FAILED"})
        path = ROOT / "reports" / ("supabase-isolated-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
        path.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({"report": str(path.relative_to(ROOT)), "checks": report["checks"], "cleanup": report["cleanup"]}))
    return 1 if "failure" in report or any(r["status"] == "FAILED" for r in report["cleanup"]) else 0

if __name__ == "__main__":
    raise SystemExit(main())
