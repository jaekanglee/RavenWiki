#!/usr/bin/env python3
"""raven-gate — Phase 게이트 자동 검증 (위임 Phase 종료 보고용).

wiki-orchestrator가 위임자에게 Phase 종료 보고를 받았을 때 호출:
    python scripts/gate.py harumoa
    python scripts/gate.py harumoa --since 2026-06-26T00:00:00

검증:
  1. wiki vault의 content/<project>/ 하위에서 결정/lesson/journal 페이지 카운트
  2. trigger 시점 (결정/막힘해결/하루끝) 중 1+ 확인
  3. verdict 출력: PASS / FAIL + 부족 항목

왜 자동화:
  - SOUL.md 인라인 룰 (Phase 게이트) 만으로는 orchestrator가 매번 수동 확인 부담
  - 자동 검증 → 위임자 보고에 "gate 검증됨" 한 줄만 보이면 OK

사용 (orchestrator 위임 보고 후):
    # 위임자가 "harumoa Phase 2 끝" 보고
    python scripts/gate.py harumoa
    # → PASS: 3 writes (decisions=2, journal=1) since 2026-06-26T00:00:00
    # 또는 → FAIL: 0 writes, no trigger matched

cron 아님 — 위임 라이프사이클에서만 호출.

exit code:
  0 = PASS (1+ write, trigger OK)
  1 = FAIL (0 write 또는 trigger 불일치)
  2 = vault 또는 project 오류
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple


VALID_PROJECTS = ("harumoa", "homeauto", "resume", "design-spec")
TRIGGER_CATEGORIES = {
    "decision": "decisions",
    "concept": "concepts",
    "lesson": "lessons",
    "journal": "journal",
}


def list_recent_writes(vault_dir: Path, project: str, since: Optional[datetime]) -> List[Tuple[str, Path]]:
    """project 폴더에서 since 이후 변경된 .md 파일 목록.

    Returns:
        list of (category, file_path) tuples
    """
    project_dir = vault_dir / "content" / project
    if not project_dir.exists():
        return []

    results: List[Tuple[str, Path]] = []
    for category in TRIGGER_CATEGORIES.values():
        cat_dir = project_dir / category
        if not cat_dir.exists():
            continue
        for md in cat_dir.glob("*.md"):
            if since is None:
                results.append((category, md))
                continue
            mtime = datetime.fromtimestamp(md.stat().st_mtime)
            if mtime >= since:
                results.append((category, md))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(prog="raven-gate")
    parser.add_argument("project", choices=VALID_PROJECTS, help="검증할 프로젝트")
    parser.add_argument(
        "--vault",
        default=None,
        help="vault 경로 (기본: WIKI_VAULT 환경변수 또는 ~/vaults/wiki)",
    )
    parser.add_argument(
        "--since",
        default=None,
        help="이 시각 이후 변경만 카운트 (ISO 8601, 예: 2026-06-26T00:00:00)",
    )
    parser.add_argument(
        "--since-hours",
        type=int,
        default=None,
        help="지금부터 N시간 이내 변경만 카운트",
    )
    args = parser.parse_args()

    if args.vault:
        vault_dir = Path(args.vault).expanduser().resolve()
    else:
        vault_name = os.environ.get("WIKI_VAULT", "wiki")
        vault_dir = Path.home() / "vaults" / vault_name

    if not vault_dir.exists():
        print(f"❌ vault not found: {vault_dir}", file=sys.stderr)
        return 2

    since: Optional[datetime] = None
    if args.since:
        since = datetime.fromisoformat(args.since)
    elif args.since_hours:
        since = datetime.now() - timedelta(hours=args.since_hours)

    writes = list_recent_writes(vault_dir, args.project, since)
    if not writes:
        since_str = since.isoformat() if since else "ever"
        print(f"❌ raven-gate FAIL — {args.project}")
        print(f"   vault: {vault_dir.name}")
        print(f"   since: {since_str}")
        print(f"   writes: 0 (none of decisions/concepts/lessons/journal)")
        print(f"   trigger: none matched")
        print(f"   → Phase 게이트 미충족. 위임자 fix 위임 또는 반려.")
        return 1

    # 카테고리별 카운트
    counts: dict[str, int] = {}
    for cat, _ in writes:
        counts[cat] = counts.get(cat, 0) + 1

    triggers_matched = list(counts.keys())
    since_str = since.isoformat() if since else "ever"
    print(f"✅ raven-gate PASS — {args.project}")
    print(f"   vault: {vault_dir.name}")
    print(f"   since: {since_str}")
    print(f"   writes: {len(writes)} ({', '.join(f'{k}={v}' for k, v in counts.items())})")
    print(f"   triggers matched: {', '.join(triggers_matched)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
