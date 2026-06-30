# raven v0.7.0 — Karpathy LLM Wiki +α 본격 도입 가이드 (`docs/vault-patterns.md`)

> **핵심**: v0.6.37~v0.6.40의 정책 layer 옵션화 + VaultMeta/AgentScope 확장 완료.
> v0.7.0은 마지막 phase — **사용자 가이드**. `docs/vault-patterns.md` 신규 — LLM Wiki 패턴을 vault에서 켜고 끄는 법, opt-in 정책, 시나리오 모음, Karpathy 원본과의 정직한 거리.

릴리스 일자: 2026-06-30
이전: v0.6.40 (AgentScope resource scope)

---

## 한 줄 요약

`docs/vault-patterns.md` 신규 — Karpathy LLM Wiki의 3-Layer (raw/wiki/schema) + log.md 패턴을 Raven vault에서 +α로 활성화하는 사용자 가이드. 10섹션, 280줄, opt-in / 비활성화 / 다시 켜기 시나리오 포함.

## 1. 변경 사항

### 1-1. `docs/vault-patterns.md` (신규, 280 lines)

10개 섹션:
1. Quick check — 이 패턴이 필요한가? (4가지 질문)
2. 활성화 방법 3가지 (features flag / 폴더 자동 감지 / 안 켜기)
3. raw/ 패턴 (immutable source)
4. log.md 패턴 (append-only work log)
5. _meta/agents/ 패턴 (에이전트 행동 지침)
6. compounding knowledge (3-Layer 통합)
7. 사용자 시나리오 모음 (4가지)
8. 비활성화 / 다시 켜기 (lock-in ❌)
9. 다음 패턴 후보 (v0.7.x+)
10. Karpathy 원본과의 정직한 거리

### 1-2. `_meta/decisions/adr-2026-06-30-llm-wiki-plus-alpha.md` (신규, ADR)

큰 결정 ADR — LLM Wiki 패턴 +α 도입 결정 (옵션화, opt-in, 사용자 자유).
- 배경: v0.6.31~36의 강한 "LLM Wiki self-host" 톤 → 사용자 정정 (north star 재정렬)
- 결정: LLM Wiki는 **영감/출발점**이며 **vault 안에서 +α로 opt-in**
- trade-off: 단순화 vs 기능 (사용자 자유 우선)
- 영향: v0.6.37~v0.6.40 4개 릴리스로 점진 옵션화

### 1-3. README.md + AGENTS.md link 추가

- README "관련 문서" 섹션에 `docs/vault-patterns.md` 링크
- AGENTS.md "참조" 섹션에 추가

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **451 passed, 1 skipped** (변경 없음, 문서만) |
| 신규 파일 | docs/vault-patterns.md, _meta/decisions/adr-2026-06-30-llm-wiki-plus-alpha.md |
| 변경 파일 | README.md, AGENTS.md (link 추가만) |

## 3. 의도 (전체 v0.6.37~v0.7.0 흐름 요약)

| 릴리스 | 핵심 |
|---|---|
| v0.6.37 | North Star 재정렬 ("Obsidian 1차 + LLM Wiki +α 옵션") |
| v0.6.38 | Lite bootstrap 프로파일화 (basic / llm-wiki) |
| v0.6.39 | VaultMeta 확장 (allow_tier1_leak, features) + Tier 1 leak lint 옵션화 |
| v0.6.40 | AgentScope resource scope (allowed_paths / deny_paths) |
| **v0.7.0** | **사용자 가이드 (docs/vault-patterns.md) + ADR** |

→ 정책 layer 단순화 흐름 완료. **도구로서의 Raven** — 사람 1차, vault 자유, LLM Wiki는 옵션.

## 4. 사용자 진입점

### 신규 사용자
1. `README.md` 읽기 (Obsidian 대체제 정체성)
2. `raven vault create personal ~/Raven/personal --profile basic` (WELCOME.md 1장)
3. `docs/vault-patterns.md` 참고 (LLM Wiki 패턴 원할 때)

### LLM Wiki 사용자
1. `raven vault create harumoa ~/Raven/harumoa --profile llm-wiki` (Lite bootstrap)
2. `docs/vault-patterns.md` 전체 읽기
3. features.llm_wiki 활성화 (필요 시)

### 고급 사용자 (에이전트 협업)
1. `AgentScope`의 `allowed_paths` / `deny_paths` 사용 (v0.6.40)
2. `docs/vault-patterns.md` §6 시나리오 D 참조

## 5. 다음 단계 (v0.7.x+ 후보)

- **compiled/ claims/ 패턴** 자동 인식 (features.complied_pages)
- **MCP 도구 확장** — raw/ 읽기 전용 도구
- **Watcher 확장** — raw/ 변경 감지 → 자동 compile 트리거
- **에이전트 어댑터 강화** — Journal auto-write (운영 자동화)

## 6. 호환성

- ✅ **v0.6.40 사용자**: 영향 없음 (문서만 추가)
- ✅ **기존 vault**: `docs/` 디렉토리는 raven 코드베이스 — 사용자 vault와 분리
- ✅ **CLI/API/Dashboard/MCP**: 변경 없음