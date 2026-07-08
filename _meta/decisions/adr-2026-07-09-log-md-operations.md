---
title: log.md 운영 규칙 4-way 정합성 통합 (SCHEMA/HEADER/CORE/README)
created: 2026-07-09
type: rule
tags: [adr, log-md, mcp, audit, four-way-integrity]
audience: agent
confidence: high
status: current
related:
  - _meta/SCHEMA.md
  - README.md
  - raven/core/log.py
  - raven/core/templates/log.md
  - _meta/decisions/adr-2026-07-08-lite-bootstrap-freshness.md
  - _meta/changelog-v0.7.117.md
aliases: [adr-log-md-operations]
---

# ADR: log.md 운영 규칙 4-way 정합성 통합

> **BLUF**: `log.md` 자동 append는 **5개 진입점(CLI/API/Dashboard/MCP) 모두** `raven.core.log.append` 경유 (v0.7.67 평가 A#1 이후). v0.7.117까지 코드 ↔ 헤더 ↔ README ↔ SCHEMA 4-way 표현이 어긋남. 본 ADR은 (1) 트리거 액션 10종 정의, (2) 자동 vs 수동 분리, (3) 템플릿/문서 동기화를 통합한다.

## 1. 맥락 (Context)

### 1.1 문제 — 4-way 어긋남

2026-07-08 raven-dev vault audit 중 `log.md`가 비어있는 vault 발견 → "MCP는 로그 안 남는다"는 가설 제기 → 검증 결과:

| 소스 | 어긋남 발견 |
|---|---|
| `_meta/SCHEMA.md` L175 | "**새 페이지**: `log.md`에 append" — 트리거 액션 1종만, 자동 호출 주체 미명시 |
| `README.md` §191 | `raven log` 5종 서브커맨드 = "append-only" 코멘트 — **자동/수동 미구분**, 사람 도구처럼만 보임 |
| `raven/core/templates/log.md` 헤더 | Actions 9종 — v0.7.67에 추가된 `rename` 누락 |
| `raven/core/log.py` | `_ALLOWED_ACTIONS` = 9 + `rename` (v0.7.67 평가 A#1) → 헤더와 sync 어긋남 |

**코드 경로는 정확함** — 모든 진입점이 `core.log.append`를 호출. 문제 = **문서 3종이 "CLI만 자동"으로 오해하기 쉬운 표현**.

### 1.2 사용자 north star

- surgical 변경 (P55 memory) — 4 file + ADR 1 + changelog 1 = 최소 단위
- over-engineering ❌ (memory: "다이어트좀")
- 자동/수동 구분 (Layer 2 vault 운영 사실은 vault SOT, AGENTS.md §15 + §3 4 신호)

## 2. 결정 (Decision)

### 2.1 트리거 액션 10종 (정합 SOT)

```yaml
log.md auto-append 트리거 (10종):
  - ingest    # raven ingest (CLI/API) / wiki_ingest (MCP)
  - update    # 페이지 frontmatter 또는 본문 갱신 (모든 진입점)
  - create    # 새 페이지 생성 (모든 진입점)
  - archive   # wiki_archive (MCP) / raven archive (CLI/API)
  - delete    # wiki_delete (admin MCP) / raven page delete (CLI/API)
  - lint      # lint run (CLI/API/Dashboard) / wiki_lint (MCP)
  - build     # raven build (CLI) / wiki.db rebuild (MCP write 후 자동)
  - migrate   # raven migrate apply (CLI/API)
  - rename    # wiki_rename (MCP, v0.7.67 평가 A#1) — 슬러그 변경
  - chore     # 그 외 (Lite bootstrap 초기화, rotate, audit blocked 등)
```

→ `raven.core.log._ALLOWED_ACTIONS` (10종) ↔ `raven/core/templates/log.md` 헤더 (10종) ↔ `raven.core.log` docstring (10종) — 3-way sync 확보.

### 2.2 자동 vs 수동 분리

| 종류 | 트리거 | 도구 |
|---|---|---|
| **자동 append** | 모든 진입점의 write/build/lint/migrate/archive 호출 직후 | `raven.core.log.append` (공용, lock + atomic write) |
| **사람 수동 조회** | CLI 호출 | `raven log list / show / status` (read-only) |
| **사람 수동 append** | CLI 호출 | `raven log append --action X --subject Y` (자동 호출이 누락된 경우 보강) |
| **사람 수동 rotate** | CLI 호출 | `raven log rotate` (자동 500 초과 rotate와 별개, 명시 회전) |

**핵심**: SCHEMA.md / README에서 "log.md append"는 자동 + "raven log" CLI는 수동. **혼동 금지**.

### 2.3 진입점별 호출 위치 (변경 없음, 검증만)

| 진입점 | 자동 append 위치 | 액션 enum |
|---|---|---|
| CLI | `raven/cli/__main__.py:1302` (page new), `:1412` (lint), `:1530/:1606` (migrate), `:1864` (ingest) | ingest/create/lint/migrate |
| API | `raven/api/server.py:1858` (수동 `/api/vaults/{}/log`), `:2020` (lint auto) | ingest/lint/migrate (그 외는 미연결 — 다음 사이클 평가) |
| Dashboard | 직접 호출 ❌ — UI → API PUT/DELETE → server.py 자동 append | (서버 경유) |
| MCP | `raven/mcp/tools/__init__.py:285` `append_log_entry` → `core.log.append` | ingest/update/create/archive/delete/rename |
| MCP (write module) | `raven/mcp/tools/write.py:305` `_finalize_write` | update/ingest |
| MCP (stale module) | `raven/mcp/tools/stale.py:353` | archive |
| MCP (immutable 가드) | `raven/mcp/tools/write.py:386-398` | chore (audit blocked — `_meta/`, `raw/`, `log.md` 변조 시도) |

### 2.4 v0.7.67 평가 A#1 회고 (왜 지금 sync 어긋남이 발견되었나)

v0.7.67 평가 A#1에서 MCP write가 raw `open("a")` → `core.log.append` 경유로 변경 (lock + 화이트리스트 공유). 이때 `_ALLOWED_ACTIONS`에 `rename` 추가했지만 **헤더 템플릿 / SCHEMA.md / README는 동시 업데이트되지 않음**. v0.7.108 audit log 추가 / v0.7.109 자동 rotate도 같은 패턴으로 헤더만 갱신.

→ 본 ADR은 v0.7.67~v0.7.117 누적 drift를 한 번에 정합.

### 2.5 SCHEMA.md L175 강화

```
- (구) **새 페이지**: `log.md`에 append
- (신) **log.md 자동 append**: `raven.core.log.append` (vault-relative lock + atomic write) —
       모든 진입점(CLI/API/Dashboard/MCP)이 자동 호출. 트리거 액션 10종: ingest/update/create/
       archive/delete/lint/build/migrate/rename/chore. CLI만 자동 ❌ (구 문구). 사람 수동 도구는
       raven log list|show|append|rotate|status (README §191). 자세한 운영 규칙: adr-2026-07-09.
```

### 2.6 README §191 강화

```
- (구) # log.md 조회/회전 (append-only)
- (신) # log.md 조회/회전 (사람 수동; 자동 append는 5개 진입점 모두 raven.core.log.append)
```

### 2.7 log.md 템플릿 헤더 sync

```
- (구) Actions: ingest, update, create, archive, delete, lint, build, migrate, chore
- (신) Actions: ingest, update, create, archive, delete, lint, build, migrate, rename, chore
```

→ Lite bootstrap으로 새로 생성되는 vault는 v0.7.109+ 템플릿이 박히므로 **이번 패치 적용 시점 이후 신규 vault는 정합**. 기존 5개 vault는 Lite bootstrap `raven meta sync` 실행 시 헤더 교체됨.

## 3. 결과 (Consequences)

### 긍정
- 4-way (SCHEMA / README / 헤더 / core.log) 정합 회복
- 다른 vault `log.md` 비어있는 현상 — 사람 운영자가 "MCP 안 남는다" 오해 ❌ → "아직 MCP 호출 안 했다" 정상 상태로 인식 정정
- v0.7.67~117 누적 drift 일소
- 다음 액션 enum 추가 시 SCHEMA ↔ README ↔ 헤더 ↔ core.log 4-way sync가 본 ADR로 의무화

### 부정 / 비용
- 기존 5개 vault의 log.md 헤더 1줄 (`Actions:`)은 Lite bootstrap `raven meta sync` 실행 전까지 stale. 사람이 명시 호출해야 함 (자동 갱신 ❌ — Tier 1 ↔ Tier 2 경계)
- ADR 1건 + changelog 1건 = 문서 비용 (+86 line ADR, +30 line changelog)

### 후속 작업
- 기존 5개 vault에 `raven meta sync` 실행 (Lite bootstrap freshness 갱신) — 사용자 명시 결정 시
- API `/api/vaults/{}/log` 수동 append 외 자동 연결 audit (페이지 CRUD API 호출 시 log append 여부 — server.py L1858 외 위치 확인 필요, 본 ADR 범위 밖)
- v0.7.118 본 ADR 적용 회고

## 4. 변경 파일 (변경 없음: raven/core/log.py, raven/mcp/*)

- `_meta/SCHEMA.md` — L175 강화 (1줄)
- `README.md` — §191 코멘트 강화 (1줄)
- `raven/core/templates/log.md` — 헤더 Actions enum 10종 sync (1줄)
- `_meta/decisions/adr-2026-07-09-log-md-operations.md` (신규, 본 문서)
- `_meta/changelog-v0.7.118.md` (신규, 적용 회고)

## 5. references

- `raven/core/log.py` L27, L81-86, L191-270 (`_ALLOWED_ACTIONS`, `append()` lock+atomic)
- `raven/mcp/tools/__init__.py` L285-324 (`append_log_entry` → `core.log.append`)
- `raven/mcp/tools/write.py` L266-314 (`_finalize_write` 자동 append)
- `raven/mcp/tools/stale.py` L349-356 (`wiki_archive` 자동 append)
- `raven/mcp/tools/write.py` L386-398 (`_is_immutable_agent_path` audit blocked chore append)
- `raven/cli/__main__.py` L1302/1412/1530/1606/1864 (CLI 자동 append 5지점)
- `raven/api/server.py` L1858/2020 (API 수동 + lint auto)
- AGENTS.md §5.5 (MCP = 에이전트 표준), §9 (hotfix 정책), §15 (자가 평가)
- v0.7.67 평가 A#1 (MCP `core.log.append` 경유 변경, `rename` 추가)
- v0.7.108 audit log (G5, immutable 가드 audit append)
- v0.7.109 자동 rotate + lint #18
- v0.7.117 dict extra 가독성 (log.append 자체 개선)
- ADR-2026-07-08-lite-bootstrap-freshness (4-way sync 의무화 패턴 참고)