# raven v0.6.32 — filesystem watcher_fs 자동화 (watch → build → lint → log)

> **핵심**: 사용자가 의도한 "Karpathy LLM Wiki 본질에 입각한 Raven 발전"의 두 번째 단계 — **filesystem watch → build → lint → log 체인 자동화**. 사람 개입 0으로 "컴파일 후 reuse, 매번 재구성 ❌" 실현.

릴리스 일자: 2026-06-30
이전: v0.6.31 (North Star 선언)

---

## 한 줄 요약

`scripts/watcher_fs.py` 신규 — `watchfiles` (Rust) 기반 filesystem watcher. vault의 .md 변경 감지 → 자동 build → lint → log append 체인. North Star "컴파일 후 reuse" 직접 실현.

## 1. 변경 사항

### 1-1. `scripts/watcher_fs.py` (신규)

기존 `scripts/watcher.py` (cron 기반 lint 비교) 와의 차이:
- watcher.py: cron, lint 결과만 비교
- **watcher_fs.py: filesystem watch, .md 변경 시 자동 build/lint/log 체인**

핵심 함수 4개:
- `watch(vault_paths, on_change)` — `watchfiles.awatch` + debounce 500ms + .md filter
- `build(vault_obj, build_db_fn)` — `raven.core.db.build_db` 호출
- `lint(vault_obj, lint_module)` — `raven.core.lint.run_all` (13개 check)
- `log(vault_obj, vault_name, action, subject, append_fn)` — `raven.core.log.append` 호출

CLI:
```bash
python scripts/watcher_fs.py --vault raven-dev --once     # 5초 watch → 종료
python scripts/watcher_fs.py --vault raven-dev --daemon   # 무한 watch
python scripts/watcher_fs.py                              # 등록된 모든 vault
```

### 1-2. `tests/test_watcher_fs_contract.py` (신규, 5 tests)

회귀 가드:
1. watchfiles 의존성 설치 확인
2. scripts/watcher_fs.py 존재
3. 4단계 함수 정의 (watch/build/lint/log)
4. .md 파일 필터 (`*.md`)
5. debounce 또는 polling 설정

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **409 passed** (v0.6.31: 404 → v0.6.32: 409, +5) |
| vitest | **20 files / 102 tests + 1 skip** (회귀 0) |
| 실제 smoke (touch trigger) | watcher 감지 → build → log.md append 확인 ✅ |

실제 동작:
```
$ touch ~/Raven/raven-dev/content/concept/test-watch-trigger.md
$ cat ~/Raven/raven-dev/log.md | tail -3
## [2026-06-29] build | wiki.db rebuild (ok, ? pages)
- db: /Users/jaekanglee/Raven/raven-dev/wiki.db
- returncode: 0
```

## 3. North Star 실현

이 watcher_fs.py는 v0.6.31에서 선언한 north star "컴파일 후 reuse, 매번 재구성 ❌"를 **코드 레벨에서 자동화**:

- ✅ 사용자가 .md 파일 편집 → 자동 build (재컴파일 0 수동)
- ✅ 같은 컨텍스트 매번 재구성 ❌ → watcher가 변경 즉시 누적
- ✅ lint 13개 자동 실행 → quality regression 자동 감지
- ✅ log.md 자동 append → audit trail

## 4. 효과

| 항목 | 효과 |
|---|---|
| 자동 build/lint 체인 | 사람 개입 0 |
| 컴파일 latency | 500ms debounce + build ~수십 ms = 1초 이내 |
| audit trail | log.md 자동 append (Karpathy 원본 패턴 그대로) |
| 사용성 | cron 등록 없이도 `python watcher_fs.py --daemon` 한 줄 |

## 5. 후속 작업 (메모리 §next session)

3. **Raven 본질 회귀 가드** (lint가 Karpathy 본질 준수 검증)
4. `raven-delegate.md` 톤 한 줄 추가 (Antigravity 가이드)
5. Worker result 어댑터 (Codex JSON + Antigravity plain text 통합)
6. Tier 1 leak 검증 hook