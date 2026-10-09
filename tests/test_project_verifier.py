"""The public verifier must reject unavailable observations and failed checks."""
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_verifier_exits_nonzero_for_missing_artifacts(tmp_path):
    env = {**os.environ, "ARTIFACTS_DIR": str(tmp_path / "missing")}
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/verify_project.py")],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0, result.stdout


def test_verifier_does_not_accept_unavailable_models_as_working():
    from scripts.verify_project import check_screen_result
    result = {
        "primary": {"status": "unavailable"},
        "urgency": {"status": "unavailable"},
        "safety": {"level": "HIGH", "subject": "self", "temporal_context": "current",
                   "immediacy": "not_stated", "support_action": "Contact someone you trust for support."},
        "components": {"preprocessing": "unavailable"},
    }
    checks = check_screen_result(result)
    assert any(check.status == "FAILED" and check.name == "Legacy inference" for check in checks)
    assert any(check.status == "FAILED" and check.name == "Preprocessing" for check in checks)
    assert any(check.status == "PASSED" and check.name == "Original-case safety" for check in checks)
