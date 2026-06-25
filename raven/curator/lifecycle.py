"""raven.curator.lifecycle — grace period + soft-archive + reviewer curation.

v3 합의 (Claude #3, #7):
- missing 폴더 grace N일 (default 7)
- grace ≥ N → soft-archive (archived=true, archived_at=today)
- soft-archive ≠ delete (FS 복원 시 자동 복귀 옵션)
- file_changes.curated flag는 reviewer 승인 시 1로 전환 (Step 7에서 사용)
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Optional

from . import db, schema


def should_archive(
    collection: schema.Collection,
    fs_exists: bool,
    grace_days: int = 7,
    today: Optional[dt.date] = None,
) -> bool:
    """grace ≥ N일 후 soft-archive 대상인지.

    Args:
        collection: yaml Collection
        fs_exists: 폴더가 FS에 실제로 존재하는가
        grace_days: grace 일수
        today: 오늘 (None = date.today())

    Returns:
        True = soft-archive 대상
    """
    if fs_exists:
        return False
    if collection.archived:
        return False  # 이미 archive

    today = today or dt.date.today()
    ref = collection.archived_at or collection.retired_at
    if not ref:
        return False

    try:
        ref_date = dt.date.fromisoformat(ref[:10])
    except (ValueError, TypeError):
        return False

    return (today - ref_date).days >= grace_days


def mark_curated(
    conn, change_id: int, now: Optional[int] = None
) -> None:
    """file_changes.curated = 1 (reviewer 승인 시 호출)."""
    import time
    db.mark_curated(conn, change_id, now if now is not None else int(time.time()))


def archive_collection(
    yaml_obj: schema.CollectionsYaml,
    collection_id: str,
    today: Optional[dt.date] = None,
) -> bool:
    """yaml Collection을 soft-archive로 마킹 (in-memory).

    Returns:
        True = 변경됨
    """
    today = today or dt.date.today()
    for c in yaml_obj.collections:
        if c.id == collection_id and not c.archived:
            c.archived = True
            c.archived_at = today.isoformat()
            return True
    return False


def unarchive_collection(
    yaml_obj: schema.CollectionsYaml,
    collection_id: str,
) -> bool:
    """archived 해제 (FS 복원 시)."""
    for c in yaml_obj.collections:
        if c.id == collection_id and c.archived:
            c.archived = False
            c.archived_at = None
            return True
    return False
