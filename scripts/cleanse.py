#!/usr/bin/env python3
"""raven-cleanse — 주기적 vault 클렌징 + 취합 자동화 (M+ 자리마련).

이 시점 (2026-06-26) 은 hook 자리만 만들어둠. 실제 구현은 M+ 단계.

왜 "자리를 미리 마련"인가:
  - A/B/E 작업하면서 자연스럽게 cleanse가 필요해질 지점이 보임
  - hook가 없으면 나중에 retrofit (귀찮음)
  - 빈 stub이라도 `raven cleanse <subcmd>` 가 동작하면 사용자 멘탈 모델 확립

핵심 개념:
  - cleanse = vault에서 stale / duplicate / weak / 잘못 분류된 페이지 정리
  - aggregate = 유사 페이지 묶고 (cluster), strong link 추가 → "다시 더 좋은 결과물"

설계 (예정):
  1. cleanse orphans     — 90일+ 미참조 페이지 archive 후보
  2. cleanse weak        — outbound < 2 페이지 → 인접 페이지 wikilink 자동 추천
  3. cleanse dup         — ngram/jaccard로 중복 페이지 감지 → 병합 후보
  4. cleanse stale       — updated > 180일 + wikilink 0 → "fresh-up" 권고
  5. aggregate clusters  — 같은 tag/project 페이지 묶음 자동 클러스터링
  6. aggregate crosslink — "관련 페이지" 자동 wikilink 추천 (M3+)
  7. report              — 위 결과 markdown 리포트 → `~/vaults/<name>/_meta/cleanse-YYYY-MM-DD.md`

사용 (예정):
    python scripts/cleanse.py orphans       # 1회 dry-run
    python scripts/cleanse.py aggregate     # cluster + crosslink
    python scripts/cleanse.py report        # 전체 리포트

cron (예정, M+):
    매주 일요일 03:00 — aggregate + report → Telegram 요약
    매일 03:00 — orphans (silent on no-change)

상호작용:
  - Phase 게이트 (B) 와 직결 — gate 가 pass 해도 cleanse 가 archive 시키면 다시 fail 가능
  - 트리거 헬퍼 (E) 와 직결 — lesson/concept 카테고리 자동 추천에 cleanse 데이터 활용
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def cmd_orphans(args: argparse.Namespace) -> int:
    """orphans dry-run. M+ 구현 예정."""
    print("🧹 raven-cleanse orphans — stub")
    print("   M+ 에서 구현. 현재 자리만 마련.")
    return 0


def cmd_weak(args: argparse.Namespace) -> int:
    """weak-link 감지. M+ 구현 예정."""
    print("🧹 raven-cleanse weak — stub")
    return 0


def cmd_dup(args: argparse.Namespace) -> int:
    """duplicate 감지. M+ 구현 예정."""
    print("🧹 raven-cleanse dup — stub")
    return 0


def cmd_stale(args: argparse.Namespace) -> int:
    """stale 페이지 감지. M+ 구현 예정."""
    print("🧹 raven-cleanse stale — stub")
    return 0


def cmd_aggregate(args: argparse.Namespace) -> int:
    """cluster + crosslink 집계. M+ 구현 예정."""
    print("🧹 raven-cleanse aggregate — stub")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """전체 리포트. M+ 구현 예정."""
    print("🧹 raven-cleanse report — stub")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="raven-cleanse",
        description="주기적 vault 클렌징 + 취합 (M+ 자리마련)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("orphans", help="90일+ 미참조 페이지 archive 후보")
    sub.add_parser("weak", help="outbound < 2 페이지 wikilink 추천")
    sub.add_parser("dup", help="중복 페이지 감지")
    sub.add_parser("stale", help="updated > 180일 + wikilink 0 페이지")
    sub.add_parser("aggregate", help="cluster + crosslink 집계")
    sub.add_parser("report", help="전체 리포트")

    args = parser.parse_args()
    handler = {
        "orphans": cmd_orphans,
        "weak": cmd_weak,
        "dup": cmd_dup,
        "stale": cmd_stale,
        "aggregate": cmd_aggregate,
        "report": cmd_report,
    }.get(args.cmd)

    if handler is None:
        parser.print_help()
        return 2
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
