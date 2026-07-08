# Changelog v0.7.114 — Lite bootstrap freshness 가드 (ADR-2026-07-08)

> **BLUF**: vault의 `_meta/agents/` 부속(SCHEMA/PROJECT-WORKFLOW)이 갱신되어도 agent가 옛 지침 기억하는 문제를, **(A) X-Guide-Hash 헤더 echo + (B) `wiki_check_freshness` 도구 + (C) lint #19 자동 검사** 3중 가드로 해소. silent warn 기본 + 사람 운영자에게는 **첫 mismatch 1회 알림** (이후 silent).

이전 changelog: `_meta/changelog-v0.7.113.md`

---

## §0 — 묶음 메타

| 항목 | 값 |
|---|---|
| 묶음 | Lite bootstrap freshness 가드 (Codex + agy review 반영) |
| 범위 | v0.7.114 (단일 사이클) |
| 기간 | 2026-07-08 |
| 시작 트리거 | 사용자 명시: "Lite bootstrap이 업데이트되면, 에이전트는 옛날 지침을 기억하고 작업" |
| 종료 트리거 | tsc/vitest/pytest 통과 + dashboard build 통과 |
| 정책 변경 | 0 — Layer 1 (Lite bootstrap 파일) 그대로, Layer 2 (에이전트 인지) 가드만 추가 |
| ADR 동반 | 1 — `_meta/decisions/adr-2026-07-08-lite-bootstrap-freshness.md` |
| 외부 review | Codex CLI + agy CLI 둘 다 "수정 후 채택" verdict |

## §1 — 무엇을 했나

### 1.1 ADR-2026-07-08 (Codex + agy review 반영 5건)

| # | 출처 | 수정 |
|---|---|---|
| 1 | Codex | `wiki_check_freshness(vault, cache_hash?)` 시그니처 3문서 통일 |
| 2 | Codex | `_meta/agents/.guide-version` Tier 2 명시 + agent write 금지 |
| 3 | Codex | PWW §1.2 MCP HTTP-only footer (stdio 미지원) |
| 4 | agy | raven build ↔ stamp 갱신 coupling 보장 + mtime 회귀 가드 |
| 5 | agy | §2.2 silent warn → 첫 mismatch 1회 알림 + Telegram 환경 명시 |

### 1.2 SCHEMA / PWW / Lite bootstrap 갱신

`raven/core/templates/agent/SCHEMA.md`:
- §lint 표: **#19 guide freshness** (info 등급, v0.7.114+)

`raven/core/templates/agent/PROJECT-WORKFLOW.md`:
- §1.1 도구 표: `wiki_check_freshness(vault, cache_hash?)` 추가 (read 모드)
- §1.2 MCP HTTP-only footer 추가 (X-Guide-Hash 헤더는 HTTP 전용)
- §8.5 "지침 freshness 인지" 항목 추가 (Telegram 환경 명시)

`~/Raven/raven-dev/_meta/agents/{SCHEMA,PROJECT-WORKFLOW}.md`: Lite bootstrap 동기화 완료

### 1.3 `wiki_check_freshness` MCP 도구

`raven/mcp/tools/guide.py` (신규, 4979 bytes):
- `_sha256(path)` — SHA256 64-bit prefix
- `_log_md_stats(path)` — log.md line_count + mtime
- `_parse_cache_hash(raw)` — `SCHEMA=abc,PROJECT-WORKFLOW=def` 또는 순서 고정 `abc,def` 둘 다 파싱
- `_format_hash_for_header(guides)` — `X-Guide-Hash` 응답 헤더 형식
- `_load_version_stamp(vault_root)` — `.guide-version` 자동 stamp 읽기
- `write_version_stamp(vault_root)` — raven build hook (Tier 2 Raven 제품만 호출)
- `check_freshness(vault_root, cache_hash=None)` — 메인 함수, freshness_warning 첨부

`raven/mcp/cli.py`:
- `@mcp.tool(name="wiki_check_freshness")` 등록 (read 모드 13종)
- 도구 헤더 docstring 갱신

### 1.4 FastAPI freshness 미들웨어

`raven/api/server.py`:
- `@app.middleware("http") async def freshness_middleware(...)` 신규
- URL path에서 vault 이름 자동 추출 (`/api/vaults/{name}/...`)
- 응답 헤더 `X-Guide-Hash: SCHEMA=...,PROJECT-WORKFLOW=...` echo (모든 응답)
- write 도구 (POST/PUT/PATCH/DELETE) 호출 시 cache_hash mismatch → `X-Guide-Freshness-Warning` 헤더 + freshness_warning 첨부
- silent fail-safe: hash 계산 실패 시 응답 정상 (성능/안정성 우선)

### 1.5 lint #19 자동 검사

`raven/core/lint.py`:
- `check_guide_freshness(vault)` 신규 (info 등급)
- 3가지 케이스: 부속 부재 / stamp 없음 / stamp stale
- run_all() return에 자동 포함

### 1.6 회귀 가드

| 테스트 | 케이스 수 |
|---|---|
| `tests/test_lint_guide_freshness.py` | 4 |
| `tests/test_mcp_check_freshness.py` | 6 |
| **합계** | **10 passed** |

## §2 — 변경 안 한 것

- **강제 read** ❌ (사용자 원칙 "매번 필수 ❌")
- **Telegram 자동 알림 OFF 기본** (사용자 명시 turn 시만)
- **`type: decision` 권한** = 사람 1차 그대로
- **Tier 1 (`_meta/system/`, `_meta/agents/` 핵심 3종) write 가드** = 기존 정책 유지
- **`.guide-version` 직접 agent write** ❌ (Raven 제품 hook만 stamp 갱신)

## §3 — 검증

```text
tsc -b                              → N/A (Dashboard 변경 없음)
pytest 10 passed
  test_lint_guide_freshness (4) + test_mcp_check_freshness (6)
vite build                          → N/A (Dashboard 변경 없음)
PYTHONPATH=. scripts/.venv/bin/python -c "from raven.core.lint import check_guide_freshness; from raven.mcp.cli import *" → OK
PYTHONPATH=. scripts/.venv/bin/python -c "from raven.api.server import app" → OK
```

## §4 — 4 저장 신호

| 신호 | 충족 |
|---|---|
| 재사용성 | 모든 vault 공통 적용 (Lite bootstrap 켠 vault) |
| 인수인계 | Codex + agy 2-party review로 합의 검증, "수정 후 채택" |
| scope/provenance | Tier 2 Raven 제품 영역 명시 + raven build coupling 보장 |
| 실패/리스크 기록 | lint #19 회귀 가드 + mtime 검증 + silent warn (사용자 원칙) |
