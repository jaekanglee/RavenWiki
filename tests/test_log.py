"""Tests for raven.core.log — log.md (작업 이력) 관리.

카파시 LLM Wiki 패턴 검증:
- log.md 위치 = vault 루트
- 형식 = `## [YYYY-MM-DD] action | subject`
- append-only, parseable
- 500 entries → rotate 권장
"""
from __future__ import annotations

import sys
import shutil
import tempfile
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.core import log as log_module
from raven.core.log import (
    LogEntry,
    _ALLOWED_ACTIONS,
    _HEADER_RE,
    append,
    count,
    ensure_log,
    list_entries,
    load,
    log_path,
    rotate,
)
from raven.core.vault import Vault


@pytest.fixture
def vault(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-log-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-log-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    v = Vault.create("log-test", target_root / "log-test")
    yield v
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


# ────────────────────────── 경로 ──────────────────────────


def test_log_path_is_vault_root(vault):
    """카파시 가이드: log.md는 vault 루트 고정."""
    assert log_path(vault) == vault.root / "log.md"


# ────────────────────────── ensure_log ──────────────────────────


def test_ensure_log_creates_from_template(vault):
    """첫 로그 작업에서만 템플릿을 생성한다."""
    assert not log_path(vault).exists()
    p = ensure_log(vault)
    assert p.exists()
    text = p.read_text()
    assert "log.md initialized" in text
    assert "## [" in text  # 카파시 grep-parseable 헤더


def test_ensure_log_idempotent(vault):
    """두 번 호출해도 동일."""
    p1 = ensure_log(vault)
    size1 = p1.stat().st_size
    p2 = ensure_log(vault)
    size2 = p2.stat().st_size
    assert p1 == p2
    assert size1 == size2


# ────────────────────────── append ──────────────────────────


def test_append_basic(vault):
    """기본 append 동작."""
    e = append(vault, action="create", subject="hello world")
    assert e.date == date.today().isoformat()
    assert e.action == "create"
    assert e.subject == "hello world"
    assert e.header() == f"## [{e.date}] create | hello world"


def test_append_with_files_and_note(vault):
    """files + note 함께 append."""
    e = append(
        vault,
        action="update",
        subject="foo",
        files=["content/foo.md", "content/bar.md"],
        note="cross-link 추가",
    )
    assert e.details == [
        "files: [content/foo.md, content/bar.md]",
        "reason: cross-link 추가",
    ]


def test_append_invalid_action_rejected(vault):
    """허용 안 된 action은 ValueError."""
    with pytest.raises(ValueError, match="action 'invalid' not allowed"):
        append(vault, action="invalid", subject="x")


def test_append_all_allowed_actions(vault):
    """9종 액션 모두 통과."""
    for action in _ALLOWED_ACTIONS:
        e = append(vault, action=action, subject=f"test {action}")
        assert e.action == action


def test_append_writes_to_disk(vault):
    """append 후 log.md에 실제 기록 확인."""
    append(vault, action="ingest", subject="karpathy LLM Wiki gist",
           files=["content/llm-wiki"], note="v0.5.0 도입")
    text = log_path(vault).read_text()
    assert "## [" in text
    assert "ingest | karpathy LLM Wiki gist" in text
    assert "files: [content/llm-wiki]" in text
    assert "reason: v0.5.0 도입" in text


def test_append_idempotent_separate_lines(vault):
    """여러 번 append 시 각자 한 entry로."""
    append(vault, "chore", "first")
    append(vault, "chore", "second")
    append(vault, "chore", "third")
    assert count(vault) == 3


# ────────────────────────── load / count / list ──────────────────────────


def test_load_empty(vault):
    """새 plain vault는 log.md를 만들지 않으며 빈 이력을 반환한다."""
    assert load(vault) == []
    assert count(vault) == 0


def test_load_parses_entries(vault):
    """append 후 load 시 entry 객체로 파싱."""
    append(vault, "create", "page-a", note="first")
    append(vault, "update", "page-b", files=["content/b"], note="second")
    entries = load(vault)
    assert len(entries) == 2
    user_entries = entries
    assert user_entries[0].action == "create"
    assert user_entries[0].subject == "page-a"
    assert "reason: first" in user_entries[0].details
    assert user_entries[1].action == "update"
    assert "files: [content/b]" in user_entries[1].details


def test_list_entries_tail(vault):
    """tail=N 옵션 동작."""
    for i in range(5):
        append(vault, "chore", f"entry {i}")
    last3 = list_entries(vault, tail=3)
    assert len(last3) == 3
    assert last3[-1]["subject"] == "entry 4"


def test_list_entries_action_filter(vault):
    """action 필터 동작."""
    append(vault, "create", "a")
    append(vault, "update", "b")
    append(vault, "create", "c")
    only_create = list_entries(vault, action="create")
    assert len(only_create) == 2
    assert all(e["action"] == "create" for e in only_create)


# ────────────────────────── rotate ──────────────────────────


def test_rotate_creates_yearly_file(vault):
    """rotate 시 log-YYYY.md 생성 + 새 log.md."""
    for i in range(3):
        append(vault, "chore", f"entry {i}")
    target = rotate(vault, year=2026)
    assert target.name == "log-2026.md"
    assert target.exists()
    # 새 log.md는 rotation entry만
    new_entries = load(vault)
    assert len(new_entries) == 1
    assert "rotated" in new_entries[0].subject


def test_rotate_collision_suffix(vault):
    """log-YYYY.md 이미 있으면 log-YYYY-1.md."""
    (vault.root / "log-2026.md").write_text("# old\n", encoding="utf-8")
    append(vault, "chore", "x")
    target = rotate(vault, year=2026)
    assert target.name == "log-2026-1.md"


# ────────────────────────── 카파시 grep-parseable ──────────────────────────


def test_format_grep_compatible(vault):
    """grep "^## \\[" 형식으로 파싱 가능해야 함 (실제 entry만).

    v0.5.5+ silent-write fix: fixture 의 Vault.create() 가 1개 create entry 를 남기므로
    2번 explicit append 후 실제 entry 헤더는 3개.
    """
    append(vault, "ingest", "source A")
    append(vault, "update", "page B")
    text = log_path(vault).read_text()
    # 실제 entry 헤더만 (YYYY-MM-DD 형식, 템플릿 placeholder 제외)
    real_headers = [
        line for line in text.splitlines()
        if line.startswith("## [") and _HEADER_RE.match(line)
    ]
    assert len(real_headers) == 2
    assert all(_HEADER_RE.match(h) for h in real_headers)
    # grep "^## \[" 카파시 팁과 일치
    grep_style = [line for line in text.splitlines() if line.startswith("## [")]
    assert len(grep_style) >= 2
