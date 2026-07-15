"""test_p2_improvements.py — 2026-07-04 제품 평가 P2 개선 회귀 가드.

P2#15 — CLI `raven search`: 사람의 CLI 검색 경로가 없었음 (Dashboard/API/MCP만).
P2#17 — lint #9: "custom은 OK"라면서 warning을 내던 자기모순 → info로.
P2#22 — SCHEMA.md가 약속한 "같은 태그 3+ 페이지 → core 승격 추천"이 미구현이었음.
P2#24 — frontmatter 없는 페이지는 #10(no frontmatter)이 이미 보고 — #13 이중 보고 제거.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from raven.core.vault import Vault
from raven.core import db as db_module
from raven.core.lint import check_tag_audit, check_cognitive_governance
from raven.cli.__main__ import app

runner = CliRunner()


@pytest.fixture
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Vault:
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(tmp_path))
    return Vault.create("p2v", tmp_path / "p2v")


def _page(vault: Vault, name: str, tags: str) -> None:
    (vault.root / "content" / f"{name}.md").write_text(
        f"---\ntitle: {name}\ntype: concept\ntags: [{tags}]\n"
        "created: 2026-07-04\nupdated: 2026-07-04\n---\n\n본문\n",
        encoding="utf-8",
    )


def test_custom_tag_is_info_not_warning(vault: Vault):
    """P2#17: core 밖 태그는 허용된 custom — warning이 아니라 info."""
    _page(vault, "커스텀태그페이지", "나만의태그")
    issues = [i for i in check_tag_audit(vault) if "나만의태그" in i["message"]]
    assert issues, "custom 태그 안내 자체가 사라지면 안 됨"
    assert all(i["severity"] == "info" for i in issues), issues


def test_promotion_recommendation_at_three_pages(vault: Vault):
    """P2#22: 같은 custom 태그 3+ 페이지 사용 시 core 승격 추천 1건."""
    for n in ("승격a", "승격b", "승격c"):
        _page(vault, n, "반복태그")
    recs = [
        i for i in check_tag_audit(vault)
        if "승격" in i["message"] and "반복태그" in i["message"] and i["slug"] == "(vault)"
    ]
    assert len(recs) == 1, recs
    assert recs[0]["severity"] == "info"

    # 2 페이지면 추천 없음
    vault2_pages = [i for i in check_tag_audit(vault) if "한쌍태그" in i["message"] and i["slug"] == "(vault)"]
    _page(vault, "한쌍a", "한쌍태그")
    _page(vault, "한쌍b", "한쌍태그")
    recs2 = [
        i for i in check_tag_audit(vault)
        if i["slug"] == "(vault)" and "한쌍태그" in i["message"]
    ]
    assert recs2 == [], recs2


def test_no_frontmatter_page_skips_cognitive_governance(vault: Vault):
    """P2#24: frontmatter 없는 페이지는 #10 담당 — #13 이중 보고 금지."""
    (vault.root / "content" / "생프론트없음.md").write_text("그냥 텍스트\n", encoding="utf-8")
    issues = [i for i in check_cognitive_governance(vault) if i["slug"] == "content/생프론트없음"]
    assert issues == [], issues


def test_cli_search_finds_page(vault: Vault):
    """P2#15: raven search — 사람의 CLI 검색 경로."""
    _page(vault, "검색가능노트", "concept")
    db_module.build_db(vault, run_lint=False)

    result = runner.invoke(app, ["search", "검색가능노트", "--vault", "p2v"])
    assert result.exit_code == 0, result.output
    assert "content/검색가능노트" in result.output


def test_cli_search_without_db_fails_clearly(vault: Vault):
    """DB 없으면 build 안내와 함께 명확히 실패 (성공 위장 금지)."""
    assert not vault.db_path.exists()
    result = runner.invoke(app, ["search", "아무거나", "--vault", "p2v"])
    assert result.exit_code == 1
    assert "build" in (result.output or "") + (result.stderr or "")
