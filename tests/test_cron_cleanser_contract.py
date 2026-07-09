"""Contract tests for scripts/cron-cleanser.py.

The cleanser may collect lint results, but creating issue pages must be an
explicit opt-in to avoid runaway `content/issues/issue-lint-*` generation.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "cron-cleanser.py"


def _load_cron_cleanser():
    spec = importlib.util.spec_from_file_location("cron_cleanser", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cron_cleanser_does_not_create_issue_pages_without_flag(monkeypatch) -> None:
    mod = _load_cron_cleanser()
    calls: list[tuple] = []

    monkeypatch.setattr(mod, "resolve_active_vault", lambda name: object())
    monkeypatch.setattr(
        mod,
        "run_all",
        lambda vault: {
            "issues": [
                {"id": "#1", "severity": "critical", "slug": "content/demo", "message": "broken"}
            ]
        },
    )
    monkeypatch.setattr(mod, "write_page", lambda *args, **kwargs: calls.append((args, kwargs)))

    assert mod.main(["demo-vault"]) == 0
    assert calls == []


def test_cron_cleanser_create_issues_requires_explicit_flag(monkeypatch) -> None:
    mod = _load_cron_cleanser()
    calls: list[tuple] = []
    fake_vault = type("FakeVault", (), {"root": Path("/tmp/nonexistent")})()

    monkeypatch.setattr(mod, "resolve_active_vault", lambda name: fake_vault)
    monkeypatch.setattr(
        mod,
        "run_all",
        lambda vault: {
            "issues": [
                {"id": "#1", "severity": "critical", "slug": "content/demo", "message": "broken"}
            ]
        },
    )
    monkeypatch.setattr(mod, "write_page", lambda *args, **kwargs: calls.append((args, kwargs)))

    assert mod.main(["demo-vault", "--create-issues"]) == 0
    assert len(calls) == 1
    assert calls[0][0][1] == "content/issues/issue-lint-1-content-demo"
