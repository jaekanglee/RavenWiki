# Changelog v0.7.89 — Lite bootstrap 3종 read-only viewer (Dashboard /guides)

> **BLUF**: vault 운영자가 "이 vault의 지침이 뭐지?"를 즉시 확인할 수 있도록 Lite bootstrap 3종(`_meta/agents/SCHEMA.md` / `_meta/agents/PROJECT-WORKFLOW.md` / `log.md`) read-only viewer 추가. **신규 진입점 0** (Tier 1 = Raven 4개 진입점 정책 유지) — `/guides` 라우트 + VaultManage 행 액션 "📖 지침 보기"로 진입. TOP nav 탭 9 → 8 (탭 과잉 방지, surgical 배치). API: 화이트리스트 3종만 노출 (그 외 403 fail-closed, Tier 1 leak 방지). 테스트 8/8 PASS + 회귀 95/95 PASS + Dashboard `npm run build` (tsc strict) clean.

이전 changelog: `_meta/changelog-v0.7.88.md`

---

## §0 — 변경 요약 (6 파일 수정 + 3 파일 신설)

| 파일 | 변경 | LOC |
|---|---|---|
| `raven/api/server.py` | `GET /api/vaults/{name}/guide/{kind:path}` endpoint 신설 + `_LITE_GUIDE_WHITELIST` | +60 |
| `dashboard/src/lib/api.ts` | `fetchGuide()` + `LITE_GUIDE_KINDS` + `LiteGuideResult` 타입 | +29 |
| `dashboard/src/components/GuidesViewer.tsx` (신설) | split view 본체 (page + drawer 재사용). `compact`/`vaultLocked`/`onClose` props | +355 |
| `dashboard/src/routes/GuidesPage.tsx` (신설 → thin wrapper로 교체) | PageHeader + GuidesViewer 임베드 + `?vault=` deep-link | +50 |
| `dashboard/src/App.tsx` | `<Route path="/guides">` 신설 | +3 |
| `dashboard/src/components/Layout.tsx` | NAV_TABS에서 "지침" 제거 (탭 9 → 8) | +2 |
| `dashboard/src/routes/VaultManage.tsx` | `ActionIcon.BookText` + 행/compact "📖 지침 보기" (drawer 토글) + drawer overlay + Esc 핸들러 | +133 |
| `dashboard/src/styles/globals.css` | `@keyframes raven-drawer-slide` (우측 slide-in) | +6 |
| `tests/test_v0_7_89_guide_endpoint.py` (신설) | 회귀 가드 8건 (200/403/404) | +174 |

---

## §1 — 무엇을 만들었나

### 1.1 진입점 정책 (Tier 1)

**신규 진입점 추가 ❌**. Raven의 4개 진입점(CLI / HTTP API / Dashboard / MCP) 정책(AGENTS.md §2) 유지. `/guides`는 Dashboard 내부 라우트이지 진입점이 아님. 진입점 어댑터 아님.

### 1.2 사용자 흐름

운영자가 vault의 Lite bootstrap 3종을 확인하는 경로 1개:

```
VaultManage → 행 액션 "📖 지침 보기" → 새 탭 /guides?vault=X
                                                  ↓
                                ┌──────────── GuidesPage ────────────┐
                                │ [Vault ▾]    in <vault>            │
                                │                                   │
                                │ ┌─────────┐  ┌─────────────────┐   │
                                │ │ 🧬 SCHEMA│  │  markdown       │   │
                                │ │ 🛠 WORKFLOW │  preview       │   │
                                │ │ 📋 log.md │  (MarkdownView)  │   │
                                │ └─────────┘  └─────────────────┘   │
                                └───────────────────────────────────┘
```

- **TOP nav 진입 ❌**: 탭 9개 과잉 회피. "지침 보기"는 vault-bound lookup이지 global 1등 시민이 아님.
- **VaultManage 짝**: 이미 있는 "지침 검증 / 지침 당겨오기"와 같은 자리에 배치 → "mismatch ❓ 원본이 뭐지? → 📖 보기" 워크플로우 자연스러움.
- **새 탭 (window.open)**: VaultManage 컨텍스트(다른 vault들과 비교)를 잃지 않음.

### 1.3 API contract

```
GET /api/vaults/{name}/guide/{kind}
```

- kind ∈ `_LITE_GUIDE_WHITELIST` (3종):
  - `_meta/agents/SCHEMA.md`
  - `_meta/agents/PROJECT-WORKFLOW.md`
  - `log.md`
- 200: `{ok, vault, kind, content, size, modified}` (raw/ endpoint와 동일 shape)
- 403: 화이트 외 kind (Tier 1 leak 방지 핵심)
- 404: vault 없음 또는 화이트 kind지만 파일 부재
- 400: 화이트 kind 매칭 후 path가 디렉토리 (`fp.is_dir()` defense-in-depth)

### 1.4 Frontend contract (`fetchGuide`)

```ts
export const LITE_GUIDE_KINDS = [
  "_meta/agents/SCHEMA.md",
  "_meta/agents/PROJECT-WORKFLOW.md",
  "log.md",
] as const;
export type LiteGuideKind = (typeof LITE_GUIDE_KINDS)[number];
export async function fetchGuide(vault: string, kind: LiteGuideKind): Promise<LiteGuideResult | null>;
```

---

## §2 — 왜 이렇게 배치했나 (디자인 결정)

### 2.1 TOP nav 대신 VaultManage 행 액션

후보 3개를 평가:

| 후보 | 탭 수 | 연결성 | 워크플로우 자연스러움 | 결정 |
|---|---|---|---|---|
| A. TOP nav + `/guides` 페이지 | 9 (과잉) | 단절 (어디서든 보임) | 매번 nav 클릭 | ❌ |
| B. VaultManage 행 액션 — 새 탭 | 8 (유지) | bootstrap status 짝 | 컨텍스트 손실 | ❌ (rejected after first review) |
| C. **VaultManage 행 액션 — 같은 탭 drawer** | **8 (유지)** | **bootstrap status 짝** | **mismatch → 📖 → 비교, 컨텍스트 100% 유지** | **✅** |
| D. VaultManage 인라인 패널 | 8 | 좋음 | 좋음 | 검토 (viewport 좁음) |

**C 선택 이유**:
- 사용자가 이미 "지침 검증" / "지침 당겨오기"로 Lite bootstrap 상태를 본 자리 → 같은 자리에 "보기"가 있어야 함.
- TOP nav = global 1등 시민. 가이드는 vault-bound 조회 → 부적합.
- 처음엔 B(새 탭)로 갔으나 **컨텍스트 손실** (다른 vault들의 status 비교 불가) 발견 → drawer로 재설계.
- drawer = Jira/Notion 표준 (이슈 페이지 우측에 댓글/활동 로그 inline expand). 즉시 visible feedback.
- 새 탭 ❌: 다른 vault들과 비교하는 "lit review" 워크플로우가 깨짐. 사용자가 짚어줘서 catch.
- 변경 footprint: 1 endpoint + 1 viewer(재사용) + 1 page wrapper + 1 라우트 + 1 nav 수정 + 1 행 액션 + 1 drawer + 1 keyframe = 6 file edit + 3 file new. viewer는 page/drawer 양쪽 재사용으로 DRY.

### 2.1.1 GuidesViewer 추출 (재사용)

split view 본체를 `GuidesViewer` 컴포넌트로 분리:
- **page** (`/guides`): 자유 vault 변경 (`vaultLocked=false`), PageHeader + 안내 문구 표시 (`compact=false`).
- **drawer** (VaultManage 우측): vault 잠금 (`vaultLocked=true`, 선택한 그 vault만), 좁은 폭 (`compact=true`, list 200px/240px), ✕ 닫기 버튼 + Esc.

**props surface**: `{ vaults, activeVault, vaultLocked?, defaultKind?, onClose?, compact? }`. 단일 책임 (split view), 호출자가 page vs drawer 결정.

### 2.2 403 fail-closed

화이트 외 경로는 **파일 존재 여부와 무관**하게 403. Tier 1(`_meta/system/`) / 사용자 페이지(`content/`) / 경로 traversal 모두 fail-closed. defense-in-depth:
- 화이트 매칭 → 403 (가장 먼저)
- vault 부재 → 404
- 파일 부재 → 404
- 디렉토리 → 400 (실제 발생 케이스 0, 가드만 유지)

### 2.3 read-only 강제

Lite bootstrap 3종은 AGENTS.md §4 Tier 2 표면 — **운영자가 직접 편집하지 않음**. UI에 `🔒 read-only` 배지 + 안내 문구 "수정이 필요하면 `raven meta sync --lite` 또는 VaultManage의 '지침 업뎃' 사용". Dashboard에서 PUT endpoint 미노출.

---

## §3 — 검증

### 3.1 pytest (신규 + 회귀)

```
tests/test_v0_7_89_guide_endpoint.py .......... 8/8 PASS
  ├─ test_read_guide_schema_200              PASS
  ├─ test_read_guide_project_workflow_200    PASS
  ├─ test_read_guide_log_md_200              PASS
  ├─ test_read_guide_rejects_system_path_403 PASS  (Tier 1 leak 방지)
  ├─ test_read_guide_rejects_content_path_403 PASS
  ├─ test_read_guide_403_for_system_path     PASS  (fail-closed)
  ├─ test_read_guide_403_for_path_traversal  PASS  (../)
  └─ test_read_guide_404_for_unknown_vault   PASS

회귀 (raw / vault / API 95 tests): PASS
```

### 3.2 Dashboard typecheck + build

```
$ npm run build
✓ 992 modules transformed.
dist/assets/index-DmUKSb3t.js  1,704.39 kB
✓ built in 1.80s
```

### 3.3 Live API 검증 (in-process TestClient)

```
created: my-vault at /tmp/.../my-vault
  log.md:         True
  SCHEMA.md:      True
  PROJECT-WORKFLOW: True

GET /api/vaults/my-vault/guide/log.md             → 200 (size=650)
GET /api/vaults/my-vault/guide/SCHEMA.md          → 200
GET /api/vaults/my-vault/guide/system/OPERATIONS  → 403 (whitelist)
GET /api/vaults/does-not-exist/guide/log.md       → 404
```

---

## §4 — AGENTS.md / SCHEMA.md 영향

- **AGENTS.md §2 (4개 진입점)**: 변경 없음. `/guides`는 Dashboard 내부 라우트, 신규 진입점 아님.
- **AGENTS.md §4 (Lite bootstrap 정책)**: 변경 없음. 3종 그대로. **읽기 전용 viewer 추가는 §4의 정책과 정합** (운영자가 보기만 가능, 편집은 도구 통해서).
- **AGENTS.md §7 (권한)**: 변경 없음. `/guide/{kind}` GET은 read-only, write 권한 불필요.
- **SCHEMA.md**: 변경 없음.

---

## §5 — 후속 작업 후보 (deferred)

- "지침 비교(diff)" — 두 vault 간 또는 vault vs 템플릿 diff 뷰 (v0.7.90+ 검토)
- "raw/ 폴더 안내 페이지" — vault 운영자가 raw/ 폴더 구조를 처음 볼 때 onboarding (Lite bootstrap 패턴과 별도)
- MCP `wiki_read` 도구에 `kind=guide` 옵션 추가 (에이전트가 SCHEMA/PROJECT-WORKFLOW를 MCP로 직접 fetch) — v0.7.90+ 검토 (현재는 사람이 API로만 조회)
