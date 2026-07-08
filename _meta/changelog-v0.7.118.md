---
title: Changelog v0.7.118
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.118 — log.md 운영 규칙 4-way 정합성 통합

## 무엇을 했는가

다른 vault에서 `log.md`가 비어있는 현상 보고 → "MCP는 로그 안 남는다" 가설 검증 → **코드는 정상 (5개 진입점 모두 `core.log.append` 자동 호출)**, 문제 = **SCHEMA / README / 헤더 / core.log 4-way 표현 drift** 진단. 4 file + ADR 1 + changelog 1 패치.

### Fix A — `_meta/SCHEMA.md` L175 강화 (1줄)

| Before | After |
|---|---|
| `**새 페이지**: log.md에 append` | `**log.md 자동 append**: raven.core.log.append (vault-relative lock + atomic write) — 모든 진입점(CLI/API/Dashboard/MCP)이 자동 호출. 트리거 액션 10종: ingest / update / create / archive / delete / lint / build / migrate / rename / chore. CLI만 자동 ❌ (구 문구) — 5개 진입점 전부 자동. 사람 수동 도구는 raven log list|show|append|rotate|status (README §191). 자세한 운영 규칙: adr-2026-07-09-log-md-operations.md.` |

### Fix B — `README.md` §191 코멘트 강화 (1줄)

| Before | After |
|---|---|
| `# log.md 조회/회전 (append-only)` | `# log.md 조회/회전 (사람 수동; 자동 append는 5개 진입점 모두 raven.core.log.append)` |

### Fix C — `raven/core/templates/log.md` 헤더 sync (1줄)

| Before | After |
|---|---|
| `Actions: ingest, update, create, archive, delete, lint, build, migrate, chore` | `Actions: ingest, update, create, archive, delete, lint, build, migrate, rename, chore` |

### New — `adr-2026-07-09-log-md-operations.md`

신규 ADR (BLUF + Pyramid). 핵심:
- 트리거 액션 10종 정의 (v0.7.67 `rename` 추가분 반영)
- 자동 vs 수동 분리표 (5 진입점 × 수동 도구)
- 진입점별 호출 위치 매트릭스 (CLI 5지점 / API 2지점 / MCP 4모듈 / Dashboard는 API 경유)
- v0.7.67~117 누적 drift 회고

## 왜 그렇게 했는가 (§5 4 신호)

- **재사용 가능성**: log.md 자동 append contract는 5개 진입점 × 10종 액션 = 50+ 호출 지점이 의존. 4-way 표현이 어긋나면 다음 운영자가 잘못된 가정으로 작업 → surgical 정합.
- **인수인계 필요성**: 다른 vault `log.md` 비어있는 것 = "아직 MCP 호출 안 한 정상 상태"인데 "MCP 안 남는다" 오해 가능. 본 패치로 정정.
- **scope/provenance 추적**: ADR로 정책 SOT 박음. v0.7.67~117 누적 drift 일소.
- **실패/리스크 기록**: silent 4-way drift는 코드 정상인데 문서만 거짓말 → 진단 비용 ↑. ADR §2.4에 회고.

## 검증

- **코드 정합**: `git grep 'log_module.append\|append_log_entry'` — 5 진입점 × 4 모듈 = 9+ 호출 지점 모두 `core.log.append` 경유 확인
- **4-way sync**: SCHEMA L175 (10종) ↔ README §191 (자동/수동) ↔ 템플릿 헤더 (10종) ↔ `core.log._ALLOWED_ACTIONS` (10종) ✓
- **실제 vault 동작**: `harumoa` vault의 build/lint 9건 = CLI 자동 append 정상 동작 증거 (mcp-via 0은 아직 MCP 호출 안 들어와서 정상)
- **Tier 1 ↔ Tier 2 경계**: `vault clone` 기본 = content only (Tier 1 leak 방지) — log.md 헤더 변경은 Lite bootstrap이 새 vault에 박음. 기존 5 vault는 `raven meta sync` 사용자 명시 시 갱신 (자동 ❌)

## 후속 작업

- 기존 5 vault의 log.md 헤더 sync = `raven meta sync` 사용자 명시 시 (다음 사이클 평가)
- API 페이지 CRUD 자동 append audit (server.py L1858 외 위치 — 본 changelog 범위 밖)
- 4-way sync 의무화 = ADR §2.5~2.7로 다음 액션 enum 추가 시 4 file 동시 업데이트