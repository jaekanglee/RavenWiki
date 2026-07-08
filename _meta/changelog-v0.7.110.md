# Changelog v0.7.110 — RawPanel viewer height sync with tree (Dashboard UX)

> **BLUF**: RawPanel 우측 viewer가 좌측 tree와 height sync 안 되어 작은 영역에 viewer/textarea가 갇혀 보이던 문제 수정. viewer를 flex column으로 재구조화해 tree와 같은 `maxHeight: calc(100vh - 220px)`까지 stretch하고, textarea는 `<TextField multiline>` 갇힘을 풀고 raw `<textarea>`로 교체해 `flex: 1; height: 100%` 패턴 적용.

이전 changelog: `_meta/changelog-v0.7.109.md`

---

## §0 — 묶음 메타

| 항목 | 값 |
|---|---|
| 묶음 | RawPanel viewer height sync |
| 범위 | v0.7.110 (단일 사이클) |
| 기간 | 2026-07-08 |
| 시작 트리거 | 사용자 명시 ("raw에서 문서열면.. 문서가 굉장히 height가 작은 영역에서만 보여 이상해") |
| 종료 트리거 | tsc --noEmit 통과 + vite build 통과 |
| 정책 변경 | 0 |
| ADR 동반 | 0 |

## §1 — 무엇을 했나 (what)

### 1.1 RawPanel viewer height sync (v0.7.110)

`dashboard/src/routes/RawPanel.tsx`:

| 위치 | 변경 |
|---|---|
| L280 grid `alignItems` | `"start"` → `"stretch"` (좌/우 column height sync) |
| L323 viewer box | `display: flex; flexDirection: column; maxHeight: calc(100vh - 220px); overflow: hidden` 추가 (트리와 동일 maxHeight) |
| L419-447 viewer textarea | `<TextField multiline rows={20}>` → raw `<textarea>` (`flex: 1; height: 100%; resize: none`). `<label>` block에 갇혀 stretch 안 되던 문제 해결 |

### 1.2 변경 안 한 것

- `<TextField>` import 유지 — L197/L204/L454/L461 (empty state modal, newFileOpen modal) 4곳에서 계속 사용 중
- 좌측 tree 박스 (L290 `maxHeight: calc(100vh - 220px)`) — 이미 정상이라 그대로

## §2 — 검증 (verify)

- `npx tsc --noEmit` — 통과
- `npm run build` — `tsc -b && vite build` 통과 (1.84s, 992 modules)
- `npm run lint` — **실패 (사전 깨짐)**: ESLint v9 + legacy `.eslintrc` 미그레이션. 본 패치 범위 밖, 별도 이슈로 분리

## §3 — 표준 viewer 패턴 정합

다른 viewer 페이지들과 동일한 패턴으로 정렬:

| 파일 | 패턴 |
|---|---|
| `routes/WorkspacePage.tsx` L784, L811 | 부모 flex column + 콘텐츠 `flex: 1; overflowY: auto; minHeight: 0` |
| `components/InlineMarkdownEditor.tsx` L509, L522-523 | grid + textarea `minHeight: 400; maxHeight: 70vh; resize: vertical` |
| `routes/RawPanel.tsx` L323, L419 (**이번**) | flex column + textarea `flex: 1; height: 100%; resize: none` (container scroll 아닌 textarea 자체 scroll) |

## §4 — 4 저장 신호

| 신호 | 충족 |
|---|---|
| 재사용성 | RawPanel 자체가 vault 운영 핵심 진입점 (5 vault audit 영역) |
| 인수인계 | 다른 viewer 페이지들도 동일 패턴이라 SOT 가치 높음 |
| scope/provenance 추적 | grid `alignItems: stretch` 패턴 §3로 후속 작업자 가이드 |
| 실패/리스크 기록 | textarea `<label>` 갇힘 문제는 별도 viewer 작업 시 재발 위험 — §3에 정답 패턴 기록 |