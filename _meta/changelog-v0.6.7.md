# raven v0.6.7 — VaultPicker inline form 제거 (Wizard 단일 진입)

> **핵심**: v0.6.6 changelog에서 약속한 "Sidebar/Layout/VaultPicker 변경 0 = 회귀 0"가 사용자 요구사항과 충돌했음. **VaultPicker의 inline form (path 입력 + mode 3 select) 사용자가 여전히 봄** — Wizard 단순화가 부분 적용됨. **이 hotfix로 Wizard가 유일한 vault 생성 진입점**.

릴리스 일자: 2026-06-27
이전: v0.6.6 (NewVaultWizard 2-step)

---

## 한 줄 요약

VaultPicker의 inline create form (3-input: name + path + mode 3-select) **제거** → "➕ 새 vault" 버튼은 단순 `<Link to="/vault/new">`. **Wizard가 유일한 진입점**.

---

## 1. 문제 (v0.6.6 회귀)

| 항목 | v0.6.6 약속 | v0.6.6 실제 |
|---|---|---|
| NewVaultWizard | ✅ 2-step, name 한 줄 | ✅ 정상 |
| **VaultPicker inline form** | (Surgical "변경 0" — 회피) | ❌ **여전히 3-input** (name + path + mode 3-select) |
| 사용자 결과 | (모든 곳 통일 기대) | "VaultPicker 열면 path 직접입력 + mode 3개" ← **사용자 정확히 지적** |

### 사용자 메시지 (2026-06-27)
> "볼트이름 / 앱솔루트 패쓰 / 퍼스널/에이전트/쉐어 이렇게 하게돼있구만 내 요구사항 다 잊었어?"

→ **v0.6.6에서 Surgical 원칙 잘못 적용** — "Sidebar/Layout/VaultPicker 변경 0"이 사용자 요구를 가림. **VaultPicker의 create form은 user-facing 핵심** → 변경 OK (Sidebar의 트리/네비는 무변경 유지).

---

## 2. 변경 사항

### 2.1 VaultPicker.tsx

| 변경 | Before (v0.6.6) | After (v0.6.7) |
|---|---|---|
| state 6개 | `showCreate, newName, newPath, newMode, newBusy, newErr` | **0** (전부 제거) |
| `createVault()` 함수 | 24 lines (fetch + state) | **0** (제거) |
| inline form 본문 | 100 lines (input × 2 + select + button × 2) | **0** (제거) |
| "➕ 새 vault" 버튼 | `<button onClick={setShowCreate(true)}>` | `<Link to="/vault/new">` (단순 navigate) |

**코드 변화**: 322 → 254 lines (-68 lines, -21%)

### 2.2 사용자 워크플로

**Before (v0.6.6) — 사용자가 본 것**:
```
VaultPicker dropdown
  → "➕ 새 vault 등록" 클릭
  → 3-input form: name + /absolute/path + personal/shared/agent select
  → 생성
```

**After (v0.6.7) — Wizard 단일 진입**:
```
VaultPicker dropdown
  → "➕ 새 vault 만들기" 클릭 (Link)
  → /vault/new 이동
  → 2-step wizard: name → 확인 (mode fixed personal, path auto)
  → 만들기
```

**단일 진입점 = Wizard**. VaultPicker의 inline form ❌.

### 2.3 mode 정책 일관성

| 위치 | 노출 모드 | 정책 |
|---|---|---|
| **NewVaultWizard** | `personal` 고정 (v0.6.6) | Dashboard 기본 |
| **VaultPicker inline form** | ❌ **제거** (v0.6.7) | Wizard로 위임 |
| **CLI** | `--mode personal\|shared\|agent` | 시스템 내부 (D8 multi-vault, 에이전트) |

→ `shared` / `agent` 노출 ❌ (AGENTS.md §3 over-promise 회피). CLI는 예외 (시스템 내부).

### 2.4 Sidebar.tsx / Layout.tsx 변경 0 (진짜 의미로)

- `Sidebar.tsx` (트리 + TreeNodeView + link): **0 변경**
- `Layout.tsx` (햄버거 + 드로어 + 744px): **0 변경**
- `VaultPicker.tsx`: create form 부분만 제거, dropdown/vault 선택/root 라벨은 **그대로**

→ **Sidebar/Layout 자체는 무변경**. VaultPicker의 **create form 한정** 변경.

---

## 3. 검증

```bash
$ cd dashboard && npm install
$ npx tsc -b --noEmit
(타입 에러 0)

$ npm run build
✓ built (precache 6 entries, ~1098 KiB)  ← -2KB (322 → 254 lines, -21%)
```

### 회귀 가드

| 항목 | 결과 |
|---|---|
| Sidebar.tsx | 변경 0 |
| Layout.tsx | 변경 0 |
| NewVaultWizard.tsx | 변경 0 (v0.6.6 그대로) |
| pytest | 371 passed (무변경) |
| Backend API | 변경 0 |

### 사용자 수동 검증

| 시나리오 | 결과 |
|---|---|
| VaultPicker dropdown → "➕ 새 vault 만들기" 클릭 | ✅ `/vault/new`로 이동 |
| Wizard 2-step 정상 동작 | ✅ name → 확인 |
| Vault 선택/전환 | ✅ 정상 (변경 없음) |
| vaultsRoot 라벨 | ✅ 정상 (변경 없음) |
| Empty state ("no vaults registered") | ✅ 정상 |

---

## 4. 변경 사항 요약

| 파일 | 변경 | 줄 |
|---|---|---|
| `dashboard/src/components/VaultPicker.tsx` | inline form 제거 + `<Link to="/vault/new">` | 322 → 254 (-68, -21%) |
| **`_meta/changelog-v0.6.7.md`** | 신규 | 이 문서 |

---

## 5. v0.6.6 changelog 정정 (정직한 기록)

**v0.6.6 changelog §3에서 잘못 약속**:
> "Sidebar.tsx / Layout.tsx / VaultPicker.tsx 변경 0 (회귀 위험 0)"

→ **이건 사실이지만, 사용자 요구 4가지 중 1가지 (mode/path 묻지 않음)를 미해결**. **v0.6.7이 그 약속의 정정**.

정직한 학습:
- **Surgical 원칙은 "안정성" 도구, "요구 무시" 도구 아님**
- **VaultPicker의 create form은 user-facing 핵심** — 제외하면 안 됨
- "변경 0"보다 "사용자 요구 100%" 우선

---

## 6. 효과

| 지표 | v0.6.6 | v0.6.7 |
|---|---|---|
| Vault 생성 진입점 | 2개 (Wizard + VaultPicker inline) | **1개 (Wizard만)** |
| 사용자가 입력하는 필드 (어디서든) | 3개 (Wizard path) + **3개 (VaultPicker inline)** | **1개 (name)** |
| mode 묻는 곳 | 1개 (Wizard Step 2) | **0개** (Wizard 내부 고정) |
| path 묻는 곳 | 0개 (readonly) + **1개 (VaultPicker input)** | **0개** (VaultPicker 제거) |
| 코드 lines | 322 | 254 (-21%) |

---

## 7. 다음 사이클 후보

1. **P1-1 후속: delete/rename_page 단일화** (archive.py richer surface)
2. **P1-2 SCHEMA sync ADR** (3-way merge vs skip+warn)
3. **P1-3 SQLite WAL + aiosqlite** (멀티 에이전트 동시성)
4. **Dashboard NewVaultWizard 실사용 검증** (방금 머지한 분)
5. **Sidebar에 디제스트 메뉴 추가** (v0.6.4 후속)

---

## 8. 작업 보고

- **무엇**: VaultPicker inline form 제거 (path input + mode 3 select), "➕ 새 vault" 버튼을 Wizard로 navigate
- **왜 (저장 신호)**: ① 재사용성 (Wizard 단일 진입), ② 인수인계 (사용자 요구 100%), ③ 추적 (changelog 정직), ④ 리스크 (Surgical 잘못 적용 학습)
- **검증**: TypeScript PASS, build PASS, Sidebar/Layout/NewVaultWizard 변경 0
- **다음 가능**: delete/rename 단일화, SCHEMA sync, SQLite WAL
