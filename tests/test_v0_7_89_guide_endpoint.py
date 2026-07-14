"""v0.7.89 — Lite bootstrap 3종 read-only viewer (Dashboard /guides 페이지).

Endpoint:
  GET /api/vaults/{name}/guide/{kind:path}   — 화이트리스트 3종만 read-only 반환

화이트리스트:
  - _meta/agents/SCHEMA.md
  - _meta/agents/RAVEN-CONTRACT.md
  - _meta/agents/PROJECT-WORKFLOW.md (legacy compatibility)
  - log.md

가드:
  1) 화이트리스트 외 kind → 403
  2) vault 미존재 → 404
  3) 화이트리스트 kind이지만 파일 없음 → 404
  4) 디렉토리 path → 400
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
def guide_vault(monkeypatch):
    """Lite bootstrap 3종 + 비화이트 파일을 모두 갖춘 vault.

    - _meta/agents/SCHEMA.md              ← 화이트 (200)
    - _meta/agents/RAVEN-CONTRACT.md      ← 화이트 (200)
    - _meta/agents/PROJECT-WORKFLOW.md    ← 화이트 (200)
    - log.md                              ← 화이트 (200)
    - _meta/system/SECRET.md              ← 비화이트 (403 검증용)
    - content/note.md                     ← 비화이트 (403 검증용)
    - _meta/agents/                       ← 디렉토리 (400 검증용)
    """
    reg_root = Path(tempfile.mkdtemp(prefix="raven-guide-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-guide-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))

    v_root = target_root / "guide-test-vault"
    v_root.mkdir()
    (v_root / "_meta" / "agents").mkdir(parents=True)
    (v_root / "_meta" / "system").mkdir(parents=True)
    (v_root / "content").mkdir()

    (v_root / "_meta" / "agents" / "SCHEMA.md").write_text(
        "# SCHEMA\nfrontmatter v2.4 — type 9종", encoding="utf-8"
    )
    (v_root / "_meta" / "agents" / "RAVEN-CONTRACT.md").write_text(
        "# RAVEN-CONTRACT\n기술 계약 / MCP / 권한", encoding="utf-8"
    )
    (v_root / "_meta" / "agents" / "PROJECT-WORKFLOW.md").write_text(
        "# PROJECT-WORKFLOW\n읽기순서 / MCP 매핑 / 권한", encoding="utf-8"
    )
    (v_root / "log.md").write_text(
        "# 작업 이력\n\n- 2026-07-07 vault 생성\n", encoding="utf-8"
    )
    # 비화이트 (negative test용)
    (v_root / "_meta" / "system" / "SECRET.md").write_text("system secret", encoding="utf-8")
    (v_root / "content" / "note.md").write_text("user note", encoding="utf-8")
    # 디렉토리 path (negative test용) — _meta/agents/ 자체는 dir

    (v_root / ".vault.json").write_text(json.dumps({
        "name": "guide-test-vault",
        "path": str(v_root),
        "mode": "personal",
        "owner": "user",
    }))

    c = TestClient(app)
    r = c.post("/api/vaults", json={
        "name": "guide-test-vault",
        "path": str(v_root),
        "bootstrap": False,
    })
    assert r.status_code == 200, f"create failed: {r.text}"

    yield v_root


# ──────────────────── 화이트리스트 (200) ────────────────────

def test_read_guide_schema_200(client, guide_vault):
    """SCHEMA.md (화이트) → 200 + content 반환."""
    r = client.get("/api/vaults/guide-test-vault/guide/_meta%2Fagents%2FSCHEMA.md")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["kind"] == "_meta/agents/SCHEMA.md"
    assert "frontmatter v2.4" in body["content"]
    assert body["size"] > 0
    assert body["modified"] is not None


def test_read_guide_raven_contract_200(client, guide_vault):
    """RAVEN-CONTRACT.md (화이트) → 200."""
    r = client.get("/api/vaults/guide-test-vault/guide/_meta%2Fagents%2FRAVEN-CONTRACT.md")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "_meta/agents/RAVEN-CONTRACT.md"
    assert "기술 계약" in body["content"]


def test_read_guide_project_workflow_200(client, guide_vault):
    """PROJECT-WORKFLOW.md (화이트) → 200."""
    r = client.get("/api/vaults/guide-test-vault/guide/_meta%2Fagents%2FPROJECT-WORKFLOW.md")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "_meta/agents/PROJECT-WORKFLOW.md"
    assert "MCP 매핑" in body["content"]


def test_read_guide_log_md_200(client, guide_vault):
    """log.md (화이트) → 200."""
    r = client.get("/api/vaults/guide-test-vault/guide/log.md")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "log.md"
    assert "2026-07-07" in body["content"]


# ──────────────────── 비화이트 (403) ────────────────────

def test_read_guide_rejects_system_path_403(client, guide_vault):
    """_meta/system/SECRET.md (비화이트, system/ = Tier 1 leak) → 403."""
    r = client.get("/api/vaults/guide-test-vault/guide/_meta%2Fsystem%2FSECRET.md")
    assert r.status_code == 403, r.text
    assert "whitelist" in r.json()["detail"].lower()


def test_read_guide_rejects_content_path_403(client, guide_vault):
    """content/note.md (사용자 페이지, 비화이트) → 403.

    /guide endpoint는 Lite bootstrap 3종만 노출 — 사용자가 자기 페이지를 여기서
    보려는 게 아님. content 보려면 /page/{vault}/{slug} 사용.
    """
    r = client.get("/api/vaults/guide-test-vault/guide/content%2Fnote.md")
    assert r.status_code == 403, r.text


# ──────────────────── 404 / 403 fail-closed ────────────────────

def test_read_guide_403_for_system_path(client, guide_vault):
    """화이트 kind가 아니면 무조건 403 (file 존재 여부와 무관).

    가드 우선순위: 화이트리스트 403 → 파일 존재 404 → 디렉토리 400.
    화이트 kind가 아닌 경로는 파일이 있어도 403. (Tier 1 leak 방지 핵심.)
    """
    r = client.get("/api/vaults/guide-test-vault/guide/_meta%2Fsystem%2FSCHEMA.md")
    assert r.status_code == 403, r.text
    assert "whitelist" in r.json()["detail"].lower()


def test_read_guide_403_for_path_traversal(client, guide_vault):
    """path traversal 시도는 403 (화이트리스트 매칭 실패). FastAPI가 '..'을
    normalize하지만 화이트리스트 외 경로는 fail-closed."""
    # '..'은 FastAPI가 normalize → 화이트리스트 매칭 안 됨 → 403
    r = client.get("/api/vaults/guide-test-vault/guide/_meta%2F..%2F..%2Fetc%2Fpasswd")
    assert r.status_code == 403, r.text


def test_read_guide_404_for_unknown_vault(client, guide_vault):
    r = client.get("/api/vaults/does-not-exist-xyz/guide/log.md")
    assert r.status_code == 404, r.text
