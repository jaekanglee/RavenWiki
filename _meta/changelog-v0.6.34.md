# raven v0.6.34 — agent/README.md 외부 위임 backend 한 줄 가이드 (vendor-neutral)

> **핵심**: subagent 분석에서 제안한 "raven-delegate.md 톤 한 줄 추가"는 실제 파일 없음. `agent/README.md` 가 LLM 에이전트 진입점 — 거기에 외부 LLM cross-check 가이드 추가.
>
> ⚠️ **v0.6.36 재정렬 노트**: 본 changelog은 역사 보존을 위해 vendor명을 그대로 유지하지만, 라이브 정책 문서(agent/README.md)와 회귀 가드(`tests/test_external_delegation_contract.py`)는 **v0.6.36에서 vendor-neutral로 재정렬됨** — "어떤 LLM이 와도 동일하게 다룬다" (LLM Wiki north star).

릴리스 일자: 2026-06-30
이전: v0.6.33 (lint #14 tier_integrity)

---

## 한 줄 요약

`raven/core/templates/agent/README.md` 끝에 "외부 위임 backend (선택, v0.6.34+)" 섹션 추가. 외부 LLM CLI 호출 가이드 + wrap-up fix 침습 금지 + 사용자 명시 시점 명시.

## 1. 변경 사항

### 1-1. `raven/core/templates/agent/README.md` (+13 lines)

신규 섹션 (v0.6.36 재정렬 전, vendor 표기 포함):
- **외부 LLM CLI** — JSON envelope / plain text / markdown 모두 vendor 구현에 따름
- **기본값은 직접 작업**
- **사용자 명시 / cross-check 시점에만** 외부 LLM 호출
- **wrap-up 단계 fix 침습 금지** — 분석만, 패치는 orchestrator에게 보고

### 1-2. `tests/test_external_delegation_contract.py` (신규, 3 tests)

회귀 가드 (v0.6.36 재정렬 후 vendor-neutral 키워드로 변경됨):
1. agent/README.md에 vendor-neutral 외부 LLM cross-check 키워드
2. wrap-up fix 침습 금지 톤
3. 사용자 명시 또는 cross-check 트리거
4. (v0.6.36+) 외부 위임 섹션에 vendor명 직접 표기 ❌

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **414 passed** (v0.6.33: 411 → v0.6.34: 414, +3) |
| vitest | **20 files / 102 tests + 1 skip** (회귀 0) |
| tsc -b | **exit 0** |

## 3. 의도

이 가이드는 **subagent (Codex/Antigravity) 호출 시 톤 컨벤션**:
- 기본 = 직접 작업
- 사용자 명시 OR Gemini cross-check 시점에만 다른 backend 시도
- wrap-up 단계에서 fix 침습 ❌ (분석만 → orchestrator에 보고)

## 4. 후속 작업 (메모리 §next session)

5. **Worker result 어댑터** (Codex JSON + Antigravity plain text 통합 회계)
6. **Tier 1 leak hook** (git pre-commit — Task 3 lint #14를 PR 단계에서 차단)