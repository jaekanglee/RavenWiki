# raven v0.5.5 — Lite bootstrap에 AGENTS.md 추가 (vault 운영자 규칙 상시)

> **핵심**: 기존 templates 패키지(`templates/ai-agent-wiki-1.0.0/`)의 "에이전트용 운영 가이드"를 vault 내부 `_meta/system/AGENTS.md`로 이동. Lite bootstrap 정책 그대로 유지 (Tier 1 ↔ Tier 2 경계).

릴리스 일자: 2026-06-27
이전: v0.5.4 (카파시 스킬 메커니즘 B + D)

---

## 한 줄 요약

**vault bootstrap 3종 → 4종.** `_meta/system/{SCHEMA,RULES,AGENTS}.md` + `log.md`. Lite 정책은 그대로, vendor-agnostic 에이전트 규칙은 vault에 박혀 다른 AI 도구가 와도 즉시 행동 가능.

---

## 1. 결정 배경

### 사용자 정정 (2026-06-27, Telegram)

> "내가 보기엔 그냥 니가 만든 템플릿은 ai한테 일회성으로 내가 프롬프트랑 파일 덤프줘야 알아서 vault에 적용하라고 해주는게 좋으려나. 아니면 vault 내부에 짱박아넣고 항상 존재하는 파일로 하는게 좋으려나"

→ **B안 (vault 내부 상시 파일)** 선택. 이유:
1. vault에 AGENTS.md 없으면 다른 AI 도구(Codex/Claude/Cursor)가 와도 "이 vault 어떻게 다뤄야 하지?" 모름
2. Lite bootstrap 정책의 정신 유지 — whitelist로 통제하면 Tier 1 ↔ Tier 2 경계 깨지지 않음
3. `meta sync --lite`로 raven 업그레이드 시 자동 갱신 가능 (1회성 템플릿은 이게 안 됨)

### 트레이드오프

| 후보 | 결정 |
|---|---|
| A안: 1회성 템플릿 (`templates/ai-agent-wiki-1.0.0/`) | ❌ 폐기 (사용자 결정) |
| **B안: vault 내부 상시 파일** | ✅ **v0.5.5 채택** |
| AGENTS.md가 Lite whitelist에 추가되는가? | ✅ 추가 (사람 + 에이전트 공통 규칙이라 Tier 2) |
| 기존 Tier 1 (OPERATIONS, agent/*, raven-policy) 정책 | ✅ 그대로 (raven 내부 운영 문서, vault 복사 ❌) |

---

## 2. 변경 사항

### 2.1 코드

| 파일 | 변경 |
|---|---|
| `raven/core/vault.py` | `_LITE_BOOTSTRAP_FILES`에 `("_meta/system/AGENTS.md",)` 추가. `_bootstrap_lite` docstring + `template_map` 갱신. `sync_meta(lite=True)` 분기에 AGENTS.md 추가. |
| `raven/core/templates/system/AGENTS.md` | **신규**. 8섹션 (read first / 4 keywords / 권한 / 4 저장 신호 / 작성 규약 / 작업 절차 / 하지 말 것 / 도구 vendor-agnostic). 4.9KB. |
| `raven/cli/__main__.py` | `vault create` 출력 메시지에 `AGENTS.md` 추가. `meta sync` docstring 갱신 (3종 → 4종). |
| `raven/api/server.py` | 변경 ❌ (이미 `bootstrapped: bool`로 추상화) |

### 2.2 테스트

| 파일 | 변경 |
|---|---|
| `tests/test_vault_create.py` | `test_bootstrap_copies_lite_templates`: AGENTS.md 파일 존재 + 내용 sanity. `test_sync_meta_lite_default` + `test_sync_meta_lite_no_op`: AGENTS.md 검증 추가. 파일 docstring 갱신 (3종 → 4종). |

### 2.3 문서/자산

| 파일 | 상태 |
|---|---|
| `templates/ai-agent-wiki-1.0.0/AGENTS.md` | **중복** (Lite 정책에 안 들어가 있었음) — 사용자 결정 보류: A 삭제 / B _archive / C deprecate 헤더만 |
| `_meta/changelog-v0.5.5.md` | **이 문서** |

---

## 3. Lite bootstrap 정책 (2-tier, v2026-06-26 → 2026-06-27 강화)

### Tier 1 — raven 패키지 (vault 복사 ❌)

```
raven-internal 운영 문서:
- OPERATIONS.md   → raven CLI/API 운영 매뉴얼
- agent/*         → raven LLM agent 행동 매뉴얼 (README/TOOLS/WORKFLOW/SAFETY)
- raven-policy.md → raven 내부 정책
```

접근: `raven docs show <topic>` (CLI 진입점)

### Tier 2 — user vault (Lite bootstrap ✅)

```
사용자 + 에이전트 공통 운영 문서:
- _meta/system/SCHEMA.md   → vault schema (frontmatter/type/tag/wikilink)
- _meta/system/RULES.md    → 편집 5규칙
- _meta/system/AGENTS.md   → 🆕 vault 운영자 규칙 (사람+에이전트 공통, vendor-agnostic)
- log.md                   → 작업 이력 (append-only)
```

**AGENTS.md가 Tier 2인 이유**: 사람 운영자와 모든 AI 도구(Codex/Claude/Cursor/MCP/자동화)가 **같이 읽는 규칙**. Tier 1은 raven 코드 내부 운영 정책이라 분리.

---

## 4. AGENTS.md 설계 (8섹션)

| § | 제목 | 핵심 |
|---|---|---|
| 1 | 작업 시작 전 — 읽을 것 | `log.md` 5-10줄 + `index.md` |
| 2 | 4가지 명령 키워드 | save / ingest / query / lint (+ first-setup) |
| 3 | 권한 — vault 내부 3개 영역 | content/ (rw), _meta/ (read), log.md (append-only) |
| 4 | 저장 결정 — 4가지 신호 | 재사용/인수인계/결정근거/실패기록 (모두 아니오 = skip) |
| 5 | 페이지 작성 규약 요약 | frontmatter/type 8종/wikilink intent |
| 6 | 작업 절차 | log 읽기 → 분류 → 실행 → 보고 |
| 7 | 하지 말 것 | 도메인 가정 ❌ / 8종 외 타입 ❌ / .vault.json 직접 수정 ❌ |
| 8 | 다른 도구/AI 호출 | vendor-agnostic — 4 진입점 (CLI/API/MCP/Dashboard) |

---

## 5. 검증

```bash
$ PYTHONPATH=. scripts/.venv/bin/python -m pytest tests/ -q
252 passed, 1 warning in 2.85s
```

- ✅ Lite bootstrap 4종 복사 (신규 vault 생성 시)
- ✅ Lite sync 4종 (기존 vault 보강 시)
- ✅ Tier 1 정책 무손상 (OPERATIONS, agent/*, raven-policy는 vault에 안 들어감)
- ✅ AGENTS.md 내용 sanity (제목 + first-setup 키워드 + vendor-agnostic)
- ✅ 252개 테스트 회귀 0

---

## 6. 사용자 결정 완료

`templates/ai-agent-wiki-1.0.0/` (1회성 템플릿 패키지) → **B안 채택 (2026-06-27)**:

```bash
git mv templates/ai-agent-wiki-1.0.0/ _deprecated/ai-agent-wiki-1.0.0/
```

- ✅ git history 보존 (rename 감지됨)
- ✅ 정책 정렬 신호 (Tier 1 ↔ Tier 2 경계)
- ✅ Lite bootstrap에 이미 통합된 vault용 AGENTS.md와 역할 분리
  - `templates/.../AGENTS.md` (1회성, vendor 패키지 의도) → deprecated
  - `raven/core/templates/system/AGENTS.md` (Lite, vault 상시) → 활성

→ v0.5.5에서 의도된 정책 경계 일치, 향후 vendor 패키지 재가공 시 `_deprecated/`에서 복원 가능.

---

## 7. 다음 사이클 후보

- `templates/ai-agent-wiki-1.0.0/` 처리 결정 (6번)
- Dashboard `meta sync` 버튼이 AGENTS.md도 갱신하는지 UX 확인
- v0.5.6: vault 생성 시 첫 페이지 템플릿 (옵션, YAGNI 신중)