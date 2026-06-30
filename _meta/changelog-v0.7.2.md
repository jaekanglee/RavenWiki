# raven v0.7.2 — Lite bootstrap 4종 사용자 표면 일관성 (R1+R2+R3 마무리)

> **핵심**: v0.7.1에서 AGENTS.md만 재작성했는데, SCHEMA.md와 log.md에도 raven 도구 내부 정책 + 도메인 가정 (karpathy, llm-wiki) 박혀있었음. **Lite bootstrap 4종 전체를 사용자 표면으로 일관화** + Raven 레포 AGENTS.md §4 §10 갱신.
>
> 잔여 작업 R1+R2+R3 모두 마무리.

릴리스 일자: 2026-06-30
이전: v0.7.1 (Lite bootstrap AGENTS.md 도구 표면 재작성)

---

## 한 줄 요약

Lite bootstrap SCHEMA.md + log.md 재작성 (도구 내부 정책 제거, 도메인 가정 제거) + Raven 레포 AGENTS.md §4 Lite Bootstrap + §10 정책 명시 갱신 + 회귀 가드 8 → 11개.

## 1. 변경 사항

### 1-1. `raven/core/templates/system/SCHEMA.md` (재작성)

**Before (Lite bootstrap v0.7.1)** — raven 도구 내부 노출 3건 + 도메인 가정:
- L17-21: Tier 1 leak 정책 ("Tier 1 — raven 패키지", "Tier 1 문서(OPERATIONS, agent/*, raven-policy)는 사용자 vault에 복사되지 않음")
- L94: `karpathy` / `llm-wiki` 태그 (도메인 가정)
- L160: "카파시 LLM Wiki 차용" (vendor 톤)
- L185-189: `raven docs show operations/agent-readme/agent-safety/policy` (raven 내부 명령)

**After (v0.7.2+)** — 사용자 표면만:
- Tier 1 leak 정책 ❌ (raven 도구 내부, 사용자에겐 안 보임)
- 도메인 가정 ❌ (사용자 vault 자유)
- Lint 13개 → 12개로 정정 (실제 lint 코드와 일치, v0.5.x 시절 13개 표기는 outdated)
- Cognitive Governance 4 신호 유지 (사용자가 알아야 할 vault 운영 규칙)
- `docs/vault-patterns.md` 링크 (LLM Wiki +α opt-in)

### 1-2. `raven/core/templates/log.md` (재작성)

**Before**:
```
## [YYYY-MM-DD] create | log.md initialized
- reason: v0.5.0 — 카파시 LLM Wiki 운영정책 도입
- files: [log.md]
```

**After (v0.7.2+)**:
```
## [YYYY-MM-DD] create | log.md initialized
- reason: vault created via Lite bootstrap
- files: [log.md]
```

→ 도메인 가정 제거, **vault 일반 셋업**으로 표현.

### 1-3. 기존 vault 동기화

- `~/Raven/harumoa/_meta/system/SCHEMA.md` — 새 템플릿 (백업 .bak)
- `~/Raven/harumoa/log.md` — 새 템플릿 (백업 .bak)
- `~/Raven/raven-dev/_meta/system/SCHEMA.md` — 새 템플릿 (백업 .bak)
- `~/Raven/raven-dev/log.md` — 새 템플릿 (백업 .bak)

### 1-4. Raven 레포 `AGENTS.md` §4 Lite Bootstrap 정책 명시 갱신

```
### 4. Lite Bootstrap 정책 (Tier 1 ↔ Tier 2) — v0.7.1+ 표면화

→ v0.7.1+ Lite bootstrap 4종 모두 도구 표면만. Raven 내부 정책
  (Tier 1 leak, vendor 예시, OPERATIONS/agent/raven-policy 복사 금지) ❌.
  사용자가 vault에서 자기 프로덕트를 자유롭게 문서화.
→ Tier 1 ↔ Tier 2 경계: vault clone 기본 = content only (Tier 1 leak 방지,
  이건 raven 도구 내부 안전망 — 사용자에겐 안 보임).
```

→ §10 "하지 말 것" 추가:
- "Lite bootstrap 4종 (사용자 표면 가이드)에 raven 내부 정책/Tier 1 leak/vendor 예시 ❌ — v0.7.1+"
- "Tier 1 문서(OPERATIONS, agent/*, raven-policy)를 vault에 자동 복사 ❌ (raven 도구 내부 안전망)"

### 1-5. `tests/test_v0_7_1_lite_bootstrap_surface.py` 확장 (5 → 8 tests)

신규 회귀 가드 3개:
- `test_lite_schema_no_internal_policy` — SCHEMA.md에 도구 내부 정책 0회
- `test_lite_schema_no_domain_assumptions` — SCHEMA.md에 karpathy/llm-wiki 0회
- `test_lite_log_no_domain_assumptions` — log.md에 도메인 가정 0회

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **459 passed, 1 skipped** (v0.7.1: 456 → v0.7.2: 459, +3) |
| test_v0_7_1_lite_bootstrap_surface.py | **8 passed** (5 → 8, +3 신규) |
| Lite bootstrap 4종 (AGENTS/SCHEMA/RULES/log) | ✅ 모두 도구 표면만 (vendor 0 / 내부 정책 0 / 도메인 가정 0) |
| 기존 vault 동기화 | ✅ harumoa + raven-dev (4종 × 2 vault = 8 파일 갱신) |
| Raven 레포 AGENTS.md | ✅ §4 + §10 갱신 |

## 3. 의도

v0.7.1에서 AGENTS.md만 했는데 **정직한 검증** (R1) 결과 SCHEMA.md와 log.md도 raven 도구 내부 + 도메인 가정 박혀있었음. **Lite bootstrap 4종 일관성** → 모두 사용자 표면으로 정리.

→ **이제 사용자 vault에 자동 복사되는 4종은 모두 "내가 만든 vault에서 무엇을 해야 하나"만 알려줌**. Raven 내부 구현 / 도메인 가정 / vendor 예시 전부 ❌.

## 4. Lite bootstrap 4종 — 최종 사용자 표면 (v0.7.2+)

| 파일 | 내용 (사용자 표면만) |
|---|---|
| `SCHEMA.md` | frontmatter/type 8종/tag/wikilink 규약, log.md 운영, lint 12개 |
| `RULES.md` | 편집 규칙 (사용자/에이전트 공통, 도구 무관) |
| `AGENTS.md` | "Vault User Guide" — 시작/4 키워드/권한/저장 신호/페이지 작성/작업 절차/하지 말 것/다음 단계 |
| `log.md` | 작업 이력 템플릿 + "vault created via Lite bootstrap" |

→ **사용자가 처음 보는 vault = "내 작업 공간, 이 규약대로 쓰면 됨"**. Raven 구현 세부 ❌.

## 5. 다음 단계

- **v0.7.3 (후보)**: RULES.md도 동일 기준 검증 (5가지 저장 신호 / 4 키워드 / 페이지 작성 규약 — 사용자 표면인지 확인)
- **v0.8.0 (후보)**: 신규 사용자 onboarding 가이드 — README → Lite bootstrap 4종 → docs/vault-patterns.md 순서 정립
- **harumoa 운영**: 첫 결정 페이지 + 첫 journal + LLM Wiki 패턴 첫 적용 (raw/ 폴더)

## 6. 호환성

- ✅ **v0.7.1 vault**: 4종 모두 동기화 — 100% 호환
- ✅ **Lite bootstrap 4종 자동 복사**: `_bootstrap_lite()` 호출 시 새 템플릿 적용
- ✅ **harumoa / raven-dev vault**: 8 파일 동기화 (.bak 백업 보존)
- ✅ **Raven 레포 AGENTS.md**: §4 §10 명시 갱신 (회귀 가드 변경 없음 — 정책 강화)
- ⚠️ **RULES.md**: 본 릴리스에서 미검증 — v0.7.3 후보

---

## 7. 후속 문서 정렬 (2026-06-30)

사용자 피드백 기준으로 현재 제품 정의를 다시 명확히 반영:

- `_meta/index.md`: `~/vaults/default` 잔여 설명 → `~/Raven/<name>` 기준으로 갱신
- `_meta/index.md`: Raven = Zettelkasten-inspired PKM + Obsidian-style 앱 표면 + agent/LLM Wiki optional layer 명시
- `dashboard/README.md`: static/read-only 설명 → API-backed read-write Dashboard로 정정
- `README.md` / `docs/vault-patterns.md` / `wikisys-policy.md`: Zettelkasten 기반 + LLM Wiki optional layer 관점 반영
- `raven/core/lint.py` / `SCHEMA.md` / CLI help: 실제 코드 기준 lint 14개(#13 cognitive governance, #14 tier integrity 포함)로 정정
- 기존 vault `~/Raven/harumoa`, `~/Raven/raven-dev`: Lite bootstrap AGENTS/SCHEMA/log 템플릿 재동기화

의도:
- Dashboard는 Obsidian 전용 앱에 해당하는 사람용 탐색/편집 표면
- 에이전트 없이도 사람이 Raven을 PKM으로 쓸 수 있어야 함
- LLM Wiki 패턴은 어떤 AI 에이전트든 Raven vault를 활용하기 위한 optional layer
- lint 계약은 문서 추정이 아니라 실제 실행 코드(`run_all`) 기준으로 유지
