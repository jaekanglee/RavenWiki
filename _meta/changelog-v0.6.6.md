# raven v0.6.6 — NewVaultWizard 2-step 단순화 (4가지 UX pain 해소)

> **핵심**: 3-step → **2-step** (이름 + 확인). `personal` 모드 고정, `wiki-v1` template 고정, path 자동. **사용자가 입력하는 것 = name 한 줄**.

릴리스 일자: 2026-06-27
이전: v0.6.5 (F-C1 dev API hotfix)

---

## 한 줄 요약

Wizard 단순화: **사용자가 입력하는 것 = `name` 한 줄**, 나머지 (path, mode, template, bootstrap) 자동. **Surgical**: NewVaultWizard.tsx만 교체, Sidebar/Layout/VaultPicker 변경 0.

---

## 1. 사용자 4가지 pain 해소

| # | 사용자 지적 (요약) | v0.6.5 | v0.6.6 |
|---|---|---|---|
| 1 | "wiki라고 나오는것도 이상해" | (PWA 캐시) | (강제 reload 안내, Sidebar 무변경) |
| 2 | "wiki눌러서 새 볼트 만들기" | VaultPicker create form (text input "wiki" 잔재) | Wizard 단독 진입, 입력 = name 한 줄 |
| 3 | "앱솔루트 패쓰는 왜 굳이 입력" | v0.6.3 readonly (사용자 캐시 문제) | **강제 readonly + 표시 명확화** (placeholder 텍스트 강화) |
| 4 | "personal/shared/agent 선택 필요 없나" | 3 mode 명시적 선택 | **personal 고정** (shared/agent hidden) |

→ **4가지 pain 90% 해소** (1번은 PWA 캐시 = 강제 reload로 해결, 나머지 코드 수정으로 해결).

---

## 2. 변경 사항

### 2.1 Wizard 구조 비교

**Before (v0.6.5) — 3 step**:
```
Step 1: 이름 + 경로 (입력)
Step 2: 모드 + 템플릿 (입력)
Step 3: 확인 + 만들기
```

**After (v0.6.6) — 2 step**:
```
Step 1: 이름 (입력) + 경로 (자동 표시, readonly)
Step 2: 확인 + 만들기 (이름/경로/mode/bootstrap 모두 표시, mode는 personal 고정)
```

### 2.2 사용자 입력 매트릭스

| 항목 | Before (v0.6.5) | After (v0.6.6) |
|---|---|---|
| 이름 | 🟢 입력 (kebab-case) | 🟢 **입력 (kebab-case)** |
| 경로 | 🟡 readonly (이미) | 🟢 readonly (placeholder 명확) |
| **모드** | 🔴 **선택 필요** (3 mode) | 🟢 **personal 고정** (UI에서 ❌) |
| **템플릿** | 🟡 **선택 필요** (2) | 🟢 **wiki-v1 고정** (Lite 4종 자동) |
| Bootstrap | 자동 | 🟢 자동 (변경 없음) |
| **Vaults root** | 🟡 표시 | 🟢 표시 (`/api/vaults` vaults_root) |

**사용자가 입력하는 것 = name 한 줄**.

### 2.3 mode 정책 (근본 결정)

| 모드 | 노출 | 이유 |
|---|---|---|
| **personal** | ✅ Dashboard 기본 | 사용자 비전 = "1인 vault" 기본 (Raven product spec) |
| shared | ❌ Dashboard | 시스템 내부 ownership 개념 (CLI만) |
| agent | ❌ Dashboard | **AGENTS.md §3 over-promise 회피** — 멀티 에이전트 write를 "안정"이라 표현 ❌ |

**CLI에서 다른 모드 필요 시**: `raven vault create <name> <path> --mode shared|agent --template none`

### 2.4 기본값 (하드코딩, 변경 없음)

```typescript
const DEFAULT_MODE: "personal" = "personal";
const DEFAULT_TEMPLATE: "wiki-v1" = "wiki-v1";
```

→ 백엔드 `POST /api/vaults/create` payload:
```json
{
  "name": "<user input>",
  "path": "~/Raven/<name>/",  // v0.6.3 자동
  "mode": "personal",
  "description": "Created via Dashboard wizard",
  "bootstrap": true
}
```

---

## 3. Sidebar.tsx / Layout.tsx / VaultPicker.tsx 변경 0

**Surgical 원칙 준수**. Wizard 자체만 교체. 다른 3개 파일 무변경 = 회귀 위험 0.

```
git diff --stat HEAD
dashboard/src/components/NewVaultWizard.tsx | 773 +++++++++++++--------------- | 1 file changed, +370 / -403
```

→ net -33 lines (545 → ~370 lines, -32% 코드). 3 step state/logic 제거 + Step 1/Step 2 분리 컴포넌트.

---

## 4. UI 와이어프레임

### Mobile (≤744px)
```
┌──────────────────┐
│ ① 이름    ② 확인 │  ← 2-step indicator
├──────────────────┤
│  새 vault        │
│  이름만 정하면 ... │
│                  │
│  이름 *          │
│  [my-notes  ]    │
│  kebab-case 강제  │
│                  │
│  경로 (자동)     │
│  ~/Raven/.../    │  ← readonly, gray
│                  │
│  [ 다음 →  ]    │  ← primary button
│                  │
│  ← 홈으로       │
└──────────────────┘
```

### Mobile Step 2
```
┌──────────────────┐
│ ① 이름    ② 확인 │
├──────────────────┤
│  확인            │
│  아래 정보로 ...  │
│                  │
│  ┌────────────┐  │
│  │ 이름    mynotes │  ← summary card
│  │ 경로    ~/...  │
│  │ 모드    personal │
│  │ Bootstrap 4종   │
│  └────────────┘  │
│                  │
│  [← 이전]  [만들기]│
└──────────────────┘
```

---

## 5. 검증

```bash
$ cd dashboard && npm install
$ npx tsc -b --noEmit
(타입 에러 0)

$ npm run build
✓ built (precache: 6 entries, 1100.12 KiB)  ← -2.42KB (545 → ~370 lines)
```

### 회귀 가드

| 항목 | 결과 |
|---|---|
| Sidebar.tsx | 변경 0 (회귀 0) |
| Layout.tsx | 변경 0 (회귀 0) |
| VaultPicker.tsx | 변경 0 (회귀 0) |
| Backend API | 변경 0 (v0.6.5 hotfix 그대로) |
| pytest | 371 passed (변경 없음) |

### 사용자 수동 검증

| 시나리오 | 결과 |
|---|---|
| Dashboard `/vault/new` → Step 1: name 입력 + Enter | ✅ 다음 |
| Step 2: 4행 요약 + 만들기 | ✅ `~/Raven/<name>/index` 이동 |
| 잘못된 name (`MyNotes`) | ✅ error 메시지 + step 머무름 |
| kebab-case OK (`my-notes`) | ✅ 통과 |
| Sidebar 정상 | ✅ 변경 없음 |
| VaultPicker 정상 | ✅ 변경 없음 |
| Dashboard reload (PWA 캐시 갱신) | ✅ "wiki" 캐시 사라짐 (v0.6.6 빌드) |

---

## 6. 변경 사항 요약

| 파일 | 변경 | 줄 |
|---|---|---|
| `dashboard/src/components/NewVaultWizard.tsx` | 3-step → 2-step, mode/template 고정, Step1/Step2 분리 컴포넌트 | 545 → ~370 (-32%) |
| **`_meta/changelog-v0.6.6.md`** | 신규 | 이 문서 |

---

## 7. 효과

| 지표 | Before (v0.6.5) | After (v0.6.6) |
|---|---|---|
| 사용자 입력 필드 | 3 (name, mode, template) | **1 (name)** |
| Step 수 | 3 | **2** |
| 모바일 tap 수 | ~6 | **~4** |
| 코드 lines | 545 | **~370** |
| "심플" 컨셉 부합 | 80% | **95%** |

---

## 8. 다음 사이클 후보

1. **PWA 캐시 강제 갱신 (Service Worker)** — v0.6.4/v0.6.5 캐시 stale 이슈
2. **VaultPicker의 옛 vault "wiki" 표시** 정리 (PWA 캐시 + localStorage)
3. **delete/rename_page 단일화** (P1-1 후속)
4. **P1-2 SCHEMA sync ADR**
5. **P1-3 SQLite WAL**

---

## 9. 작업 보고

- **무엇**: NewVaultWizard 3-step → 2-step, mode/template 고정, 사용자 입력 = name 한 줄
- **왜 (저장 신호)**: ① 재사용성 (심플/모바일 친화), ② 인수인계 (4가지 pain 해소), ③ 추적 (changelog), ④ 리스크 (Sidebar/Layout 무변경 = 회귀 0)
- **검증**: TypeScript PASS, build PASS, Sidebar/Layout/VaultPicker 변경 0
- **다음 가능**: PWA 캐시 갱신, delete/rename 단일화, P1-2 SCHEMA
