"""Regression guards for lint read-only behavior and archive exclusion.

`wiki_lint` / `raven.core.lint.run_all()` must behave like a linter: report
active vault issues without mutating content and without re-surfacing archived
issue pages.
"""
from __future__ import annotations

import json
from pathlib import Path

from raven.core.lint import run_all
from raven.core.registry import VaultMeta
from raven.core.vault import Vault


def _vault(tmp_path: Path) -> Vault:
    root = tmp_path / "lint-vault"
    (root / "content").mkdir(parents=True)
    (root / "_meta").mkdir()
    meta = VaultMeta(name="lint-vault", path=root)
    (root / ".vault.json").write_text(json.dumps(meta.to_json(), indent=2), encoding="utf-8")
    return Vault.load(meta)


def test_run_all_ignores_content_archive_pages(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    archived = vault.root / "content" / "issues" / "_archive" / "2026-07-09" / "issue-lint-1-demo.md"
    archived.parent.mkdir(parents=True)
    archived.write_text("no frontmatter and [[missing-target]]\n", encoding="utf-8")

    result = run_all(vault)

    slugs = {issue.get("slug") for issue in result["issues"]}
    assert "content/issues/_archive/2026-07-09/issue-lint-1-demo" not in slugs


def test_run_all_does_not_promote_or_write_draft_issues(tmp_path: Path) -> None:
    vault = _vault(tmp_path)
    issue_path = vault.root / "content" / "issues" / "old-draft.md"
    issue_path.parent.mkdir(parents=True)
    original = """---
title: Old Draft
type: issue
status: draft
created: 2000-01-01
updated: 2000-01-01
---

# Old Draft

# 요약
- old issue
"""
    issue_path.write_text(original, encoding="utf-8")

    result = run_all(vault)

    assert result["draft_promoted"] == 0
    assert issue_path.read_text(encoding="utf-8") == original
    assert not (vault.root / "log.md").exists()
