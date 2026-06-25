#!/usr/bin/env python3
"""raven-watcher — silent lint-watchdog for registered vaults.

카파시 LLM Wiki 패턴 + M2 강화. 매 실행마다:
  1. 등록된 vault 각각에 대해 `raven.core.lint.run_all(vault)` 실행.
  2. lint 결과의 (critical, warning, info, total) + 상위 N개 issue를 JSON 해시화.
  3. 이전 state 파일 (~/.cache/raven-watcher/state.json) 의 hash 와 비교.
     - 같음 → stdout 비움 (cron no_agent=True = silent on empty stdout = Telegram 폭주 ❌).
     - 다름 → Telegram 메시지 형식으로 stdout emit.
       ```
       🔔 raven-watcher — {vault_name}
       🔴 {prev_c} → {new_c} (Δ 변화)
       🟡 {prev_w} → {new_w} (Δ 변화)
       🔵 {prev_i} → {new_i} (Δ 변화)
       변경: {top changed slug(s)}
       ```

cron 사용 예:
    hermes cron create \
        --schedule "0 3 * * *" \
        --prompt "" \
        --script scripts/watcher.py \
        --no-agent

cron output → origin (현재 chat). Telegram 폭주 방지를 위해 silent on no-change 필수.

CLI 디버그:
    python scripts/watcher.py                 # 1회 실행 (변경 시 stdout emit)
    python scripts/watcher.py --vault default # 단일 vault만
    python scripts/watcher.py --force         # 비교 무시, 항상 emit (테스트)
    python scripts/watcher.py --dry-run       # 변경 없더라도 시뮬레이션 (emit OK)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional


# watcher 메타 — cron이 자신을 재귀 호출하지 않도록.
STATE_DIR = Path(os.environ.get("raven_WATCHER_STATE", str(Path.home() / ".cache" / "raven-watcher")))
STATE_PATH = STATE_DIR / "state.json"

# repo root (scripts/ 의 부모)
REPO_ROOT = Path(__file__).resolve().parent.parent


def _import_raven() -> Any:
    """raven.core 의 lint/registry 모듈 import. 실패 시 stderr + exit 2."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    try:
        from raven.core import lint as lint_module
        from raven.core import registry as registry_fn
        from raven.core.vault import Vault
    except ImportError as e:
        print(f"❌ watcher: raven import 실패: {e}", file=sys.stderr)
        sys.exit(2)
    return lint_module, registry_fn, Vault


def _hash_counts(counts: dict, top_issues: list[dict]) -> str:
    """counts + 상위 N issue 의 sha256. 비교 기준."""
    payload = {
        "c": counts.get("critical", 0),
        "w": counts.get("warning", 0),
        "i": counts.get("info", 0),
        "t": counts.get("total", 0),
        "top": sorted(top_issues, key=lambda x: (x.get("severity", ""), x.get("slug", ""))),
    }
    s = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _load_state() -> dict:
    """이전 state 로드. 파일 없거나 손상 시 빈 dict."""
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    """state 저장. atomic-ish (write to .tmp + rename)."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATE_PATH)


def _format_diff_message(
    vault_name: str,
    prev: dict,
    new: dict,
    prev_top: list[dict],
    new_top: list[dict],
) -> str:
    """Telegram 형식 메시지 생성."""
    pc = prev.get("critical", 0)
    pw = prev.get("warning", 0)
    pi = prev.get("info", 0)
    nc = new.get("critical", 0)
    nw = new.get("warning", 0)
    ni = new.get("info", 0)
    dc = nc - pc
    dw = nw - pw
    di = ni - pi

    def _delta_str(prev_v: int, new_v: int) -> str:
        d = new_v - prev_v
        if d == 0:
            return f"{prev_v} → {new_v}"
        if d < 0:
            return f"{prev_v} → {new_v} (-{-d})"
        return f"{prev_v} → {new_v} (+{d})"

    lines = [f"🔔 raven-watcher — {vault_name}"]
    lines.append(f"🔴 {_delta_str(pc, nc)}")
    lines.append(f"🟡 {_delta_str(pw, nw)}")
    lines.append(f"🔵 {_delta_str(pi, ni)}")
    # top 변경 (prev엔 있는데 new엔 없는 slug = fixed; new엔 있는데 prev엔 없는 slug = new)
    prev_slugs = {x.get("slug", "") for x in prev_top}
    new_slugs = {x.get("slug", "") for x in new_top}
    fixed = sorted(prev_slugs - new_slugs)[:5]
    new_added = sorted(new_slugs - prev_slugs)[:5]
    if fixed:
        lines.append(f"✅ fixed: {', '.join(s for s in fixed if s)}")
    if new_added:
        lines.append(f"🆕 new: {', '.join(s for s in new_added if s)}")
    return "\n".join(lines)


def _format_first_run_message(vault_name: str, counts: dict) -> str:
    """첫 실행 (prev 없음) 메시지 — baseline 알림."""
    c = counts.get("critical", 0)
    w = counts.get("warning", 0)
    i = counts.get("info", 0)
    return (
        f"🔔 raven-watcher — {vault_name}\n"
        f"baseline established\n"
        f"🔴 {c}  🟡 {w}  🔵 {i}\n"
        f"다음 변경부터 알림."
    )


def _run_one_vault(
    vault_obj: Any,
    vault_name: str,
    state: dict,
    lint_module: Any,
    *,
    force: bool,
) -> Optional[str]:
    """vault 1개 lint + diff. 변경 시 메시지(str) 반환, 없으면 None."""
    result = lint_module.run_all(vault_obj)
    counts = result["counts"]
    issues = result["issues"]
    top_issues = issues[:20]  # 상위 20개 슬라이스 (hash 안정성 + 가독성)
    new_hash = _hash_counts(counts, top_issues)
    prev = state.get(vault_name)
    if force:
        # 강제 emit — baseline 메시지 (테스트용)
        return _format_first_run_message(vault_name, counts)
    if prev is None:
        # 첫 실행 — baseline 알림 (silent 아님, 다음 비교 기준 확립)
        state[vault_name] = {
            "hash": new_hash,
            "critical": counts.get("critical", 0),
            "warning": counts.get("warning", 0),
            "info": counts.get("info", 0),
            "top": top_issues,
        }
        return _format_first_run_message(vault_name, counts)
    if prev.get("hash") == new_hash:
        # 변경 없음 — silent
        return None
    # 변경 감지
    prev_counts = {
        "critical": prev.get("critical", 0),
        "warning": prev.get("warning", 0),
        "info": prev.get("info", 0),
    }
    prev_top = prev.get("top", [])
    msg = _format_diff_message(vault_name, prev_counts, counts, prev_top, top_issues)
    state[vault_name] = {
        "hash": new_hash,
        "critical": counts.get("critical", 0),
        "warning": counts.get("warning", 0),
        "info": counts.get("info", 0),
        "top": top_issues,
    }
    return msg


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="raven-watcher: silent lint-watchdog for vaults."
    )
    parser.add_argument(
        "--vault",
        default=None,
        help="단일 vault 만 검사 (default: 등록된 모든 vault)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="비교 무시, 항상 emit (테스트 / smoke-test)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="state 갱신 ❌, 변경 감지 시 메시지만 stdout",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="state 파일 삭제 후 baseline 부터 다시 시작",
    )
    args = parser.parse_args(argv)

    lint_module, registry_fn, Vault = _import_raven()

    if args.reset and STATE_PATH.exists():
        STATE_PATH.unlink()
        print(f"🗑️  state reset: {STATE_PATH}", file=sys.stderr)

    reg = registry_fn()
    if args.vault:
        m = reg.get(args.vault)
        if m is None:
            print(f"❌ vault {args.vault!r} not registered", file=sys.stderr)
            return 2
        vaults_to_check = [(args.vault, Vault.load(m))]
    else:
        vaults_to_check = [(m.name, Vault.load(m)) for m in reg.list()]
    if not vaults_to_check:
        print("⚠️  no vaults registered", file=sys.stderr)
        return 0

    state = _load_state()
    messages: list[str] = []
    for vname, vobj in vaults_to_check:
        msg = _run_one_vault(vobj, vname, state, lint_module, force=args.force)
        if msg:
            messages.append(msg)

    if not args.dry_run:
        _save_state(state)

    if messages:
        # vault 여러 개면 한 메시지로 합치기 (Telegram 폭주 방지)
        sys.stdout.write("\n\n---\n\n".join(messages))
        sys.stdout.write("\n")
    # else: silent on no-change (stdout 비움 → cron no_agent 가 발송 안 함)
    return 0


if __name__ == "__main__":
    sys.exit(main())