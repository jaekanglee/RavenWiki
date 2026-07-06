---
title: Raven Code Review 패치 계획 — v0.7.47~68 위배 9건 + 정책 § 갱신 3건
created: 2026-07-06
type: rule
tags: [patch-plan, code-review, v0.7.69, north-star]
audience: agent
confidence: high
status: draft (Claude Code 검토 대기)
sources:
  - 51-commit 코드리뷰 결과 (8c8113f..HEAD, 2026-07-06)
  - AGENTS.md §0.5 North Star
  - AGENTS.md §7 raw/ 정책 (v0.7.50+)
  - AGENTS.md §10 금지
  - AGENTS.md §14 docs/ 컨벤션
---

# Raven Code Review 패치 계획

> **목적**: 2026-07-06 51-commit 코드리뷰에서 발견된 정책 위배 9건 + 정책 § 자체 갱신 필요 3건을 어떻게 패치할지.
> **대상**: v0.7.69 patch release (또는 다음 minor)
> **검토**: Claude Code CLI (의견 검토 후 사용자 결정)

---

## 0. 우선순위 매트릭스

| P | 정의 | 이번 패치 대상 |
|---|---|---|
| **P0** | North Star / 사용자 안전 / 정책 위반 | 4건 |
| **P1** | 정책 자체 모호함 / 사용자 명명 규칙 위반 | 4건 |
| **P2** | 정책 § 자체 갱신 / 미래 재발 방지 | 3건 |
| **P3** | housekeeping (cleanup) | 1건 |

---

## 1. P0 패치 — 즉시 처리 (4건)

### P0-1: 9cd586e — Dashboard raw/ panel writeRaw/deleteRaw 제거
- **정책**: AGENTS.md §7 raw/ (사람 1차 운영, 에이전트 read-only)
- **현황**: `dashboard/src/lib/api.ts` 90줄에 writeRaw/deleteRaw 존재, `routes/RawPanel.tsx`에 editor/write UI 구현
- **옵션**:
  - (a) **전면 제거** — raw/ panel = viewer only, 사람 운영자는 OS 파일관리자/CLI 사용 (가장 안전, 정책 완전 정합)
  - (b) **사람 운영자 가드 추가** — `actor == 'user'`일 때만 write UI 노출 (에이전트 read-only 유지) (정책 정합 + UX 유지)
  - (c) **`actor` 헤더 기반으로 API 자체 거부** — read-only 강제 (UI/API 레벨 모두)
- **권장**: **(b)** — Dashboard UX는 유지하되, actor 기반 가드. v0.7.50 raw/ 정책 의도 ("사람 1차 운영")와 정합
- **작업 범위**:
  - `dashboard/src/routes/RawPanel.tsx` — write UI 컴포넌트 actor 체크
  - `dashboard/src/lib/api.ts` — writeRaw/deleteRaw 호출 시 actor 강제
  - `raven/api/server.py` — raw/ write 엔드포인트에 actor 검증
  - 회귀 테스트 1개 (agent actor 거부)
- **리스크**: 사람 운영자가 CLI 외에 Dashboard에서 못 쓰면 약간 불편 — 그러나 §7 정책 그대로

### P0-2: 817e2a2 — SCHEMA.md `index` type 추가 제거
- **정책**: AGENTS.md §10 "SCHEMA 9종 외 type 정의 ❌"
- **현황**: `raven/core/templates/system/SCHEMA.md`가 9종 → 10종 (`index` 추가). `raven/core/contracts.py:436` `valid_types`도 영향 받을 가능성. 카탈로그는 `content/_index/{type}.md` 자동 생성으로 변경됨.
- **옵션**:
  - (a) **SCHEMA.md에서 `index` 제거, 카탈로그 자동 생성은 별도 메커니즘** (frontmatter 없이 자동 생성, type 미사용)
  - (b) **`index` type 정식 승격** — ADR 작성 + 사용자 승인 후 9종 → 10종 (§10 금칙 우회 정식 절차)
  - (c) **frontmatter 없이 content/_index/ 폴더는 시스템 영역으로 격리** (type 검증 면제)
- **권장**: **(c)** — §10 9종 고수하면서 자동 카탈로그 폴더는 type 면제 (마치 `_meta/` 면제처럼). ADR 작성
- **작업 범위**:
  - `raven/core/templates/system/SCHEMA.md` — `index` type 라인 제거, 대신 `content/_index/` 시스템 영역 면제 규칙 추가
  - `raven/core/contracts.py:436` `valid_types` — 변경 없음 (이미 9종)
  - `raven/core/lint.py:90` `valid_types` — 변경 없음
  - ADR 작성: `_meta/decisions/adr-YYYY-MM-DD-content-index-folder-system-zone.md`
- **리스크**: 기존 카탈로그 동작 회귀 — 자동 인덱싱 깨질 가능성. 테스트 필요

### P0-3: faa099e — AGENTS.md §15.2 Hermes Constitution 인용 제거
- **정책**: AGENTS.md §10 Lite bootstrap leak 금지, §11 "도구 vendor에 종속되지 않습니다"
- **현황**: `AGENTS.md` §15.2 (RAG 평가 부문의 4원칙)가 `~/.hermes/SOUL.SHARE.md`/`SOUL.SHARE.CORE.md`의 Karpathy 4원칙을 "Hermes Constitution 투영"이라고 명시 인용
- **옵션**:
  - (a) **§15.2를 Raven 자체 원칙으로 재작성** — Karpathy 4원칙을 vendor-neutral하게 재진술 (Think Before / Surgical / Goal-Driven / Root-Cause). 출처 표기 = "Karpathy LLM Wiki 원칙" 정도
  - (b) **§15.2 통째로 삭제** — Karpathy 4원칙은 vault 사용자가 원하면 `docs/vault-patterns.md`에서 자기 책임으로 enable
  - (c) **`SOUL.SHARE.md` 일반 출처로 인정** — vendor 의존이 아니라 "참고 외부 문헌"으로 격하
- **권장**: **(a)** — Karpathy 4원칙 자체는 일반적으로 인정된 LLM 운영 원칙. Raven 자체 RAG 평가 4원칙으로 재진술. 출처 표기 X (Raven 내부 규약으로 흡수)
- **작업 범위**:
  - `AGENTS.md` §15.2 — 4원칙을 Raven 원칙으로 재작성 ("Constitution §4.①" 등 표기 제거)
  - `raven/core/templates/agent/PROJECT-WORKFLOW.md` §10 — Tier 2 vault 템플릿에는 이미 제거됨 확인 (ebcde83 자체 교정)
  - `_meta/changelog-v0.7.69.md` (또는 다음) — §15.2 자가 평가 기준 갱신 entry
- **리스크**: Karpathy 4원칙 자체는 유지되므로 RAG 품질 영향 없음. 단순 재진술

### P0-4: e75a7ee — commit 메시지 형식 + 묵시적 commit 사후 정당화
- **정책**: AGENTS.md §6.5 묵시적 commit 금지, §9 hotfix 정책 (silent failure)
- **현황**: commit 제목 `[Pause] MCP 문제 해결 중` — PlanNote 박혀있음. 실제 코드 변경은 있음 (86+25+50+30+24+78 lines). 의도는 MCP 멀티볼트 라우팅 (이후 다른 commit에서 완성됨)
- **옵션**:
  - (a) **commit 메시지 reword** — git history는 보존, message만 `[MCP] 멀티볼트 라우팅 (stage 1: cli.py register_tools + ADR)`로 갱신
  - (b) **squash** — e75a7ee + 후속 구현 commit들 1개로 합치기
  - (c) **두기** — history 보존, §6.5 정책 자체에 "PlanNote 형태 commit 허용" 명시 (정책 완화)
- **권장**: **(c) + (a)** — 정책은 §6.5 유지하되 (PlanNote 형태 commit 사후 명시), e75a7ee commit 메시지만 reword (history 보존). 단 사용자 결정 필요
- **작업 범위**:
  - e75a7ee commit message만 reword (`PlanNote` 박지 말고 정식 prefix)
  - 이후 commit (f274252 v0.7.67 P0/P1 개편)에서 멀티볼트 라우팅이 완성된 것으로 보임 — e75a7ee의 의도가 흡수됨
- **리스크**: commit reword는 force push 필요 → AGENTS.md §10 "force push ❌" 금칙과 충돌. **신중 결정**

---

## 2. P1 패치 — 단기 (4건)

### P1-1: df99565 — `docs/issues/` 한글 title → 한글 파일명
- **정책**: AGENTS.md §10 "한글 title → 한글 파일명 (음차/번역 금지)"
- **현황**: 3건 파일 모두 한글 title + 영문 slug
  - `link-module-rglob-triplication.md` (title: "link_module의 자체 rglob 3회 — lint 캐싱 범위 밖 잔여")
  - `server-error-envelope-unification.md` (title: "server.py 전역 에러 응답 envelope 불일치 (3종 혼재)")
  - `vaults-clone-rest-naming.md` (title: "POST /api/vaults/clone — vaults/create와 동일한 REST 네이밍 위반")
- **옵션**:
  - (a) **파일명 한글화** — `link-module-rglob-3회-잔여.md` 등. §10 정합
  - (b) **title 영문화** — 파일명 그대로, title을 영문으로. §10 정합
- **권장**: **(a)** — 한글 운영 일관성 (raven-dev vault concept 페이지들이 한글 파일명). 3건 rename
- **작업 범위**: `git mv` 3건, frontmatter 확인 (aliases 추가 권장)
- **리스크**: wikilink 깨질 수 있음 — content/, _meta/ 내 다른 페이지에서 이 3건을 참조하는지 audit 필요

### P1-2: raw/ 정책 명확화 — AGENTS.md §7 갱신
- **정책**: AGENTS.md §7 raw/ (사람 1차 운영, 에이전트 read-only) — **범위 모호**
- **옵션**:
  - (a) **§7에 "actor 레벨 명시" 추가** — "raw/ write는 사람 운영자만. MCP `wiki_ingest`는 사람 명시 명령 시. CLI는 `actor=user`일 때만. Dashboard UI는 `actor=user` 가드"
  - (b) **별도 ADR** — `adr-YYYY-MM-DD-raw-folder-permission-matrix.md`로 권한 매트릭스 문서화
- **권장**: **(a) + (b)** — §7 본문 1-2줄 추가 + ADR 정식 기록
- **작업 범위**: `AGENTS.md` §7 1-2줄 보강, `_meta/decisions/adr-*.md` 신규 1건

### P1-3: §15.1 self-eval 9종 type 미반영
- **현황**: `AGENTS.md` §15.1 (형식/구조)가 "8종 타입" 박혀있음. 정정 사실은 `de3ff72`에서 9종으로 갱신됨. **하지만 §15.1 박힌 시점은 faa099e라 그 전** — 현재 §15.1이 9종 반영했는지 확인 필요
- **옵션**: §15.1 자체 검증 후 9종으로 정정 (실제 코드: `raven/core/contracts.py:436` `valid_types` = 9종)
- **권장**: §15.1 grep 확인 후 9종 박혀있지 않으면 1줄 정정

### P1-4: §14 `docs/` 인덱스 표 갱신
- **정책**: AGENTS.md §14 docs/ 컨벤션 (architecture/evaluations/vault-patterns)
- **현황**: 실제론 `docs/superpowers/{plans,specs}`, `docs/issues/` 추가됨 (a48fb91, 2f8dee3). §14 표에 미반영
- **옵션**: §14 표에 `docs/superpowers/`, `docs/issues/` 1-2줄 추가
- **권장**: §14 표 1-2줄 보강

---

## 3. P2 정책 갱신 (3건)

### P2-1: e75a7ee → PlanNote commit 정책 명확화
- **현황**: AGENTS.md §6.5 "묵시적 commit 금지" — 그러나 "PlanNote 형태 commit" 자체는 금칙 안 명시
- **옵션**: §6.5에 "PlanNote 형태 commit 금지 (코드 변경 시 정식 prefix + commit 메시지 작성)" 추가
- **권장**: 1-2줄 추가

### P2-2: SCHEMA.md `content/_index/` 자동 카탈로그 영역 면제
- **옵션**: SCHEMA.md 또는 PROJECT-WORKFLOW.md에 `content/_index/` 시스템 영역 면제 명시
- **권장**: 1줄 추가

### P2-3: §15 RAG 평가 부문을 vendor-neutral로
- **P0-3과 연계**: §15.2 Karpathy 4원칙을 Raven 자체 원칙으로 재진술
- **권장**: §15.2 자가 평가 기준 자체는 유지하되, 출처 표기 제거

---

## 4. P3 housekeeping (1건)

### P3-1: 7120134 인라인 hex — 자가 교정 확인 + 잔존 hex grep
- **현황**: `c013ed1` (v0.7.59 phase 2)에서 rgba 토큰 치환했음. **잔존 hex 없는지 grep**
- **작업**: `git grep "#0f172a\|#1e293b\|#334155\|#f1f5f9\|#f43f5e" dashboard/src/` 0건 확인
- **결과**: 0건이면 별도 패치 불필요. 잔존 시 패치

---

## 5. 패치 일정 (안)

| 단계 | 내용 | commit 수 |
|---|---|---|
| **Stage 1** (즉시) | P0-1 (raw/ actor 가드), P0-2 (SCHEMA 9종 복원 + ADR), P0-3 (§15.2 재작성), P0-4 (commit 메시지 결정) | 4-6 |
| **Stage 2** (단기) | P1-1 (한글 파일명 3건), P1-2 (raw/ 정책 명확화), P1-3 (§15.1 9종 정정), P1-4 (§14 docs/ 인덱스) | 3-4 |
| **Stage 3** (정책) | P2-1 (§6.5 PlanNote 금지), P2-2 (`content/_index/` 면제), P2-3 (§15.2 vendor-neutral) | 2-3 |
| **Stage 4** (검증) | P3-1 (잔존 hex grep) | 0-1 |
| **합계** | | ~10-14 commit |

→ **v0.7.69 patch release** 또는 다음 minor (v0.7.70)에 묶음 가능.

---

## 6. Claude Code 검토 요청 항목

다음 사항에 대한 claude code 의견 요청:

1. **P0-1 옵션 (a/b/c) 중 어느 게 맞나?** — raw/ panel 사람 운영자 가드 vs 전면 제거 vs API 레벨 거부
2. **P0-2 옵션 (a/b/c)** — SCHEMA 9종 고수하면서 카탈로그 시스템 영역 격리 vs ADR 정식 10종 승격
3. **P0-4 commit reword vs 두기** — force push 정책 §10 금칙과 충돌. 안전 결정
4. **Stage 1~4 묶음 단위** — 1 release로 vs 여러 release 분리
5. **회귀 테스트 범위** — 각 패치마다 필요한 테스트 식별

---

## 7. 자기 audit (Karpathy §6)

- ✅ **가정 명시**: 각 옵션에 trade-off 명시
- ✅ **단순성**: 권장 옵션은 가장 적은 코드 변경
- ✅ **Surgical**: 패치별 영향 범위 명시
- ⚠️ **Goal-Driven**: 성공 기준 — "위배 9건 중 P0 4건 해소 + 정책 자체 3건 갱신 + 회귀 0건"
- ⚠️ **§6.5 묵시적 commit 준수**: 이 plan 자체는 plan 문서이므로 commit 안 함 (사용자 결정 후 실행)
