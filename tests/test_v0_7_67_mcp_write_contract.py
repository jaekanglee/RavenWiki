"""v0.7.67 (평가 A#1) — MCP 쓰기 경로의 단일 쓰기 계약(contracts.write_page) 편입 가드.

pre-v0.7.67 MCP wiki_update는 독자 구현이었다:
  - slug 검증 없음 → `../` / 절대경로로 vault 밖 파일 쓰기 가능 (path traversal)
  - frontmatter_data 전달 시 기존 메타를 병합이 아닌 "대체" → created/tags 소실
  - .vault.json의 agents 허용목록(write allowlist) 우회
  - provenance가 스칼라 `actor:` (CLI/API는 `agents:` 리스트) — 표면 간 불일치

이 파일은 위 4가지가 재발하지 않음을 고정한다 (AGENTS.md §8: write contract
변경 시 최소 5개 테스트).
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import frontmatter
import pytest

from raven.mcp.tools import ADMIN, WRITE, VaultContext
from raven.mcp.tools.write import wiki_delete, wiki_rename, wiki_update


@pytest.fixture
def temp_vault(tmp_path: Path) -> Path:
    (tmp_path / "content").mkdir()
    (tmp_path / "log.md").write_text("# log\n", encoding="utf-8")
    return tmp_path


# ─────────────── 1. path traversal 차단 ───────────────


def test_update_rejects_parent_traversal(temp_vault: Path, tmp_path: Path):
    ctx = VaultContext(vault=temp_vault, mode=WRITE)
    r = wiki_update(slug="../escape", content="pwned\n", actor="mallory", ctx=ctx)
    assert r["ok"] is False
    assert r.get("error") == "invalid_slug"
    assert not (temp_vault.parent / "escape.md").exists()


def test_update_rejects_absolute_slug(temp_vault: Path, tmp_path: Path):
    ctx = VaultContext(vault=temp_vault, mode=WRITE)
    outside = tmp_path / "outside-target"
    r = wiki_update(slug=str(outside), content="pwned\n", actor="mallory", ctx=ctx)
    assert r["ok"] is False
    assert r.get("error") == "invalid_slug"
    assert not outside.with_suffix(".md").exists()


def test_delete_rejects_traversal(temp_vault: Path):
    ctx = VaultContext(vault=temp_vault, mode=ADMIN)
    r = wiki_delete(slug="../../etc/passwd", ctx=ctx)
    assert r["ok"] is False
    assert r.get("error") == "invalid_slug"


def test_rename_rejects_traversal_target(temp_vault: Path):
    slug = f"content/page_{uuid.uuid4().hex[:8]}"
    (temp_vault / f"{slug}.md").write_text(
        "---\ntitle: t\n---\n\nbody\n", encoding="utf-8"
    )
    ctx = VaultContext(vault=temp_vault, mode=ADMIN)
    r = wiki_rename(old_slug=slug, new_slug="../stolen", ctx=ctx)
    assert r["ok"] is False
    assert r.get("error") == "invalid_slug"
    assert not (temp_vault.parent / "stolen.md").exists()


# ─────────────── 2. frontmatter_data는 병합 (created/tags 보존) ───────────────


def test_update_frontmatter_data_preserves_created_and_tags(temp_vault: Path):
    slug = f"content/keep_{uuid.uuid4().hex[:8]}"
    fp = temp_vault / f"{slug}.md"
    fp.write_text(
        "---\ntitle: Keep\ntype: concept\ncreated: 2026-01-01\n"
        "tags:\n  - alpha\n  - beta\n---\n\nv1\n",
        encoding="utf-8",
    )
    ctx = VaultContext(vault=temp_vault, mode=WRITE)
    r = wiki_update(
        slug=slug, content="v2\n",
        frontmatter_data={"confidence": "high"},
        actor="tester", ctx=ctx,
    )
    assert r["ok"] is True
    post = frontmatter.loads(fp.read_text(encoding="utf-8"))
    assert str(post.metadata.get("created")) == "2026-01-01"  # NOT reset
    assert list(post.metadata.get("tags") or []) == ["alpha", "beta"]  # NOT erased
    assert post.metadata.get("confidence") == "high"  # update applied


# ─────────────── 3. .vault.json agents allowlist 준수 ───────────────


def test_update_honors_vault_agents_allowlist(temp_vault: Path):
    (temp_vault / ".vault.json").write_text(
        json.dumps({"path": str(temp_vault), "agents": ["trusted-bot"]}),
        encoding="utf-8",
    )
    ctx = VaultContext(vault=temp_vault, mode=WRITE)
    denied = wiki_update(
        slug="content/gated", content="nope\n", actor="rogue-bot", ctx=ctx,
    )
    assert denied["ok"] is False
    assert not (temp_vault / "content" / "gated.md").exists()

    allowed = wiki_update(
        slug="content/gated", content="yes\n", actor="trusted-bot", ctx=ctx,
    )
    assert allowed["ok"] is True
    assert (temp_vault / "content" / "gated.md").exists()


# ─────────────── 4. provenance 형식 통일 (agents: 리스트) ───────────────


def test_update_provenance_is_agents_list_and_appends(temp_vault: Path):
    slug = f"content/prov_{uuid.uuid4().hex[:8]}"
    fp = temp_vault / f"{slug}.md"
    fp.write_text(
        "---\ntitle: P\ntype: concept\nagents:\n"
        "  - name: old-bot\n    timestamp: 2026-01-01T00:00:00\n---\n\nv1\n",
        encoding="utf-8",
    )
    ctx = VaultContext(vault=temp_vault, mode=WRITE)
    r = wiki_update(slug=slug, content="v2\n", actor="new-bot", ctx=ctx)
    assert r["ok"] is True
    post = frontmatter.loads(fp.read_text(encoding="utf-8"))
    names = [a.get("name") for a in (post.metadata.get("agents") or [])]
    assert names == ["old-bot", "new-bot"]  # 이력 보존 + append
    assert "actor" not in post.metadata  # 스칼라 키는 더 이상 기록하지 않음


# ─────────────── 5. 재색인 (평가 A#2): MCP 쓰기 후 wiki.db 갱신 ───────────────


def test_wiki_update_rebuilds_index_visible_to_fts(temp_vault: Path):
    """pre-v0.7.67: wiki_update never rebuilt wiki.db — a page written via
    MCP was invisible to DB-backed reads until a manual `raven build`."""
    from raven.mcp.db import search_fts

    ctx = VaultContext(vault=temp_vault, mode=WRITE)
    slug = f"content/findme_{uuid.uuid4().hex[:8]}"
    r = wiki_update(
        slug=slug, content="uniquemarkerxyz body\n",
        frontmatter_data={"title": "Findme", "type": "concept"},
        actor="tester", ctx=ctx,
    )
    assert r["ok"] is True
    assert (temp_vault / "wiki.db").exists()
    hits = search_fts("uniquemarkerxyz", vault=temp_vault)
    assert any(slug in h.get("slug", "") for h in hits)


def test_wiki_delete_archives_nested_page_restorably(temp_vault: Path):
    """평가 B#5 회귀 가드: pre-v0.7.67 MCP wiki_delete flattened the archive
    path (`_archive/<stem>-<ts>.md`), so a nested page restored to the vault
    root instead of its original nested slug. Now it uses the same
    core.archive.archive_page recipe CLI/API use — nesting is preserved."""
    from raven.core.archive import restore_archived
    from raven.core.registry import VaultMeta
    from raven.core.vault import Vault as _Vault

    slug = f"content/sub/nested_{uuid.uuid4().hex[:8]}"
    (temp_vault / f"{slug}.md").parent.mkdir(parents=True, exist_ok=True)
    (temp_vault / f"{slug}.md").write_text(
        "---\ntitle: Nested\ntype: concept\n---\n\nbody\n", encoding="utf-8"
    )
    ctx = VaultContext(vault=temp_vault, mode=ADMIN)
    r = wiki_delete(slug=slug, ctx=ctx)
    assert r["ok"] is True
    assert r["archived"].startswith("_archive/content/sub/")

    v = _Vault.load(VaultMeta(name=temp_vault.name, path=temp_vault))
    result = restore_archived(v, slug)  # restore by original slug
    assert result.ok is True
    assert result.restored_to == f"{slug}.md"
    assert (temp_vault / f"{slug}.md").exists()


def test_wiki_delete_rebuild_reaches_real_build_db(temp_vault: Path):
    """pre-v0.7.67: _rebuild_db looked for <vault>/scripts/build_db.py,
    which doesn't exist in a normal user vault — silent permanent no-op."""
    slug = f"content/gone_{uuid.uuid4().hex[:8]}"
    (temp_vault / f"{slug}.md").write_text(
        "---\ntitle: Gone\ntype: concept\n---\n\nbody\n", encoding="utf-8"
    )
    ctx = VaultContext(vault=temp_vault, mode=ADMIN)
    r = wiki_delete(slug=slug, ctx=ctx)
    assert r["ok"] is True
    assert (temp_vault / "wiki.db").exists()
