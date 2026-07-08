"""v0.7.113+ ADR-2026-07-08: type=issue + draft 7일+ 자동 current 머신 검증."""
import json
import shutil
from raven.core.registry import VaultMeta  # noqa: E402
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


def _write_md(p: Path, fm: dict, body: str = "body") -> None:
    """YAML frontmatter 작성 (status 머신 머신이 그대로 읽을 수 있는 형식)."""
    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            lines.append(f"{k}: [{', '.join(str(x) for x in v)}]")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append(body)
    p.write_text("\n".join(lines), encoding="utf-8")


def _setup_vault(tmp_path: Path, age_days: int = 8, status: str = "draft"):
    """테스트용 임시 Vault 객체. type=issue 페이지 1개 + _meta/agents/ 부속 + log.md."""
    from raven.core.vault import Vault
    vault_root = tmp_path / "v"
    (vault_root / "content" / "issues").mkdir(parents=True)
    (vault_root / "_meta" / "agents").mkdir(parents=True)
    (vault_root / "log.md").write_text("# log\n", encoding="utf-8")
    created = (datetime.now(timezone.utc) - timedelta(days=age_days)).strftime("%Y-%m-%d")
    _write_md(
        vault_root / "content" / "issues" / "2026-07-01-test.md",
        {
            "title": "테스트 이슈",
            "type": "issue",
            "status": status,
            "created": created,
            "tags": ["issue", "high", "bug", "draft"],
        },
        body="본문.\n",
    )
    meta = VaultMeta(name="test", path=vault_root, mode="personal", owner="test")
    return Vault(meta=meta, root=vault_root)


def test_draft_older_than_7d_promotes_to_current(tmp_path):
    from raven.core.lint import _auto_promote_draft_issues, _swap_status_in_fm

    vault = _setup_vault(tmp_path, age_days=8, status="draft")
    n = _auto_promote_draft_issues(vault)
    assert n == 1
    text = (vault.root / "content" / "issues" / "2026-07-01-test.md").read_text()
    assert "status: current" in text


def test_draft_younger_than_7d_not_promoted(tmp_path):
    from raven.core.lint import _auto_promote_draft_issues

    vault = _setup_vault(tmp_path, age_days=3, status="draft")
    n = _auto_promote_draft_issues(vault)
    assert n == 0
    text = (vault.root / "content" / "issues" / "2026-07-01-test.md").read_text()
    assert "status: draft" in text


def test_non_issue_pages_not_promoted(tmp_path):
    """type=issue가 아니면 status 머신 무관 — 변경 ❌."""
    from raven.core.lint import _auto_promote_draft_issues
    from raven.core.vault import Vault

    vault_root = tmp_path / "v"
    (vault_root / "content" / "concept").mkdir(parents=True)
    (vault_root / "_meta" / "agents").mkdir(parents=True)
    (vault_root / "log.md").write_text("# log\n", encoding="utf-8")
    created = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")
    _write_md(
        vault_root / "content" / "concept" / "old-concept.md",
        {
            "title": "오래된 concept",
            "type": "concept",
            "status": "draft",
            "created": created,
            "tags": ["concept", "draft"],
        },
    )
    meta = VaultMeta(name="test", path=vault_root, mode="personal", owner="test")
    vault = Vault(meta=meta, root=vault_root)
    n = _auto_promote_draft_issues(vault)
    assert n == 0
    text = (vault_root / "content" / "concept" / "old-concept.md").read_text()
    assert "status: draft" in text


def test_swap_status_in_fm_idempotent():
    from raven.core.lint import _swap_status_in_fm

    src = "---\ntitle: x\nstatus: draft\ntype: issue\n---\nbody"
    out = _swap_status_in_fm(src, "draft", "current")
    assert "status: current" in out
    assert "status: draft" not in out
