# raven v0.5.6 — AGENTS.md(레포) + README 정체성 정리 + v0.5.5 hotfix

> **핵심**: Codex/Claude 컨셉 리뷰 결과 (2026-06-27) — v0.5.5 머지 시 누락된 hotfix + Raven repo 최상위 `AGENTS.md` 신규 + README 정체성 보강.
>
> 사용자 정정 (Telegram ❌, README + AGENTS.md 구조 ✅) 반영.

릴리스 일자: 2026-06-27
이전: v0.5.5 (Lite bootstrap 4종 with AGENTS.md)

---

## 한 줄 요약

**v0.5.5 hotfix (silent bootstrap bug) + Raven repo AGENTS.md 신규 + README 정체성/버전 정리.** Lite 정책 그대로, Tier 1 ↔ Tier 2 경계 강제, 멀티 에이전트 write 표현 정직화.

---

## 1. v0.5.5 hotfix (silent bug)

### 발견

Codex 컨셉 리뷰 지적: "v0.5.5의 4종 bootstrap 주장과 실제 vault.py/test의 3종 bootstrap 전제가 충돌."

### 진짜 root cause (더 깊음)

| 위치 | v0.5.5 패치 누락 | 영향 |
|---|---|---|
| `raven/core/vault.py:128-132` (template_map) | AGENTS.md 추가 안 됨 | **silent 실패** — 4종 메시지 표시하지만 실제 3종만 복사 |
| `raven/cli/__main__.py:154` (bootstrapped 메시지) | 3종 표시 | 사용자 혼동 |
| `tests/test_vault_create.py:52` (docstring) | 3종 표시 | 테스트 의도와 실제 동작 mismatch |

### 패치

```python
# raven/core/vault.py
template_map = {
    "_meta/system/SCHEMA.md": "templates/system/SCHEMA.md",
    "_meta/system/RULES.md":  "templates/system/RULES.md",
    "_meta/system/AGENTS.md": "templates/system/AGENTS.md",   # 추가
    "log.md":                  "templates/log.md",
}
```

```python
# raven/cli/__main__.py
typer.echo(f"   bootstrapped: content/, _meta/{{SCHEMA.md, RULES.md, AGENTS.md}}")
```

```python
# tests/test_vault_create.py
"""Lite bootstrap: SCHEMA.md, RULES.md, AGENTS.md, log.md are copied (v0.5.5+)."""
```

### 검증

```
$ raven vault create real /tmp/v055-real
✅ vault created: real → /private/tmp/v055-real
   bootstrapped: content/, _meta/{SCHEMA.md, RULES.md, AGENTS.md}

$ find /tmp/v055-real -type f
/tmp/v055-real/.vault.json
/tmp/v055-real/_meta/system/AGENTS.md    ← 복구됨
/tmp/v055-real/_meta/system/RULES.md
/tmp/v055-real/_meta/system/SCHEMA.md
/tmp/v055-real/log.md

$ pytest tests/ -q → 252 passed
```

→ **silent failure → 명시적 4종 복사**. v0.5.5 제품 표면과 일치.

---

## 2. Raven repo 최상위 `AGENTS.md` 신규

### 사용자 결정 (2026-06-27)

> "레이븐 소스프로젝트 레포 안에 리드미랑 소울이 아니라 리드미랑 agents.md로 하자"

### 분리

| 위치 | 대상 | 차이 |
|---|---|---|
| `~/Desktop/Dev/Project/Raven/AGENTS.md` | **AI 에이전트**가 **Raven 코드**를 다룰 때 | build/test/lint/doc/commit |
| `~/vaults/<vault>/_meta/system/AGENTS.md` | 사람 + AI 에이전트가 **vault 데이터**를 다룰 때 | save/ingest/query/lint |

### Raven repo AGENTS.md 12섹션

| § | 내용 |
|---|---|
| 0 | 당신은 무엇인가 (Raven 개발팀 일원) |
| 1 | 작업 시작 전 — README + changelog + git log |
| 2 | 4가지 진입점 (CLI/HTTP API/Dashboard/MCP) — **5번째 진입점 추가 ❌** |
| 3 | 사용자 3종 — **멀티 에이전트 experimental** 정직화 |
| 4 | Lite Bootstrap 정책 (Tier 1 ↔ Tier 2) |
| 5 | 저장 결정 — 4가지 신호 |
| 6 | 작업 절차 (build/test/lint/doc/commit + verify-in-loop) |
| 7 | 권한 — 4개 영역 (raven/tests/_meta/dashboard) |
| 8 | 진입점 추가/제거 의사결정 절차 |
| 9 | hotfix / silent 버그 정책 |
| 10 | 하지 말 것 (10개) |
| 11 | 예외: 다른 도구/AI에서의 호출 (vendor-agnostic) |
| 12 | 작업 완료 보고 형식 |

### 핵심 경계 명시

```
❌ SOUL.md 수정 ❌ (Hermes 프로필 설정이지 Raven 제품 문서 ❌)
❌ 5번째 진입점 추가 ❌ (Telegram, Slack 등은 외부 오케스트레이터 영역)
❌ 멀티 에이전트 write를 "안정 지원"이라 표현 ❌ (over-promise)
❌ mcp/ 패키지 이름 변경 없이 import 추가 ❌ (네임스페이스 충돌)
```

---

## 3. README 정체성 보강

### Before (v0.5.5)

```markdown
# Raven — 옵시디언을 대체할 마크다운 기반 PKM 노트 프로덕트
> Obsidian-free, agent-aware, multi-vault.
```

→ Codex/Claude 비판: "negative definition" + "Obsidian clone 오해"

### After (v0.5.6)

```markdown
# Raven — local-first agent-aware markdown vault
> markdown SoT + agent-native + multi-vault.
> 옵시디언의 모티브를 빌려왔지만, 에이전트 1급 시민 + 프로그래머블 진입점이 차별점.
> Obsidian clone이 아님.
```

### 추가 변경

- §"누가 쓰는가" 신규 — 3종 사용자 + 멀티 에이전트 experimental 명시
- §"왜 만들었나" 표에서 "5개 진입점" (MCP 추가) 명시
- §"대체하지 않는 범위" 신규 — 정직한 한계 명시 (모바일/sync/플러그인/팀)
- §"진입점 추가/제거 의사결정" 절차 신규 — ADR + write contract 단일화
- §"라이선스/상태" — v0.2.0 → v0.5.5, 멀티 에이전트 experimental 명시
- §"관련 문서" — AGENTS.md 링크, vault AGENTS.md 구분 명시

---

## 4. Claude 리뷰 기각: "Telegram 진입점"

Claude 지적:
> "Telegram bot 진입점 미정의 (핵심 워크플로우인데 설계 외 처리)"

→ **기각**. 사용자 명확화:

> "텔레그램이랑 레이븐이랑 전혀 상관없어. 없어야돼 텔레그램 개념"

| 구분 | 진입점 | 소속 |
|---|---|---|
| 사람 ↔ Hermes | Telegram | **Hermes 오케스트레이터** (Hermes가 Raven 호출) |
| 사람 ↔ Raven | CLI/Dashboard | **Raven** (자체 진입점) |
| 자동화 ↔ Raven | HTTP API/MCP | **Raven** |

→ **5번째 진입점 추가 ❌** (Raven repo AGENTS.md §2 + §10 + README §"진입점 추가/제거 의사결정"에 명시).

---

## 5. Codex/Claude 통합 분석 (P0/P1/P2 매트릭스)

### P0 (긴급)

| # | 약점 | 출처 | 상태 |
|---|---|---|---|
| P0-1 | Lite bootstrap 정책 문서↔코드 불일치 | Codex #2 | ✅ v0.5.6 hotfix |
| P0-2 | 멀티 에이전트 write over-promise | Codex #3, Claude #1 | ✅ AGENTS.md §3 + README 정직화 |
| P0-3 | 정체성 두 마리 토끼 | Codex #1, Claude Q1 | ✅ README §"누가 쓰는가" + §"대체하지 않는 범위" |
| P0-4 | MCP 네임스페이스 핵 | Codex/Claude | ⏳ 다음 사이클 (ADR + `raven/mcp/` 이동) |

### P1 (단기, 다음 사이클)

| # | 약점 | 출처 |
|---|---|---|
| P1-1 | write-path 단일화 | Codex #4, Claude Q3-1 |
| P1-2 | SCHEMA.md sync 충돌 정책 미정의 | Codex Q4-2, Claude #3 |
| P1-3 | SQLite 동시 쓰기 contention | Claude #1 |
| P1-4 | 빠진 사용자군: mobile/quick capture, reader-only, migration | Codex Q2 |

### P2 (중기)

| # | 약점 | 출처 |
|---|---|---|
| P2-1 | AGENTS.md 이름 사람 친화성 (이미 분리됨, OK) | Codex Q4-1 |
| P2-2 | FastAPI + sync SQLite → aiosqlite | Claude Q5-3 |
| P2-3 | git author 오염 | Claude Q5-2 |
| P2-4 | Vector search 부재 | Claude Q5-5 |
| P2-5 | 인증 부재 | Claude Q5-6 |

---

## 6. 변경 사항 요약

| 파일 | 변경 |
|---|---|
| `raven/core/vault.py` | template_map에 AGENTS.md 추가 (1줄) |
| `raven/cli/__main__.py` | bootstrapped 메시지 4종 (1줄) |
| `tests/test_vault_create.py` | docstring 4종 (1줄) |
| **`AGENTS.md`** | **신규** (7.8KB, 12섹션) |
| **`README.md`** | 정체성 + 사용자 + 진입점 + 라이선스/상태 갱신 |
| **`_meta/changelog-v0.5.6.md`** | **이 문서** |

코드 변경: +1 +1 +1 = 3줄, 문서 변경: AGENTS.md 신규 + README 부분 갱신.

---

## 7. 검증

```bash
$ PYTHONPATH=. scripts/.venv/bin/python -m pytest tests/ -q
252 passed, 1 warning in 2.23s

$ PYTHONPATH=. scripts/.venv/bin/python -m raven.cli vault create real /tmp/v055-real
✅ vault created: real → /private/tmp/v055-real
   bootstrapped: content/, _meta/{SCHEMA.md, RULES.md, AGENTS.md}

$ find /tmp/v055-real -type f | sort
/tmp/v055-real/.vault.json
/tmp/v055-real/_meta/system/AGENTS.md
/tmp/v055-real/_meta/system/RULES.md
/tmp/v055-real/_meta/system/SCHEMA.md
/tmp/v055-real/log.md
```

→ 4종 모두 복사 ✅, 회귀 0 ✅.

---

## 8. 다음 사이클 후보 (P0-4, P1 모두)

1. **MCP 네임스페이스 핵 제거** (P0-4): `mcp/` → `raven/mcp/` 이동 + import path 검증
2. **write-path 단일화** (P1-1): `raven.core.contracts.write_page()` 같은 단일 진입 함수로 모든 write path 통합
3. **SCHEMA.md sync 충돌 정책** (P1-2): ADR 작성 + `meta sync` 동작 명시 (3-way merge vs skip+warn)
4. **SQLite WAL + aiosqlite** (P1-3): 멀티 에이전트 동시성 해결

→ v0.5.7 또는 v0.6 사이클에서 처리.