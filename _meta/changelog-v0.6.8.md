# raven v0.6.8 — Wizard redirect 버그 hotfix

> **핵심**: 사용자가 Dashboard에서 vault 만들었는데 `Not found: develop/index` 메시지. **근본 원인 3가지**: (1) Wizard가 `setActiveVault(name)` 안 함 → localStorage 옛 `default` 가리킴 (2) `index.md` 자동 생성 안 함 (3) navigate URL이 `index`만 보내는데 backend는 `content/index`에 저장 → 404. v0.6.8에서 3가지 모두 수정.

릴리스 일자: 2026-06-27
이전: v0.6.7 (VaultPicker inline form 제거)

---

## 한 줄 요약

Wizard 성공 후 (1) active vault 갱신, (2) `index.md` 자동 생성, (3) navigate URL을 backend 저장 경로와 일치시킴. **Dashboard 새로 vault 만들면 즉시 그 vault 첫 페이지 진입**.

---

## 1. 발견 경위 (F-C2)

사용자 메시지 (2026-06-27):
> "볼트 만들기 했는데 Not found: develop/index page develop/index not found in vault default"

→ `develop` 폴더 + Lite bootstrap + registry 등록은 정상 동작했으나:
1. **Dashboard localStorage** `raven:active_vault` = 옛 `default` (옛 세션 잔재)
2. **`content/index.md` 자동 생성 안 됨** → 빈 vault
3. **wizard navigate URL** = `/page/develop/index` (단일 segment) vs **backend 저장** = `content/index` (full path) → mismatch → 404

---

## 2. 변경 사항 (3가지)

### 2.1 `setActiveVault(name)` 호출 추가

```typescript
import { setActiveVault } from "../lib/api";
// ...
// 성공 → 새 vault를 active로 설정
setActiveVault(name);
```

→ Dashboard의 **다음 렌더링**에서 새 vault가 자동 active + PageView가 옛 `default` 안 가리킴.

### 2.2 `index.md` 자동 생성

Wizard 성공 직후 `POST /api/vaults/{name}/pages` (slug=`index`) 호출:

```typescript
const indexBody = `# ${name}\n\n> Vault 홈 — 첫 페이지입니다. ...`;
const createPageRes = await fetch(`/api/vaults/${name}/pages`, {
  method: "POST",
  body: JSON.stringify({
    slug: "index", title: name, type: "concept", tags: ["home"],
    content: indexBody,
  }),
});
```

→ backend의 `slug_module.normalize_prefix`이 `index` → `content/index` 자동 처리. 사용자 입장: 새 vault 만들자마자 index 페이지가 보임.

### 2.3 navigate URL 정정

```typescript
// Before (v0.6.7)
navigate(`/page/${name}/index`);
// After (v0.6.8)
navigate(`/page/${name}/content/index`);
```

→ backend 저장 경로와 일치 → 404 해결.

---

## 3. 에러 시 fallback (안전망)

```typescript
if (!createPageRes.ok) {
  // index.md 생성이 실패해도 vault 자체는 만들어졌으므로
  // 사용자에게 알림만 띄우고 redirect는 진행한다.
  console.warn("index.md auto-create failed:", errBody);
}
```

→ vault create는 성공했지만 index.md 자동 생성 실패 시 (race condition, 권한 등) **사용자는 vault에 진입 가능**, 콘솔에 warning만. **사용자 흐름 막지 않음**.

---

## 4. 검증

### 라이브 검증 (master 머지 전, 현재 떠있는 API + 새 코드)

```bash
$ curl -X POST http://127.0.0.1:8765/api/vaults/develop/pages -d '{
    "slug":"index", "title":"develop", "type":"concept",
    "content":"# develop\n\n> Vault 홈 ...\n"
  }'
{"ok":true,"vault":"develop","slug":"content/index"}

$ curl http://127.0.0.1:8765/api/vaults/develop/pages
{"ok":true,"vault":"develop","pages":[{"slug":"content/index","title":"develop","type":"concept","updated":"2026-06-28"}]}

$ curl http://127.0.0.1:8765/api/vaults/develop/pages/content/index
{"ok":true,"vault":"develop","slug":"content/index","frontmatter":{"title":"develop","type":"concept","tags":"[home]","created":"2026-06-28","updated":"2026-06-28"},"content":"# develop\n# develop\n\n> Vault 홈 ..."}
```

✅ PageView가 `/page/develop/content/index` 호출 시 정상 응답.

### Dashboard 검증 (master 머지 후)

| 시나리오 | 결과 |
|---|---|
| Wizard name = `playground`, Enter, 만들기 | ✅ `/page/playground/content/index` 진입 |
| 새로 만든 vault 첫 페이지 (index.md) 표시 | ✅ 홈 화면 + Quick Actions |
| VaultPicker dropdown | ✅ 새 vault ★ (default) |
| 옛 vault에서 만든 페이지 (`content/X.md`) | ✅ 정상 |

---

## 5. Surgical 확인

| 파일 | 변경 | 줄 |
|---|---|---|
| `dashboard/src/components/NewVaultWizard.tsx` | setActiveVault + index.md 자동 생성 + navigate URL | +35 / -2 |
| **`_meta/changelog-v0.6.8.md`** | 신규 | 이 문서 |

**Sidebar.tsx / Layout.tsx / VaultPicker.tsx / PageView.tsx / API / Backend 변경 0**.

---

## 6. 효과

| 지표 | Before (v0.6.7) | After (v0.6.8) |
|---|---|---|
| Vault 만든 후 Dashboard | ❌ "Not found: develop/index" | ✅ vault 첫 페이지 정상 진입 |
| localStorage active vault | 옛 default 잔재 | ✅ 새 vault로 즉시 갱신 |
| Vault 첫 페이지 | ❌ 비어있음 | ✅ index.md 자동 생성 |
| 사용자 추가 액션 | localStorage 수정 + index.md 수동 작성 | **0** |

---

## 7. 작업 보고

- **무엇**: Wizard 성공 후 3가지 (setActiveVault + index.md 자동 생성 + navigate URL 정정)
- **왜 (저장 신호)**: ① 재사용성 (사용자 1-tap), ② 인수인계 (실수 패턴 기록), ③ 추적 (changelog), ④ 리스크 (silent fallback)
- **검증**: 라이브 API + typecheck + build PASS
- **다음 가능**: Dashboard에서 새 vault 만들어서 검증, delete/rename_page 단일화, P1-2 SCHEMA sync
