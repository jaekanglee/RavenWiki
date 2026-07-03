"""test_mcp_update_upsert_and_frontmatter.py — wiki_update upsert + frontmatter 오염 방어.

회귀 가드 (2026-07-04 제품 평가 P0#2, P0#3):

P0#2 — 에이전트의 신규 content 페이지 생성 경로 부재:
  wiki_update가 존재하지 않는 slug를 거부하고 "Use wiki_ingest for new pages"로
  안내했으나, wiki_ingest는 raw/ 전용 + 사람 명시 명령(user_command=True) 필수
  (ADR-2026-07-02) → 에이전트가 새 노트를 만들 MCP 경로가 없었음.
  → wiki_update는 이제 스키마 가드를 통과하는 신규 페이지를 생성한다 (upsert).

P0#3 — content 선두 frontmatter 블록의 본문 박제:
  에이전트가 frontmatter 포함 전체 md 문서를 content로 보내면, 검증은 기존
  메타로 통과시키고 frontmatter 블록을 본문 텍스트로 이중 기록했음 (SoT 오염).
  → 선두 frontmatter는 파싱해 메타로 승격하고 본문에서 제거, 검증도 그 메타로 수행.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from raven.mcp.tools import VaultContext, WRITE
from raven.mcp.tools.write import wiki_update


@pytest.fixture
def llm_vault(tmp_path: Path) -> Path:
    """_meta/agents/ 존재 → is_llm_wiki=True인 vault (strict schema 가드 활성)."""
    (tmp_path / "content").mkdir()
    (tmp_path / "_meta" / "agents").mkdir(parents=True)
    (tmp_path / "_meta" / "agents" / "SCHEMA.md").write_text("# schema\n", encoding="utf-8")
    (tmp_path / "log.md").write_text("# Vault Log\n", encoding="utf-8")
    return tmp_path


# ─────────────── P0#2 upsert ───────────────


def test_update_creates_new_page_with_valid_frontmatter(llm_vault: Path):
    ctx = VaultContext(vault=llm_vault, mode=WRITE)
    r = wiki_update(
        slug="content/새-노트",
        content="본문입니다.",
        frontmatter_data={"title": "새 노트", "type": "concept"},
        actor="tester",
        ctx=ctx,
    )
    assert r["ok"] is True, r
    fp = llm_vault / "content" / "새-노트.md"
    assert fp.exists()
    text = fp.read_text(encoding="utf-8")
    assert "type: concept" in text
    assert "본문입니다." in text


def test_update_create_rejects_missing_type_in_llm_wiki(llm_vault: Path):
    ctx = VaultContext(vault=llm_vault, mode=WRITE)
    r = wiki_update(
        slug="content/무타입-노트",
        content="타입 없는 본문",
        frontmatter_data={"title": "무타입"},
        actor="tester",
        ctx=ctx,
    )
    assert r["ok"] is False, r
    assert "type" in r["message"]
    assert not (llm_vault / "content" / "무타입-노트.md").exists()


def test_update_create_still_blocks_protected_paths(llm_vault: Path):
    ctx = VaultContext(vault=llm_vault, mode=WRITE)
    r = wiki_update(
        slug="raw/신규-원본",
        content="에이전트가 raw/에 생성 시도",
        frontmatter_data={"title": "x", "type": "concept"},
        actor="tester",
        ctx=ctx,
    )
    assert r["ok"] is False
    assert r.get("error") == "permission_denied"


# ─────────────── P0#3 frontmatter-in-content ───────────────


def test_update_promotes_embedded_frontmatter_no_double_block(llm_vault: Path):
    """전체 md 문서(frontmatter 포함)를 content로 보내도 이중 frontmatter가 생기지 않는다."""
    ctx = VaultContext(vault=llm_vault, mode=WRITE)
    full_doc = "---\ntitle: 임베디드\ntype: concept\n---\n\n임베디드 본문."
    r = wiki_update(slug="content/임베디드", content=full_doc, actor="tester", ctx=ctx)
    assert r["ok"] is True, r

    text = (llm_vault / "content" / "임베디드.md").read_text(encoding="utf-8")
    # frontmatter 블록('---')은 문서 선두 1쌍만 — 본문에 '---' 재등장 금지
    body = text.split("---", 2)[2]
    assert "---" not in body, f"본문에 frontmatter 박제됨:\n{text}"
    assert "임베디드 본문." in body
    assert "type: 이상한타입" not in text


def test_update_embedded_bad_type_is_rejected(llm_vault: Path):
    """기존 페이지에 임베디드 frontmatter로 9종 외 type을 보내면 거부된다 (가드 우회 금지)."""
    fp = llm_vault / "content" / "기존.md"
    fp.write_text(
        "---\ntitle: 기존\ntype: concept\ncreated: 2026-07-04\nupdated: 2026-07-04\n---\n\n원본\n",
        encoding="utf-8",
    )
    ctx = VaultContext(vault=llm_vault, mode=WRITE)
    full_doc = "---\ntitle: 기존\ntype: 이상한타입\n---\n\n오염 시도"
    r = wiki_update(slug="content/기존", content=full_doc, actor="tester", ctx=ctx)

    assert r["ok"] is False, r
    text = fp.read_text(encoding="utf-8")
    assert "원본" in text
    assert "이상한타입" not in text
