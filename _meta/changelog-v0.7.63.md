# raven v0.7.63 — WorkspacePage 우측 패널 탭 분리 (워크스페이스 / 변경사항)

> **핵심**: v0.7.61에서 추가한 우측 패널(미리보기 + diff)이 두 트리(워크스페이스 / 변경사항)에서 모두 채워지다 보니 "지금 어느 트리 결과인지" 헷갈리는 UX 문제. v0.7.63에서 우측 패널 상단에 **`[🌳 워크스페이스] [📋 변경사항 N]`** 탭 2개로 명시 분리. 트리 클릭 = 워크스페이스 탭 활성화, Git 변경파일 클릭 = 변경사항 탭 활성화.

릴리스 일자: 2026-07-03
이전: v0.7.62

---

## 1. 변경 사항

### 1-1. `WorkspacePage.tsx` — 탭 모드 state

```tsx
type RightTab = "workspace" | "changes";
const [activeTab, setActiveTab] = useState<RightTab>("workspace");
```

기본값: `"workspace"` (워크스페이스 트리 보고 있는 게 자연스러운 시작점).

### 1-2. 탭 자동 활성화 — 4개 핸들러

| 핸들러 | 트리거 | 결과 |
|---|---|---|
| `handleTreeDirClick` | 트리 디렉토리 클릭 | `setActiveTab("workspace")` |
| `handleTreeFileClick` | 트리 파일 클릭 (미리보기 시작) | `setActiveTab("workspace")` |
| `handleTreeUp` | ⬆ breadcrumb up 버튼 | `setActiveTab("workspace")` |
| 변경사항 행 클릭 | `setSelectedFile(c.file)` | `setActiveTab("changes")` |

→ 사용자가 트리/변경사항 어느 쪽을 만지든 해당 탭이 active로 자동 전환. 명시 클릭으로도 가능.

### 1-3. 탭 UI 디자인

```
┌────────────────────────────────────────────────┐
│  [🌳 워크스페이스]  [📋 변경사항 ③]            │
│   ╰─────────────                                  │  ← border-bottom 2px
├────────────────────────────────────────────────┤
│                                                 │
│  (active 탭의 본문)                             │
│   workspace 탭: 미리보기 / binary 안내 / Empty  │
│   changes 탭: diff / Empty                      │
│                                                 │
└────────────────────────────────────────────────┘
```

| 토큰 | 사용 |
|---|---|
| `var(--color-primary)` | active 탭 border-bottom + badge 배경 |
| `var(--color-ink)` | active 탭 텍스트 |
| `var(--color-muted)` | inactive 탭 텍스트 + inactive badge |
| `var(--color-on-primary)` | active badge 텍스트 (primary 위) |
| `var(--color-hairline)` | 탭 그룹 하단 border |
| `var(--color-surface-soft)` | inactive badge 배경 |

### 1-4. 본문 분기 단순화

**v0.7.61~62**: `{previewContent || previewLoading || previewError ? ... : selectedFile ? ... : EmptyState}` 3중 분기. 트리 미리보기가 변경사항 diff보다 우선이라 **사용자가 "왜 diff가 안 보이지"** 헷갈림.

**v0.7.63**: `{activeTab === "workspace" ? <미리보기 분기> : <diff 분기>}` 2중 분기. 각 탭이 자기 영역의 상태(`previewContent` vs `selectedFile`/`diffText`)만 봄. 모드 명시적.

### 1-5. EmptyState 메시지 모드별 분리

| 시나리오 | v0.7.62 | v0.7.63 |
|---|---|---|
| 워크스페이스 탭 + 파일 미선택 | (diff 안내) | **"🌳 워크스페이스 트리에서 파일 선택"** |
| 변경사항 탭 + 파일 미선택 + 변경 있음 | (diff 안내) | **"📋 비교할 파일 선택"** |
| 변경사항 탭 + 변경 0개 | (위와 동일) | **"✨ 변경사항 없음"** |

→ 사용자가 어느 탭에 있든 "다음에 뭘 해야 하는지" 명확.

---

## 2. UX 시나리오 (검증용)

```
1. /workspace 진입 → 워크스페이스 탭 active (default)
2. 트리에서 .md 클릭 → 미리보기 표시, 워크스페이스 탭 active 유지
3. 트리에서 다른 .md 클릭 → 미리보기 갱신, 워크스페이스 탭 active 유지
4. 변경사항에서 파일 클릭 → 변경사항 탭 자동 active, diff 표시
5. 워크스페이스 탭 클릭 → 미리보기 상태로 복귀 (있다면)
6. 변경사항 0개일 때 변경사항 탭 → "✨ 변경사항 없음"
7. 변경사항 탭에 N badge → 변경파일 수 표시
```

---

## 3. 검증 결과

| 항목 | 결과 |
|---|---|
| `cd dashboard && npm run build` (tsc -b + vite build) | exit 0, 988 modules |
| `cd dashboard && npm test -- --run` | **116/116 passed** (회귀 ❌) |
| WorkspacePage 변경 | 1 file, 탭 헤더 + 본문 분기 |

---

## 4. 안전성 / 정책 정렬

- **§13.1 재사용 컴포넌트** — 새 `<Tab>` 컴포넌트 ❌ (1회 사용 + 디자인 토큰 inline). 추후 3+ 페이지에서 동일 패턴 나오면 그때 공통화.
- **§13.2 CSS 변수 우선** — 인라인 hex 0개. 모든 색은 `var(--xxx)`.
- **접근성** — `role="tablist"`, `role="tab"`, `aria-selected` 박음. 키보드 네비게이션은 추후 (Arrow Key 좌우 이동).
- **모바일** — v0.7.62 stack layout과 호환. 탭 헤더는 가로로 그대로 (작은 폭에서도 2 탭은 OK).

---

## 5. 추가 가능 작업 (다음 패치 후보)

- 탭 키보드 네비게이션 (← →, Home/End)
- `localStorage`에 마지막 active 탭 기억 (페이지 재방문 시 복원)
- 변경사항 0개일 때 변경사항 탭 disabled
- `<Tab>` 공통 컴포넌트 추출 (3+ 페이지 사용 시점)

---

## 6. 부록 — self-audit (Karpathy §6 + AGENTS.md §6,9)

- [x] **명시 (§6 ①)**: "두 트리가 다 있으면 헷갈리는 UX" — 사용자 요청 정확히 따름
- [x] **단순성 (YAGNI)**: 탭 2개, active state 1개, 자동 활성화 4-핸들러 — 최소 구현
- [x] **Surgical (§3)**: 1 파일만. 다른 페이지/컴포넌트 미접촉
- [x] **Goal-Driven**: `activeTab` state + 4-핸들러 set + 본문 분기 단순화로 모드 명시
- [x] **4 저장 신호**: changelog + UX 일관성 (트리/변경사항 = 미리보기/diff 매핑)
- [x] **재사용 컴포넌트 (§13.1)**: 인라인 탭 (YAGNI — 1회 사용)
- [x] **CSS 변수 우선 (§13.2)**: 인라인 hex 0개