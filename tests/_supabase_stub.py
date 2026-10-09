"""
In-memory stand-in for Supabase GoTrue + PostgREST.

Shared by the API contract tests so they can exercise the real request path -
routing, authentication, validation and persistence - without a network or real
credentials. It is a STUB: it proves our contract behaves as written, it does
not prove anything about Supabase itself.

Secrets are not involved. The values below are fixtures, not credentials.
"""
from __future__ import annotations

import json
import urllib.parse

from api import db

ACCOUNTS = {
    "alice@example.com": {"id": "uuid-alice", "name": "Alice Adams", "password": "alice-pass"},
    "bob@example.com": {"id": "uuid-bob", "name": "Bob Brown", "password": "bob-pass"},
}


class StubSupabase:
    """Records every call so tests can assert on what left the service."""

    def __init__(self) -> None:
        self.screenings: dict[str, dict] = {}
        self.profiles = {
            a["id"]: {"id": a["id"], "email": e, "display_name": a["name"]}
            for e, a in ACCOUNTS.items()
        }
        self.counter = 0
        self.requests: list[tuple[str, str, dict, bytes | None]] = []
        # Test hooks.
        self.unreachable = False        # transport fails -> status 0
        self.rest_status: dict[str, int] = {}  # path -> forced status

    def _user(self, email):
        return {
            "id": ACCOUNTS[email]["id"],
            "email": email,
            "user_metadata": {"full_name": ACCOUNTS[email]["name"]},
        }

    def _session(self, email, suffix):
        return {
            "access_token": f"AT-{email}-{suffix}",
            "refresh_token": f"RT-{email}-{suffix}",
            "expires_in": 3600,
            "expires_at": 1800000000,
            "user": self._user(email),
        }

    def __call__(self, method, url, headers, body, timeout):
        parsed = urllib.parse.urlparse(url)
        query = dict(urllib.parse.parse_qsl(parsed.query))
        path = parsed.path
        self.requests.append((method, path, dict(headers), body))

        if self.unreachable:
            return db.Response(status=0, headers={}, body=b"")
        if path in self.rest_status:
            return db.Response(self.rest_status[path], {}, b'{"error":"forced"}')

        if path == "/auth/v1/token":
            grant = query.get("grant_type")
            payload = json.loads(body) if body else {}
            if grant == "password":
                email = payload.get("email", "")
                account = ACCOUNTS.get(email)
                if not account or account["password"] != payload.get("password"):
                    return db.Response(400, {}, b'{"error_code":"invalid_credentials"}')
                return db.Response(200, {}, json.dumps(self._session(email, "1")).encode())
            wanted = payload.get("refresh_token", "")
            email = next((e for e in ACCOUNTS if wanted.startswith(f"RT-{e}-")), None)
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
            if method == "POST":
                self.counter += 1
                rid = f"screening-{self.counter}"
                self.screenings[rid] = json.loads(body)
                return db.Response(201, {}, json.dumps([{"id": rid}]).encode())
            user_id = query.get("user_id", "").removeprefix("eq.")
            owned = [
                {"id": k, "created_at": "2026-01-01T00:00:00Z", **v}
                for k, v in self.screenings.items()
                if v.get("user_id") == user_id
            ]
            if method == "GET":
                return db.Response(
                    200,
                    {"content-range": f"0-{max(0, len(owned) - 1)}/{len(owned)}"},
                    json.dumps(owned).encode(),
                )
            if method == "DELETE":
                gone = [k for k, v in self.screenings.items() if v.get("user_id") == user_id]
                for k in gone:
                    del self.screenings[k]
                return db.Response(204, {"content-range": f"*/{len(gone)}"}, b"")

        return db.Response(404, {}, b"{}")


def install(stub: StubSupabase) -> None:
    """Point api/db.py at the stub for the duration of a test."""
    db.reset_client()
    db._client = db.SupabaseClient(
        "https://stub.supabase.co", "stub-publishable", "stub-secret", transport=stub
    )