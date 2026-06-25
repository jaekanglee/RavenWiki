"""wikisys.core.lint — vault-aware lint runner (v0.5.1+ 12 checks).

카파시 LLM Wiki gist의 12개 lint 항목 전체 자동화.

12 checks (severity: critical / warning / info):
    #1  broken wikilinks              (link_module.find_broken)
    #2  broken-intent false positive  (link_module: [[x]]! 인데 target 존재)
    #3  missing wikilinks              (link_module.find_missing)
    #4  orphan pages (7일 grace)       (check_orphans)
    #5  contradictions                 (check_contradictions)
    #6  confidence low                 (check_confidence_low)
    #7  stale pages (90일)             (check_stale)
    #8  page size > 200줄              (check_page_size)
    #9  tag not in core taxonomy       (check_tag_audit)
    #10 frontmatter 완전성             (check_frontmatter_completeness)
    #11 index 완전성 (FS vs DB)        (check_index_completeness)
    #12 log size > 500 entries         (check_log_size)

v0.5.0: #12 (log_size) + #1-3 (link_module) 선반영.
v0.5.1: #4-#11 추가. 12/12 완성.

grace period (orphan): vault 메타의 .vault.json에 `lint_orphan_grace_days` 키로
override 가능 (없으면 기본 7일).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from .vault import Vault
from . import link as link_module


# 카파시 가이드 상수
LOG_ROTATE_THRESHOLD = 500
ORPHAN_GRACE_DAYS_DEFAULT = 7
STALE_DAYS = 90
PAGE_SIZE_LINES = 200
INDEX_COMPLETE_BUILD_REQUIRED = True  # build 후에만 검증

# core tag fallback (SCHEMA.md에 명시 안 됐을 때 사용)
CORE_TAGS_FALLBACK = {
    # 시스템
    "system", "tool", "ui", "search", "viewer", "schema", "mcp", "dashboard",
    # 컨텐츠
    "concept", "person", "comparison", "project", "rule", "query", "journal",
    # 도메인
    "ai", "wiki", "karpathy", "llm-wiki", "tailscale", "react", "python", "docker",
    # 상태
    "draft", "review", "final", "deprecated", "orphan",
}


# ────────────────────────── 데이터 구조 ──────────────────────────


# Issue는 dict: {"id": "#N", "severity": "critical|warning|info",
#                 "slug": "content/foo", "message": "..."}
# 또는 link_module 결과 그대로 {"source_slug", "target", "intent"}


def _mk_issue(check_id: str, severity: str, slug: str, message: str) -> dict:
    return {"id": check_id, "severity": severity, "slug": slug, "message": message}


# ────────────────────────── helpers ──────────────────────────


def _repo_root() -> Optional[Path]:
    return Path(__file__).resolve().parents[2]


def _all_pages(vault: Vault) -> list[Path]:
    """vault 안 모든 .md 페이지 (content/ + _meta/)."""
    out = list(vault.content_root.rglob("*.md"))
    meta_dir = vault.meta_root
    if meta_dir.exists():
        out.extend(meta_dir.rglob("*.md"))
    return sorted(out)


def _slug_of(vault: Vault, fp: Path) -> str:
    return str(fp.relative_to(vault.root))[:-3]


def _parse_fm(fp: Path) -> dict:
    """frontmatter parse (없으면 {})."""
    from . import frontmatter as fm_mod
    text = fp.read_text(errors="replace")
    meta, _ = fm_mod.parse(text)
    return meta


def _core_tags(vault: Vault) -> set[str]:
    """SCHEMA.md에서 core tags 동적 파싱, 실패 시 fallback."""
    schema = vault.meta_root / "SCHEMA.md"
    if not schema.exists():
        return set(CORE_TAGS_FALLBACK)
    text = schema.read_text(errors="replace")
    # "### Core Tags" 또는 "## Tag Taxonomy" 섹션의 `- tag` 패턴 추출
    tags: set[str] = set()
    in_core = False
    for line in text.splitlines():
        if re.search(r"core\s*tags?", line, re.IGNORECASE):
            in_core = True
            continue
        if in_core:
            # 다음 ## 헤더 나오면 중단
            if line.startswith("##") and not line.startswith("###"):
                in_core = False
                continue
            m = re.match(r"^\s*[-*]\s*`?([a-z0-9-]+)`?", line)
            if m:
                tags.add(m.group(1).lower())
    return tags if tags else set(CORE_TAGS_FALLBACK)


def _orphan_grace_days(vault: Vault) -> int:
    """vault 메타의 .vault.json에서 grace 기간 override."""
    vf = vault.root / ".vault.json"
    if vf.exists():
        try:
            data = json.loads(vf.read_text())
            v = data.get("lint_orphan_grace_days")
            if isinstance(v, int) and v >= 0:
                return v
        except Exception:
            pass
    return ORPHAN_GRACE_DAYS_DEFAULT


# ────────────────────────── check 함수들 (v0.5.1+ 신규) ──────────────────────────


def check_orphans(vault: Vault) -> list[dict]:
    """#4 orphan: inbound wikilink 0 인 페이지. grace 기간 (기본 7일) 지나면 warning.

    Returns: [{"id":"#4", "severity":"warning|info", "slug":..., "message":...}, ...]
    """
    grace = _orphan_grace_days(vault)
    today = date.today()

    # inbound map (slug → count)
    inbound: dict[str, int] = {}
    for fp in _all_pages(vault):
        text = fp.read_text(errors="replace")
        src_slug = _slug_of(vault, fp)
        for lnk in link_module.parse(text):
            if lnk.intent != "auto":
                continue
            tgt = lnk.target.split("|", 1)[0].strip()
            if not tgt or "/" not in tgt:
                continue
            inbound[tgt] = inbound.get(tgt, 0) + 1

    out: list[dict] = []
    for fp in _all_pages(vault):
        slug = _slug_of(vault, fp)
        if inbound.get(slug, 0) > 0:
            continue
        # orphan: created 기준 grace 계산
        fm = _parse_fm(fp)
        created_str = fm.get("created")
        try:
            created = date.fromisoformat(created_str) if created_str else today
        except Exception:
            created = today
        age = (today - created).days
        if age >= grace:
            out.append(_mk_issue(
                "#4", "warning", slug,
                f"orphan (no inbound, age {age}d ≥ grace {grace}d)",
            ))
        else:
            out.append(_mk_issue(
                "#4", "info", slug,
                f"orphan (no inbound, age {age}d < grace {grace}d — grace 중)",
            ))
    return out


def check_contradictions(vault: Vault) -> list[dict]:
    """#5 contradictions: frontmatter.contradictions: [a, b] 인데 a/b 미존재 → warning."""
    out: list[dict] = []
    existing = {_slug_of(vault, fp) for fp in _all_pages(vault)}
    for fp in _all_pages(vault):
        slug = _slug_of(vault, fp)
        fm = _parse_fm(fp)
        cont = fm.get("contradictions")
        if not cont:
            continue
        if not isinstance(cont, list):
            out.append(_mk_issue(
                "#5", "info", slug,
                f"contradictions field is not a list: {cont!r}",
            ))
            continue
        for ref in cont:
            if ref not in existing:
                out.append(_mk_issue(
                    "#5", "warning", slug,
                    f"contradictions: [{ref}] 가 vault에 없음",
                ))
    return out


def check_confidence_low(vault: Vault) -> list[dict]:
    """#6 confidence low: frontmatter.confidence: low 인 페이지 → info."""
    out: list[dict] = []
    for fp in _all_pages(vault):
        slug = _slug_of(vault, fp)
        fm = _parse_fm(fp)
        if fm.get("confidence") == "low":
            out.append(_mk_issue(
                "#6", "info", slug,
                "confidence: low (단일 출처 / 미검증 주장)",
            ))
    return out


def check_stale(vault: Vault) -> list[dict]:
    """#7 stale: updated > 90일 + content/RAG/위키 등 도메인 페이지 → info.

    운영 문서 (`type: rule`) + `_meta/`는 면제.
    """
    today = date.today()
    out: list[dict] = []
    for fp in _all_pages(vault):
        slug = _slug_of(vault, fp)
        if slug.startswith("_meta/"):
            continue
        fm = _parse_fm(fp)
        if fm.get("type") == "rule":
            continue
        updated_str = fm.get("updated")
        try:
            updated = date.fromisoformat(updated_str) if updated_str else None
        except Exception:
            updated = None
        if not updated:
            continue
        age = (today - updated).days
        if age >= STALE_DAYS:
            out.append(_mk_issue(
                "#7", "info", slug,
                f"stale (updated {age}d 전, {STALE_DAYS}d+ 기준)",
            ))
    return out


def check_page_size(vault: Vault) -> list[dict]:
    """#8 page size > 200줄 → info (분할 권장)."""
    out: list[dict] = []
    for fp in _all_pages(vault):
        slug = _slug_of(vault, fp)
        try:
            n = sum(1 for _ in fp.open(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        if n > PAGE_SIZE_LINES:
            out.append(_mk_issue(
                "#8", "info", slug,
                f"page size {n}줄 > {PAGE_SIZE_LINES}줄 (분할 권장)",
            ))
    return out


def check_tag_audit(vault: Vault) -> list[dict]:
    """#9 tag not in core taxonomy → warning. 단, custom tag도 가능 (코어 권장)."""
    core = _core_tags(vault)
    out: list[dict] = []
    for fp in _all_pages(vault):
        slug = _slug_of(vault, fp)
        fm = _parse_fm(fp)
        tags = fm.get("tags")
        if not isinstance(tags, list):
            continue
        for t in tags:
            if not isinstance(t, str):
                continue
            t_norm = t.lower().strip()
            if t_norm and t_norm not in core:
                out.append(_mk_issue(
                    "#9", "warning", slug,
                    f"tag {t!r} not in core taxonomy (custom은 OK, 코어 승격은 SCHEMA.md에 추가)",
                ))
    return out


def check_frontmatter_completeness(vault: Vault) -> list[dict]:
    """#10 frontmatter 완전성: title/type/created/updated 필수. created/updated는 warning, 나머지는 info."""
    out: list[dict] = []
    for fp in _all_pages(vault):
        slug = _slug_of(vault, fp)
        fm = _parse_fm(fp)
        if not fm:
            out.append(_mk_issue(
                "#10", "warning", slug, "no frontmatter",
            ))
            continue
        if not fm.get("title"):
            out.append(_mk_issue("#10", "info", slug, "frontmatter.title missing"))
        if not fm.get("type"):
            out.append(_mk_issue("#10", "info", slug, "frontmatter.type missing"))
        if not fm.get("created"):
            out.append(_mk_issue("#10", "warning", slug, "frontmatter.created missing"))
        if not fm.get("updated"):
            out.append(_mk_issue("#10", "warning", slug, "frontmatter.updated missing"))
    return out


def check_index_completeness(vault: Vault) -> list[dict]:
    """#11 index 완전성: filesystem 페이지 vs wiki.db. DB 없으면 info (build 필요).

    `wikisys build` 후 실행 가정. DB 없으면 build 요청.
    """
    out: list[dict] = []
    db_path = vault.db_path
    if not db_path.exists():
        out.append(_mk_issue(
            "#11", "info", "(vault)",
            f"wiki.db 없음: `wikisys build` 필요 ({db_path})",
        ))
        return out
    # DB의 pages 테이블 slug 조회
    try:
        import sqlite3
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cur = con.execute("SELECT slug FROM pages")
        db_slugs = {r[0] for r in cur.fetchall()}
        con.close()
    except Exception as e:
        out.append(_mk_issue(
            "#11", "warning", "(vault)",
            f"wiki.db 읽기 실패: {e}",
        ))
        return out

    fs_slugs = {_slug_of(vault, fp) for fp in _all_pages(vault)}
    only_fs = fs_slugs - db_slugs
    only_db = db_slugs - fs_slugs
    for slug in sorted(only_fs):
        out.append(_mk_issue(
            "#11", "warning", slug, "filesystem에만 있음 (build 필요)",
        ))
    for slug in sorted(only_db):
        out.append(_mk_issue(
            "#11", "warning", slug, "DB에만 있음 (stale build, 재build 필요)",
        ))
    return out


def check_log_size(vault: Vault) -> list[dict]:
    """#12 log size > 500 entries → info."""
    from . import log as _log
    path = _log.log_path(vault)
    if not path.exists():
        return []
    entries = _log.count(vault)
    if entries >= LOG_ROTATE_THRESHOLD:
        return [_mk_issue(
            "#12", "info", "(vault)",
            f"log.md {entries} entries ≥ {LOG_ROTATE_THRESHOLD} (rotate 권장)",
        )]
    return []


# ────────────────────────── 합쳐서 run ──────────────────────────


def _legacy_link_issues(vault: Vault) -> list[dict]:
    """#1-3 (link_module 결과를 lint issue 형식으로 변환)."""
    out: list[dict] = []
    for b in link_module.find_broken(vault):
        # [[x]]인데 target 없음 → critical
        out.append({
            "id": "#1",
            "severity": "critical",
            "slug": b["source_slug"],
            "message": f"broken wikilink [[{b['target']}]] — target 없음",
            "target": b["target"],
        })
    # #2: [[x]]! 인데 target 존재 → critical (v0.5.1+)
    for b in link_module.find_broken_intent(vault):
        out.append({
            "id": "#2",
            "severity": "critical",
            "slug": b["source_slug"],
            "message": f"broken-intent false positive: [[{b['target']}]]! 인데 target 존재 — intent 잘못",
            "target": b["target"],
        })
    for m in link_module.find_missing(vault):
        # [[x]]? 인데 target 없음 → info (의도적 placeholder)
        out.append({
            "id": "#3",
            "severity": "info",
            "slug": m["source_slug"],
            "message": f"missing wikilink [[{m['target']}]]? — 의도적 placeholder (OK)",
            "target": m["target"],
        })
    return out


def run_all(vault: Vault) -> dict:
    """12 check 모두 실행. counts + issues list 반환.

    Returns:
        {
          "vault": name,
          "ok": bool (no critical),
          "counts": {"critical": N, "warning": M, "info": K, "total": N+M+K},
          "issues": [issue dicts],
          "by_check": {"#1": count, "#2": ..., ...},
        }
    """
    issues: list[dict] = []
    # #1-3 link
    issues.extend(_legacy_link_issues(vault))
    # #4-12
    issues.extend(check_orphans(vault))
    issues.extend(check_contradictions(vault))
    issues.extend(check_confidence_low(vault))
    issues.extend(check_stale(vault))
    issues.extend(check_page_size(vault))
    issues.extend(check_tag_audit(vault))
    issues.extend(check_frontmatter_completeness(vault))
    issues.extend(check_index_completeness(vault))
    issues.extend(check_log_size(vault))

    counts = {"critical": 0, "warning": 0, "info": 0, "total": 0}
    by_check: dict[str, int] = {}
    for iss in issues:
        sev = iss.get("severity", "info")
        counts[sev] = counts.get(sev, 0) + 1
        counts["total"] += 1
        cid = iss.get("id", "?")
        by_check[cid] = by_check.get(cid, 0) + 1

    return {
        "ok": counts["critical"] == 0,
        "vault": vault.meta.name,
        "counts": counts,
        "issues": issues,
        "by_check": by_check,
    }


# ────────────────────────── legacy run_lint (back-compat) ──────────────────────────


def run_lint(vault: Vault) -> dict:
    """기존 호출자 호환용 wrapper. run_all() 호출 후 counts만 추출.

    v0.5.0의 단순 wrapper는 _inline_scan / _run_legacy 양쪽 모두 합친 결과 반환.
    새 코드는 run_all()을 직접 호출 권장.
    """
    repo_root = _repo_root()
    script = repo_root / "scripts" / "lint.py" if repo_root else None
    legacy = {"output_tail": "", "returncode": 0}
    if script and script.exists():
        try:
            argv = [sys.executable, str(script), str(vault.root)]
            env = os.environ.copy()
            result = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=10)
            legacy["output_tail"] = ((result.stdout or "") + (result.stderr or ""))[-800:]
            legacy["returncode"] = result.returncode
        except Exception:
            pass
    full = run_all(vault)
    return {
        "ok": full["ok"],
        "vault": full["vault"],
        "counts": full["counts"],
        "returncode": legacy["returncode"],
        "output_tail": legacy["output_tail"],
        "issues": full["issues"],
        "by_check": full["by_check"],
    }
