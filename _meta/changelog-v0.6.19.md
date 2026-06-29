# raven v0.6.19 — Path picker UX for new page modal

> **핵심**: 새 페이지 만들기 모달에서 저장 위치를 직접 타이핑하던 UX를 vault 트리 클릭으로 변경. Obsidian/Notion식 경로 피커. 빈 폴더도 포함.

릴리스 일자: 2026-06-29
이전: v0.6.18 (Portal fix)

---

## 한 줄 요약

`NewPageButton` 모달 안에 vault 트리(`fetchTree`)를 좌측에 렌더, 폴더 클릭 시 `slug` 인풋에 prefix 주입. 기존 인풋 직접 타이핑도 유지 (fallback).

## 1. 발견 경위

사용자 짚어줌: "근데 새페이지 만들 때 저장위치를 패스를 ui로 선택하는 구조가 아니라 직접 타이핑이라니.. 오타날수도있고 별로 좋은 ux가 아닌 듯"

→ 직접 타이핑은 오타 위험 + 사용자가 폴더 구조를 모를 수 있음. 트리 클릭이 직관적.

## 2. 변경 사항

### 2-1. `dashboard/src/components/NewPageButton.tsx` (+204 / -47)

- `useEffect` 추가: 모달 `open` 시 `fetchTree(vault)` 호출, 결과 state 저장
- 2-column grid 레이아웃 (좌측 트리 picker 240px / 우측 폼 1fr)
- `PathPicker` 컴포넌트 신규 — vault 트리를 폴더만 표시 (페이지 ❌, 빈 폴더 ✅)
- `pickFolder(folderPath)` 함수 — slug에 prefix 주입 (기존 다른 prefix 제거, trailing slash 유지해 파일명 입력 자리)
- fetchTree 실패 시 graceful: "트리를 불러올 수 없습니다. 우측에서 직접 입력해 주세요."
- 모달 maxWidth 720 → 880 (2-column 공간)

### 2-2. `dashboard/tests/Path-picker.test.tsx` (신규, 3 tests)

회귀 가드:
1. 모달 열면 트리 picker 영역에 `data-path="content/concept"` 등 노드 렌더
2. 폴더 클릭 → slug input이 `content/concept/` prefix로 시작
3. fetchTree 실패 시에도 slug 인풋 직접 입력 동작

## 3. UX

```
┌──────────────────────────────────────────────────┐
│ 새 페이지 만들기                          [취소] │
│                                                  │
│ ┌──────────────┐ ┌────────────────────────────┐ │
│ │ 📁 content   │ │ 경로 *                      │ │
│ │   📁 concept │ │ [content/concept/]          │ │
│ │   📁 decision│ │                            │ │
│ │     📁 smoke │ │ 제목 *                      │ │
│ │              │ │ [내 컨셉]                   │ │
│ └──────────────┘ └────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

- 폴더 클릭 → 우측 인풋에 prefix 주입 + cursor 파일명 위치
- 우측 인풋 직접 타이핑도 가능 (오타 교정 가능성)
- 빈 폴더도 picker에 표시 (ADR 05311e0)
- 현재 선택 폴더 하이라이트

## 4. 검증

| 항목 | 결과 |
|---|---|
| vitest | **13 파일 / 68 tests pass** (회귀 0) |
| tsc -b | **exit 0** |
| 브라우저 smoke | pickerPaths 4개 정상 표시, `content/concept` 클릭 → slug = `content/concept/` |

## 5. 후속 작업 후보

- 폴더 hover 시 + 버튼 (인라인 폴더 생성) — 메모리 §다음 큐 2번 일부
- 다른 모달(EditButton, DeleteButton)도 Portal 미적용 점검 (v0.6.18 changelog §7)
- Type ADR + 📑 Index 자동 표시 — 메모리 §다음 큐 2번
- MiniMax 회귀 검증 — 메모리 §다음 큐 3번