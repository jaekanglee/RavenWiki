# ADR: Karpathy LLM Wiki 패턴 +α 도입 (옵션화, opt-in)

> **날짜**: 2026-06-30
> **상태**: ✅ Accepted
> **관련 릴리스**: v0.6.37~v0.7.0
> **의사결정자**: 사용자 (삐질 리)

---

## 1. 배경 (Context)

Raven은 v0.6.31부터 "Karpathy LLM Wiki 패턴의 self-host 구현체" 톤으로 north star가 박혀 있었음. README/AGENTS.md/wikisys-policy.md/changelog v0.6.31~36에서 강한 LLM Wiki 강조.

사용자 정정 (2026-06-30):
> "사실상 그럼 llm위키는 상관없이 옵시디언 대체제를 자체적으로 만들 뿐이네? 레이븐은?"
> "기본은 1. 옵시디언대체제 2. llm 위키 개념 적용을 선택적으로 추가 할수있게 하자"
> "결국엔 모드 개념이 맞았네. 근데 그렇다거 볼트 스코프 전체를 모드적용하기보다. 약간 볼트 안에 추가할 플러스 알파 느낌?"

→ 사용자가 Raven의 본질은 **Obsidian 대체 자체 구현체**라고 재정립. LLM Wiki는 **vault 안에서 +α로 선택적 도입**.

## 2. 결정 (Decision)

**Raven = Obsidian-style 마크다운 PKM 도구.** LLM Wiki 패턴은 **vault 내 opt-in +α layer**.

### 구체적 결정

1. **North Star 재정렬** (v0.6.37)
   - "Karpathy LLM Wiki self-host 구현체" → "사람 1차 Obsidian 대체체 + LLM Wiki +α 옵션"
   - README/AGENTS.md/wikisys-policy.md 4곳 마이그레이션

2. **Lite bootstrap 프로파일화** (v0.6.38)
   - `--profile basic`: WELCOME.md 1장만 (사람 1차)
   - `--profile llm-wiki`: SCHEMA+RULES+AGENTS+log.md (LLM Wiki 패턴)
   - 기본값 = `llm-wiki` (v0.6.37 호환)

3. **VaultMeta 확장** (v0.6.39)
   - `allow_tier1_leak: bool` — Tier 1 leak lint 옵트인
   - `features: tuple` — feature flag (예: `{"llm_wiki": True}`)
   - `mode` 필드는 손대지 않음 (이미 display-only metadata, 코드 분기 0건)

4. **Tier 1 leak lint 옵션화** (v0.6.39)
   - 기본 critical 유지 (안전망)
   - `allow_tier1_leak=True` 시 warning 강등

5. **AgentScope resource scope** (v0.6.40)
   - `allowed_paths` / `deny_paths` (glob pattern)
   - 빈 tuple = 현재 동작 (모든 경로 허용)
   - deny_paths 우선 (deny wins over allow)

6. **사용자 가이드** (v0.7.0)
   - `docs/vault-patterns.md` — LLM Wiki +α 도입 가이드
   - 활성화 방법 3가지, 패턴 3종, 시나리오 4가지, 비활성화 가능

## 3. Trade-off

### 단순화 vs 기능
- **단순화**: 정책 layer 다 제거 → 사용자 자유 극대화
- **기능**: tier leak safety + scope 격리 → 데이터 안전

→ **선택**: 옵션화 (기본 OFF, opt-in 시 ON). 안전망 유지 + 사용자 자유 양립.

### mode 필드 제거 vs 유지
- **제거**: 정책 layer 더 단순
- **유타**: 표시용 metadata로 강등 (코드 분기 0건 확인)

→ **선택**: 유지. 사용자가 기존 vault 그대로 사용 가능 (32+ 곳 호환).

### 강제 vs 자유
- **강제**: 모든 vault가 같은 패턴 (LLM Wiki 통일)
- **자유**: vault마다 다른 패턴 (사용자 결정)

→ **선택**: 자유. 사용자 north star 정직 반영.

## 4. 결과 (Consequences)

### 긍정
- ✅ 사용자 north star 정직 반영 ("vault 자유")
- ✅ 정책 layer 단순화 (4개 릴리스로 점진 옵션화)
- ✅ 데이터 안전망 유지 (Tier leak default critical, scope default allow)
- ✅ Karpathy LLM Wiki 패턴을 **원하는 사용자**가 그대로 활용 가능
- ✅ 옵트인 → 비활성화 자유 (lock-in ❌)

### 부정
- ❌ vault마다 다른 패턴 가능 → cross-vault 일관성 약화
- ❌ 신구 vault 정책 다름 → 신규 사용자 onboarding 가이드 필요
- ❌ Karpathy LLM Wiki 강제가 아님 → 멀티 에이전트 협업 표준화 약화

### 리스크
- ⚠️ VaultMeta `features` field 검증 부족 (v0.7.0+ 보강)
- ⚠️ raw/ 자동 감지 미구현 (v0.7.x+ 예정)

## 5. 대안 (Alternatives Considered)

### A. 정책 layer 다 제거 (단순화 최우선)
- 장점: 가장 단순, 사용자 자유 극대
- 단점: cross-vault 격리 사라짐 (multi-vault 사용자 위험)

→ **거절**. Antigravity 권고 (Antigravity 분석: "안전벨트는 사용자가 직접 해제")와 충돌.

### B. mode 필드 완전 제거
- 장점: 32+ 곳 단순화
- 단점: 기존 vault registry 호환 깨짐 (메모리 정책 §사용자: "메모리에 있다 = 가설, 작업 시작 (1) git log (2) source grep (3) 정책 read")

→ **거절**. v0.6.39에서 검증 결과 mode는 코드 분기 0건 → 유지가 안전.

### C. Lite bootstrap 그대로 (강제 4종 복사)
- 장점: 기존 동작 100% 보존
- 단점: 신규 사용자 cold start UX 문제 (Antigravity 분석)

→ **거절**. Antigravity 권고 채택 — basic profile 추가.

## 6. 영향 (Impact)

### 코드 변경
- 5개 릴리스 (v0.6.37~v0.7.0)
- 7개 신규 파일 (changelog 4 + plan + test_basic_profile + test_v0_6_39 + test_v0_6_40 + docs/vault-patterns)
- 13개 수정 파일 (vault.py, registry.py, lint.py, agent.py, cli, README, AGENTS, wikisys-policy, changelog 3, north_star_contract, external_delegation_contract)

### 사용자 영향
- 신규 vault 생성: `--profile basic` 옵션 (안 쓰면 v0.6.37과 동일)
- 기존 vault: 영향 없음 (VaultMeta 확장만, default 호환)
- 에이전트 adapter: `allowed_paths` / `deny_paths` 옵트인 (안 쓰면 현재 동작)

### 운영 영향
- 정책 layer 옵션화로 문서 일관성 ↑
- 데이터 안전망 유지 (Tier leak default critical)
- 사용자 자유 회복 (vault 구조/정책 사용자 결정)

## 7. 후속 작업

- [ ] VaultMeta `features` 검증 강화 (v0.7.x+)
- [ ] raw/ 자동 감지 (v0.7.x+ 예정)
- [ ] _meta/agents/ 자동 생성 (사용자 요청 시)
- [ ] MCP 도구 확장 (raw/ read-only 도구)

## 8. 참고 (References)

- Karpathy LLM Wiki gist (2026): `_meta/raw/articles/karpathy-llm-wiki-2026.md`
- 사용자 메시지 (2026-06-30, Telegram): 옵시디언 대체 + LLM Wiki +α
- Codex CLI 검토 (취합): v0.6.37 north star 재정렬안
- Antigravity CLI 검토 (취합): basic profile + cold start UX + Tier lint 옵션화
- changelog: v0.6.37 / v0.6.38 / v0.6.39 / v0.6.40 / v0.7.0
- docs: `docs/vault-patterns.md` (v0.7.0 신규)

## 9. 결론 (한 줄)

> **Raven은 Obsidian-style 자유 vault가 기본. LLM Wiki 패턴은 켜고 끄기 자유. 강제 ❌.**
> **도구로서의 Raven — 사람 1차, vault 자유, 정책은 vault 안에서.**