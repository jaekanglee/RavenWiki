# raven v0.6.22 — Sidebar 폴더 hover 메뉴

> **핵심**: 사이드바 폴더 row에 인라인 + (페이지 만들기) 버튼 추가. 클릭 시 NewPageButton 모달이 열리고 `initialSlug` = parentPath 로 자동 prefix 주입 — 사용자가 폴더 안에서 바로 페이지 생성 가능.

릴리스 일자: 2026-06-29
이전: v0.6.21 (PageMetaRow)

---

## 한 줄 요약

`Sidebar.tsx` TreeLeaf의 dir row에 `NewPageButton` 추가 (`initialSlug={node.path}`). 폴더마다 자체 페이지 만들기 버튼. 모달 열리면 slug input에 자동으로 그 폴더 경로 prefix.

## 1. 변경 사항

### 1-1. `dashboard/src/components/Sidebar.tsx` (+8)

```tsx
<div className="sidebar-tree-dir-row" ...>
  <button ...>{label}</button>
  <NewFolderButton vault={vault} parentPath={node.path} ... />
  {/* v0.6.22+ — 폴더 hover 메뉴 */}
  <NewPageButton
    vault={vault}
    variant="icon"
    label="페이지"
    initialSlug={node.path}   // ← 자동 prefix
    onOpen={onClose}
  />
</div>
```

### 1-2. `dashboard/tests/Folder-hover-menu.test.tsx` (신규)

회귀 가드: 트리 펼친 후 페이지 만들기 버튼 ≥2개 (vault row 1 + 폴더별 N).

## 2. UX

```
📁 raven-dev    [+]
  📁 concept    [+] [📄+]   ← 폴더 옆 ＋ 누르면 concept 안에 페이지 생성 모달
  📁 decision   [+] [📄+]
```

**작동**:
1. 폴더 옆 📄+ 클릭
2. 모바일: drawer 자동 닫힘 (v0.6.17 onOpen={onClose})
3. Portal로 viewport 중앙 모달 (v0.6.18)
4. slug input에 자동으로 `content/concept/` (또는 그 폴더) prefix
5. 파일명만 입력 → 저장 → 그 폴더 안에 페이지 생성

## 3. 검증

| 항목 | 결과 |
|---|---|
| vitest | **16 파일 / 82 tests pass** (회귀 0) |
| tsc -b | **exit 0** |
| 브라우저 smoke | 트리 펼친 후 페이지 만들기 버튼 3개 (vault + concept + decision) |

## 4. 재사용 컴포넌트 일관성

- `<NewPageButton>` (기존 v0.6.18) 재사용 — 코드 0 추가
- `<NewFolderButton>` (기존) 재사용 — 코드 0 추가
- `initialSlug` prop (기존 v0.6.19 NewPageButton) 재사용

## 5. 후속 작업 후보

- Task 3: NewVaultWizard/NewPageInline/DeleteButton 도 TextField 교체
- Task 4: MiniMax 회귀 검증
- 폴더 hover 시 row 강조 (CSS hover effect 강화)
- 페이지 row에도 인라인 메뉴 (편집/삭제) — 기존 EditButton/DeleteButton 활용