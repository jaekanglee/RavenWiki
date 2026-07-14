"""v0.8.1+ 회귀 가드: 에이전트 포인터 스텁이 wiki.db 페이지로 오색인되지 않는지 확인.

AGENTS.md/CLAUDE.md/GEMINI.md는 vault 루트의 순수 포인터 스텁이지 콘텐츠
페이지가 아니다. build_db()가 이들을 색인하면 lint #11(FS↔DB 불일치)이
영구 오탐을 낸다 — lint의 _all_pages()는 content/+_meta/만 페이지로 보기 때문.
(.cursorrules/.windsurfrules는 .md 확장자가 아니라 애초에 rglob("*.md")에
안 걸리므로 영향 없음.)
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core import db as db_module
from raven.core.lint import check_index_completeness
from raven.core.vault import Vault, ROOT_AGENT_INSTRUCTION_FILES


@pytest.fixture
def isolated_vaults_root(monkeypatch):
    tmp = Path(tempfile.mkdtemp(prefix="raven-stub-db-reg-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(tmp))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def isolated_target():
    tmp = Path(tempfile.mkdtemp(prefix="raven-stub-db-target-"))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


def test_agent_pointer_stubs_not_indexed_as_pages(isolated_vaults_root, isolated_target):
    v = Vault.create("stub-db-check", isolated_target / "stub-db-check", profile="llm-wiki")
    db_module.build_db(v, run_lint=False)
    issues = check_index_completeness(v)
    stub_basenames = {Path(f).stem for f in ROOT_AGENT_INSTRUCTION_FILES if f.endswith(".md")}
    offending = [i for i in issues if i["slug"] in stub_basenames]
    assert offending == [], offending
