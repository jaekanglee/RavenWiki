"""Tests for building and verifying the relations table from page frontmatter."""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3

from raven.core import db as db_module
from raven.core.vault import Vault


def test_build_db_relations_parsing_and_resolution(tmp_path: Path, monkeypatch) -> None:
    reg_root = tmp_path / "registry"
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    vault = Vault.create("build-relations", tmp_path / "vault", bootstrap=False)
    content_dir = vault.root / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    # 1. Create a target page with a specific path to test slug resolution
    (content_dir / "target-concept.md").write_text(
        "---\ntitle: Target Concept\ntype: concept\ncreated: 2026-01-01\nupdated: 2026-01-01\n---\n\nTarget content\n",
        encoding="utf-8",
    )

    # 2. Create a source page containing relations
    (content_dir / "source-page.md").write_text(
        """---
title: Source Page
type: implementation
created: 2026-01-01
updated: 2026-01-01
relations:
  - type: uses
    target: target-concept  # Should resolve to 'content/target-concept'
    confidence:
      semantic: 0.95
      structural: 0.88
      provenance: 0.99
    verified_by:
      - human
      - ai
    evidence:
      - repo/app/auth/
      - raw/session/123
    reason: Explicitly stated in session 123.
  - type: depends_on
    target: non-existent-page  # Should remain 'non-existent-page' since it cannot be resolved
    confidence: medium
    verified_by: ai
    evidence: []
    reason: Inferred relationship.
---

Source content
""",
        encoding="utf-8",
    )

    # 3. Run build_db
    result = db_module.build_db(vault, run_lint=False)
    assert result["ok"] is True

    # 4. Query the relations table in SQLite
    db_file = Path(result["db_path"])
    assert db_file.exists()

    conn = sqlite3.connect(str(db_file))
    try:
        conn.row_factory = sqlite3.Row
        # Verify uses relation (target should be normalized, confidence parsed to separate columns)
        row_uses = conn.execute(
            "SELECT * FROM relations WHERE source_slug = 'content/source-page' AND relation_type = 'uses'"
        ).fetchone()
        assert row_uses is not None
        assert row_uses["target_slug"] == "content/target-concept"
        assert row_uses["confidence_semantic"] == 0.95
        assert row_uses["confidence_structural"] == 0.88
        assert row_uses["confidence_provenance"] == 0.99
        assert row_uses["verified_by"] == "human, ai"
        
        evidence = json.loads(row_uses["evidence"])
        assert isinstance(evidence, list)
        assert "repo/app/auth/" in evidence
        assert "raw/session/123" in evidence
        assert row_uses["reason"] == "Explicitly stated in session 123."

        # Verify depends_on relation (unresolved target, single confidence value)
        row_depends = conn.execute(
            "SELECT * FROM relations WHERE source_slug = 'content/source-page' AND relation_type = 'depends_on'"
        ).fetchone()
        assert row_depends is not None
        assert row_depends["target_slug"] == "non-existent-page"
        assert row_depends["confidence_semantic"] == "medium"
        assert row_depends["confidence_structural"] is None
        assert row_depends["confidence_provenance"] is None
        assert row_depends["verified_by"] == "ai"
        assert row_depends["reason"] == "Inferred relationship."
    finally:
        conn.close()
