"""Tests for raven.migrate — v0.5.2+ 마이그레이션 dry-run/apply."""
from __future__ import annotations

import sys
import shutil
import tempfile
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven import migrate as migrate_module
from raven.migrate import (
    CATEGORIES,
    MigrationPlan,
    apply_broken_to_missing,
    apply_frontmatter_fill,
    apply_orphan_cleanup,
    make_plan,
    apply_plan,
)
from raven.core.vault import Vault


@pytest.fixture
def vault(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-mig-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-mig-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    v = Vault.create("mig-test", target_root / "mig-test")
    yield v
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def _write_page(v: Vault, slug: str, fm: dict, body: str = "# x\n") -> Path:
    from raven.core.frontmatter import render
    fp = v.root / f"{slug}.md"
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(render(fm, body), encoding="utf-8")
    return fp


# ────────────────────────── plan 구조 ──────────────────────────


def test_make_plan_returns_5_categories(vault):
    plan = make_plan(vault)
    assert plan.vault == vault.meta.name
    assert isinstance(plan.fixes, list)
    # 5개 카테고리 모두 키 존재
    by = plan.by_category
    for c in CATEGORIES:
        assert c in by


def test_make_plan_with_clean_vault(vault):
    """깨끗한 vault → fix 없거나 매우 적음."""
    today = date.today().isoformat()
    _write_page(vault, "content/clean", {
        "title": "Clean", "type": "concept",
        "created": today, "updated": today,
    }, body="nothing here\n")
    plan = make_plan(vault)
    # 깨끗한 vault는 broken_to_missing 0개
    assert all(f.category != "broken_to_missing" for f in plan.fixes)


# ────────────────────────── apply 함수들 ──────────────────────────


def test_apply_broken_to_missing(vault):
    """[[x]] (broken) → [[x]]? (의도적 placeholder) 변환."""
    today = date.today().isoformat()
    _write_page(vault, "content/src", {
        "title": "Src", "type": "concept",
        "created": today, "updated": today,
    }, body="see [[content/missing]]\n")
    ok = apply_broken_to_missing(vault, "content/src", "content/missing")
    assert ok
    text = (vault.root / "content" / "src.md").read_text()
    assert "[[content/missing]]?" in text
    assert "[[content/missing]]\n" not in text  # intent 없는 버전은 사라짐


def test_apply_broken_to_missing_skips_with_intent(vault):
    """[[x]]! 또는 [[x]]? 는 그대로."""
    today = date.today().isoformat()
    _write_page(vault, "content/src", {
        "title": "Src", "type": "concept",
        "created": today, "updated": today,
    }, body="see [[content/x]]? and [[content/y]]!\n")
    apply_broken_to_missing(vault, "content/src", "content/x")
    apply_broken_to_missing(vault, "content/src", "content/y")
    text = (vault.root / "content" / "src.md").read_text()
    assert "[[content/x]]?" in text
    assert "[[content/y]]!" in text


def test_apply_broken_to_missing_without_target_is_noop(vault):
    """평가 A#6: target 없이 호출하면 (구 시그니처 오용) 아무것도 바꾸지 않는다."""
    today = date.today().isoformat()
    _write_page(vault, "content/src", {
        "title": "Src", "type": "concept",
        "created": today, "updated": today,
    }, body="see [[content/missing]]\n")
    ok = apply_broken_to_missing(vault, "content/src")
    assert ok is False
    text = (vault.root / "content" / "src.md").read_text()
    assert "[[content/missing]]\n" in text  # unchanged


def test_apply_broken_to_missing_only_touches_named_target(vault):
    """평가 A#6 회귀 가드: pre-v0.7.67은 페이지 내 intent-suffix 없는 위키링크
    *전부*를 강등했다 (그 판별 헬퍼가 항상 False를 반환하는 죽은 로직이었기
    때문). 이제 lint #1이 지목한 target 하나만 강등되고, 같은 페이지의 다른
    유효한 링크는 손대지 않는다."""
    today = date.today().isoformat()
    _write_page(vault, "content/src", {
        "title": "Src", "type": "concept",
        "created": today, "updated": today,
    }, body=(
        "see [[content/valid-a]] and [[content/valid-b]] "
        "and [[content/missing]]\n"
    ))
    ok = apply_broken_to_missing(vault, "content/src", "content/missing")
    assert ok is True
    text = (vault.root / "content" / "src.md").read_text()
    assert "[[content/missing]]?" in text
    # 유효한 링크는 그대로 — placeholder로 강등되지 않음
    assert "[[content/valid-a]]" in text and "[[content/valid-a]]?" not in text
    assert "[[content/valid-b]]" in text and "[[content/valid-b]]?" not in text


def test_apply_frontmatter_fill(vault):
    """created/updated missing → today로 채움."""
    from raven.core.frontmatter import parse
    # frontmatter 자체는 있지만 created/updated 없음
    fp = vault.root / "content" / "no-dates.md"
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text("---\ntitle: X\ntype: concept\n---\n\nbody\n", encoding="utf-8")
    ok = apply_frontmatter_fill(vault, "content/no-dates")
    assert ok
    meta, _ = parse(fp.read_text())
    assert "created" in meta
    assert "updated" in meta


def test_apply_orphan_cleanup(vault):
    """orphan 페이지를 _archive/로 이동."""
    today = date.today().isoformat()
    _write_page(vault, "content/lonely", {
        "title": "Lonely", "type": "concept",
        "created": today, "updated": today,
    })
    ok = apply_orphan_cleanup(vault, "content/lonely")
    assert ok
    assert not (vault.root / "content" / "lonely.md").exists()
    # _archive/ 아래로
    archive_files = list((vault.root / "_archive").rglob("lonely-*.md"))
    assert len(archive_files) == 1


# ────────────────────────── apply_plan (통합) ──────────────────────────


def test_apply_plan_safe_only(vault):
    today = date.today().isoformat()
    _write_page(vault, "content/src", {
        "title": "Src", "type": "concept",
        "created": today, "updated": today,
    }, body="see [[content/missing]]\n")
    plan = make_plan(vault)
    # safe만 적용
    result = apply_plan(vault, plan, risk_filter="safe")
    # safe fix는 applied, manual/review는 skipped
    for a in result["applied"]:
        assert a.get("action") in ("apply_broken_to_missing", "apply_frontmatter_fill", "apply_orphan_cleanup")
    for s in result["skipped"]:
        # skipped의 reason은 risk 또는 manual
        assert s.get("reason") in ("manual", "no apply_fn", "no change") or "risk" in s.get("reason", "")


def test_apply_plan_dry_run_no_change(vault):
    """apply_plan 호출 전과 후 filesystem 동일 (safe 적용 안 했을 때)."""
    today = date.today().isoformat()
    _write_page(vault, "content/src", {
        "title": "Src", "type": "concept",
        "created": today, "updated": today,
    }, body="see [[content/missing]]\n")
    before = list(vault.content_root.rglob("*.md"))
    plan = make_plan(vault)
    apply_plan(vault, plan, risk_filter="manual")  # manual은 모두 skip
    after = list(vault.content_root.rglob("*.md"))
    assert len(before) == len(after)
