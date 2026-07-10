from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path

from raven.core.draft import commit_draft
from raven.core.vault import Vault
from raven.curator import curator, db as curator_db


def _git(vault_root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(vault_root), check=True)


def test_raw_curator_proposal_approve_wiki_e2e(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(tmp_path / "registry"))
    vault = Vault.create("curation-e2e", tmp_path / "vault", bootstrap=False)

    # Raw: source material is tracked as the human-owned input.
    raw_file = vault.root / "raw" / "articles" / "session-note.md"
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    raw_file.write_text(
        "# Session Note\n\nRaven uses semantic relation evidence to keep graph links explainable.\n",
        encoding="utf-8",
    )

    collections_yaml = vault.root / "_meta" / "collections.yaml"
    collections_yaml.parent.mkdir(parents=True, exist_ok=True)
    collections_yaml.write_text(
        """schema_version: 1
collections:
  - id: raw-notes
    paths: [raw/articles]
    first_run_strategy: full_scan
""",
        encoding="utf-8",
    )

    # Existing wiki target used by the approved proposal's relation metadata.
    content_dir = vault.root / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    (content_dir / "source-index.md").write_text(
        "---\ntitle: Source Index\ntype: concept\ncreated: 2026-07-10\nupdated: 2026-07-10\n---\n\nIndex\n",
        encoding="utf-8",
    )

    _git(vault.root, "add", "-A")
    _git(vault.root, "commit", "-q", "-m", "add raw source and collection")

    # Curator: raw change set becomes a proposal row in curation_history.db.
    curator_db_path = tmp_path / "curation_history.db"
    result = curator.execute(
        collection_id="raw-notes",
        vault_root=vault.root,
        collections_yaml_path=collections_yaml,
        db_path=curator_db_path,
        dry_run=False,
        now=1_800_000_000,
    )
    assert result.status == "ok"
    assert any(change.path == "raw/articles/session-note.md" for change in result.changes)

    conn = curator_db.connect(curator_db_path)
    try:
        row = conn.execute(
            "SELECT change_id, path, curated FROM file_changes WHERE path = ?",
            ("raw/articles/session-note.md",),
        ).fetchone()
        assert row is not None
        change_id = row[0]
        assert row[2] == 0

        # Approve: reviewer accepts the proposal and marks it curated.
        review_id = curator_db.insert_review(
            conn,
            change_id=change_id,
            decision="accept",
            reason="source distilled into a wiki page",
            reviewer="human:test",
            ts=1_800_000_001,
        )
        curator_db.mark_curated(conn, change_id=change_id, ts=1_800_000_001)
        assert review_id > 0
        assert conn.execute(
            "SELECT curated FROM file_changes WHERE change_id = ?", (change_id,)
        ).fetchone()[0] == 1
    finally:
        conn.close()

    # Wiki: approved proposal is published via the existing draft commit path.
    approved_content = """---
title: Session Note
type: concept
created: 2026-07-10
updated: 2026-07-10
status: current
relations:
  - type: uses
    target: content/source-index
    evidence:
      - raw/articles/session-note.md
    reason: Raw session note explicitly says Raven uses relation evidence.
---

# Session Note

Raven uses semantic relation evidence to keep graph links explainable.
"""
    commit = commit_draft(
        vault,
        draft_slug="drafts/session-note",
        content=approved_content,
        overwrite=True,
    )
    assert commit["ok"] is True
    assert commit["slug"] == "content/session-note"

    wiki_page = vault.root / "content" / "session-note.md"
    assert wiki_page.exists()
    text = wiki_page.read_text(encoding="utf-8")
    assert "raw/articles/session-note.md" in text
    assert "reason: Raw session note explicitly says Raven uses relation evidence." in text

    db_conn = sqlite3.connect(str(vault.db_path))
    try:
        db_conn.row_factory = sqlite3.Row
        rel = db_conn.execute(
            "SELECT relation_type, target_slug, evidence, reason "
            "FROM relations WHERE source_slug = ?",
            ("content/session-note",),
        ).fetchone()
        assert rel is not None
        assert rel["relation_type"] == "uses"
        assert rel["target_slug"] == "content/source-index"
        assert json.loads(rel["evidence"]) == ["raw/articles/session-note.md"]
        assert rel["reason"] == "Raw session note explicitly says Raven uses relation evidence."
    finally:
        db_conn.close()
