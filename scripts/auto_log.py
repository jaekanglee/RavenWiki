#!/usr/bin/env python3
"""raven-auto-log — 일일 journal 누락 감지.

vault의 journal/ 디렉토리에 오늘 날짜 (YYYY-MM-DD.md) 가 없으면 알림.

왜 필요한가:
  - playbook §10.1 트리거 3 = "하루끝" — 매일 journal
  - 깜빡하고 안 쓰면 그날 자산 누락
  - cron 23:50 실행 → 다음날 00:00 넘으면 journal 없는 것 감지

설계:
  1. today = YYYY-MM-DD (로컬 시간)
  2. active vault의 각 project 폴더 순회 (harumoa/homeauto/resume/design-spec)
  3. journal/{today}.md 존재 확인
  4. 0건 발견 → "N개 프로젝트 journal 미작성" stdout emit
  5. 모두 있음 → silent (cron 폭주 방지)

사용:
    python scripts/auto_log.py                 # WIKI_VAULT 환경변수 또는 'wiki' 기본
    python scripts/auto_log.py ~/vaults/wiki   # 명시

cron 예:
    hermes cron create \\
        --schedule "50 23 * * *" \\
        --prompt "" \\
        --script scripts/auto_log.py \\
        --no-agent
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import List

# Phase 1 vault 구조 기준 — 4개 프로젝트
PROJECTS = ("harumoa", "homeauto", "resume", "design-spec")


def find_journal_today(vault_dir: Path, project: str, today: str) -> bool:
    """project의 journal/{today}.md 존재 여부."""
    journal = vault_dir / "content" / project / "journal" / f"{today}.md"
    return journal.exists()


def main() -> int:
    if len(sys.argv) > 1:
        vault_dir = Path(sys.argv[1]).expanduser().resolve()
    else:
        # WIKI_VAULT 환경변수 또는 기본 'wiki'
        vault_name = os.environ.get("WIKI_VAULT", "wiki")
        vault_dir = Path.home() / "vaults" / vault_name

    if not vault_dir.exists():
        print(f"❌ vault not found: {vault_dir}", file=sys.stderr)
        return 2

    today = date.today().isoformat()
    missing: List[str] = []

    for project in PROJECTS:
        if not find_journal_today(vault_dir, project, today):
            missing.append(project)

    if not missing:
        # silent — all journals present
        return 0

    # stdout emit — alert
    print(f"📔 raven-auto-log — {today} journal 누락")
    print(f"   vault: {vault_dir.name}")
    print(f"   누락 프로젝트 ({len(missing)}):")
    for p in missing:
        print(f"   - content/{p}/journal/{today}.md")
    return 1


if __name__ == "__main__":
    sys.exit(main())
