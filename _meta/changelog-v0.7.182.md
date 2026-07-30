# Raven Changelog — v0.7.182

## 1. 개요

모바일 저장이 PC 편집을 조용히 덮어쓰던 경로를 닫았다. v0.7.181 백로그 P1 소진.

서버는 v0.7.178부터 lost update를 막을 준비가 다 돼 있었다 — `GET /pages/{slug}`가 `precondition` 토큰을 주고 `PUT`이 그 토큰을 받아 `stale_precondition` → 409를 낸다. 앱만 토큰을 싣지 않았고, 서버는 토큰이 없으면 검사를 건너뛰므로 **모바일 저장은 항상 무조건 승리**했다. `PendingWrite.failureKind`의 `CONFLICT` 분기는 도달 불가능한 코드였다.

의존성 추가 없음. 진입점 변경 없음. vault 데이터 write 없음.

## 2. 로컬 스키마 — 상태 토큰 보관 (schema 4)

토큰을 실어 보내려면 "내가 읽은 시점의 서버 상태"를 기기에 들고 있어야 한다. `4.sqm`으로 두 칸을 추가했다 (ADD COLUMN이라 기존 행은 NULL = 토큰 미상 = 검사 생략, 하위 호환).

| 칸 | 뜻 |
|---|---|
| `Document.precondition` | 이 본문을 읽은 시점의 서버 상태 |
| `PendingWrite.basePrecondition` | 큐에 넣을 때의 base — 전송 시점 값이 아니라 **편집이 출발한 지점** |

두 칸을 나눈 이유: 오프라인에서 쓴 글은 며칠 뒤에 전송될 수 있다. 전송 시점의 최신 토큰을 쓰면 "내가 본 것과 서버가 같다"는 단언이 거짓이 되어 검사가 무력화된다.

## 3. 쓰기 경로

- `fetchDocument`가 본문과 토큰을 **한 문장에서 함께** 저장한다 (`updateDocumentContent`). 본문과 그 본문의 출처 상태는 갈라지면 안 된다.
- `saveDocument`는 `INSERT OR REPLACE`로 행을 덮기 **전에** base를 읽는다. 순서를 뒤집으면 토큰이 자기 자신에 의해 지워진다.
- `PUT` body에 `precondition`을 싣는다. `ravenJson`에 `explicitNulls = false`를 켜서 **토큰을 모를 때는 필드 자체가 빠진다** — 서버 계약에서 `""`는 "파일 부재 단언"이고 필드 없음은 "검사 생략"이라, null을 실어 보내면 의미가 흐려진다.
- PUT 성공 응답의 새 토큰으로 로컬을 갱신한다. 이걸 빼먹으면 연속 수정 두 번째가 **방금 자기가 쓴 글과** 충돌한다.
- `deleteDocument`도 같은 base를 큐에 넣는다.

## 4. 충돌을 화면까지 올린다

DB에 `failureKind=CONFLICT`만 적고 끝내면, 사용자 입장에서는 "저장했는데 조용히 안 올라감"으로 바뀔 뿐 이전보다 나아지지 않는다. `WriteOutcome`(`Synced` / `Queued` / `Conflict`)를 `saveDocument` 반환값으로 올려 스낵바를 구분한다.

| 결과 | 사용자에게 보이는 것 |
|---|---|
| `Synced` | (조용히 성공) |
| `Queued` | "지금 PC에 닿지 않아 기기에만 저장했습니다. 재연결 후 당겨 내리면 올라가요." |
| `Conflict` | "PC에서 이 문서가 먼지 바뀌어 서버에 반영하지 않았습니다. 문서를 다시 받아 합치세요." |

충돌 시 큐 항목과 payload는 지우지 않는다 — 사용자가 합칠 원본이 사라지면 안 된다.

## 5. 회귀 가드 6건 (RED 먼저)

`searchDocuments`가 없던 v0.7.181과 같은 방식으로, `basePrecondition` 부재로 컴파일이 깨지는 상태에서 시작했다.

| 테스트 | 잠근 것 |
|---|---|
| `fetchDocumentStoresServerPrecondition` | GET 응답의 토큰이 로컬에 남는다 |
| `putSendsPreconditionReadFromServer` | PUT body에 그 토큰이 실리고, 응답의 새 토큰으로 갱신된다 |
| `queuedWriteKeepsBasePreconditionUntilFlush` | 오프라인에서 굳은 base가 나중 전송까지 그대로 간다 |
| `stalePreconditionIsReportedAsConflictAndKeepsQueueEntry` | 409 → `CONFLICT` + 큐·payload 보존 |
| `documentWithoutKnownPreconditionOmitsTheField` | 토큰 미상이면 필드 자체가 빠진다 |
| `saveOutcomeTellsSyncedQueuedAndConflictApart` | 세 결과가 서로 구분된다 |

## 6. 검증

| 항목 | 결과 |
|---|---|
| `:shared:testDebugUnitTest` | 23 passed, 0 failed (v0.7.181의 17 + 신규 6) |
| `:shared:verifySqlDelightMigration` | BUILD SUCCESSFUL (schema 4 마이그레이션 + CREATE 정합) |
| `:androidApp:assembleDevDebug` | BUILD SUCCESSFUL |
| `pytest tests/ -q` | 769 passed, 1 skipped |

에뮬레이터·실기 실행은 하지 않았다 (운영 규약).

## 7. 이번 사이클에서 발견한 별건

**모바일 신규 문서 작성은 서버에 안 올라갈 가능성이 크다.** 앱은 생성도 `PUT /pages/{slug}`로 보내는데 서버 `update_page`는 파일이 없으면 404다 (생성은 `POST /pages`). 즉 새 문서는 `REMOTE_FAILURE`로 큐에 남아 영구 재시도한다. unit test는 mock 서버라 이 차이를 못 잡았다.

이번 패치 범위(precondition)와 별개 결함이므로 손대지 않았다. 실기 절차 §1~§2를 밟으면 바로 드러난다 — `raven log list`에 create 기록이 없고 `content/`에 파일이 안 생기면 이 건이다.

## 8. 남은 백로그

| 항목 | 우선순위 | 비고 |
|---|---|---|
| 모바일 신규 문서 생성 경로 (PUT → POST) | P0 후보 | §7. 확인되면 즉시 |
| 충돌 문서 병합 UX | P2 | 지금은 "다시 받아 합치세요" 안내까지. 양쪽 본문을 나란히 보여주는 화면은 별도 |
| 모바일 검색 오프라인 fallback | P2 | v0.7.181에서 이월 |
| 대시보드 스크린샷 회귀 | P2 | Playwright 도입 승인 필요 |
| Crashlytics 도입 여부 | 사용자 결정 | 미통합 상태 유지 |
