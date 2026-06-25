#!/usr/bin/env python3
"""backup_db.py — wiki.db 일 1회 백업 + rotation.

두 종류의 백업을 동시에 생성:

1. ``wiki-{YYYYMMDD}.db`` — 일자별 스냅샷 (덮어쓰지 않음)
   - ``backups/`` 디렉토리에 보관
   - ``--keep N`` (기본 7) 초과 시 오래된 것부터 삭제

2. ``wiki.db.backup`` — 항상 최신 사본 1개
   - 빠른 롤백용 (단일 파일)

Usage
-----
    python3 backup_db.py                    # default: vault=스크립트 부모, keep=7
    python3 backup_db.py --vault ~/wiki     # 명시적 vault
    python3 backup_db.py --keep 14          # 2주 보관
    python3 backup_db.py --quiet            # 로그 억제 (cron/timer 적합)

Schedule
--------
systemd timer (``deploy/systemd/wiki-backup.timer``) 가 일 1회 실행.
macOS LaunchAgent 사용자: ``~/Library/LaunchAgents/com.wiki.backup.plist``
을 별도 생성하거나 launchd `StartCalendarInterval` 사용.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


def log(msg: str, *, quiet: bool = False) -> None:
    if not quiet:
        print(msg)


def main() -> int:
    p = argparse.ArgumentParser(
        description="wiki.db 일 1회 백업 + rotation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--vault",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="vault root (wiki.db 위치)",
    )
    p.add_argument(
        "--keep",
        type=int,
        default=7,
        help="일자별 백업 보관 수 (초과 시 오래된 것부터 삭제)",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="stdout 출력 억제 (cron/systemd timer 적합)",
    )
    args = p.parse_args()

    vault: Path = args.vault.resolve()
    db = vault / "wiki.db"

    if not db.exists():
        log(f"❌ {db} 없음 (build_db.py 먼저 실행)", quiet=args.quiet)
        return 1

    backups_dir = vault / "backups"
    backups_dir.mkdir(exist_ok=True)

    # ── 1. 일자별 백업 (덮어쓰지 않음) ───────────────────────────────
    today = datetime.now().strftime("%Y%m%d")
    dated = backups_dir / f"wiki-{today}.db"

    if dated.exists():
        log(f"⚠️  오늘 백업 이미 존재 (skip): {dated}", quiet=args.quiet)
    else:
        shutil.copy2(db, dated)
        size = dated.stat().st_size
        log(f"✅ 일자별 백업: {dated.name} ({size:,} bytes)", quiet=args.quiet)

    # ── 2. 단순 백업 (항상 최신 1개) ────────────────────────────────
    simple = vault / "wiki.db.backup"
    shutil.copy2(db, simple)
    log(f"✅ 단순 백업:   {simple.name} ({simple.stat().st_size:,} bytes)", quiet=args.quiet)

    # ── 3. rotation: 오래된 일자별 백업 삭제 ────────────────────────
    backups = sorted(backups_dir.glob("wiki-*.db"), key=lambda p: p.name)
    if len(backups) > args.keep:
        stale = backups[: len(backups) - args.keep]
        for old in stale:
            old.unlink()
            log(f"🗑️  삭제:       {old.name}", quiet=args.quiet)
        log(
            f"🧹 rotation 완료 (보관: {args.keep}, 삭제: {len(stale)})",
            quiet=args.quiet,
        )

    log("", quiet=args.quiet)
    remaining = sorted(backups_dir.glob("wiki-*.db"))
    log(
        f"📦 현재 백업 수: {len(remaining)}개 (backups/)",
        quiet=args.quiet,
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
