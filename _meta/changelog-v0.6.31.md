# raven v0.6.31 — North Star 한 줄 선언 (README + wikisys-policy.md)

> **핵심**: Karpathy LLM Wiki 본질을 Raven README + wikisys-policy.md에 정면으로 박음. 모든 운영 결정의 자석. 사용자가 의도한 "LLM Wiki에 입각한 Raven 발전"의 첫 단계.

릴리스 일자: 2026-06-30
이전: v0.6.30 (Button pill)

---

## 한 줄 요약

Karpathy LLM Wiki의 north star 한 줄 ("컴파일 후 reuse, 매번 재구성 ❌")을 README 첫 페이지 + wikisys-policy.md 운영 정책 문서 첫머리에 추가. 회귀 가드 7건 (Python).

## 1. 변경 사항

### 1-1. `README.md` (+7 lines)

description 직후에 `## North Star` 섹션 추가:
> "LLM의 휘발성 메모리를 git-tracked 영속 markdown으로 변환해, 매 세션 재구성하지 않고 compounding knowledge를 누적한다."
> — Karpathy LLM Wiki (2026) 패턴의 self-host 구현체. 분업: 사람은 source curate + 방향 결정, 에이전트는 compile / cross-reference / lint / consistency 유지. **컴파일 후 reuse, 매번 재구성 ❌.**

### 1-2. `raven/core/templates/wikisys-policy.md` (+7 lines)

vault 운영 정책 문서 첫머리에 동일 패턴의 `## North Star` 섹션 추가. vault 사용자에게는 `raven sync_meta(full=True, force=True)` 시 반영.

### 1-3. `tests/test_north_star_contract.py` (신규, 7 tests)

회귀 가드:
1. README `## North Star` 헤더
2. README `Karpathy LLM Wiki (2026)` 인용
3. README `compounding knowledge` 문구
4. README `컴파일 후 reuse` + `매번 재구성`
5. wikisys-policy.md `## North Star` 헤더
6. wikisys-policy.md `컴파일 후 reuse`
7. 분업 (사람 + 에이전트 + compile) 명시

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **404 passed** (v0.6.30: 397 → v0.6.31: 404, +7) |
| vitest | **20 files / 102 tests + 1 skip** (회귀 0) |
| tsc -b | **exit 0** |

## 3. 의미

이 north star 한 줄은 **모든 운영 결정의 자석** 역할:
- 새 기능 추가 시: "이게 compounding knowledge를 누적하는가? 컴파일 후 reuse를 돕는가?"
- lint 항목 추가 시: "이게 카파시 본질을 강화하는가? 매번 재구성을 줄이는가?"
- 다중 에이전트 write 정책 시: "single-agent 가정의 Karpathy 본질을 깨지 않는가?"

## 4. 후속 작업 (메모리 §next session)

2. `scripts/watcher.py` 자동 워크플로우 완성 (watch → build → lint → log)
3. Raven 본질 회귀 가드 (lint가 Karpathy 본질 준수 검증)
4. `raven-delegate.md` 톤 한 줄 추가 (Antigravity 가이드)
5. Worker result 어댑터 (Codex JSON + Antigravity plain text 통합)
6. Tier 1 leak 검증 hook