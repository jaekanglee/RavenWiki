---
title: Changelog v0.7.120
created: 2026-07-09
updated: 2026-07-09
type: rule
audience: agent
confidence: high
---

# v0.7.120 — GardenPage object-shaped link_candidates 렌더 크래시 수정

## 무엇을 했는가

Dashboard 정원(Garden) 탭에서 API 200 이후 화면이 공백으로 사라지는 렌더 크래시를 수정했다.

### Root cause

`/api/vaults/{name}/garden`의 `orphan[].link_candidates`는 실제로 다음 shape의 객체 배열을 반환한다:

```json
{"slug":"content/...","title":"...","reason":"본문 내 'index' 키워드 포함","score":5}
```

하지만 Dashboard 타입은 `string[]`로 선언되어 있었고, `GardenPage.tsx`가 `{cand}`를 그대로 React child로 렌더링했다.

브라우저 debug log 실제 에러:

```text
Objects are not valid as a React child (found: object with keys {slug, title, reason, score})
```

즉 v0.7.119의 DB schema drift fix로 API 500은 해결됐지만, 그 다음 단계에서 **frontend type/API contract drift**가 드러난 것.

## 변경

| 파일 | 변경 |
|---|---|
| `dashboard/src/lib/api.ts` | `GardenLinkCandidate = string | {slug,title?,reason?,score?}` 추가, `OrphanPage.link_candidates` 타입 갱신 |
| `dashboard/src/routes/GardenPage.tsx` | candidate를 `candSlug/candTitle/candReason`으로 정규화 후 렌더. object/string 모두 호환 |
| `dashboard/tests/GardenPage.link-candidates.test.tsx` | object-shaped candidate가 렌더되는 regression test 추가 |
| `raven/api/server.py` | stale comment `# list of slugs` → `# list of {slug,title,reason,score} objects` |

## 왜 그렇게 했는가 (§5 4 신호)

- **재사용 가능성**: Garden API contract를 Dashboard 타입과 맞춤. 같은 shape를 수동 연결 버튼에도 재사용.
- **인수인계 필요성**: v0.7.119는 backend 500만 해결했고, v0.7.120은 그 다음 React render crash를 분리 기록.
- **scope/provenance 추적**: `find_link_candidates()`는 원래 객체를 반환한다. 프론트 타입이 틀렸던 것.
- **실패/리스크 기록**: "API는 200인데 화면 공백" = React render crash. debug log와 regression test로 고정.

## 검증

- `npx vitest run tests/GardenPage.link-candidates.test.tsx` → 1 passed
- `npx tsc -b --noEmit` → exit 0
- `npm run build` → `vite_exit=0`, 993 modules transformed
- `/api/vaults/{raven-dev,harumoa,homelab,babymoa,hermes-infra}/garden` → all HTTP 200

## 후속

- GardenPage에는 아직 일부 raw `<button>`/inline style이 남아 있음. 이번 범위는 render crash fix만. UI 정리(§13 Button 통일)는 별도 사이클.