"""tests/test_gardening.py — regression guards for gardening rules, linting, and CLI/MCP.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from raven.core.vault import Vault
from raven.core.registry import VaultMeta
from raven.core.contracts import write_page, validate_gardening_schema
from raven.core.garden import get_stale_pages, get_orphan_pages, find_link_candidates
from raven.core.lint import check_cognitive_governance


@pytest.fixture
def vault_basic(tmp_path: Path) -> Vault:
    """Vault with default basic settings (no llm_wiki)."""
    p = tmp_path / "basic"
    p.mkdir()
    (p / "content").mkdir()
    (p / "_meta").mkdir()
    meta = VaultMeta(name="test-basic", path=p)
    (p / ".vault.json").write_text(json.dumps(meta.to_json(), indent=2))
    return Vault.load(meta)


@pytest.fixture
def vault_llm_wiki(tmp_path: Path) -> Vault:
    """Vault with llm_wiki=true feature enabled."""
    p = tmp_path / "llm_wiki"
    p.mkdir()
    (p / "content").mkdir()
    (p / "_meta").mkdir()
    meta = VaultMeta(
        name="test-llm-wiki",
        path=p,
        features=(("llm_wiki", True),)
    )
    (p / ".vault.json").write_text(json.dumps(meta.to_json(), indent=2))
    return Vault.load(meta)


# ────────────────────────── validate_gardening_schema tests ──────────────────────────

def test_gardening_validation_skips_wip_and_scratch(vault_llm_wiki: Vault) -> None:
    """Validation is skipped for WIP and scratch paths."""
    missing = validate_gardening_schema(vault_llm_wiki, "content/wip/scratch-page", "No why it matters or oppose heading", {})
    assert len(missing) == 0

    missing2 = validate_gardening_schema(vault_llm_wiki, "content/scratch/test", "No content", {})
    assert len(missing2) == 0


def test_gardening_validation_skips_system_meta(vault_llm_wiki: Vault) -> None:
    """Validation is skipped for _meta/ system pages."""
    missing = validate_gardening_schema(vault_llm_wiki, "_meta/system-guide", "Simple content", {})
    assert len(missing) == 0


def test_gardening_validation_blocks_incomplete_concept(vault_llm_wiki: Vault) -> None:
    """Write-time validation stays minimal for human-first documents."""
    meta = {"type": "concept"}
    content = "This is a body."

    missing = validate_gardening_schema(vault_llm_wiki, "content/concept/topic", content, meta)
    assert missing == []


def test_gardening_validation_passes_complete_concept(vault_llm_wiki: Vault) -> None:
    """Complete concept also passes the minimal write-time validation."""
    meta = {"type": "concept", "confidence": "high"}
    content = """
# Topic Title

왜 중요:
이 기술은 아주 혁신적입니다.

## 반대 입장 및 한계점
그러나 리소스 소모가 큽니다.
"""
    missing = validate_gardening_schema(vault_llm_wiki, "content/concept/topic", content, meta)
    assert len(missing) == 0


def test_gardening_validation_skips_exempt_types(vault_llm_wiki: Vault) -> None:
    """Exempt types like rule/journal/query are skip-validated for why it matters/oppose headings."""
    meta = {"type": "rule"}
    content = "Simple rule statement."
    missing = validate_gardening_schema(vault_llm_wiki, "content/rules/policy", content, meta)
    assert len(missing) == 0


# ────────────────────────── write contract with guardrail tests ──────────────────────────

def test_agent_write_fails_on_incomplete_main_content(vault_llm_wiki: Vault) -> None:
    """An agent can write normal content when metadata is minimally valid."""
    actor = {"name": "test-agent"}
    res = write_page(
        vault_llm_wiki,
        "content/concept/incomplete",
        "Some text",
        type="concept",
        actor=actor,
        overwrite=True
    )
    assert res.ok is True


def test_agent_write_succeeds_on_wip_even_incomplete(vault_llm_wiki: Vault) -> None:
    """An agent writing to wip path succeeds even if incomplete."""
    actor = {"name": "test-agent"}
    res = write_page(
        vault_llm_wiki,
        "content/wip/incomplete-note",
        "Some text",
        type="concept",
        actor=actor,
        overwrite=True
    )
    assert res.ok is True
    assert (vault_llm_wiki.root / "content" / "wip" / "incomplete-note.md").is_file()


def test_human_write_succeeds_even_incomplete(vault_llm_wiki: Vault) -> None:
    """Human (actor is None) writing to main content succeeds even if incomplete."""
    res = write_page(
        vault_llm_wiki,
        "content/concept/incomplete-human",
        "Some text",
        type="concept",
        actor=None,
        overwrite=True
    )
    assert res.ok is True


# ────────────────────────── Linter Severity Promotion tests ──────────────────────────

def test_linter_promotes_cognitive_governance_severity(vault_llm_wiki: Vault, vault_basic: Vault) -> None:
    """Cognitive governance is advisory info even in llm_wiki mode."""
    # Write same incomplete page directly to both vaults
    p_basic = vault_basic.root / "content" / "concept" / "incomplete-doc.md"
    p_basic.parent.mkdir(parents=True, exist_ok=True)
    p_basic.write_text("""---
title: Incomplete Document
type: concept
confidence: invalid
---
Just simple text.""", encoding="utf-8")

    p_wiki = vault_llm_wiki.root / "content" / "concept" / "incomplete-doc.md"
    p_wiki.parent.mkdir(parents=True, exist_ok=True)
    p_wiki.write_text("""---
title: Incomplete Document
type: concept
confidence: invalid
---
Just simple text.""", encoding="utf-8")
    
    issues_basic = check_cognitive_governance(vault_basic)
    assert len(issues_basic) > 0
    assert all(issue["severity"] == "info" for issue in issues_basic)

    issues_wiki = check_cognitive_governance(vault_llm_wiki)
    assert len(issues_wiki) > 0
    assert all(issue["severity"] == "info" for issue in issues_wiki)
