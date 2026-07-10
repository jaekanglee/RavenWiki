"""GET /api/vaults/{name}/lint 및 .../lint/summary 응답에 checks 필드가 있는지 검증."""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core import lint as lint_module
from raven.core import log as log_module
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


@pytest.fixture
def client_and_vault(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-lintapi-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-lintapi-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    v = Vault.create("lintapi-test", target_root / "lintapi-test", bootstrap=False)
    from raven.api.server import app
    with TestClient(app) as c:
        yield c, v
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


def test_get_lint_write_log_subject_uses_dynamic_check_count(client_and_vault):
    """write_log=true로 append된 log.md subject가 하드코딩된 '12개'가 아니라
    CHECK_REGISTRY 기반 동적 개수(현재 23개)를 반영하는지 검증.

    회귀 대상: raven/api/server.py get_lint()의 write_log 블록이 CLI와
    달리 `subject=f"lint 12개 (...)"`로 하드코딩되어 있던 버그.
    """
    client, v = client_and_vault
    r = client.get("/api/vaults/lintapi-test/lint?write_log=true")
    assert r.status_code == 200

    entries = log_module.list_entries(v, action="lint")
    assert entries, "log.md에 lint action entry가 기록되어야 함"
    subject = entries[-1]["subject"]
    expected_count = str(len(lint_module.CHECK_REGISTRY))
    assert expected_count in subject, (
        f"log.md subject={subject!r}에 CHECK_REGISTRY 개수({expected_count}개)가 반영되지 않음"
    )
    assert "12개" not in subject, f"log.md subject={subject!r}에 하드코딩된 stale count(12개)가 남아있음"
