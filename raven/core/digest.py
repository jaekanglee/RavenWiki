"""raven.core.digest — vault digest aggregation (v0.5.6, M5 F5).

사람 운영자가 Dashboard에 들어왔을 때 "오늘 vault 상태"를 한 화면에
요약해주기 위한 aggregator. 단일 vault 단위로 다음을 한 번에 계산:

    today         — 오늘 (KST 로컬 자정 기준) log entries
    this_week     — 최근 N일간 날짜별 활동 카운트 (chart data)
    lint          — critical/warning/info counts + top issues
    log_recent    — 최근 log entries (latest first)
    stats         — total pages, types, recent_pages, broken_links

이 모듈은 **순수 aggregator** — db query 없음. log.md 파싱 + lint 호출 +
content_root rglob 만 사용. N+1 호출 방지를 위해 내부 helper는 vault
당 한 번만 동작.

Dashboard는 이 모듈을 통해 일관된 digest payload를 받음.
"""
from __future__ import annotations

import datetime as _dt
from collections import Counter
from pathlib import Path
from typing import Optional

from . import lint as lint_module
from . import log as log_module
from . import link as link_module
from .vault import Vault


# ── 상수 ─────────────────────────────────────────

# 기본 digest 윈도우 (사람 운영자 = "이번 주")
DEFAULT_DAYS = 7

# 오늘 log 상한 (성능 / UX 균형)
TODAY_ENTRIES_LIMIT = 50

# 최근 노트 카드 표시 개수
RECENT_PAGES_LIMIT = 5

# Top lint issues per severity
TOP_ISSUES_PER_SEVERITY = 3


# ── helpers ──────────────────────────────────────


def _today_iso() -> str:
    """오늘 날짜 (ISO 8601). 타임존은 시스템 로컬 — 운영자 머신 기준."""
    return _dt.date.today().isoformat()


def _date_range(days: int) -> list[str]:
    """[오늘, 어제, ..., 오늘-(days-1)] ISO 날짜 리스트."""
    today = _dt.date.today()
    return [(today - _dt.timedelta(days=i)).isoformat() for i in range(days)]


def _filter_today(entries: list[dict]) -> list[dict]:
    """log entries 중 오늘 것만."""
    today = _today_iso()
    return [e for e in entries if e.get("date") == today]


def _group_by_date(entries: list[dict], days: int) -> list[dict]:
    """최근 N일 각 날짜별 카운트 + action breakdown.

    Returns:
        [
          {"date": "2026-06-27", "count": 3, "by_action": {"create": 1, "update": 2}},
          {"date": "2026-06-26", "count": 0, "by_action": {}},
          ...
        ]
    """
    dates = _date_range(days)
    # entries dict {date, action, ...} → Counter
    by_date: dict[str, Counter] = {d: Counter() for d in dates}
    for e in entries:
        d = e.get("date")
        if d in by_date:
            by_date[d][e.get("action", "?")] += 1
    out = []
    for d in dates:
        c = by_date[d]
        out.append({
            "date": d,
            "count": sum(c.values()),
            "by_action": dict(c),
        })
    return out


# ── page aggregation ─────────────────────────────


def _recent_pages(vault: Vault, limit: int = RECENT_PAGES_LIMIT) -> list[dict]:
    """최근 updated 순으로 페이지 N개.

    DB (wiki.db) 가 있으면 거기서 정렬, 없으면 content_root rglob + 파일 mtime.
    페이지 단위 정렬 비용은 limit=5 이므로 rglob 도 충분히 빠름.
    """
    rows: list[tuple[str, str, str]] = []
    for fp in vault.content_root.rglob("*.md"):
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        # frontmatter parse (간단 형태 — body는 무시)
        meta = _parse_frontmatter(text)
        if not meta:
            continue
        slug = str(fp.relative_to(vault.root))[:-3]
        updated = meta.get("updated", "")
        title = meta.get("title", slug)
        ptype = meta.get("type", "?")
        rows.append((updated, slug, f"{title}\x00{ptype}"))
    # updated desc, 빈 updated 는 뒤로
    rows.sort(key=lambda r: (r[0] == "", r[0]), reverse=True)
    out = []
    for updated, slug, title_ptype in rows[:limit]:
        title, ptype = title_ptype.split("\x00", 1)
        out.append({
            "slug": slug,
            "title": title,
            "type": ptype,
            "updated": updated,
        })
    return out


def _parse_frontmatter(text: str) -> dict:
    """`---` 로 감싼 frontmatter 를 dict 로. 없으면 빈 dict.

    서드파티 의존성 없이 inline parsing (server.py 의 _split_fm 와 동일 패턴).
    """
    if not text.startswith("---"):
        return {}
    try:
        _, fm, _body = text.split("---", 2)
    except ValueError:
        return {}
    meta = {}
    for line in fm.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta


def _total_pages(vault: Vault) -> int:
    """content_root 의 총 .md 페이지 수."""
    return sum(1 for _ in vault.content_root.rglob("*.md"))


def _types_breakdown(vault: Vault) -> dict[str, int]:
    """frontmatter.type 별 카운트."""
    counts: Counter = Counter()
    for fp in vault.content_root.rglob("*.md"):
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        meta = _parse_frontmatter(text)
        t = meta.get("type", "?")
        counts[t] += 1
    return dict(counts)


# ── public API ──────────────────────────────────


def compute_digest(
    vault: Vault,
    days: int = DEFAULT_DAYS,
    *,
    # 테스트용 injection — 기본은 실제 lint/log 모듈 호출
    _lint_fn=None,
    _log_fn=None,
) -> dict:
    """vault 의 digest payload 생성.

    Args:
        vault: 대상 vault
        days: this_week 윈도우 (기본 7일)
        _lint_fn: override for lint_module.run_all (test only)
        _log_fn: override for log_module.list_entries (test only)

    Returns:
        {
          "vault": str,
          "generated_at": ISO datetime,
          "today": [log entries],
          "this_week": [{date, count, by_action}],
          "lint": {ok, counts, by_check, top_issues},
          "log_recent": [latest entries desc],
          "stats": {
            total_pages, types, recent_pages, broken_links, missing_links,
          }
        }
    """
    if days < 1:
        days = 1
    if days > 30:
        days = 30  # safety cap

    log_fn = _log_fn or log_module.list_entries
    lint_fn = _lint_fn or lint_module.run_all

    # log: load full → derive today / this_week / log_recent
    try:
        all_entries = log_fn(vault)
    except Exception:
        all_entries = []

    today_entries = _filter_today(all_entries)
    this_week_grouped = _group_by_date(all_entries, days)
    log_recent = list(reversed(all_entries[-TODAY_ENTRIES_LIMIT:]))

    # lint
    try:
        lint_result = lint_fn(vault)
    except Exception as e:
        lint_result = {
            "ok": False,
            "counts": {"critical": 0, "warning": 0, "info": 0, "total": 0},
            "by_check": {},
            "issues": [],
            "error": f"{type(e).__name__}: {e}",
        }
    counts = lint_result.get("counts", {})
    by_check = lint_result.get("by_check", {})
    issues = lint_result.get("issues", [])
    top_issues: dict[str, list[dict]] = {"critical": [], "warning": [], "info": []}
    for iss in issues:
        sev = iss.get("severity", "info")
        bucket = top_issues.get(sev)
        if bucket is not None and len(bucket) < TOP_ISSUES_PER_SEVERITY:
            bucket.append({
                "id": iss.get("id"),
                "slug": iss.get("slug"),
                "message": iss.get("message"),
            })

    # links
    try:
        broken = link_module.find_broken(vault)
    except Exception:
        broken = []
    try:
        missing = link_module.find_missing(vault)
    except Exception:
        missing = []

    return {
        "vault": vault.meta.name,
        "generated_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "today": today_entries,
        "this_week": this_week_grouped,
        "lint": {
            "ok": lint_result.get("ok", True),
            "counts": counts,
            "by_check": by_check,
            "top_issues": top_issues,
        },
        "log_recent": log_recent,
        "stats": {
            "total_pages": _total_pages(vault),
            "types": _types_breakdown(vault),
            "recent_pages": _recent_pages(vault),
            "broken_links": len(broken),
            "missing_links": len(missing),
        },
    }