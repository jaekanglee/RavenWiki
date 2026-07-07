"""v0.7.94 — Lite bootstrap 3종 diff endpoint (vault vs raven install 템플릿).

difllib 표준 라이브러리 (외부 의존성 0). 동일 화이트리스트 (Tier 1 leak 방지).
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from raven.api.server import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def diff_vault(monkeypatch):
    """3종 + 변형된 vault (vs 템플릿 mismatch)."""
    reg = Path(tempfile.mkdtemp(prefix="raven-diff-reg-"))
    target = Path(tempfile.mkdtemp(prefix="raven-diff-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg))

    v_root = target / "diff-test-vault"
    v_root.mkdir()
    (v_root / "_meta" / "agents").mkdir(parents=True)

    # 3종을 템플릿과 **다르게** 작성 → diff가 나와야 함
    (v_root / "_meta" / "agents" / "SCHEMA.md").write_text(
        "# SCHEMA (vault-modified)\n\nvault edited line\n", encoding="utf-8"
    )
    (v_root / "_meta" / "agents" / "PROJECT-WORKFLOW.md").write_text(
        "# PROJECT-WORKFLOW (vault-modified)\n\nanother edited line\n", encoding="utf-8"
    )
    (v_root / "log.md").write_text(
        "# Vault Log (vault-modified)\n\n- vault init\n", encoding="utf-8"
    )
    # 비화이트 (negative test용)
    (v_root / "_meta" / "system").mkdir(parents=True)
    (v_root / "_meta" / "system" / "SECRET.md").write_text("secret", encoding="utf-8")

    (v_root / ".vault.json").write_text(json.dumps({
        "name": "diff-test-vault",
        "path": str(v_root),
        "mode": "personal",
        "owner": "user",
    }))

    c = TestClient(app)
    r = c.post("/api/vaults", json={
        "name": "diff-test-vault",
        "path": str(v_root),
        "bootstrap": False,
    })
    assert r.status_code == 200, f"create failed: {r.text}"

    yield v_root


@pytest.fixture
def identical_vault(monkeypatch):
    """3종을 raven 템플릿과 **동일하게** 작성 → diff identical=true."""
    reg = Path(tempfile.mkdtemp(prefix="raven-diff-ident-reg-"))
    target = Path(tempfile.mkdtemp(prefix="raven-diff-ident-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg))

    v_root = target / "identical-test-vault"
    v_root.mkdir()
    (v_root / "_meta" / "agents").mkdir(parents=True)

    # 템플릿 (raven install) 그대로 복사
    from pathlib import Path as _P
    template_root = _P(__file__).resolve().parent.parent / "raven" / "core" / "templates"
    (v_root / "_meta" / "agents" / "SCHEMA.md").write_text(
        (template_root / "agent" / "SCHEMA.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (v_root / "_meta" / "agents" / "PROJECT-WORKFLOW.md").write_text(
        (template_root / "agent" / "PROJECT-WORKFLOW.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (v_root / "log.md").write_text(
        (template_root / "log.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    (v_root / ".vault.json").write_text(json.dumps({
        "name": "identical-test-vault",
        "path": str(v_root),
        "mode": "personal",
        "owner": "user",
    }))

    c = TestClient(app)
    r = c.post("/api/vaults", json={
        "name": "identical-test-vault",
        "path": str(v_root),
        "bootstrap": False,
    })
    assert r.status_code == 200, f"create failed: {r.text}"

    yield v_root


# ──────────────────── 정상 diff ────────────────────

def test_diff_schema_returns_modified(client, diff_vault):
    r = client.get(
        "/api/vaults/diff-test-vault/guide-diff/_meta%2Fagents%2FSCHEMA.md"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["kind"] == "_meta/agents/SCHEMA.md"
    assert body["identical"] is False
    assert body["stats"]["added"] > 0 or body["stats"]["removed"] > 0
    # diff_lines 구조 검증
    assert isinstance(body["diff_lines"], list)
    assert len(body["diff_lines"]) > 0
    for line in body["diff_lines"]:
        assert "tag" in line
        assert "content" in line
        assert line["tag"] in ("+", "-", " ")


def test_diff_project_workflow_200(client, diff_vault):
    r = client.get(
        "/api/vaults/diff-test-vault/guide-diff/_meta%2Fagents%2FPROJECT-WORKFLOW.md"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["identical"] is False
    assert body["stats"]["removed"] >= 1  # vault가 다른 내용 → 템플릿 라인 일부 removed


def test_diff_log_md_200(client, diff_vault):
    r = client.get(
        "/api/vaults/diff-test-vault/guide-diff/log.md"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["identical"] is False
    assert body["stats"]["added"] >= 1


# ──────────────────── identical ────────────────────

def test_diff_identical_returns_no_changes(client, identical_vault):
    """SCHEMA/PROJECT-WORKFLOW는 동일 (template 그대로 복사) → identical=True.

    log.md는 `ensure_log()` 가 vault create 시 자동 append entry를 박기 때문에
    "template과 byte-equal" 일 수 없음. 이건 v0.7.65+ Lite bootstrap 정책의
    의도된 동작 (silent write 방지, README §8/§9). 따라서 log.md는 identical
    검증에서 제외 — schema/workflow 가 true 면 정책 정합.
    """
    for kind in ("_meta%2Fagents%2FSCHEMA.md", "_meta%2Fagents%2FPROJECT-WORKFLOW.md"):
        r = client.get(f"/api/vaults/identical-test-vault/guide-diff/{kind}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["identical"] is True, f"{kind} should be identical but got: {body}"
        assert body["diff_lines"] == []
        assert body["stats"]["added"] == 0
        assert body["stats"]["removed"] == 0


# ──────────────────── 비화이트 (403) ────────────────────

def test_diff_rejects_non_whitelist_403(client, diff_vault):
    """_meta/system/SECRET.md (비화이트, Tier 1) → 403."""
    r = client.get(
        "/api/vaults/diff-test-vault/guide-diff/_meta%2Fsystem%2FSECRET.md"
    )
    assert r.status_code == 403, r.text
    assert "whitelist" in r.json()["detail"].lower()


def test_diff_rejects_content_path_403(client, diff_vault):
    """content/note.md (사용자 페이지, 비화이트) → 403."""
    r = client.get(
        "/api/vaults/diff-test-vault/guide-diff/content%2Fnote.md"
    )
    assert r.status_code == 403, r.text


# ──────────────────── 404 / 400 ────────────────────

def test_diff_404_for_unknown_vault(client, diff_vault):
    r = client.get("/api/vaults/does-not-exist-xyz/guide-diff/log.md")
    assert r.status_code == 404, r.text


# ──────────────────── 큰 diff truncation ────────────────────

def test_diff_truncates_at_200_lines(client, diff_vault):
    """PROJECT-WORKFLOW.md 템플릿 (~333줄) 와 많이 다른 vault → truncation=True."""
    # vault 파일을 매우 다르게 작성 (300줄 추가)
    big_content = "\n".join([f"vault-line-{i}" for i in range(300)]) + "\n"
    (diff_vault / "_meta" / "agents" / "PROJECT-WORKFLOW.md").write_text(
        big_content, encoding="utf-8"
    )
    r = client.get(
        "/api/vaults/diff-test-vault/guide-diff/_meta%2Fagents%2FPROJECT-WORKFLOW.md"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["identical"] is False
    assert body["truncated"] is True
    assert body["truncation_note"] is not None
    assert "200" in body["truncation_note"]
    # 200줄 이하로 truncate
    assert len(body["diff_lines"]) <= 200
