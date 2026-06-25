"""raven.migrate — vault 마이그레이션 도구 (v0.5.2+).

lint 결과를 5 카테고리로 분류하고, 적용 가능한 fix를 dry-run으로 미리 보여줌.
**기본 = dry-run, 절대 데이터 변경 ❌** (사용자 --apply 명시 시에만 실행).

카테고리:
    1. broken_wikilink_to_missing: [[x]] (target 없음) → [[x]]? 로 변환 후보
    2. orphan_cleanup: inbound 0 페이지 → archive 후보
    3. page_size_split: 200줄+ 페이지 → 분할 필요 (사용자 결정)
    4. tag_promotion: custom tag → core 승격 후보 (SCHEMA.md에 추가)
    5. frontmatter_fill: missing created/updated → 자동 채움 (안전)

CLI:
    raven migrate plan --vault <name>           # dry-run
    raven migrate plan --vault <name> --apply   # 적용 (위험!)
    raven migrate category broken --vault <name> # 특정 카테고리만
"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from .core import lint as lint_module
from .core.vault import Vault


CATEGORIES = [
    "broken_to_missing",   # 1
    "orphan_cleanup",      # 2
    "page_size_split",     # 3
    "tag_promotion",       # 4
    "frontmatter_fill",    # 5
]


@dataclass
class Fix:
    """하나의 수정 사항."""
    category: str
    slug: str
    description: str
    risk: str  # "safe" | "review" | "manual"
    apply_fn: Optional[str] = None  # 함수 이름 (실행 시 호출)


@dataclass
class MigrationPlan:
    """vault의 migration plan (dry-run 결과)."""
    vault: str
    fixes: list[Fix] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    lint_summary: dict = field(default_factory=dict)

    @property
    def by_category(self) -> dict[str, list[Fix]]:
        out = {c: [] for c in CATEGORIES}
        for f in self.fixes:
            out.setdefault(f.category, []).append(f)
        return out

    def summary(self) -> dict:
        by_cat = {c: len(self.by_category[c]) for c in CATEGORIES}
        safe = sum(1 for f in self.fixes if f.risk == "safe")
        review = sum(1 for f in self.fixes if f.risk == "review")
        manual = sum(1 for f in self.fixes if f.risk == "manual")
        return {
            "vault": self.vault,
            "total_fixes": len(self.fixes),
            "by_category": by_cat,
            "by_risk": {"safe": safe, "review": review, "manual": manual},
            "lint_summary": self.lint_summary,
        }


# ────────────────────────── plan builders ──────────────────────────


def _plan_broken_to_missing(vault: Vault, lint_result: dict) -> list[Fix]:
    """#1 broken wikilink 중 target 없는 것 → [[x]]? 변환 후보.

    단, template placeholder (`<...>`) 는 자동 변환 ❌ (의도적일 수 있음).
    """
    fixes = []
    for iss in lint_result.get("issues", []):
        if iss.get("id") != "#1":
            continue
        target = iss.get("target", "")
        slug = iss.get("slug", "")
        if not target or not slug:
            continue
        # template placeholder는 skip
        if "<" in target or ">" in target:
            fixes.append(Fix(
                category="broken_to_missing",
                slug=slug,
                description=f"template placeholder [[{target}]] — 수동 결정 필요",
                risk="manual",
            ))
            continue
        fixes.append(Fix(
            category="broken_to_missing",
            slug=slug,
            description=f"[[{target}]] → [[{target}]]? (의도적 placeholder로 표시)",
            risk="safe",
            apply_fn="apply_broken_to_missing",
        ))
    return fixes


def _plan_orphan_cleanup(vault: Vault, lint_result: dict) -> list[Fix]:
    """#4 orphan (grace 만료) → archive 후보.

    inbound 0 + created가 grace 초과. archive = _archive/로 이동.
    """
    fixes = []
    for iss in lint_result.get("issues", []):
        if iss.get("id") != "#4" or iss.get("severity") != "warning":
            continue
        fixes.append(Fix(
            category="orphan_cleanup",
            slug=iss.get("slug", ""),
            description=f"orphan (grace 만료) → _archive/ 이동 후보",
            risk="review",  # 사용자 확인 필요
            apply_fn="apply_orphan_cleanup",
        ))
    return fixes


def _plan_page_size_split(vault: Vault, lint_result: dict) -> list[Fix]:
    """#8 page size > 200줄 → 분할 필요 (사용자 결정).

    자동 분할 ❌ (내용 의미 단위 분할은 LLM이 해야 함).
    """
    fixes = []
    for iss in lint_result.get("issues", []):
        if iss.get("id") != "#8":
            continue
        fixes.append(Fix(
            category="page_size_split",
            slug=iss.get("slug", ""),
            description=f"{iss.get('message', '')} — 분할 결정 필요 (수동)",
            risk="manual",
        ))
    return fixes


def _plan_tag_promotion(vault: Vault, lint_result: dict) -> list[Fix]:
    """#9 tag not in core → custom tag (SCHEMA.md 승격 후보).

    자동 승격 ❌ (사용자가 SCHEMA.md 보고 결정).
    """
    fixes = []
    for iss in lint_result.get("issues", []):
        if iss.get("id") != "#9":
            continue
        # message format: "tag {t!r} not in core taxonomy"
        msg = iss.get("message", "")
        m = re.search(r"tag\s+'([^']+)'", msg)
        if not m:
            continue
        tag = m.group(1)
        fixes.append(Fix(
            category="tag_promotion",
            slug=iss.get("slug", ""),
            description=f"tag '{tag}' → SCHEMA.md core 승격 후보",
            risk="review",
        ))
    return fixes


def _plan_frontmatter_fill(vault: Vault, lint_result: dict) -> list[Fix]:
    """#10 frontmatter 완전성 missing created/updated → 자동 채움 (safe).

    title/type 없으면 자동 채움 불가 (사용자 결정).
    created/updated 없으면 today로 채움 (safe).
    """
    fixes = []
    today = date.today().isoformat()
    for iss in lint_result.get("issues", []):
        if iss.get("id") != "#10":
            continue
        msg = iss.get("message", "")
        if "created" in msg or "updated" in msg:
            fixes.append(Fix(
                category="frontmatter_fill",
                slug=iss.get("slug", ""),
                description=f"frontmatter {msg} → today로 채움",
                risk="safe",
                apply_fn="apply_frontmatter_fill",
            ))
        else:
            fixes.append(Fix(
                category="frontmatter_fill",
                slug=iss.get("slug", ""),
                description=f"frontmatter {msg} — 사용자 입력 필요 (수동)",
                risk="manual",
            ))
    return fixes


# ────────────────────────── apply 함수들 (안전한 것만) ──────────────────────────


def apply_broken_to_missing(vault: Vault, slug: str) -> bool:
    """[[x]] (broken) → [[x]]? (의도적 placeholder).

    Args:
        vault: vault handle
        slug: 변경할 페이지의 slug

    Returns:
        True if changed, False otherwise
    """
    fp = vault.root / f"{slug}.md"
    if not fp.exists():
        return False
    text = fp.read_text(encoding="utf-8")
    # [[target]] (intent 없음) → [[target]]?
    # 단, [[target]]! / [[target]]? 는 그대로
    new_text = re.sub(
        r"\[\[([^\[\]\n]+?)\]\](\s|$)",
        lambda m: f"[[{m.group(1)}]]?{m.group(2)}"
        if not _has_intent_suffix(text, m.start())
        else m.group(0),
        text,
    )
    if new_text == text:
        return False
    fp.write_text(new_text, encoding="utf-8")
    return True


def _has_intent_suffix(text: str, offset: int) -> bool:
    """[[x]] 다음 문자가 ! 또는 ?인지 확인."""
    # offset은 [[x]] 매치 시작점. 매치 끝은 offset + len("[[x]]")
    end = offset + 1
    while end < len(text) and text[end] not in "[]\n":
        end += 1
    # 매치 다음 문자
    if end < len(text) and text[end] in "!?":
        return True
    return False


def apply_orphan_cleanup(vault: Vault, slug: str) -> bool:
    """orphan 페이지를 _archive/로 이동.

    Args:
        vault: vault handle
        slug: archive할 페이지 slug

    Returns:
        True if moved
    """
    import datetime as _dt
    fp = vault.root / f"{slug}.md"
    if not fp.exists():
        return False
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_dir = vault.root / "_archive"
    archive_dir.mkdir(exist_ok=True)
    rel = fp.relative_to(vault.root)
    dest = archive_dir / rel.parent / f"{rel.stem}-{ts}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    fp.rename(dest)
    return True


def apply_frontmatter_fill(vault: Vault, slug: str) -> bool:
    """frontmatter created/updated 없으면 today로 채움."""
    from .core import frontmatter as fm_mod
    fp = vault.root / f"{slug}.md"
    if not fp.exists():
        return False
    text = fp.read_text(encoding="utf-8")
    meta, body = fm_mod.parse(text)
    today = date.today().isoformat()
    changed = False
    if "created" not in meta:
        meta["created"] = today
        changed = True
    if "updated" not in meta:
        meta["updated"] = today
        changed = True
    if not changed:
        return False
    fp.write_text(fm_mod.render(meta, body), encoding="utf-8")
    return True


# ────────────────────────── main: plan / apply ──────────────────────────


_PLAN_BUILDERS = {
    "broken_to_missing": _plan_broken_to_missing,
    "orphan_cleanup": _plan_orphan_cleanup,
    "page_size_split": _plan_page_size_split,
    "tag_promotion": _plan_tag_promotion,
    "frontmatter_fill": _plan_frontmatter_fill,
}

_APPLY_FNS = {
    "apply_broken_to_missing": apply_broken_to_missing,
    "apply_orphan_cleanup": apply_orphan_cleanup,
    "apply_frontmatter_fill": apply_frontmatter_fill,
}


def make_plan(vault: Vault, categories: Optional[list[str]] = None) -> MigrationPlan:
    """vault의 lint 결과를 5 카테고리로 분류한 plan 생성 (dry-run).

    Args:
        vault: vault handle
        categories: 특정 카테고리만 (None = 전체)

    Returns:
        MigrationPlan
    """
    lint_result = lint_module.run_all(vault)
    plan = MigrationPlan(
        vault=vault.meta.name,
        lint_summary=lint_result.get("counts", {}),
    )
    cats = categories or CATEGORIES
    for cat in cats:
        builder = _PLAN_BUILDERS.get(cat)
        if not builder:
            continue
        plan.fixes.extend(builder(vault, lint_result))
    return plan


def apply_plan(vault: Vault, plan: MigrationPlan, risk_filter: Optional[str] = None) -> dict:
    """plan 적용. risk_filter로 안전 단계만 (예: 'safe').

    Returns:
        {"applied": [...], "skipped": [...], "errors": [...]}
    """
    applied: list[dict] = []
    skipped: list[dict] = []
    errors: list[dict] = []

    for fix in plan.fixes:
        if risk_filter and fix.risk != risk_filter:
            skipped.append({"slug": fix.slug, "reason": f"risk={fix.risk} != {risk_filter}"})
            continue
        if fix.risk == "manual":
            skipped.append({"slug": fix.slug, "reason": "manual"})
            continue
        if not fix.apply_fn:
            skipped.append({"slug": fix.slug, "reason": "no apply_fn"})
            continue
        fn = _APPLY_FNS.get(fix.apply_fn)
        if not fn:
            errors.append({"slug": fix.slug, "error": f"unknown apply_fn: {fix.apply_fn}"})
            continue
        try:
            ok = fn(vault, fix.slug)
            if ok:
                applied.append({"slug": fix.slug, "category": fix.category, "action": fix.apply_fn})
            else:
                skipped.append({"slug": fix.slug, "reason": "no change"})
        except Exception as e:
            errors.append({"slug": fix.slug, "error": f"{type(e).__name__}: {e}"})

    return {"applied": applied, "skipped": skipped, "errors": errors}
