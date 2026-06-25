"""raven.curator.reports — reviews 승인/거절 + dry-run report + pattern 분석.

v3 합의 (Claude #5, #7, 보너스):
- reviews.collection_id 인덱스 활용 (collection별 reject 패턴 집계)
- curated flag: reviewer 승인 시 1 (file_changes.curated_at)
- dry-run 리포트: human-readable table / JSON 양쪽
- log.md append: sync event 기록 (Step 5에서 호출)
"""
from __future__ import annotations

import datetime as dt
import json
import time
from pathlib import Path
from typing import List, Optional

from . import db


def submit_review(
    conn,
    change_id: int,
    decision: str,                  # accept | reject | defer
    reason: str,
    reviewer: str,
    now: Optional[int] = None,
) -> int:
    """reviewer 결정 기록.

    accept → file_changes.curated = 1 (auto)
    reject/defer → curated 변경 없음 (다음 curator 실행에 다시 등장 가능)
    """
    ts = now if now is not None else int(time.time())
    rid = db.insert_review(conn, change_id, decision, reason, reviewer, ts)

    if decision == "accept":
        db.mark_curated(conn, change_id, ts)

    return rid


def reject_pattern_summary(conn, collection_id: str) -> List[tuple[str, int]]:
    """collection의 reject 패턴 집계 (LLM 학습 데이터)."""
    return db.reject_pattern_for_collection(conn, collection_id)


def render_curation_report(
    result,  # curator.CuratorResult
    collection_name: str = "",
) -> str:
    """CuratorResult → human-readable text (Telegram-friendly)."""
    lines: List[str] = []
    lines.append(f"🐦‍⬛ raven curator — {collection_name or result.collection_id}")
    lines.append(f"   status: {result.status}")
    if result.event_id:
        lines.append(f"   event_id: {result.event_id}")
    if result.changes:
        lines.append(f"   changes: {len(result.changes)}")
        for c in result.changes[:5]:
            lines.append(f"   - {c.change_type}  {c.path}")
        if len(result.changes) > 5:
            lines.append(f"   ... +{len(result.changes) - 5} more")
    if result.warnings:
        for w in result.warnings:
            lines.append(f"   ⚠️  {w}")
    if result.note:
        lines.append(f"   note: {result.note}")
    return "\n".join(lines)


def render_sync_report(report) -> str:
    """SyncReport → human-readable text."""
    return report.to_human()


def curation_summary(conn, collection_id: str) -> dict:
    """collection의 큐레이션 통계."""
    cur = conn.execute(
        """
        SELECT
            COUNT(DISTINCT e.event_id) AS total_events,
            COUNT(DISTINCT CASE WHEN e.status='ok' THEN e.event_id END) AS ok_events,
            COUNT(DISTINCT CASE WHEN e.status='error' THEN e.event_id END) AS error_events,
            COUNT(fc.change_id) AS total_changes,
            COUNT(CASE WHEN fc.curated=1 THEN 1 END) AS curated_changes,
            COUNT(DISTINCT r.review_id) AS total_reviews,
            COUNT(CASE WHEN r.decision='accept' THEN 1 END) AS accept_reviews,
            COUNT(CASE WHEN r.decision='reject' THEN 1 END) AS reject_reviews
        FROM events e
        LEFT JOIN file_changes fc ON fc.event_id = e.event_id
        LEFT JOIN reviews r ON r.change_id = fc.change_id
        WHERE e.collection_id = ?
        """,
        (collection_id,),
    ).fetchone()
    if cur is None:
        return {
            "total_events": 0, "ok_events": 0, "error_events": 0,
            "total_changes": 0, "curated_changes": 0,
            "total_reviews": 0, "accept_reviews": 0, "reject_reviews": 0,
        }
    return {
        "total_events": cur[0],
        "ok_events": cur[1],
        "error_events": cur[2],
        "total_changes": cur[3],
        "curated_changes": cur[4],
        "total_reviews": cur[5],
        "accept_reviews": cur[6],
        "reject_reviews": cur[7],
    }
