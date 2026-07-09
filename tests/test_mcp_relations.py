"""test_mcp_relations.py — unit tests for MCP semantic relations tools."""
from __future__ import annotations

from pathlib import Path
import pytest

from raven.mcp.tools import VaultContext, WRITE
from raven.mcp.tools.write import wiki_relation_add, wiki_relation_remove
from raven.mcp.tools.read import wiki_relations_list


@pytest.fixture
def test_vault(tmp_path: Path) -> Path:
    """Setup a vault with basic structures for testing relations."""
    (tmp_path / "content").mkdir()
    (tmp_path / "_meta" / "agents").mkdir(parents=True)
    (tmp_path / "_meta" / "agents" / "SCHEMA.md").write_text("# schema\n", encoding="utf-8")
    (tmp_path / "log.md").write_text("# Vault Log\n", encoding="utf-8")
    
    # Create two pages
    (tmp_path / "content" / "source-page.md").write_text(
        "---\ntitle: Source Page\ntype: concept\ncreated: 2026-07-09\nupdated: 2026-07-09\n---\n\nSource content",
        encoding="utf-8"
    )
    (tmp_path / "content" / "target-page.md").write_text(
        "---\ntitle: Target Page\ntype: concept\ncreated: 2026-07-09\nupdated: 2026-07-09\n---\n\nTarget content",
        encoding="utf-8"
    )
    return tmp_path


def test_relation_add_and_list_and_remove(test_vault: Path):
    ctx = VaultContext(vault=test_vault, mode=WRITE)
    
    # 1. Add valid relation
    r_add = wiki_relation_add(
        source_slug="content/source-page",
        target_slug="content/target-page",
        relation_type="uses",
        evidence=["code/auth"],
        reason="Uses the authentication logic",
        actor="tester",
        ctx=ctx
    )
    assert r_add["ok"] is True, r_add
    
    # Verify file content updated
    source_text = (test_vault / "content" / "source-page.md").read_text(encoding="utf-8")
    assert "relations:" in source_text
    assert "type: uses" in source_text
    assert "target: content/target-page" in source_text
    assert 'reason: Uses the authentication logic' in source_text

    # 2. List relations
    r_list = wiki_relations_list(
        slug="content/source-page",
        ctx=ctx
    )
    assert len(r_list) == 1
    assert r_list[0]["source"] == "content/source-page"
    assert r_list[0]["target"] == "content/target-page"
    assert r_list[0]["type"] == "uses"
    assert r_list[0]["reason"] == "Uses the authentication logic"
    assert r_list[0]["evidence"] == ["code/auth"]

    # 3. Add relation validation failures
    # invalid type
    r_err_type = wiki_relation_add(
        source_slug="content/source-page",
        target_slug="content/target-page",
        relation_type="invalid_type_name",
        evidence=["code/auth"],
        reason="x",
        actor="tester",
        ctx=ctx
    )
    assert r_err_type["ok"] is False
    assert r_err_type["error"] == "invalid_relation_type"

    # missing evidence
    r_err_ev = wiki_relation_add(
        source_slug="content/source-page",
        target_slug="content/target-page",
        relation_type="uses",
        evidence=[],
        reason="x",
        actor="tester",
        ctx=ctx
    )
    assert r_err_ev["ok"] is False
    assert r_err_ev["error"] == "evidence_required"

    # missing reason
    r_err_reason = wiki_relation_add(
        source_slug="content/source-page",
        target_slug="content/target-page",
        relation_type="uses",
        evidence=["code/auth"],
        reason="",
        actor="tester",
        ctx=ctx
    )
    assert r_err_reason["ok"] is False
    assert r_err_reason["error"] == "reason_required"

    # self referencing
    r_self = wiki_relation_add(
        source_slug="content/source-page",
        target_slug="content/source-page",
        relation_type="uses",
        evidence=["code/auth"],
        reason="x",
        actor="tester",
        ctx=ctx
    )
    assert r_self["ok"] is False
    assert r_self["error"] == "self_referencing"

    # 4. Remove relation
    r_remove = wiki_relation_remove(
        source_slug="content/source-page",
        target_slug="content/target-page",
        relation_type="uses",
        actor="tester",
        ctx=ctx
    )
    assert r_remove["ok"] is True, r_remove

    # Verify file content updated to empty list
    source_text_removed = (test_vault / "content" / "source-page.md").read_text(encoding="utf-8")
    assert "relations: []" in source_text_removed

    # Verify list is empty
    r_list_empty = wiki_relations_list(
        slug="content/source-page",
        ctx=ctx
    )
    assert len(r_list_empty) == 0
