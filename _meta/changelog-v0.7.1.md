# raven v0.7.1 — Lite bootstrap AGENTS.md 도구 표면 재작성

> **핵심**: 사용자 정정 (2026-06-30) — "사용자는 Raven이 정의한 최소한의 vault 구조 내에서 자기 프로덕트를 알아서 문서화하는 사람이지, Raven의 세부 로직이나 구현사항을 알 필요는 없음. 알아야 할 건 명확히 Raven이 제공하는 도구로써의 표면일 뿐."
>
> Lite bootstrap의 AGENTS.md를 **vault 사용자 표면 가이드**로 재작성. Raven 내부 구현(Tier 1 leak 정책, vendor 예시, OPERATIONS/agent/raven-policy 복사 금지) 모두 제거. 기존 vault (harumoa, raven-dev) 동기화.

릴리스 일자: 2026-06-30
이전: v0.7.0 (Karpathy LLM Wiki +α 가이드)

---

## 한 줄 요약

Lite bootstrap AGENTS.md가 "Vault Agent Operations" (raven 개발팀 톤) → **"Vault User Guide"** (vault 사용자 표면)으로 개편. 8섹션 (시작 / 4 키워드 / 권한 / 저장 신호 / 페이지 작성 / 작업 절차 / 하지 말 것 / 다음 단계).

## 1. 변경 사항

### 1-1. `raven/core/templates/system/AGENTS.md` (재작성)

**Before (Lite bootstrap v0.6.37)** — "Vault Agent Operations" (raven 개발팀 관점):
- §7에 Tier 1 leak 정책 ("raven 운영 코드(OPERATIONS, agent/*, raven-policy)를 vault에 복사 ❌") 박힘
- §8에 vendor 예시 ("Codex CLI든, Claude Code든, Cursor든, 자동화 스크립트든") 박힘
- §3에 `_meta/`를 직접 수정 ❌ ("raven meta sync만")

**After (v0.7.1+)** — "Vault User Guide" (vault 사용자 표면):
- §1. 시작 — vault 파악 (log.md 5-10줄, index.md)
- §2. 4가지 명령 키워드 (save/ingest/query/lint)
- §3. 권한 — vault 내부 3개 영역 (content/_meta/log.md)
- §4. 저장 결정 — 4가지 신호
- §5. 페이지 작성 규약 (8종 type, wikilink, frontmatter)
- §6. 작업 절차 (사람 보고 형식)
- §7. 하지 말 것 — 도메인 가정 ❌, type 8종 외 ❌, 외부 write ❌
- §8. 다음 단계 (LLM Wiki +α 가이드, Karpathy 원본 참조)

**제거된 Raven 내부 정책 (사용자 노출 ❌)**:
- Tier 1 leak 정책 (lint #14 자동 검사)
- OPERATIONS.md / agent/* / raven-policy.md 복사 금지
- vendor 예시 (Codex / Claude / Cursor / agy)
- raven 패키지 내부 안전망 언급

### 1-2. 기존 vault 동기화

`~/Raven/harumoa/_meta/system/AGENTS.md` — 새 템플릿으로 갱신 (백업: `.bak`)
`~/Raven/raven-dev/_meta/system/AGENTS.md` — 새 템플릿으로 갱신 (백업: `.bak`)

→ Lite bootstrap 정책 ("기존 파일은 절대 덮어쓰지 않음")을 한 번 **명시적으로 갱신** (v0.7.1 changelog에서 추적 가능).

### 1-3. `tests/test_v0_7_1_lite_bootstrap_surface.py` (신규, 5 tests)

회귀 가드:
1. Lite bootstrap AGENTS.md에 vendor 예시 0회 (Codex/Claude/Cursor/Antigravity/agy)
2. Lite bootstrap AGENTS.md에 도구 내부 정책 0회 (Tier 1 leak / raven 운영 코드 / OPERATIONS / raven-policy / vendor에 종속)
3. Lite bootstrap AGENTS.md는 vault 사용자 표면 (저장 신호, 권한, 페이지 작성, type 8종)
4. Lite bootstrap AGENTS.md 헤더 = "Vault User Guide" (이전 "Vault Agent Operations" ❌)
5. 기존 vault (harumoa, raven-dev) AGENTS.md 동기화 확인

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **456 passed, 1 skipped** (v0.7.0: 451 → v0.7.1: 456, +5) |
| test_v0_7_1_lite_bootstrap_surface.py | **5 passed** (신규) |
| 기존 vault 동기화 | ✅ harumoa + raven-dev (백업 .bak 보존) |
| 사용자 vault 데이터 write 정책 | ⚠️ Lite bootstrap 4종은 raven이 만든 거라 정책 외 (사용자 vault 자체는 read-only 유지) |

## 3. 의도

사용자 정정 핵심:
> "사용자는 Raven이 정의한 최소한의 vault 구조 내에서 자기 프로덕트를 알아서 문서화하고 폴더링하고 가꾸는 것. Raven의 세부 로직이나 구현사항을 알 필요 없음. 알아야 할 건 명확히 Raven이 제공하는 도구로써의 표면일 뿐."

→ Lite bootstrap AGENTS.md의 **본질**: 도구 사용자에게 "Raven이 정의한 최소한의 vault 구조" + "어떻게 사용" 알려주는 표면.

→ Lite bootstrap의 다른 3종 (SCHEMA.md, RULES.md, log.md) 도 비슷한 검토 필요 (다음 phase 후보).

## 4. 두 AGENTS.md의 명확한 경계 (v0.7.1+)

| 파일 | 대상 | 톤 | 위치 |
|---|---|---|---|
| **`raven/core/templates/system/AGENTS.md`** (Lite bootstrap) | vault 사용자 (사람/에이전트) | "Vault User Guide" — 도구 표면 | raven 패키지 → `~/Raven/<vault>/_meta/system/AGENTS.md` 자동 복사 |
| **`AGENTS.md`** (Raven 레포 자체) | Raven 개발팀 에이전트 | "Raven — Agent Operations" — Raven 코드베이스 운영 | `~/Desktop/Dev/Project/Raven/AGENTS.md` |

→ **혼용 ❌**. Lite bootstrap 사용자 = 도구 사용자 (vault 작업자). Raven 레포 사용자 = Raven 코드베이스 개발자.

## 5. 다음 단계

- **v0.7.2 (후보)**: Lite bootstrap 4종 전체 검토 (SCHEMA.md, RULES.md, log.md 동일 기준)
- **v0.7.3 (후보)**: Raven 레포의 `AGENTS.md` §4 Lite Bootstrap 섹션 — Lite 4종이 사용자 표면으로 재편됨을 반영
- **v0.8.0 (후보)**: 신규 사용자가 처음 보는 순서 — README → Lite bootstrap 4종 → docs/vault-patterns.md

## 6. 호환성

- ✅ **v0.7.0 vault**: AGENTS.md가 raven 패키지 템플릿 동기화 — 100% 호환 (Lite bootstrap 정책)
- ✅ **Lite bootstrap 4종 자동 복사**: 변경 없음 (`_bootstrap_lite()` 호출 시 새 템플릿 적용)
- ✅ **harumoa / raven-dev vault**: 동기화 완료 (.bak 백업 보존)
- ⚠️ **사용자 편집 보호**: AGENTS.md 사용자가 편집했다면 .bak으로 복구 가능 — 필요 시 `cp .bak AGENTS.md`