"""test_self_healing_validation.py — Integration tests for orphan node self-healing workflow."""
from __future__ import annotations

import sqlite3
from pathlib import Path
import pytest

from raven.core.registry import VaultMeta
from raven.core.vault import Vault
from raven.core.advice import get_advice
from raven.mcp.tools import VaultContext, WRITE
from raven.mcp.tools.write import wiki_relation_add
from raven.mcp.tools.read import wiki_relations_list


@pytest.fixture
def test_vault(tmp_path: Path) -> Path:
    """Setup a test vault with one orphan node and one target node."""
    (tmp_path / "content").mkdir()
    (tmp_path / "_meta" / "agents").mkdir(parents=True)
    (tmp_path / "_meta" / "agents" / "SCHEMA.md").write_text("# schema\n", encoding="utf-8")
    (tmp_path / "log.md").write_text("# Vault Log\n", encoding="utf-8")
    
    # 1. Target node
    (tmp_path / "content" / "target-node.md").write_text(
        "---\ntitle: Target Node\ntype: concept\ncreated: 2026-07-09\nupdated: 2026-07-09\n---\n\n"
        "This is the core auth module of the system.",
        encoding="utf-8"
    )
    
    # 2. Orphan node (has no links or relations initially, mentions target-node in content)
    (tmp_path / "content" / "isolated-node.md").write_text(
        "---\ntitle: Isolated Node\ntype: concept\ncreated: 2026-07-09\nupdated: 2026-07-09\n---\n\n"
        "This node is isolated but we import target-node inside it.",
        encoding="utf-8"
    )
    
    return tmp_path


def test_self_healing_workflow(test_vault: Path):
    meta = VaultMeta(name="test", path=test_vault, mode="personal", owner="test")
    vault = Vault(meta=meta, root=test_vault)
    ctx = VaultContext(vault=test_vault, mode=WRITE)
    
    # Step 1: Diagnose using get_advice (wiki_get_advice)
    advices = get_advice(vault)
    orphans = [adv for adv in advices if adv["type"] == "orphan"]
    
    assert len(orphans) > 0
    assert any(o["slug"] == "content/isolated-node" for o in orphans)
    
    # Step 2: Simulate self-healing
    res = wiki_relation_add(
        source_slug="content/isolated-node",
        target_slug="content/target-node",
        relation_type="uses",
        evidence=None,
        reason=None,
        actor="self-healing-agent",
        ctx=ctx
    )
    assert res["ok"] is True, res
    assert res["source_slug"] == "content/isolated-node"
    assert res["target_slug"] == "content/target-node"
    
    # Verify frontmatter was updated in isolated-node.md
    source_content = (test_vault / "content" / "isolated-node.md").read_text(encoding="utf-8")
    assert "relations:" in source_content
    assert "target: content/target-node" in source_content
    assert "type: uses" in source_content
    
    # Step 3: Diagnose again and verify that the node is no longer an orphan
    advices_after = get_advice(vault)
    orphans_after = [adv for adv in advices_after if adv["type"] == "orphan"]
    assert not any(o["slug"] == "content/isolated-node" for o in orphans_after)
    
    # Step 4: Verify database sync
    conn = sqlite3.connect(vault.db_path)
    conn.row_factory = sqlite3.Row
    db_relations = conn.execute(
        "SELECT source_slug, target_slug, relation_type FROM relations WHERE source_slug = 'content/isolated-node'"
    ).fetchall()
    assert len(db_relations) == 1
    assert db_relations[0]["target_slug"] == "content/target-node"
    assert db_relations[0]["relation_type"] == "uses"
    conn.close()
    
    # Step 5: Check log.md tracking (M4/F1 provenance check)
    log_content = (test_vault / "log.md").read_text(encoding="utf-8")
    assert "relation add: content/isolated-node uses content/target-node" in log_content
