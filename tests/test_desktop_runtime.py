"""Lifecycle contract for the local Python Core used by the desktop spike."""
from __future__ import annotations

import json
import select
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]


def _wait_for_ready(process: subprocess.Popen[str], timeout: float = 5.0) -> dict:
    assert process.stdout is not None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        readable, _, _ = select.select([process.stdout], [], [], 0.1)
        if readable:
            line = process.stdout.readline()
            if line:
                return json.loads(line)
        if process.poll() is not None:
            stderr = process.stderr.read() if process.stderr else ""
            raise AssertionError(f"desktop core exited early: {stderr}")
    raise AssertionError("desktop core did not report readiness")


def test_desktop_core_reports_loopback_health_and_stops_cleanly() -> None:
    process = subprocess.Popen(
        [sys.executable, "-m", "raven.desktop.runtime"],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        ready = _wait_for_ready(process)
        assert ready["host"] == "127.0.0.1"
        assert isinstance(ready["port"], int) and ready["port"] > 0

        with urlopen(f"http://{ready['host']}:{ready['port']}/health", timeout=2) as response:
            assert response.status == 200
            assert json.load(response) == {"status": "ready"}
    finally:
        process.terminate()
        process.wait(timeout=3)

    assert process.returncode is not None
