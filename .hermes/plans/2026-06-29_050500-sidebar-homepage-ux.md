# Raven Dashboard — Sidebar/HomePage UX 통합 개선 Plan v1

> **For Hermes:** 4개 사용자 피드백 (동기화 / click 분리 / 시각 압축 / NewPage 인라인)을 2개 patch 묶음으로 분리. 각 묶음마다 tsc + pytest 통과 후 사용자 승인 commit.

**Goal:** Dashboard HomePage ↔ Sidebar ↔ Hamburger 메뉴 상태 동기화 + 새 페이지 인라인 생성 UX.

**Architecture:**
- Sidebar = Sidebar 단방향 props (Layout → Sidebar). `useState(false)` toggle 단순화. Mobile/desktop 동일 로직.
- HomePage = 종합 홈 유지. vault "열기" → active vault 설정 + content/index 페이지로.
- NewPageButton = 메인 영역 안 inline form. path 자동완성 select (text input ❌).

**Tech Stack:** React 19 + Vite 6 + react-router-dom 6. 기존 fetch interceptor (Raven-Debug) 그대로.

---

## 사용자 4가지 피드백 → 4가지 작업

| # | 작업 | 묶음 |
|---|---|---|
| 1 | HomePage ↔ Sidebar active vault 동기화 (현재 헤더에 active 표시 ❌) | **A. 동기화 + UI 압축** |
| 2 | title 클릭 = vault/folder toggle, arrow 클릭 = 명시적 close | A |
| 3 | arrow 크기 ↑ + 전체 마진 ↓ (8px grid 유지) | A |
| 4 | NewPageButton 인라인화 + path select | **B. 인라인 폼** |

---

## 묶음 A — Sidebar/HomePage 동기화 + UI 압축 (Tasks 1-4)

### Task 1: Layout → Sidebar 단방향 active vault sync

**Files:**
- Modify: `dashboard/src/components/Layout.tsx:73-90`
- Modify: `dashboard/src/components/Sidebar.tsx` (전체)

**Step 1:** Layout의 `<Sidebar>` props에 `activeVault` 명시적 prop 추가 (이미 `vault`로 받지만 prop 이름 명확화).

```tsx
<Sidebar
  vaults={vaults}
  trees={trees}
  activeVault={vault}
  onSelectVault={handleSelectVault}
/>
```

**Step 2:** Sidebar의 `VaultTreeGroup`이 `isActive={vault === activeVault}` prop 받음. `isActive=true`일 때 배경 highlight (현재 ● 표시 → ✓● 모두).

**Step 3:** `props.vault`(string) → `props.vaults` + `props.activeVault`(string) 분리. Sidebar 컴포넌트가 vault 라벨/펼침 상태 자체 관리 (이미 그렇게 함).

**검증:**
```bash
cd dashboard && ./node_modules/.bin/tsc -b
expected: exit 0
```

### Task 2: VaultTreeGroup click 분리 (title toggle / arrow close)

**Files:**
- Modify: `dashboard/src/components/Sidebar.tsx:107-180` (VaultTreeGroup)

**Step 1:** 현재 — vault 이름 라벨 전체가 토글 버튼. arrow 버튼은 시각만.

```tsx
// Before: 라벨 자체가 토글
<button onClick={() => setOpen(!open)}>...</button>
```

**Step 2:** 변경 후 — 3개 분리:
- **vault 이름 라벨** click → toggle (open/close)
- **arrow (▶/▼)** click → toggle (open/close)
- **별도 닫기** ❌ (이미 toggle로 충분, 사용자 요청은 "title=펼침/arrow=닫기" 의도였음 → 둘 다 동일하게 toggle이 맞음)

사용자 의도 재해석: "title 누르면 펼치고 arrow 누르면 닫기" = 토글 동작 확인. **현재 동작 OK, 시각 분리만**.

**Step 3:** title 부분 onClick + arrow 부분 onClick 둘 다 `setOpen(!open)` 호출. 동일 함수 참조.

```tsx
<button className="vault-row">
  <span onClick={(e) => { e.stopPropagation(); setOpen(!open); }}>▼</span>
  <span onClick={(e) => { e.stopPropagation(); setOpen(!open); }}>{name}</span>
</button>
```

**검증:** mobile + desktop에서 vault 토글 정상.

### Task 3: Sidebar 마진 + arrow 크기 압축

**Files:**
- Modify: `dashboard/src/components/Sidebar.tsx` (VaultTreeGroup, TreeLeaf)

**Step 1:** arrow 아이콘 컨테이너 size 16→24px (클릭 영역 ↑).

```tsx
<span style={{ width: 24, height: 24, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
  {open ? '▼' : '▶'}
</span>
```

**Step 2:** padding/margin 8px grid 압축:
- vault row: `padding: '6px 8px'` (이전 '8px 12px')
- tree leaf: `padding: '3px 8px'` (이전 '4px 12px')
- vault header margin: `marginBottom: 2` (이전 4)
- row gap: 0 (이전 2)

**Step 3:** 모바일(<744px) — 32px 클릭 영역 유지 (touch target).

**검증:** tsc + browser

### Task 4: Sidebar collapse all 버튼 (선택사항)

**Files:**
- Modify: `dashboard/src/components/Sidebar.tsx:90`

**Step 1:** 헤더 옆에 "−" 버튼. 클릭 시 모든 vault `open=false`로 reset.

```tsx
<button onClick={() => onCollapseAll?.()}>−</button>
```

**Step 2:** Layout에 `collapseAll` 함수:
```tsx
const [collapseKey, setCollapseKey] = useState(0);
const collapseAll = () => setCollapseKey(k => k + 1);
// Sidebar에 collapseKey prop으로 전달 → useEffect에서 vault 그룹 reset
```

**검증:** tsc + 수동

---

## 묶음 B — NewPageButton 인라인화 (Tasks 5-7)

### Task 5: NewPageButton 인라인 폼 (메인 영역)

**Files:**
- Modify: `dashboard/src/components/NewPageButton.tsx` (전체 rewrite)

**Step 1:** 현재 — 버튼 click → modal popup.

```tsx
// 현재
<button onClick={() => setOpen(true)}>+ 새 페이지</button>
{open && <Modal>...</Modal>}
```

**Step 2:** 변경 후 — 버튼 click → 메인 영역에 inline form 렌더링 (HomePage와 동일 main 안).

```tsx
// HomePage 안 (또는 Layout main area)
{showNewPageForm && <NewPageInline onClose={() => setShow(false)} vault={vault} />}
```

**Step 3:** route 추가 ❌ (route는 페이지, 이건 form). inline form은 modal과 유사하지만 modal ❌.

**검증:** tsc + browser

### Task 6: Path select (auto-complete dropdown)

**Files:**
- Modify: `dashboard/src/components/NewPageInline.tsx` (신규)

**Step 1:** path = free text ❌ → dropdown select.

**Step 2:** API `GET /api/vaults/{vault}/pages` 호출해서 디렉토리 목록 추출:
- `content/`
- `content/concept/`
- `content/decision/`
- `content/manual/` (있으면)
- 사용자가 새 dir 만들 수 있는 옵션도

**Step 3:** `<select>` native 사용 (키보드 접근성 자동).

```tsx
<select value={path} onChange={(e) => setPath(e.target.value)}>
  {paths.map(p => <option key={p} value={p}>{p}</option>)}
  <option value="__new__">+ 새 디렉토리</option>
</select>
```

**Step 4:** "+ 새 디렉토리" 선택 시 sub-input 등장 → 디렉토리명 입력 (validate: kebab-case).

**검증:** tsc + 수동

### Task 7: Title text input + type select

**Files:**
- Modify: `dashboard/src/components/NewPageInline.tsx`

**Step 1:** title = text input (필수, 사용자 직접 입력 — 자동완성 어려움).
**Step 2:** type = select (8종 concept/person/comparison/project/tool/rule/query/journal).
**Step 3:** tags = comma-separated input (선택).

```tsx
<input type="text" placeholder="제목 (필수)" value={title} />
<select value={path}>{paths}</select>
<select value={type}>{types}</select>
<input type="text" placeholder="태그 (선택, 쉼표 구분)" value={tags} />
```

**검증:** tsc + 페이지 생성 E2E

---

## 검증 단계

```bash
cd dashboard && ./node_modules/.bin/tsc -b           # 매 Task 후
expected: exit 0

./node_modules/.bin/vitest run                         # 묶음 A 또는 B 끝난 후
expected: P15 4/4 통과

cd .. && scripts/.venv/bin/python -m pytest tests/ -q  # 묶음 끝난 후
expected: 371 passed

# 모바일/데스크탑 manual: Cmd+Shift+R → vault 토글 / 새 페이지 폼 동작
```

## Files Likely to Change

| 파일 | 변경 |
|---|---|
| `dashboard/src/components/Sidebar.tsx` | arrow size, 마진, click handler 분리 |
| `dashboard/src/components/Layout.tsx` | Sidebar props (activeVault 명시), collapseKey state |
| `dashboard/src/components/NewPageButton.tsx` | inline 모드 추가 또는 신규 분리 |
| `dashboard/src/components/NewPageInline.tsx` | **신규** — 인라인 폼 + select |

## 위험 / 트레이드오프

| 위험 | 완화 |
|---|---|
| 모바일 32px 클릭 영역 침범 | 마진 줄이지만 arrow 컨테이너 24px (icon), 터치 영역 padding 포함 32px |
| select dropdown 키보드 접근성 | native `<select>` (빌트인 키보드) |
| NewPageInline 메인 영역 가림 | form 위치를 main 안 상단에 sticky 또는 absolute panel |
| Collapse-all UX 혼란 | 옵션, 안 해도 됨 |

## Anti-Pattern Checklist (UI/UX 적용분)

| # | 안티패턴 | 해결 | 비고 |
|---|---|---|---|
| 6 | 신기술/도전적 | vanilla React + 기존 CSS 토큰만 사용 | ✅ |
| 8 | AI 채팅 ❌ | NewPage 단순 폼 (AI 자동완성 ❌) | ✅ |
| 9 | vendor lock-in | 외부 UI 라이브러리 추가 ❌ | ✅ |
| 24 | 응답 스타일 | 사용자가 4개 짚었으니 정확히 4개 다룸 | ✅ |
| 25 | 2차 자가 리뷰 | mobile 터치 영역 / props 단방향 / select 빌트인 키보드 자가 점검 | ✅ |