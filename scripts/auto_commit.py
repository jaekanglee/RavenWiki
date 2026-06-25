#!/usr/bin/env python3
"""raven-auto-commit — silent git watchdog for vault 변경.

vault 디렉토리에서 .md 변경 감지 → git add + commit.
변경 없으면 silent (cron no_agent=True = silent on empty stdout).

왜 silent인가:
  - 5분마다 cron 실행 시 0건 commit → Telegram 폭주 방지
  - 실제 변경만 commit 메시지로 알림

설계:
  1. vault 디렉토리에서 `git status --porcelain` 실행
  2. 0줄 → silent return (exit 0, no stdout)
  3. 1+줄 → git add . + git commit (메시지 자동 생성)
  4. stdout = commit 요약 (Telegram용)

사용:
    python scripts/auto_commit.py ~/vaults/wiki
    python scripts/auto_commit.py              # 현재 cwd

cron 예 (hermes):
    hermes cron create \\
        --schedule "*/30 * * * *" \\
        --prompt "" \\
        --script scripts/auto_commit.py ~/vaults/wiki \\
        --no-agent

핵심 결정 (2026-06-26 raven §A):
  - vault 루트에서 실행 (vault 자체가 git repo)
  - 1 commit = 1 변경 묶음 (atomic)
  - 메시지 자동: "vault: auto-commit (N files changed)" 또는 첫 변경 파일 slug
  - wiki.db는 .gitignore (regenerable)
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import List


def run(cmd: List[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def auto_commit(vault_dir: Path) -> int:
    """vault_dir를 git commit. 0건 변경이면 silent return 0.

    Returns:
        0 = silent (no change)
        1 = commit OK (with stdout message)
        2 = git init 필요 (vault가 git repo 아님)
    """
    if not vault_dir.exists():
        print(f"❌ vault not found: {vault_dir}", file=sys.stderr)
        return 2

    if not (vault_dir / ".git").exists():
        # git init + initial commit (1회)
        run(["git", "init", "-q"], vault_dir)
        run(["git", "add", "-A"], vault_dir)
        run(
            [
                "git",
                "-c",
                "user.email=raven@local",
                "-c",
                "user.name=raven-auto",
                "commit",
                "-q",
                "-m",
                "vault: initial (auto)",
            ],
            vault_dir,
        )
        print(f"🆕 git init + initial commit: {vault_dir}")
        return 1

    # status check
    status = run(["git", "status", "--porcelain"], vault_dir)
    if not status.stdout.strip():
        # silent — no change
        return 0

    # 변경 있음 → add + commit
    changed_files = [
        line.split()[-1]
        for line in status.stdout.strip().splitlines()
        if line.strip()
    ]
    n = len(changed_files)

    run(["git", "add", "-A"], vault_dir)

    # commit message: 첫 변경 파일 slug + N files
    first = changed_files[0]
    msg = f"vault: auto-commit ({n} file{'s' if n > 1 else ''}) — {first}"

    result = run(
        [
            "git",
            "-c",
            "user.email=raven@local",
            "-c",
            "user.name=raven-auto",
            "commit",
            "-q",
            "-m",
            msg,
        ],
        vault_dir,
    )

    if result.returncode != 0:
        print(f"❌ git commit failed: {result.stderr}", file=sys.stderr)
        return 1

    # stdout — Telegram-friendly
    print(f"📝 raven-auto-commit — {vault_dir.name}")
    print(f"   {n} file{'s' if n > 1 else ''} changed")
    for f in changed_files[:5]:
        print(f"   - {f}")
    if n > 5:
        print(f"   ... +{n - 5} more")
    return 1


def main() -> int:
    if len(sys.argv) > 1:
        vault_dir = Path(sys.argv[1]).expanduser().resolve()
    else:
        vault_dir = Path.cwd()

    return auto_commit(vault_dir)


if __name__ == "__main__":
    sys.exit(main())
