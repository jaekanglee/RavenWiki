"""tests/test_index_builder.py — raven.core.index_builder 카테고리 인덱스 페이지 회귀 테스트.

배경: 예전엔 build_index()가 모든 페이지를 content/index.md에 직접 링크해서
content/index가 그래프상 out-degree == 페이지 수인 거대 허브 노드가 됐다
(실사용 vault에서 26/105 엣지, 25%). 이제는 타입별로 content/_index/{type}.md
카탈로그 페이지를 만들고, 루트 index.md는 그 카탈로그 페이지에만 링크한다.
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
    p = tmp_path / "ib-vault"
    p.mkdir()
    (p / "content").mkdir()
    (p / "_meta").mkdir()
    meta = VaultMeta(name="ib-vault", path=p)
    (p / ".vault.json").write_text(json.dumps(meta.to_json(), indent=2))
    return Vault.load(meta)


def _seed_pages(v: Vault) -> None:
    write_page(v, "content/concepts/a", "concept a body", title="A", type="concept", normalize=False)
    write_page(v, "content/concepts/b", "concept b body", title="B", type="concept", normalize=False)
    write_page(v, "content/issues/c", "issue c body", title="C", type="issue", normalize=False)
    build_db(v, run_lint=False)


def test_build_index_creates_per_type_category_pages(vault: Vault) -> None:
    _seed_pages(vault)
    # v0.7.66: build_db가 내부에서 이미 build_index를 수행 — 직후 재호출은
    # "변경 없음"(False)이어야 한다 (멱등 수렴, 평가 P1#5).
    assert build_index(vault) is False

    concept_page = vault.root / "content" / "_index" / "concept.md"
    issue_page = vault.root / "content" / "_index" / "issue.md"
    assert concept_page.exists()
    assert issue_page.exists()

    concept_text = concept_page.read_text(encoding="utf-8")
    assert "[[content/concepts/a]]" in concept_text
    assert "[[content/concepts/b]]" in concept_text
    assert "content/issues/c" not in concept_text

    issue_text = issue_page.read_text(encoding="utf-8")
    assert "[[content/issues/c]]" in issue_text


def test_build_index_root_links_only_to_category_pages(vault: Vault) -> None:
    """루트 index.md는 개별 페이지가 아니라 카테고리 페이지에만 링크해야 한다 (허브 방지)."""
    _seed_pages(vault)
    build_index(vault)

    root_text = (vault.root / "content" / "index.md").read_text(encoding="utf-8")
    assert "[[content/_index/concept]]" in root_text
    assert "[[content/_index/issue]]" in root_text
    # 개별 페이지로의 직접 링크는 더 이상 없어야 한다.
    assert "[[content/concepts/a]]" not in root_text
    assert "[[content/concepts/b]]" not in root_text
    assert "[[content/issues/c]]" not in root_text


def test_build_index_category_pages_excluded_from_their_own_catalog(vault: Vault) -> None:
    """content/_index/* 자신은 다음 재빌드에서 카탈로그 대상으로 다시 잡히면 안 된다."""
    _seed_pages(vault)
    build_index(vault)
    # 카테고리 페이지가 DB에 반영되도록 한 번 더 재빌드.
    build_db(vault, run_lint=False)
    build_index(vault)

    concept_text = (vault.root / "content" / "_index" / "concept.md").read_text(encoding="utf-8")
    assert "_index/concept" not in concept_text
    assert "_index/issue" not in concept_text


def test_build_index_handles_empty_vault(vault: Vault) -> None:
    build_db(vault, run_lint=False)
    # v0.7.66: build_db 내부에서 index가 이미 생성됨 → 재호출은 변경 없음.
    assert build_index(vault) is False
    root_text = (vault.root / "content" / "index.md").read_text(encoding="utf-8")
    assert "아직 등록된 정제 페이지가 없습니다" in root_text
    assert not (vault.root / "content" / "_index").exists()
