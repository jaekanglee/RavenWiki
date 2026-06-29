#!/usr/bin/env python3
"""raven-watcher-fs — filesystem watcher: watch → build → lint → log 체인 자동화.

v0.6.32+ (Karpathy LLM Wiki north star 발현): 매번 재구성 ❌, 컴파일 후 reuse ⭕.
사람이 vault에 .md 파일을 쓰면 자동 build + lint + log append — 사람 개입 0.

기존 scripts/watcher.py (cron 기반 lint 비교) 와의 차이:
  - watcher.py: cron, lint 결과만 비교
  - watcher_fs.py: filesystem watch, .md 변경 시 자동 build/lint/log 체인

CLI 사용:
  # 1회 실행 (vault 1개 등록 후 5초 watch → 종료)
  python scripts/watcher_fs.py --vault default --once

  # daemon 모드 (background, 무한 watch)
  python scripts/watcher_fs.py --vault default --daemon

  # 등록된 모든 vault watch
  python scripts/watcher_fs.py

플로우:
  1. watchfiles.awatch() — .md 파일 변경 감지 (debounce 500ms)
  2. build → raven.core.build.build_all() 또는 vault.build() 호출
  3. lint → raven.core.lint.run_all() (lint 13개 자동화)
  4. log → log.md append (build | N pages)

north star 준수:
  - "컴파일 후 reuse" — 변경 즉시 자동 컴파일
  - "매번 재구성 ❌" — vault 사용자가 build 안쳐도 OK
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Iterable, Optional

# repo root (scripts/ 의 부모)
REPO_ROOT = Path(__file__).resolve().parent.parent

# watchfiles (Rust 기반 빠른 watcher, venv에 이미 설치됨)
try:
    from watchfiles import awatch, Change
except ImportError:
    print(
        "❌ watcher_fs: 'watchfiles' 모듈 필요. "
        "scripts/.venv/bin/pip install watchfiles",
        file=sys.stderr,
    )
    sys.exit(2)


# watch 설정
DEBOUNCE_MS = 500  # 연속 edit 1회만 처리
WATCH_FILTER = ["*.md"]  # .md 파일만 감지 (.py, .db 등 제외)


def _import_raven() -> Any:
    """raven.core 의 registry/build/lint 모듈 import. 실패 시 stderr + exit 2."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    try:
        from raven.core import registry as registry_fn
        from raven.core.vault import Vault
        from raven.core.db import build_db
        from raven.core import lint as lint_module
        from raven.core.log import append
    except ImportError as e:
        print(f"❌ watcher_fs: raven import 실패: {e}", file=sys.stderr)
        sys.exit(2)
    return registry_fn, Vault, build_db, lint_module, append


def watch(
    vault_paths: Iterable[Path],
    *,
    on_change: Optional[Any] = None,
    stop_event: Any = None,
) -> None:
    """vault_paths 디렉토리들에서 .md 변경 감지 (Rust watchfiles 기반).

    Args:
        vault_paths: 감지할 vault 경로들 (각 vault의 root)
        on_change: 변경 감지 시 호출할 콜백 (paths 인자). None이면 print.
        stop_event: threading.Event — set되면 watch 종료 (daemon 모드용)
    """
    paths = [str(p) for p in vault_paths]
    if not paths:
        return
    callback = on_change if on_change is not None else _default_on_change
    # awatch = async generator → async for 필요
    import asyncio

    async def _run() -> None:
        try:
            async for changes in awatch(
                *paths,
                watch_filter=WATCH_FILTER,
                debounce=DEBOUNCE_MS,
                stop_event=stop_event,
                yield_on_timeout=False,
            ):
                # changes: set[Change] — Change는 (path, change_type) 튜플
                changed_paths = [str(p) for (p, _) in changes]
                callback(changed_paths)
        except KeyboardInterrupt:
            return

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        return


def build(vault_obj: Any, build_db_fn: Any) -> dict:
    """vault build (wiki.db 재빌드 + log.md append).

    Returns:
        dict with keys: pages, log_entry, duration_ms
    """
    import time

    start = time.time()
    result = build_db_fn(vault_obj, run_lint=False)  # lint는 별도 호출
    duration_ms = int((time.time() - start) * 1000)
    return {
        "pages": result.get("pages", 0),
        "log_entry": result.get("log_entry"),
        "duration_ms": duration_ms,
    }


def lint(vault_obj: Any, lint_module: Any) -> dict:
    """vault lint (13개 check + log.md append).

    Returns:
        dict with keys: counts (critical/warning/info/total), top_issues
    """
    result = lint_module.run_all(vault_obj)
    return {
        "counts": result["counts"],
        "top_issues": result["issues"][:20],
    }


def log(
    vault_obj: Any,
    vault_name: str,
    *,
    action: str = "build",
    subject: str = "",
    append_fn: Any = None,
) -> None:
    """log.md append (vault 루트, append-only).

    Args:
        vault_obj: vault 객체 (append에 전달)
        vault_name: vault 이름
        action: 액션 종류 (build, lint, watch 등) — 9종 중 하나
        subject: 부가 설명
        append_fn: raven.core.log.append — None이면 stderr warn
    """
    if append_fn is None:
        print(
            f"⚠️  watcher_fs.log: append_fn=None, log skipped ({vault_name} {action})",
            file=sys.stderr,
        )
        return
    try:
        append_fn(vault_obj, action=action, subject=subject)
    except ValueError as e:
        # action이 허용 목록에 없을 때 — 워치독은 계속 동작
        print(f"⚠️  watcher_fs.log: {e}", file=sys.stderr)


def _default_on_change(changed_paths: list[str]) -> None:
    """watch 콜백 기본값 — 변경 감지만 stdout 알림."""
    print(f"🔔 watcher_fs: {len(changed_paths)} files changed")
    for p in changed_paths[:5]:
        print(f"   • {p}")
    if len(changed_paths) > 5:
        print(f"   ... (+{len(changed_paths) - 5} more)")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="raven-watcher-fs: watch → build → lint → log 자동화"
    )
    parser.add_argument(
        "--vault",
        default=None,
        help="단일 vault만 watch (default: 등록된 모든 vault)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="1회 실행 (5초 watch 후 종료) — cron/smoke-test용",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="무한 watch (Ctrl+C로 종료)",
    )
    args = parser.parse_args(argv)

    if not args.once and not args.daemon:
        # default = once 모드 (안전)
        args.once = True

    registry_fn, Vault, build_db_fn, lint_module, append_fn = _import_raven()
    reg = registry_fn()
    if args.vault:
        m = reg.get(args.vault)
        if m is None:
            print(f"❌ vault {args.vault!r} not registered", file=sys.stderr)
            return 2
        vaults_to_watch = [(m.name, Vault.load(m))]
    else:
        vaults_to_watch = [(m.name, Vault.load(m)) for m in reg.list()]
    if not vaults_to_watch:
        print("⚠️  no vaults registered", file=sys.stderr)
        return 0

    vault_paths = [vobj.root for (_, vobj) in vaults_to_watch]

    def on_change_pipeline(changed_paths: list[str]) -> None:
        """watch 감지 시 build → lint → log 파이프라인."""
        _default_on_change(changed_paths)
        for vname, vobj in vaults_to_watch:
            try:
                b = build(vobj, build_db_fn)
                print(f"   📦 build: {b['pages']} pages ({b['duration_ms']}ms)")
                l = lint(vobj, lint_module)
                c = l["counts"]
                print(f"   🔍 lint: 🔴 {c.get('critical', 0)}  🟡 {c.get('warning', 0)}  🔵 {c.get('info', 0)}")
                log(
                    vobj,
                    vname,
                    action="build",
                    subject=f"watcher_fs: {len(changed_paths)} files → {b['pages']} pages",
                    append_fn=append_fn,
                )
            except Exception as e:
                print(f"   ❌ {vname}: {e}", file=sys.stderr)

    import threading

    stop_event = threading.Event()

    if args.once:
        # 5초 watch → 종료
        import time
        print(f"👀 watcher_fs: watching {len(vault_paths)} vault(s) for 5s...")
        stop = threading.Timer(5.0, stop_event.set)
        stop.start()
        try:
            watch(vault_paths, on_change=on_change_pipeline, stop_event=stop_event)
        finally:
            stop.cancel()
    else:
        # daemon 모드
        print(f"👀 watcher_fs: watching {len(vault_paths)} vault(s) — Ctrl+C to stop")
        watch(vault_paths, on_change=on_change_pipeline, stop_event=stop_event)
    return 0


if __name__ == "__main__":
    sys.exit(main())