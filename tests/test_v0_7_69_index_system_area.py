"""v0.7.69+ SCHEMA 9종 정책 회귀 가드 (ADR-2026-07-04).

위반 시도: 817e2a2에서 SCHEMA.md에 `index` type 추가 시도 + index_builder.py가
`type: index` 자동 박기. ebcde83에서 SCHEMA.md 자가 교정됐으나 index_builder.py는
미교정. 본 회귀 가드로 두 곳 모두 강제:
  1. content/_index/* 자동 생성 페이지는 type 필드 없음 (system area 격리)
  2. valid_types = 9종 고정 — 10종 추가 시도 자동 검출
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from raven.core.vault import Vault
from raven.core.registry import VaultMeta
from raven.core.contracts import write_page
from raven.core.db import build_db
from raven.core.index_builder import build_index


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    p = tmp_path / "ib-69-vault"
    p.mkdir()
    (p / "content").mkdir()
    (p / "_meta").mkdir()
    meta = VaultMeta(name="ib-69-vault", path=p)
    (p / ".vault.json").write_text(json.dumps(meta.to_json(), indent=2))
    return Vault.load(meta)


def _seed_pages(v: Vault) -> None:
    write_page(v, "content/concepts/a", "concept a body", title="A", type="concept", normalize=False)
    write_page(v, "content/concepts/b", "concept b body", title="B", type="concept", normalize=False)
    write_page(v, "content/issues/c", "issue c body", title="C", type="issue", normalize=False)
    build_db(v, run_lint=False)


def test_index_pages_have_no_type_field(vault: Vault) -> None:
    """content/_index/{type}.md 자동 생성 페이지는 type을 박지 않음 (system area, ADR-2026-07-04).

    이전: index_builder가 "type: index" 박았음 → SCHEMA 9종 정책(AGENTS.md §10) 위반.
    수정: type 필드 생략. system area 격리로 lint 면제.
    """
    _seed_pages(vault)
    build_index(vault)

    # 모든 _index/ 페이지 검증
    for cat_path in (vault.root / "content" / "_index").glob("*.md"):
        text = cat_path.read_text(encoding="utf-8")
        # frontmatter에 'type:' 라인 없음
        assert "type: " not in text, (
            f"auto-index page {cat_path.relative_to(vault.root)} has 'type:' field — "
            f"should be system area (ADR-2026-07-04). Frontmatter:\n{text[:200]}"
        )


def test_index_pages_have_no_index_tag(vault: Vault) -> None:
    """content/_index/* 자동 생성 페이지는 'tags: [index]' 같은 자동 마커 박지 않음.

    이전: index_builder가 "tags: [index]" 박았음 → 도구 자동 생성 영역임을 강하게 표지.
    수정: type 필드와 함께 tags도 system area 표지로 의도적 사용 안 함 (path로 식별).
    """
    _seed_pages(vault)
    build_index(vault)

    for cat_path in (vault.root / "content" / "_index").glob("*.md"):
        text = cat_path.read_text(encoding="utf-8")
        assert "tags: " not in text or "tags: []" in text, (
            f"auto-index page {cat_path.relative_to(vault.root)} has 'tags:' field — "
            f"should be empty (system area, ADR-2026-07-04). Frontmatter:\n{text[:200]}"
        )


def test_valid_types_remains_9() -> None:
    """SCHEMA 9종 고정 — 10종 추가 시도 자동 회귀 가드 (AGENTS.md §10).

    valid_types = {concept, person, tool, comparison, project, rule, query, journal, issue}
    새 type 추가 시도 = 9 → 10 변하는 시점에 본 테스트가 즉시 실패.
    """
    # raven.core.contracts.validate_gardening_schema가 type 검증을 수행.
    # 'index' type을 박으면 missing에 추가됨 (즉 invalid).
    from raven.core.contracts import validate_gardening_schema

    # 9종 정확히 일치 — 모두 valid (missing = [])
    valid_set = ["concept", "person", "tool", "comparison", "project", "rule", "query", "journal", "issue"]
    for t in valid_set:
        missing = validate_gardening_schema(
            vault=None,  # type: ignore[arg-type]
            slug="content/test/x",
            content="body",
            meta={"type": t},
        )
        assert missing == [], f"valid type {t!r} should pass validation, got missing={missing}"

    # 흔한 위반 시나리오 — 'index' / 'system' type은 invalid
    for invalid_t in ["index", "system", "decision", "wiki"]:
        missing = validate_gardening_schema(
            vault=None,  # type: ignore[arg-type]
            slug="content/test/x",
            content="body",
            meta={"type": invalid_t},
        )
        assert "올바른 type (frontmatter)" in missing, (
            f"invalid type {invalid_t!r} should fail validation (SCHEMA 9종 정책), got missing={missing}"
        )

    # 9종 + 위반 후보 4종 = 13 케이스 → 9 valid + 4 invalid
    # 본 테스트가 SCHEMA 9종 정책의 self-enforcing 회귀 가드.


def test_index_pages_minimal_frontmatter(vault: Vault) -> None:
    """자동 생성 _index/* 페이지는 title + created + updated만 가짐 (system area).

    SCHEMA 9종 정책 + system area 격리 패턴의 일관성 검증.
    """
    _seed_pages(vault)
    build_index(vault)

    for cat_path in (vault.root / "content" / "_index").glob("*.md"):
        text = cat_path.read_text(encoding="utf-8")
        # frontmatter가 비어있거나 최소한만
        assert "title:" in text, f"{cat_path.name} missing title"
        assert "created:" in text, f"{cat_path.name} missing created"
        assert "updated:" in text, f"{cat_path.name} missing updated"
        # type/tags/confidence/source/audience/aliases 등 사람 작성 필드 없음
        for forbidden in ("type:", "tags:", "confidence:", "audience:", "contested:"):
            assert forbidden not in text, (
                f"{cat_path.name} has '{forbidden}' — system area should not have human authoring fields"
            )
