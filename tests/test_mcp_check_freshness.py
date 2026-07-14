"""v0.7.114+ (ADR-2026-07-08): MCP guide.check_freshness 동작 검증."""
import json
from pathlib import Path

import pytest


def _setup_vault(tmp_path: Path, *, with_stamp: bool = True):
    root = tmp_path / "v"
    agents = root / "_meta" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    (root / "log.md").write_text("# log\n", encoding="utf-8")
    (agents / "SCHEMA.md").write_text("# SCHEMA v1\n", encoding="utf-8")
    (agents / "RAVEN-CONTRACT.md").write_text("# CONTRACT v1\n", encoding="utf-8")
    if with_stamp:
        from raven.mcp.tools.guide import _sha256
        stamp = {
            "SCHEMA": _sha256(agents / "SCHEMA.md"),
            "RAVEN-CONTRACT": _sha256(agents / "RAVEN-CONTRACT.md"),
        }
        (agents / ".guide-version").write_text(
            "\n".join(f"{k}: {v}" for k, v in stamp.items()) + "\n",
            encoding="utf-8",
        )
    return root


def test_check_freshness_no_cache_hash_returns_no_stale():
    from raven.mcp.tools.guide import check_freshness

    root = _setup_vault(Path("/tmp/v_test1"))  # noqa
    info = check_freshness(vault_root=root, cache_hash=None)
    assert info["vault"] == "v"
    assert info["stale"] is False
    assert info["stale_kinds"] == []
    assert info["guides"]["SCHEMA"]["cache_match"] is None


def test_check_freshness_cache_match_returns_no_stale():
    from raven.mcp.tools.guide import check_freshness, _sha256

    root = _setup_vault(Path("/tmp/v_test2"))  # noqa
    schema_h = _sha256(root / "_meta" / "agents" / "SCHEMA.md")
    contract_h = _sha256(root / "_meta" / "agents" / "RAVEN-CONTRACT.md")
    info = check_freshness(
        vault_root=root,
        cache_hash=f"SCHEMA={schema_h},RAVEN-CONTRACT={contract_h}",
    )
    assert info["stale"] is False
    assert info["guides"]["SCHEMA"]["cache_match"] is True
    assert info["guides"]["RAVEN-CONTRACT"]["cache_match"] is True


def test_check_freshness_mismatch_returns_stale():
    from raven.mcp.tools.guide import check_freshness

    root = _setup_vault(Path("/tmp/v_test3"))  # noqa
    info = check_freshness(
        vault_root=root,
        cache_hash="SCHEMA=stale_abc,RAVEN-CONTRACT=stale_def",
    )
    assert info["stale"] is True
    assert set(info["stale_kinds"]) == {"SCHEMA", "RAVEN-CONTRACT"}


def test_check_freshness_positional_fallback():
    """cache_hash 순서 고정 (key=value 없는 형식) 도 파싱."""
    from raven.mcp.tools.guide import check_freshness, _sha256

    root = _setup_vault(Path("/tmp/v_test4"))  # noqa
    schema_h = _sha256(root / "_meta" / "agents" / "SCHEMA.md")
    contract_h = _sha256(root / "_meta" / "agents" / "RAVEN-CONTRACT.md")
    info = check_freshness(
        vault_root=root,
        cache_hash=f"{schema_h},{contract_h}",
    )
    assert info["stale"] is False
    assert info["guides"]["SCHEMA"]["cache_match"] is True


def test_format_hash_for_header():
    from raven.mcp.tools.guide import _format_hash_for_header

    guides = {
        "SCHEMA": {"vault_hash": "abc123"},
        "RAVEN-CONTRACT": {"vault_hash": "def456"},
        "log": {"lines": 100, "mtime": 1.0},
    }
    out = _format_hash_for_header(guides)
    assert out == "SCHEMA=abc123,RAVEN-CONTRACT=def456"


def test_write_version_stamp_creates_file():
    from raven.mcp.tools.guide import write_version_stamp, _load_version_stamp

    root = _setup_vault(Path("/tmp/v_test5"), with_stamp=False)  # noqa
    assert write_version_stamp(root) is True
    stamp = _load_version_stamp(root)
    assert "SCHEMA" in stamp
    assert "RAVEN-CONTRACT" in stamp
    assert "log.md" in stamp  # log.md line_count:mtime 형식
