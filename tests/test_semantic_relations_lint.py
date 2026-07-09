"""Tests for verifying semantic relations lint rule (#23) in frontmatter."""
from __future__ import annotations

from pathlib import Path
from raven.core import lint as lint_module
from raven.core.vault import Vault


def test_semantic_relations_lint_all_cases(tmp_path: Path, monkeypatch) -> None:
    reg_root = tmp_path / "registry"
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    vault = Vault.create("test-relations-lint", tmp_path / "vault", bootstrap=False)
    content_dir = vault.root / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    # 1. Create a target concept document
    (content_dir / "target-concept.md").write_text(
        "---\ntitle: Target Concept\ntype: concept\ncreated: 2026-01-01\nupdated: 2026-01-01\n---\n\nConcept details\n",
        encoding="utf-8",
    )

    # 2. Create a source document with a valid relation, and some invalid ones
    (content_dir / "source-doc.md").write_text(
        """---
title: Source Doc
type: concept
created: 2026-01-01
updated: 2026-01-01
relations:
  - type: uses
    target: target-concept  # Should resolve correctly
    evidence: ["repo/auth"]
    reason: Uses the concept.
  - type: invalid_type
    target: target-concept
    evidence: ["repo/auth"]
    reason: Invalid type test.
  - type: depends_on
    target: non-existent-doc  # Target does not exist
    evidence: ["repo/auth"]
    reason: Non-existent target test.
  - type: implements
    target: target-concept
    evidence: []  # Missing evidence
    reason: ""    # Missing reason
  - type: related
    target: content/source-doc  # Self-referencing
    evidence: ["self"]
    reason: Self link.
---

Body content
""",
        encoding="utf-8",
    )

    issues = lint_module.check_semantic_relations(vault)
    
    # We expect 5 issues from source-doc:
    # 1. invalid_type: relation type 'invalid_type' is not allowed (warning)
    # 2. depends_on: target 'non-existent-doc' does not exist (warning)
    # 3. implements: evidence or reason is missing (warning)
    # 4. related: self-referencing (warning)
    # 5. related: self-referencing target (source-doc) does not exist (warning) - wait, target is content/source-doc.
    #    Does content/source-doc exist? Yes, since it is source-doc.md (which is slug 'content/source-doc').
    #    So only self-referencing warning.
    
    warnings = [iss for iss in issues if iss["id"] == "#23"]
    assert len(warnings) > 0

    # Let's map issues by their message keywords to verify
    msgs = [w["message"] for w in warnings]
    
    assert any("허용되지 않습니다" in m for m in msgs)
    assert any("존재하지 않습니다" in m for m in msgs)
    assert any("evidence(근거) 또는 reason(이유)이 누락되었습니다" in m for m in msgs)
    assert any("자기 자신" in m for m in msgs)
