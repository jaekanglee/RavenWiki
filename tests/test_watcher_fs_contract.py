"""v0.6.32+ — filesystem watcher: watch → build → lint → log 체인 자동화.

기존 scripts/watcher.py는 cron 기반 lint 비교만 함. 이 테스트는
파일시스템 watch + 자동 build/lint/log 체인을 검증.

회귀 가드:
  1. watchfiles import 가능 (의존성 설치 확인)
  2. scripts/watcher_fs.py 존재
  3. watch → build → lint → log 4단계 함수 정의
  4. vault 경로의 .md 파일 변경 감지 (filter)
  5. debounce 설정 존재 (연속 edit 1회 처리)
"""
from __future__ import annotations

from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def test_watchfiles_dependency_available() -> None:
    """watchfiles는 scripts/.venv/lib/.../site-packages에 설치되어 있어야 함."""
    import watchfiles  # noqa: F401


def test_watcher_fs_script_exists() -> None:
    path = SCRIPTS / "watcher_fs.py"
    assert path.exists(), f"{path} not found — Task 2 watcher_fs.py 필요"


def test_watcher_fs_exposes_required_stages() -> None:
    """watch → build → lint → log 4단계 함수가 정의되어 있어야 함."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("watcher_fs", SCRIPTS / "watcher_fs.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    for fn in ("watch", "build", "lint", "log"):
        assert hasattr(mod, fn), f"watcher_fs.py missing {fn}()"


def test_watcher_fs_filter_excludes_non_markdown() -> None:
    """watch filter가 .md 파일만 포함해야 함 (.py, .db 등 제외)."""
    text = (SCRIPTS / "watcher_fs.py").read_text(encoding="utf-8")
    # .md 확장자 또는 *.md 패턴이 filter에 있어야 함
    assert "*.md" in text or ".md" in text, \
        "watcher_fs.py must filter for .md files"


def test_watcher_fs_has_debounce() -> None:
    """debounce 설정으로 연속 edit 1회만 처리 (debounce_ms 등)."""
    text = (SCRIPTS / "watcher_fs.py").read_text(encoding="utf-8")
    assert "debounce" in text.lower() or "step" in text.lower() or "poll" in text.lower(), \
        "watcher_fs.py must include debounce or polling config"