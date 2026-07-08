# Changelog v0.7.112 — Dashboard NewIssueButton (사람 운영자 발행 폼)

> **BLUF**: `type: issue` 페이지를 Dashboard에서 사람이 직접 발행할 수 있는 포멀 폼(`NewIssueButton`)을 Sidebar vault row에 추가. SCHEMA 9종 issue 본문 템플릿(상태/문제/원인/해결/관련)을 자동 채우고 severity·kind 메타를 정식 태그로 박는다. agent는 여전히 발의만 가능 — `wiki_update` 자율 호출로 issue를 만들 수 없다 (PWW §7.1).

이전 changelog: `_meta/changelog-v0.7.111.md`

---

## §0 — 묶음 메타

| 항목 | 값 |
|---|---|
| 묶음 | Dashboard NewIssueButton |
| 범위 | v0.7.112 (단일 사이클) |
| 기간 | 2026-07-08 |
| 시작 트리거 | 사용자 명시: "이슈문서를 만드는 기능 하나 있어야겠네 포멀하게" |
| 종료 트리거 | tsc 통과 + vitest 8 passed + vite build 통과 |
| 정책 변경 | 0 — `type: issue` 권한 경계(PWW §7.1) 그대로 유지 |
| ADR 동반 | 0 — Dashboard 발행 UX 추가, agent 권한 변경 없음 |

## §1 — 무엇을 했나

`dashboard/src/components/NewIssueButton.tsx` (신규):

| 항목 | 내용 |
|---|---|
| 트리거 | Sidebar vault row 옆 ⚠ 아이콘 버튼 |
| 폼 필드 | 제목 / 심각도(high·medium·low) / 종류(bug·broken-link·orphan·stale·lint·spec-gap·other) / BLUF / 문제 상황 / 원인 분석 / 해결 방안 / 관련 wikilink |
| 저장 위치 | 좌측 PathPicker로 vault 폴더 선택 (기본 `content/issues/`) |
| 본문 자동 생성 | SCHEMA §issue 템플릿 그대로 (상태/문제/원인/해결/관련 5섹션) |
| frontmatter | `type: issue` 고정, `tags: [issue, severity, kind]` 자동 주입 |
| slug | `content/issues/YYYY-MM-DD-{slugified-title}` 자동 생성 |
| 권한 | 사람 운영자만 발행 가능. agent는 본 폼을 호출하지 않음 (자동화 경로 ❌) |

`dashboard/src/components/Sidebar.tsx`:

- vault row 옆 `NewPageButton` 다음에 `NewIssueButton` 추가
- `initialSlug="content/issues"` 기본, `onOpen={onClose}` 모바일 사이드바 자동 close

`dashboard/tests/NewIssueButton.contract.test.ts` (신규, 5 케이스):

- Sidebar에 와이어링 확인
- SCHEMA issue 본문 5섹션 자동 채움
- `type: issue` + severity/kind 태그
- dated slug 자동 생성
- 사람 운영자 severity·kind 차원 노출

## §2 — 변경 안 한 것

- **agent 권한 변경 없음** — `wiki_update`/`wiki_ingest`가 type: issue 만들 수 있는 경로 그대로 없음 (PWW §7.1)
- 백엔드 `/api/vaults/{name}/pages` contract 변경 0
- SCHEMA 9종 매트릭스 변경 0
- Lite bootstrap / PROJECT-WORKFLOW.md / SCHEMA.md SOT 변경 0

## §3 — 검증

```text
tsc -b               → 통과
vitest 8 passed      (NewIssueButton 5 + RawPanel 2 + Sidebar 1)
vite build           → 993 modules, 1.84s
```

## §4 — 4 저장 신호

| 신호 | 충족 |
|---|---|
| 재사용성 | 사람 운영자가 issue를 발행하는 표준 폼 — vault 5종 모두 공통 진입로 |
| 인수인계 | agent가 직접 만들 수 없는 type을 사람이 발행하는 경계가 코드에도 박힘 |
| scope/provenance | `actor=human` 명시적 폼 트리거 — log.md 자동 기록 |
| 실패/리스크 기록 | 폼은 사람 전용, agent가 호출할 수 없는 export 0 (re-export 가드 회피 위험) |
