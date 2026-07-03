# -*- coding: utf-8 -*-
"""raven.core.lint — vault-aware lint runner (v0.5.1+ 14 checks).

Markdown PKM vault의 무결성을 확인한다. 일부 check는 Karpathy LLM Wiki
패턴에서 영감을 받았지만, Raven 기본 vault에도 적용 가능한 일반 lint다.

14 checks (severity: critical / warning / info):
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
    #13 cognitive governance           (check_cognitive_governance)
    #14 tier integrity                 (check_tier_integrity)

v0.5.0: #12 (log_size) + #1-3 (link_module) 선반영.
v0.5.1: #4-#11 추가. 12/12 완성.
v0.5.3: #13 cognitive governance 추가.
v0.6.33: #14 tier integrity 추가.

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


# vault lint defaults
LOG_ROTATE_THRESHOLD = 500
ORPHAN_GRACE_DAYS_DEFAULT = 7
STALE_DAYS = 90
PAGE_SIZE_LINES = 200
INDEX_COMPLETE_BUILD_REQUIRED = True  # build 후에만 검증

# #13 cognitive governance (Zettelkasten/LLM Wiki quality signal, v0.5.3+)
# 면제: type ∈ {rule, journal, query, issue} 또는 _meta/ 안 페이지 (운영 문서).
COG_GOV_EXEMPT_TYPES: frozenset[str] = frozenset({"rule", "journal", "query", "issue"})
# 본문 wikilink가 cross-discipline 후보로 인정받으려면 다음 단어가 slug에 포함.
# (heuristic — 사람/예술/생물/역사/철학 카테고리 위주)
COG_GOV_DISCIPLINE_KEYWORDS: tuple[str, ...] = (
    "human", "person", "art", "music", "paint", "literature", "poetry",
    "biology", "evolution", "ecology", "anatomy",
    "history", "ancient", "medieval", "renaissance",
    "philosophy", "ethics", "metaphysic", "epistemolog", "logic",
    "society", "culture", "religion", "mythology",
    "psychology", "cognitive", "linguistic",
)
# 명시적 cross-discipline 마커 (frontmatter.tags 또는 본문)
COG_GOV_CROSS_MARKERS: tuple[str, ...] = (
    "humanities", "art", "biology", "history", "philosophy",
)
# 반대 입장 헤딩 패턴
COG_GOV_OPPOSE_HEADINGS: tuple[str, ...] = (
    "반대 입장", "fights against", "alternatives", "alternative view",
    "counterargument", "criticism", "limitations",
)
# Why it matters 시그널 (본문 첫 문단/헤딩)
COG_GOV_WHY_PATTERNS: tuple[str, ...] = (
    "why it matters", "왜 중요", "why this matters",
)
# confidence 필드 화이트리스트
COG_GOV_CONFIDENCE_LEVELS: frozenset[str] = frozenset({"high", "medium", "low"})

# core tag fallback (SCHEMA.md에 명시 안 됐을 때 사용)
CORE_TAGS_FALLBACK = {
    # 시스템
    "system", "tool", "ui", "search", "viewer", "schema", "mcp", "dashboard",
    "meta", "workflow",
    # 컨텐츠
    "concept", "person", "comparison", "project", "rule", "query", "journal", "issue",
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
            # 형식 1: `- 시스템: \`tag1\`, \`tag2\`, ...` (한 줄에 여러 tag)
            m = re.match(r"^\s*[-*]\s*[^*]+:\s*`?([a-z0-9-]+)`?", line)
            if m:
                tags.add(m.group(1).lower())
                # 같은 줄에 더 있는 tag도 추출
                for extra in re.findall(r"`([a-z0-9-]+)`", line):
                    tags.add(extra.lower())
                continue
            # 형식 2: `- \`tag\`` (한 줄에 한 tag)
            m = re.match(r"^\s*[-*]\s*`?([a-z0-9-]+)`?\s*$", line)
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

    면제 (v0.5.2+ SCHEMA): _meta/ 안 페이지 (rule/reference). 운영 문서는 inbound 0이 정상.
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
        # 면제: _meta/ 안 (rule/reference, 운영 문서)
        if slug.startswith("_meta/"):
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

    운영 문서 (`type: rule` 또는 `_meta/` 안) 면제 (v0.5.2+).
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
    """#8 page size > 200줄 → info (분할 권장).

    면제 (v0.5.2+ SCHEMA): _meta/ 안 (rule/reference, 운영 문서).
    """
    out: list[dict] = []
    for fp in _all_pages(vault):
        slug = _slug_of(vault, fp)
        if slug.startswith("_meta/"):
            continue  # 운영 문서 면제
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

    `raven build` 후 실행 가정. DB 없으면 build 요청.
    """
    out: list[dict] = []
    db_path = vault.db_path
    if not db_path.exists():
        out.append(_mk_issue(
            "#11", "info", "(vault)",
            f"wiki.db 없음: `raven build` 필요 ({db_path})",
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


# v0.6.33+: Tier 1 leak — Karpathy LLM Wiki 3-Layer 분리의 vault 침투 감지.
#
# 카파시 LLM Wiki 패턴의 핵심: vault는 Layer 2 (사용자/에이전트가 쓰는 곳)지,
# Layer 1 (raven internal docs — OPERATIONS.md / agent/* / raven-policy.md) 이
# vault에 복사되면 안 됨. 사람이 실수로 vault clone 시 Tier 1 문서가 누설되는
# 것을 자동 검증.
#
# v0.6.39+: 옵션화. vault.meta.allow_tier1_leak = True인 vault는
# critical 대신 warning으로 강등 (사용자 명시적 안전벨트 해제).
TIER1_LEAK_PATTERNS = (
    "OPERATIONS.md",
    "agent/",
    "raven-policy.md",
)


def check_tier_integrity(vault: Vault) -> list[dict]:
    """#14 tier_integrity — Tier 1 leak 감지.

    vault.content/ 하위에 Tier 1 문서 패턴이 있으면 기본 critical 보고.
    vault.meta.allow_tier1_leak = True이면 warning으로 강등 (사용자 옵트인).

    카파시 3-Layer 분리 (raw/wiki/schema)를 lint 레벨에서 강제. 기본은
    안전망. 사용자가 명시적으로 allow_tier1_leak = True 설정 시 강등.
    """
    out: list[dict] = []
    content_root = vault.content_root
    if not content_root.exists():
        return out
    # v0.6.39+: 사용자가 옵트인하면 critical → warning 강등
    severity = "warning" if getattr(vault.meta, "allow_tier1_leak", False) else "critical"
    leak_label = "Tier 1 leak (warning, allow_tier1_leak=True)" if severity == "warning" \
        else "Tier 1 leak"
    for fp in content_root.rglob("*"):
        if not fp.is_file():
            continue
        rel = fp.relative_to(content_root)
        rel_str = str(rel)
        for pattern in TIER1_LEAK_PATTERNS:
            if pattern in rel_str:
                slug = str(rel.with_suffix("")).replace("\\", "/")
                out.append(_mk_issue(
                    "#14", severity, slug,
                    f"{leak_label}: '{rel}' — "
                    f"matches '{pattern}' (Karpathy 3-Layer 위반)",
                ))
                break
    return out


def check_cognitive_governance(vault: Vault) -> list[dict]:
    """#13 cognitive governance (Zettelkasten/LLM Wiki quality signal, v0.5.3+).

    concept/comparison/page 타입에 다음 4 신호 중 누락 시 1 issue당 1 line 출력:
      1. **Why it matters** — 본문 첫 문단 또는 헤딩에 명시
      2. **반대 입장 (Fights against)** — `## 반대 입장` / `## Fights against` /
         `## Alternatives` (및 영어 변형) 헤딩 존재
      3. **Cross-disciplinary links** — 본문에 wikilink ≥ 1 (slug에 discipline
         키워드 또는 명시적 cross-discipline 마커)
      4. **confidence 등급** — frontmatter.confidence ∈ {high, medium, low}

    면제:
      - type ∈ {rule, journal, query} (SCHEMA §X)
      - _meta/ 안 페이지 (운영 문서)
      - .vault.json 내 disable_cognitive_governance=True 인 경우 (글로벌 비활성화)
      - wip/, scratch/ 하위 경로 페이지 (임시 작성 영역)
      - tags 내 wip, draft, scratch, memo, quick 단어가 포함된 경우 (초안 면제)

    v0.5.3: info 등급 — 페이지 lint 통과에 영향 ❌. v0.6.x에서 warning 격상 후보.
    """
    # 글로벌 비활성화 체크
    vf = vault.root / ".vault.json"
    if vf.exists():
        try:
            data = json.loads(vf.read_text(encoding="utf-8"))
            if data.get("disable_cognitive_governance") or data.get("features", {}).get("cognitive_governance") is False:
                return []
        except Exception:
            pass

    out: list[dict] = []
    exempt_tags = {"wip", "draft", "scratch", "memo", "quick"}
    for fp in _all_pages(vault):
        slug = _slug_of(vault, fp)
        # 면제: _meta/ 안 페이지 (운영 문서)
        if slug.startswith("_meta/"):
            continue
        # 면제: wip/, scratch/ 하위 (임시 작업)
        if slug.startswith("content/wip/") or slug.startswith("content/scratch/") or slug.startswith("wip/") or slug.startswith("scratch/"):
            continue
        try:
            text = fp.read_text(errors="replace")
        except Exception:
            continue
        meta, body = _split_fm_body(text)
        # 면제: type 면제
        ptype = (meta.get("type") or "").strip().lower()
        if ptype in COG_GOV_EXEMPT_TYPES:
            continue
        # 면제: 초안/임시 태그 면제
        tags = meta.get("tags") or []
        if isinstance(tags, list):
            tags_set = {t.strip().lower() for t in tags if isinstance(t, str)}
            if tags_set & exempt_tags:
                continue

        missing: list[str] = []

        # 1) Why it matters — 헤딩 또는 본문 첫 문단
        if not _has_why_it_matters(body):
            missing.append("Why it matters")

        # 2) 반대 입장 헤딩
        if not _has_oppose_heading(body):
            missing.append("반대 입장")

        # 3) Cross-disciplinary wikilink (heuristic)
        if not _has_cross_discipline_link(body, slug, meta):
            missing.append("Cross-disciplinary link")

        # 4) confidence 등급
        conf = meta.get("confidence")
        if not isinstance(conf, str) or conf.strip().lower() not in COG_GOV_CONFIDENCE_LEVELS:
            missing.append("confidence")

        if missing:
            sev = "info"
            out.append(_mk_issue(
                "#13", sev, slug,
                f"cognitive governance 누락 ({len(missing)}/4): {', '.join(missing)}",
            ))
    return out


# ────────────────────────── helpers for #13 ──────────────────────────


def _split_fm_body(text: str) -> tuple[dict, str]:
    """frontmatter와 body 분리. (frontmatter dict, body str) 반환."""
    from . import frontmatter as fm_mod
    meta, body = fm_mod.parse(text)
    return meta, body


def _first_paragraph(body: str, max_chars: int = 400) -> str:
    """본문 첫 문단 (frontmatter 제외, 첫 '#' 헤딩 다음)."""
    if not body:
        return ""
    # 첫 h1/h2 헤딩 다음 빈 줄까지 또는 max_chars 까지
    lines = body.splitlines()
    started = False
    para: list[str] = []
    for line in lines:
        s = line.strip()
        if not started:
            if s.startswith("#"):
                started = True
                continue
            continue
        if not s:
            if para:
                break
            continue
        para.append(s)
        if sum(len(p) for p in para) >= max_chars:
            break
    return " ".join(para)[:max_chars].lower()


def _has_why_it_matters(body: str) -> bool:
    """헤딩 또는 본문 첫 문단에 'why it matters' 시그널."""
    body_lower = body.lower() if body else ""
    if any(p in body_lower for p in COG_GOV_WHY_PATTERNS):
        return True
    first_para = _first_paragraph(body or "")
    return any(p in first_para for p in COG_GOV_WHY_PATTERNS)


def _has_oppose_heading(body: str) -> bool:
    """'## 반대 입장' / '## Fights against' / '## Alternatives' 헤딩 존재."""
    if not body:
        return False
    body_lower = body.lower()
    for line in body.splitlines():
        s = line.strip().lower()
        if not s.startswith("## "):
            continue
        heading = s[3:].strip()
        for pat in COG_GOV_OPPOSE_HEADINGS:
            if pat in heading or heading.startswith(pat):
                return True
    # 본문 어딘가에 헤딩 텍스트가 직접 등장해도 OK (마크다운 형식이 약간 달라도 허용)
    return any(pat in body_lower for pat in COG_GOV_OPPOSE_HEADINGS)


def _has_cross_discipline_link(body: str, slug: str, meta: dict) -> bool:
    """본문 wikilink 중 cross-discipline 후보가 ≥ 1.

    heuristic:
      - wikilink target slug에 discipline 키워드 (사람/예술/생물/역사/철학) 매치
      - 또는 frontmatter.tags에 cross-discipline 마커
    """
    if not body:
        return False
    # 1) tags에 cross-discipline 마커
    tags = meta.get("tags") or []
    if isinstance(tags, list):
        for t in tags:
            if not isinstance(t, str):
                continue
            t_low = t.strip().lower()
            if any(m in t_low for m in COG_GOV_CROSS_MARKERS):
                return True
    # 2) wikilink target slug 추출
    targets = _extract_wikilink_targets(body)
    if not targets:
        return False
    for tgt in targets:
        tgt_low = tgt.lower()
        if any(kw in tgt_low for kw in COG_GOV_DISCIPLINE_KEYWORDS):
            return True
    return False


def _extract_wikilink_targets(body: str) -> list[str]:
    """[[target]] / [[target|alias]] / [[target?]] / [[target!]] 에서 target 추출."""
    out: list[str] = []
    if not body:
        return out
    for m in re.finditer(r"\[\[([^\[\]]+?)\]\]", body):
        raw = m.group(1).strip()
        # alias 제거
        target = raw.split("|", 1)[0].strip()
        # intent marker 제거
        target = target.rstrip("?!.").strip()
        if target:
            out.append(target)
    return out


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
    """14 check 모두 실행. counts + issues list 반환.

    v0.6.33+: #14 tier_integrity 추가 — Karpathy 3-Layer 분리를 lint로 자동 검증.
    """
    issues: list[dict] = []
    # #1-3 link
    issues.extend(_legacy_link_issues(vault))
    # #4-14
    issues.extend(check_orphans(vault))
    issues.extend(check_contradictions(vault))
    issues.extend(check_confidence_low(vault))
    issues.extend(check_stale(vault))
    issues.extend(check_page_size(vault))
    issues.extend(check_tag_audit(vault))
    issues.extend(check_frontmatter_completeness(vault))
    issues.extend(check_index_completeness(vault))
    issues.extend(check_log_size(vault))
    issues.extend(check_cognitive_governance(vault))
    issues.extend(check_tier_integrity(vault))  # v0.6.33+

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
