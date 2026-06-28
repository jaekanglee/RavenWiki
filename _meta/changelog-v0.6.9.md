# raven v0.6.9 — Wizard 후 vault active race hotfix (P15)

> **핵심**: v0.6.8에서 Wizard가 `setActiveVault(name)` + `navigate(/page/<name>/content/index)` 둘 다 호출했지만, **Layout의 `ctx.vault` state가 stale**인 경우에 URL과 vault state가 어긋나면서 `Not found: content/index in vault <oldvault>`가 뜨는 race가 남았음. v0.6.9에서 **URL의 `:vault` 파라미터를 SOT로** 만들어서 Layout state와 무관하게 항상 URL 우선 동작.

릴리스 일자: 2026-06-28
이전: v0.6.8 (Wizard redirect 버그 hotfix)

---

## 한 줄 요약

Dashboard 라우팅을 `/page/:vault/*`로 바꾸고 `PageView`가 `params.vault`를 최우선으로 사용. **Wizard 후 vault 전환 race 차단 — 새 vault 만들고 도착한 URL은 항상 그 vault를 가리킴.**

---

## 1. 발견 경위

사용자 보고 (2026-06-28):
> "what이라는 볼트를 만들었더니 `/page/what/content/index`로 갔는데 화면엔 `Not found: content/index in vault develop`"

**URL은 `what`, vault state는 `develop`** — v0.6.8의 setActiveVault + index.md 자동 생성은 동작했지만, PageView가 `ctx.vault`를 우선시하면서 Layout의 stale state를 따라간 게 원인.

## 2. 근본 원인

`PageView.tsx` (이전):
```ts
const vault = ctx?.vault || getActiveVault() || "default";
```

- `ctx.vault` = Layout의 React state. Wizard 직후 remount가 즉시 안 일어나면 stale.
- `getActiveVault()` = localStorage. Wizard가 `setActiveVault(name)` 호출했지만 React state와 동기화가 race.
- URL은 `/page/what/content/index`인데, vault는 `develop` → 잘못된 vault에서 content/index 조회 → 404.

## 3. 패치 (3가지)

### 3.1 라우트 변경 — `dashboard/src/App.tsx`

```diff
- <Route path="/page/*" element={<PageView />} />
+ <Route path="/page/:vault/*" element={<PageView />} />
```

`/page/<vault>/<slug>` 형태로 명시. URL이 곧 vault 진실.

### 3.2 PageView 변경 — `dashboard/src/routes/PageView.tsx`

```diff
+ // v0.6.9 (P15 fix): URL의 :vault 파라미터를 SOT로 사용.
+ const vaultFromUrl = params.vault;
  const ctx = useOutletContext<Ctx>();
- const vault = ctx?.vault || getActiveVault() || "default";
+ const vault = vaultFromUrl || ctx?.vault || getActiveVault() || "default";
```

URL → Layout → localStorage 순서로 우선순위. URL이 있으면 그걸 신뢰.

### 3.3 회귀 테스트 — `dashboard/tests/PageView.vault-sot.test.tsx`

4개 케이스:
- `/page/what/content/index` → vault="what", slug="content/index"
- `/page/develop/content/foo` → vault="develop", slug="content/foo"
- `/page/infra` → vault="infra", slug=""
- `/page` (단독) → 라우트 mismatch (가드)

## 4. 검증

- `vitest run` → 신규 4/4 통과, 기존 wikilink 1개 실패는 master에서 이미 깨져있던 거 (무관)
- `tsc -b` → exit 0, 에러 없음

## 5. 사용자 영향

| Before | After |
|---|---|
| 새 vault 만들고 도착한 페이지에 옛 vault 이름 404 | 새 vault 이름으로 정확히 조회 |
| Layout state 동기화에 의존 | URL이 곧 진실 — state와 무관 |

## 6. 후속 후보

- P14 (vite.config PWA cache) 별도 PR — `navigateFallback: null` + `/api/*` NetworkFirst
- Sidebar/VaultPicker에서 `/page/<vault>/...` 링크 형태로 변경 (현재 `/page/<slug>` 형태 있으면 그쪽도 수정)
- ADR: "URL as single source of truth for routing" (`_meta/decisions/`)