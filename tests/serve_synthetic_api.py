"""Loopback-only development acceptance server: real routes/models, STUB provider.

Never import this module from production. No real identity/project is contacted.
Run explicitly with --isolated-development; storage lives only in this process.
"""
import argparse
import os
import tempfile
from pathlib import Path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--isolated-development", action="store_true", required=True)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="mental-ai-browser-") as temp:
        os.environ["MENTAL_AI_ENV_FILE"] = str(Path(temp) / "absent.env")
        os.environ["MENTAL_AI_LIMIT_STORE"] = str(Path(temp) / "limits.sqlite3")
        from _supabase_stub import StubSupabase, install
        install(StubSupabase())
        from api.api import app
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
