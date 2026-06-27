# raven v0.6.4 — HomePage 모바일/데스크탑 양쪽 최적화 (A안)

> **핵심**: 메인 페이지를 "**vault 운영 콘솔**" 3영역으로 재구성. 모바일에서 검색·새페이지·그래프·디제스트 **1-tap 도달** (기존 2-tap → 1-tap). "안정적이고 심플" 원칙 준수 — 새 라우트 0, Sidebar 그대로.

릴리스 일자: 2026-06-27
이전: v0.6.3 (Raven root 단일화)

---

## 한 줄 요약

3영역 (**Quick Actions 4카드** · **Hero + vault 요약** · **Recent pages**) + 744px 분기. 모바일 pain (사이드바 2-tap) 해결.

---

## 1. 변경 사항

### 1.1 Layout 비교 (시각화)

**Before (v0.6.3)** — desktop과 mobile 동일, hero만:

```
┌─────────────────────────────────────┐
│ Wiki Home                           │  ← h1
│ 전체 N개 페이지 · M개 타입          │  ← 한 줄 설명
├─────────────────────────────────────┤
│ [Card] [Card] [Card] [Card] ...     │  ← recent grid만
└─────────────────────────────────────┘
   (모바일: 검색·새페이지 = sidebar → 항목 = 2-tap)
```

**After (v0.6.4)** — Quick Actions + Recent + vault 요약:

Desktop (≥745px):
```
┌──────────────────────────────────────────────────────────┐
│  wiki  (h1)                                              │
│  전체 36개 페이지 · 5개 타입 · ~/Raven/wiki/              │  ← vault 요약
├──────────────────────────────────────────────────────────┤
│  빠른 액션                                                │
│  [🔍 검색] [✚ 새 페이지*] [⬡ 그래프] [◐ 디제스트]         │  ← 4-col
├──────────────────────────────────────────────────────────┤
│  최근 수정                                       전체 검색→│
│  [Card] [Card] [Card]                                     │  ← 3-col
│  [Card] [Card] [Card]                                     │
└──────────────────────────────────────────────────────────┘
* 새 페이지 = primary (blue border + brand background)
```

Mobile (≤744px):
```
┌──────────────────┐
│  wiki            │  ← h1 22px
│  36p · 5t · path │  ← 14px muted
├──────────────────┤
│  빠른 액션       │
│  [🔍][✚]         │  ← 2-col grid
│  [⬡][◐]         │  ← 4 카드 모두 1-tap
├──────────────────┤
│  최근 수정      │
│  [Card]          │  ← 1-col stack
│  [Card]          │  ← 큰 tap target
│  [Card]          │
│  [Card]          │
└──────────────────┘
```

### 1.2 모바일 pain 해소 (1-tap 도달)

| 액션 | Before | After |
|---|---|---|
| 검색 | sidebar → 검색 (2-tap) | **메인 1-tap** ✅ |
| 새 페이지 | sidebar → +새 페이지 (2-tap) | **메인 1-tap** ✅ (primary) |
| 그래프 | sidebar → 그래프 (2-tap) | **메인 1-tap** ✅ |
| 디제스트 | ❌ (sidebar에도 없음, /digest 직접) | **메인 1-tap** ✅ (신규 노출) |

### 1.3 데스크탑 변화

- **추가 노출**: 디제스트 카드 (M5 F5 — 기존 `/digest` 라우트, 메인에서 1-tap 진입)
- **Hero 강화**: vault name (h1) + path + counts (사용자 인지)
- **신호**: 새 페이지 = primary (blue border + brand bg) — 의도 명확
- **호버 이펙트**: 모바일에서 비활성 (`if (isMobile) return`) — 데스크탑만

---

## 2. 디자인 토큰 (BMW + IBM Carbon)

| 토큰 | 용도 |
|---|---|
| `--cds-field-01` | 액션 카드 배경 (#fff) |
| `--cds-border-subtle-01` | 액션 카드 border (#e0e0e0) |
| `--cds-background-brand` | primary 액션 카드 bg (#f4f7fc) |
| `--shadow-card` | 데스크탑 hover 그림자 (0 2px 6px) |
| `--color-primary` | primary 액션 border (#1c69d4) |
| `--color-ink` / `--color-muted` | 본문 / 보조 텍스트 |

→ 기존 토큰만 사용, **신규 토큰 0** (디자인 시스템 일관성 보존).

---

## 3. 744px 분기 전략

| 영역 | Mobile (≤744) | Desktop (≥745) |
|---|---|---|
| h1 크기 | 22px | 28px |
| Hero padding | 8px / 24px | 16px / 48px |
| Quick Actions grid | **2-col** | **4-col** |
| Recent grid | **1-col stack** | **3-col auto-fill 280px** |
| Recent count | 8 | 12 |
| Card min-height | 88px (44×2 + padding) | 96px |
| Recent min-height | 64px (44 + padding) | inherit |
| Hover effects | ❌ 비활성 | ✅ box-shadow + translateY |
| font size card title | 15px | 16px |

→ `window.matchMedia("(max-width: 744px)")` + `change` listener (Layout.tsx와 동일 패턴).

---

## 4. 구현 디테일

### 4.1 신규 component (2개)

| 컴포넌트 | 책임 |
|---|---|
| `ActionCard` | Quick Action 1개 (icon + label + description, hover 효과) |
| `RecentCard` | Recent page 1개 (chip + date + title + path) |

### 4.2 데이터 fetch (기존 API 그대로)

| API | 용도 |
|---|---|
| `GET /api/index.json` | 페이지 목록 (slug, title, type, path, updated) |
| `GET /api/vaults` | vault 목록 → default/첫번째 → h1에 표시 |

→ **신규 API 0**, 기존 인프라 활용.

### 4.3 라우트 변경

| 라우트 | 변경 |
|---|---|
| `/` (HomePage) | 본문만 교체, 라우트 변경 0 |
| `/digest` (DashboardDigest) | 기존 라우트 그대로 (M5 F5) — Quick Action에서 1-tap 진입 |

---

## 5. 검증

```bash
$ cd dashboard && npx tsc -b --noEmit
(타입 에러 0)

$ cd dashboard && npm run build
✓ built in 1.49s
PWA precache: 6 entries (1102.54 KiB)  ← +2.79KB (HomePage 116 → 280 lines)
```

### 수동 검증 (사용자)

| 시나리오 | 결과 |
|---|---|
| Desktop `/` (≥745px) | Hero (vault name) + 4-col Quick Actions + 3-col Recent |
| Mobile `/` (≤744px) | Hero (작게) + 2-col Quick Actions + 1-col Recent stack |
| Quick Action 클릭 | 각 라우트로 정상 이동 |
| Recent 카드 클릭 | PageView로 정상 이동 |
| 모바일 햄버거 → sidebar | 정상 (Layout.tsx 그대로) |
| Sidebar 동작 | 변화 없음 (의도된 변경만 OK) |

---

## 6. 변경 사항 요약

| 파일 | 변경 | 줄 |
|---|---|---|
| `dashboard/src/routes/HomePage.tsx` | 3영역 재구성 (Quick Actions + Hero 강화 + Recent 1-tap) | 116 → 280 lines |
| **`_meta/changelog-v0.6.4.md`** | 신규 | 이 문서 |

**Sidebar.tsx / Layout.tsx / VaultPicker.tsx 변경 0** (Surgical 원칙).

---

## 7. 효과

| 지표 | Before | After |
|---|---|---|
| 모바일 검색 1-tap | ❌ (2-tap sidebar) | ✅ |
| 모바일 새 페이지 1-tap | ❌ (2-tap) | ✅ |
| 모바일 그래프 1-tap | ❌ (2-tap) | ✅ |
| 모바일 디제스트 진입 | ❌ (URL 직접) | ✅ (1-tap) |
| Hero 정보량 | 1줄 (counts) | 3요소 (name + path + counts) |
| Recent tap target (mobile) | ~56px | 64px (Apple HIG 충족) |

---

## 8. 다음 사이클 후보

1. **Sidebar에 "디제스트" 메뉴 항목 추가** (홈에서 들어간 후 sidebar로 돌아와도 진입 가능)
2. **Quick Action 5번째** — "Lint" (vault 검수)
3. **M5 F5 Digest 컴포넌트 모바일 최적화** (별도)
4. **delete/rename_page 단일화** (P1-1 후속)
5. **SCHEMA sync ADR** (P1-2)

---

## 9. 작업 보고

- **무엇**: HomePage 3영역 재구성 (Quick Actions 4 + Hero 강화 + Recent 1-tap)
- **왜 (저장 신호)**: ① 재사용 가능성 (모바일 1-tap 진입), ② 인수인계 (vault 운영 콘솔 명확), ③ 결정 추적 (changelog)
- **검증**: TypeScript typecheck PASS, build PASS (1.49s)
- **다음 가능**: Sidebar 디제스트 메뉴, Quick Action 5번째, delete/rename_page 단일화
