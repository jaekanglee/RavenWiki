"""GET /api/vaults/{name}/lint 및 .../lint/summary 응답에 checks 필드가 있는지 검증."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core.vault import Vault


@pytest.fixture
def client(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-lintapi-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-lintapi-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    Vault.create("lintapi-test", target_root / "lintapi-test", bootstrap=False)
    from raven.api.server import app
    with TestClient(app) as c:
        yield c
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def test_get_lint_includes_checks_field(client):
    r = client.get("/api/vaults/lintapi-test/lint")
    assert r.status_code == 200
    body = r.json()
    assert "checks" in body
    assert body["checks"]["#4"] == "고아 문서"
    assert len(body["checks"]) == 23


def test_get_lint_summary_includes_checks_field(client):
    r = client.get("/api/vaults/lintapi-test/lint/summary")
    assert r.status_code == 200
    body = r.json()
    assert "checks" in body
    assert len(body["checks"]) == 23
