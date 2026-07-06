"""Pytest config for ADR-2026-07-06 §1.4 scenarios.

격리 vault fixture를 제공하여 시나리오 테스트가 실 vault를 침범하지 않도록 한다.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest


@pytest.fixture
def isolated_vault(tmp_path: Path) -> Path:
    """격리 vault 디렉터리 (content/ + .vault.json 최소 구성).

    Returns:
        tmp_path 하위에 생성된 vault 경로.

    골격 한계: 현 fixture는 content/ 디렉터리만 생성. 실제 vault 부트스트랩
    (`.vault.json` + Lite bootstrap 3종)은 별도 패치에서 추가.
    """
    vault = tmp_path / "test_vault"
    (vault / "content").mkdir(parents=True)
    return vault


@pytest.fixture
def make_page():
    """vault에 stub 페이지를 만드는 helper fixture.

    Usage:
        def test_x(make_page, isolated_vault):
            make_page(isolated_vault, "foo.md", frontmatter={"status": "current", ...}, body="...")
    """
    from raven.core import frontmatter as core_frontmatter

    def _make(
        vault: Path,
        slug: str,
        *,
        frontmatter: dict | None = None,
        body: str = "",
    ) -> Path:
        path = vault / "content" / f"{slug}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        fm = frontmatter or {}
        text = core_frontmatter.render(fm, body) if fm else body
        path.write_text(text, encoding="utf-8")
        return path

    return _make