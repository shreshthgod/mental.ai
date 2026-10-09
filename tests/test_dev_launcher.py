"""Control child programs to verify launcher gating/configuration/lifecycle."""
import os
from pathlib import Path
import subprocess
import signal

ROOT = Path(__file__).resolve().parents[1]


def run_launcher(tmp_path, ready):
    commands = tmp_path / "commands"
    commands.mkdir()
    python = commands / "test-python"
    python.write_text('''#!/bin/bash
if [ "$1" = "-c" ]; then
  echo "$3" >> "$PROBE_LOG"
  exit "$PROBE_STATUS"
fi
echo $$ > "$PID_LOG"
exec sleep 60
''')
    python.chmod(0o700)
    npm = commands / "npm"
    npm.write_text('''#!/bin/bash
echo "$VITE_DEV_PROXY_TARGET $*" > "$FRONTEND_LOG"
''')
    npm.chmod(0o700)
    # The old /health gate treats any HTTP200 as ready, even if readiness fails.
    curl = commands / "curl"
    curl.write_text("#!/bin/bash\nexit 0\n")
    curl.chmod(0o700)
    env = {**os.environ, "PATH": f"{commands}:{os.environ['PATH']}", "PYTHON": str(python),
           "API_PORT": "8127", "WEB_PORT": "5199", "DEV_STARTUP_TIMEOUT_SECONDS": "1",
           "DEV_BACKEND_LOG": str(tmp_path / "backend.log"),
           "PROBE_STATUS": "0" if ready else "1", "PROBE_LOG": str(tmp_path / "probe.log"),
           "PID_LOG": str(tmp_path / "backend.pid"), "FRONTEND_LOG": str(tmp_path / "frontend.log")}
    try:
        result = subprocess.run(["bash", str(ROOT / "start-dev.sh")], env=env,
                                text=True, capture_output=True, timeout=8)
    except subprocess.TimeoutExpired:
        pid_file = tmp_path / "backend.pid"
        if pid_file.exists():
            try:
                os.kill(int(pid_file.read_text()), signal.SIGTERM)
            except ProcessLookupError:
                pass
        raise
    return result, tmp_path


def test_launcher_waits_for_ready_and_connects_custom_ports(tmp_path):
    result, work = run_launcher(tmp_path, True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "/ready" in (work / "probe.log").read_text()
    assert "http://127.0.0.1:8127" in (work / "frontend.log").read_text()
    assert "--strictPort" in (work / "frontend.log").read_text()
    pid = int((work / "backend.pid").read_text())
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        pass
    else:
        raise AssertionError("Launcher left its backend running")


def test_launcher_does_not_start_frontend_when_required_readiness_fails(tmp_path):
    result, work = run_launcher(tmp_path, False)
    assert result.returncode != 0
    assert not (work / "frontend.log").exists()
