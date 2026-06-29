# raven v0.6.35 — root AGENTS.md 보강 (North Star + Audience 라우팅 + 인덱스)

> **핵심**: 사용자 보강 요청 (2026-06-30) — "Raven 루트 레포 자체의 AGENTS.md와 연관 개발문서". root AGENTS.md가 3 audience (사람/개발팀/LLM agent) 구분 없이 stale (2026-06-27) 였던 것 보강.

릴리스 일자: 2026-06-30
이전: v0.6.34 (agent/README.md 외부 위임)

---

## 한 줄 요약

`AGENTS.md` 3개 섹션 추가 — §0.5 North Star, §4.5 Audience 라우팅 표, §14 `_meta/` 인덱스 표. frontmatter `updated: 2026-06-30`. 5개 회귀 가드 + North Star 계약 contract.

## 1. 변경 사항

### 1-1. `AGENTS.md` (+54 lines)

| 섹션 | 내용 |
|---|---|
| frontmatter | `updated: 2026-06-27` → `2026-06-30` |
| **§0.5 North Star** | README/wikisys-policy.md 와 동일 한 줄 — "compounding knowledge" + "이 레포는 Karpathy LLM Wiki (2026) 패턴의 self-host 구현체" |
| **§1.4** | `_meta/index.md` (코드베이스 wiki 카탈로그) — 신규 항목 |
| **§4.5 Audience 라우팅 표** | 3 독자 (사람/개발팀/LLM agent) → 3 시작 문서 매핑. **"당신(=개발팀 agent)이 agent/* 읽을 필요 없음"** 명시 |
| **§14 인덱스 표** | `_meta/` SOT 10개 파일 매핑 + 신규 2개 (`raven-architecture.md`, `llm-wiki-scenario.md`) — 별도 패치로 |

### 1-2. `tests/test_root_agents_md_contract.py` (신규, 5 tests)

회귀 가드:
1. frontmatter `updated >= 2026-06-30`
2. §0.5 North Star 키워드 (compounding knowledge, Karpathy LLM Wiki)
3. §4.5 audience 표 (3 독자 행)
4. §14 인덱스 표 (SCHEMA/RULES/decisions/adr-/ai-roadmap/raven-architecture)
5. §10 force-push ❌ 회귀 (보존 확인)

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **419 passed** (v0.6.34: 414 → v0.6.35: 419, +5) |
| vitest | **20 files / 102 tests + 1 skip** (회귀 0) |
| tsc -b | **exit 0** |

## 3. 2-Track Cross-Review 결과 반영

이 패치는 사용자 보강 요청 2개 중 **Track 1 (AGENTS.md + 연관 개발문서)** 응답:

- **Track 1 ✅** (이 커밋): root AGENTS.md 보강 + 회귀 가드
- **Track 2 ⏳ (별도 검토)**: LLM Wiki 시나리오 walkthrough + AI agent 첨부 문서 셋. → `_meta/llm-wiki-scenario.md` 신규 작성 (P2 우선순위)

## 4. 후속 작업 (메모리 §next session)

- `_meta/raven-architecture.md` 신규 (M2 4-Layer 현행) — `_meta/index.md` 가 가리키는 깨진 링크 해소
- `_meta/llm-wiki-scenario.md` 신규 — "vault 만들고 → agent 4-file 첨부 → write → log → 4-pass 보고" 패턴 (Track 2 응답)
- `_meta/index.md` 갱신 (stale 해소)
- README.md "관련 문서" 슬림화 (3개 핵심만)