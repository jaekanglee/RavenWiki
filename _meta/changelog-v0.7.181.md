# Raven Changelog — v0.7.181

## 1. 개요

모바일 검색이 로컬 캐시만 훑던 한계를 서버 검색으로 걷어내고, 대시보드 정보구조를 사람 기준으로 다시 세웠다.

- **모바일 보관소 전체 검색** — 열어본 적 없는 문서의 본문도 찾힌다. 목록 API에 본문이 없다는 사실이 그대로 검색 결함이던 상태를 끊었다.
- **전역 탭 8개 → 5칸** — 홈/그래프/검색/로그/린트/정원/워크스페이스/관리가 같은 위계라 390px에서 가로로 잘렸다. 운영 도구 4종을 더보기 하위로 내렸다.
- **홈 = 오늘의 작업대** — 절대경로·용량 중심 vault 콘솔에서 최근 문서·손볼 문서·건강 요약으로 전환. test/tmp vault는 사람용 목록에서 뺐다.

의존성 추가 없음. 진입점 변경 없음. vault 데이터 write 없음.

## 2. 모바일 — 보관소 전체 검색

`SearchScreen`은 `state.documents`를 in-memory로 필터했다. 목록 API(`GET /pages`)는 본문을 주지 않고 본문은 `fetchDocument`로 문서를 열 때만 캐시에 들어오므로, **열어본 적 없는 문서는 본문 검색 대상이 아예 아니었다**. 제목이 우연히 맞을 때만 찾히는 검색이었다.

`DocumentRepository.searchDocuments(vault, query)`를 신설해 서버로 넘겼다.

- 1차 `GET /api/vaults/{vault}/hybrid-search` — 대시보드 `SearchPage`가 쓰는 것과 같은 엔드포인트.
- 결과 0건이면 `GET /api/vaults/{vault}/search`(BM25-lite)로 이어 붙인다. hybrid는 `wiki.db` FTS 인덱스에 올라오지 않은 문서를 못 보고 snippet도 만들지 않는다. 두 번째 파이프에서 나온 오류는 삼키지 않고 그대로 올려 화면에 표시한다.
- 서버 snippet은 `<mark>` 하이라이트 + html 이스케이프가 섞여 오고 Compose `Text`는 이를 렌더링하지 않는다. 태그를 벗기고 엔티티를 되돌려 평문으로 쓴다.
- 검색 히트는 `insertDocumentMetaIfAbsent`로 캐시에 메타만 심는다. 캐시에 없던 문서를 탭해도 기존 `OpenDocument` 경로가 그대로 본문을 채운다 — 검색 결과 전용 상세 화면을 따로 만들지 않았다.
- 빈 쿼리는 서버를 때리지 않고, 새 쿼리는 이전 검색 코루틴을 취소한다. 220ms debounce는 대시보드와 같은 값을 유지.

vault 선택이 바뀌면 검색 쿼리·결과·오류가 함께 비워진다. (vault 차원은 v0.7.180 사이클의 `(vault, id)` 복합 PK 위에 그대로 얹혀 있다.)

### 회귀 가드 4건

RED를 먼저 세웠다 — `searchDocuments` 부재로 `compileDebugUnitTestKotlinAndroid`가 실패하는 상태에서 구현을 시작했다.

| 테스트 | 잠근 것 |
|---|---|
| `searchFindsDocumentWhoseBodyIsNotCached` | 캐시 본문이 전부 빈 상태를 먼저 단언한 뒤(전제 붕괴 방지) 서버 히트가 나오는지 |
| `searchIsScopedToRequestedVaultAndSkipsBlankQuery` | 요청 경로가 `/api/vaults/{vault}/hybrid-search`이고 빈 쿼리는 요청 자체가 없음 |
| `searchFallsBackToSnippetEndpointWhenHybridHasNoHits` | hybrid 0건 → BM25-lite로 이어지고 snippet이 평문으로 벗겨짐 |
| `searchHitOutsideCacheBecomesOpenable` | 캐시에 없던 히트를 열면 제목·본문이 채워짐 |

## 3. 대시보드 — 전역 탭 5칸

`GLOBAL_NAV` 하나에 8개가 평평하게 들어 있었다. `PRIMARY_NAV`(홈·검색·그래프·정원)와 `MORE_NAV`(로그·린트·워크스페이스·관리)로 갈라 레일을 5칸으로 고정했다.

- 레일 = 탐색 4개 + 더보기 1개. 가로 스크롤에 의존하던 구조를 없앴다.
- 390px 이하에서는 비활성 탭이 아이콘만 남는다. 활성 탭만 라벨을 유지하고, 접힌 탭은 `aria-label` + `title`로 이름을 보존한다.
- 더보기는 경로 이동과 Esc로 닫히고, 하위 경로에 있으면 트리거 자체가 활성으로 보인다.

반응형 계약은 `planSectionNav(width)` / `isMoreNavActive(pathname)` 순수 함수로 노출해 320/390/744/1024/1440 다섯 폭 전부를 테스트에서 확인한다 (`dashboard/tests/Layout.section-nav.test.tsx`). 스크린샷 회귀는 Playwright가 없어 넣지 않았다 — 브라우저 러너 도입은 의존성 추가 승인 사항.

## 4. 대시보드 — 홈을 작업대로

`HomePage`는 vault 카드(이름·모드·절대경로·용량·로그 수)가 첫 화면이었다. 사람이 홈에서 하려는 일은 vault 운영이 아니라 "어제 쓰던 것 이어 쓰기"다.

- `최근 문서` — `updated` 내림차순, updated 없는 문서는 뒤로.
- `손볼 문서` — SCHEMA status 4종 중 `stale`·`contested`만. `archived`는 격리된 것이므로 부르지 않는다.
- 건강 요약 3칸 — 페이지 수 / 깨진 링크 / 손볼 문서. 활성 vault 하나만 본다.
- 보관소 목록은 맨 아래로. `test`·`tmp`·`scratch` 계열 이름과 `/tmp`·`/var/folders` 경로를 스크래치로 판별해 기본 숨김이며, "스크래치 N개 보기" 토글로만 드러난다.

선별 규칙은 `pickRecentPages` / `pickUnfinishedPages` / `isScratchVault`로 분리해 렌더 없이도 검증한다. 이름 오탐 가드도 포함 — `protest-notes`는 스크래치가 아니다.

## 5. 문서

`docs/모바일-오프라인-보관함-실기-검증-절차.md` — 사람이 실기로 밟을 3단계(비행기 모드 작성 → 재연결 전송 → 동시 수정) 체크리스트.

3단계는 "충돌이 잡히는지"가 아니라 **어느 쪽 글이 지워지는지 눈으로 확인**하는 절차로 썼다. `PendingWrite.failureKind`에 `CONFLICT`(409/412) 분기가 있지만 모바일 PUT은 `{"content": ...}`만 보내고 `precondition`을 싣지 않는다. 서버 `update_page`는 토큰이 없으면 검사를 건너뛰므로 **409가 나올 수 없고, 앱 저장이 PC 편집을 조용히 덮는다.** 문서에 그 사실과 재현 순서를 적었다.

## 6. 검증

| 항목 | 결과 |
|---|---|
| `:shared:testDebugUnitTest` | 17 passed, 0 failed (기존 13 + 신규 4) |
| `:shared:verifySqlDelightMigration` | BUILD SUCCESSFUL |
| `:androidApp:assembleDevDebug` | BUILD SUCCESSFUL |
| dashboard `npx vitest run` | 42 files, 197 passed, 1 skipped, 0 failed |
| dashboard `npx tsc -b --force` | exit 0 |

vitest의 skip 1건은 `All-modals-portal.test.tsx`의 기존 `it.skip` — 이 사이클에서 손대지 않았다.

에뮬레이터·실기 실행은 하지 않았다 (운영 규약). 사람이 확인할 항목은 본 사이클 보고에 체크리스트로 남겼다.

## 7. 남은 백로그

| 항목 | 우선순위 | 비고 |
|---|---|---|
| 모바일 PUT에 `precondition` 실어 보내기 | P1 | 서버는 이미 `GET /pages/{slug}` 응답에 토큰을 준다. 실으면 `failureKind=CONFLICT`가 살아나고 앱이 "서버가 먼저 바뀌었습니다"를 띄울 수 있다. 지금은 조용한 lost update |
| 모바일 검색 오프라인 fallback | P2 | 서버가 닿지 않으면 결과 0건 + 오류 문구다. 캐시 본문으로 부분 검색을 되살릴지는 별개 결정 |
| 대시보드 스크린샷 회귀 | P2 | 반응형을 픽셀로 잠그려면 Playwright 도입 승인 필요 |
| Crashlytics 도입 여부 | 사용자 결정 | SDK/plugin 미통합 상태. `google-services.json`과 App Distribution만 있어 배포 기기 크래시는 어디에도 남지 않는다 |
