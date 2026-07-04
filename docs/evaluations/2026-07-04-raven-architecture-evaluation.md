# Raven 아키텍처 평가 (2026-07-04)

> **결론(BLUF): 종합 3.0/5.** 선언된 아키텍처(마크다운 SoT + 단일 쓰기 계약 + 4 진입점 + 재생성 가능한 파생물)는
> 명료하고 문서·테스트로 집행하려는 문화도 실재한다. 그러나 **선언과 구현 사이의 이행률이 절반**이다:
> MCP는 쓰기 계약에 미가입 상태이고(contracts.py:28-31이 v0.6.3로 미룬 것이 v0.7.66에도 미이행),
> SoT→인덱스 재생성 계약은 쓰기 시점에 강제되지 않으며, frontmatter 파서 5벌·아카이브 4벌·검색 3벌·락 2체계가
> 표면마다 다른 동작을 만든다. 구조적 P0 4건을 수렴하면 아키텍처 자체는 3.8~4.0까지 올라갈 골격이다.

- 평가 관점: **아키텍처 건전성** (계층 규율, 계약 집행, 일관성, 중복, 동시성·데이터 안전 구조)
- 평가 방법: 4개 병렬 심층 분석 (core 엔진 / 진입점 3종 / Dashboard / 테스트·운영) + 실행 검증 일부
  (frontmatter 왕복 손실은 코드 실행 재현, 테스트 스위트는 실측 실행: tests/ 604 passed 31s, vitest 117 passed 6s)
- 평가 시점 버전: v0.7.66 (commit `a8deb7e`)
- 자매 문서: [2026-07-04-raven-product-evaluation.md](2026-07-04-raven-product-evaluation.md) (제품 관점 3.3/5)

---

## 1. 채점표 — 종합 **3.0 / 5**

| # | 축 (가중치) | 점수 | 근거 요약 |
|---|---|---|---|
| 1 | 계층 규율 — 진입점이 core를 경유하는가 (20%) | **2.5** | CLI/API 쓰기는 contracts 경유 ✅. MCP는 전면 우회(A#1). CLI→MCP, API→MCP 역의존. 인덱스 빌더·export가 core 밖 `scripts/`에 존재 |
| 2 | SoT→파생 일관성 계약 (20%) | **2.0** | 쓰기가 인덱스를 갱신하지 않고, `connect()`는 stale 무시, MCP 재색인은 경로 오류로 영구 no-op(A#2), inline 폴백은 스키마 비호환 |
| 3 | 데이터 안전·동시성 구조 (20%) | **2.0** | frontmatter 블록 YAML 왕복 파괴 재현됨(A#3), 락 2체계 상호배제 실패, stale lock 영구 고착, 페이지/로그 쓰기 비원자. 단 curator 서브시스템은 모범(5점감) |
| 4 | 모듈 응집·중복 통제 (15%) | **2.5** | frontmatter 파서 5벌, 아카이브 4벌, 검색 3벌, slug 해석 3벌, wikilink regex 4벌. 프론트도 타입 3중 선언·isMobile 훅 5벌 |
| 5 | 진입점 표면 각자의 설계 품질 (10%) | **3.5** | slug.py 경로 방어·MCP 멱등성 설계·raw 경로 다층 가드는 수준급. REST 관례 혼재, CORS `*`+무인증, 죽은 엔드포인트 1개 |
| 6 | 테스트·문서·결정 추적 구조 (15%) | **4.5** | 4 진입점 전부 실동작 테스트 그린(721개, 37s), write 계약이 테스트로 집행, changelog 110개+ADR 5개. 감점: 죽은 스위트 2개, CI 부재 |

**핵심 진단 한 줄**: 이 코드베이스의 문제는 설계가 없어서가 아니라, **좋은 설계(contracts, slug, curator, archive)가 이미 레포 안에 있는데 절반의 코드가 그걸 안 쓰고 자기 버전을 만든 것**이다.

---

## 2. 구조적 테마 (개별 버그를 관통하는 4가지)

### 테마 1 — "단일 쓰기 계약"의 미가입자: MCP

`contracts.py:1-31`은 "single write contract shared by all entrypoints"를 선언하고 CLI(`cli/__main__.py:522`)와
API(`server.py:1839,1883`)는 실제로 경유한다. 그러나 MCP `wiki_update`(`mcp/tools/write.py:284-448`)는
slug 검증·FileLock·frontmatter 병합·provenance 형식·log 검증 전부 독자 구현이다. contracts.py:28-31 스스로
"Deferred to v0.6.3"라 기록한 부채가 20개 마이너 버전째 미이행. 표면 간 동작 분기의 대부분(§3 A#1, B#5, B#7)이 이 한 지점에서 파생된다.

### 테마 2 — SoT→인덱스 계약은 "쓰기 시 보장"이 아니라 "lint가 알려주면 사람이 재빌드"

증분 색인이 없고(전량 재생성만), `contracts.write_page`는 wiki.db를 건드리지 않으며, `db.connect()`는
"missing이면 빌드, stale이면 그냥 사용"(db.py:88-92)이다. 이 모델 자체는 선택 가능하나, MCP 재색인 no-op(A#2)과
inline 폴백 스키마 비호환(B#4)은 그 모델의 마지막 안전망(lint 사후 감지 → 수동 rebuild)조차 깨뜨린다.
에이전트가 "방금 쓴 페이지를 검색하면 없다"를 기본으로 경험한다.

### 테마 3 — 중복 구현이 "표면마다 다른 진실"을 만든다

| 대상 | 구현 수 | 위치 |
|---|---|---|
| frontmatter 파싱 | **5벌** | core/frontmatter.py(정본) / server.py:2639 `_split_fm` / server.py:1283+1408(복붙 2회) / cli:464 / db.py:151 — build_db는 별도로 python-frontmatter(진짜 YAML) 사용 |
| 페이지 아카이브 | **4벌** | core/archive.py(정본, garden만 사용) / cli:970 / server.py:1916(줄 단위 복붙) / mcp write.py:691(평면 경로 — restore 호환 깨짐) |
| 검색 | **3벌** | API rglob 단어빈도 / MCP FTS5 BM25 / CLI(mcp.db import) — 같은 질의에 다른 순위 |
| slug/링크 해석 | **3벌+regex 4벌** | build_db / link.py / lint — 짧은 링크가 그래프엔 있고 lint엔 안 잡히는 비대칭 |
| 파일 락 | **2체계** | core FileLock(mkdir) vs MCP advisory(locks.json) — 상호배제 없음 |
| log append | **2벌** | core log.append(락+화이트리스트) vs mcp append_log_entry(무락+무검증) — `rename` 액션이 CLI면 ValueError, MCP면 기록됨 |
| 프론트 타입 | **3중** | VaultStats가 HomePage/VaultManage/Sidebar에 각각 선언, VaultInfo↔VaultMeta 동형 중복 |

### 테마 4 — 문서·테스트 문화는 진짜지만, 가드 밖은 썩는다

계약 테스트가 있는 곳(write 계약, north star 문구, Lite bootstrap 표면)은 코드와 동기화되고, 가드 없는 곳은 부패했다:
Makefile 헤더는 "Docker 우선"(현행 정책과 정반대), `deploy/systemd`는 기동 불가 유물, `__version__ = "0.5.7"`(현행 0.7.66),
docs/architecture.md는 제거된 `_meta/system/`을 참조. **"docs as contract"는 커버리지가 곧 진실성**임을 보여주는 이분 구조.

---

## 3. 발견 목록

### P0 — 심각 (데이터 손실·정합성 파괴·보안)

| # | 발견 | 위치 | 요지 |
|---|---|---|---|
| **A#1** | MCP 쓰기 경로가 core 계약 전면 우회 + **path traversal** | mcp/tools/write.py:38-47, 284-448 | `slug="../../x"`·절대경로로 vault 밖 파일 쓰기 가능(slug.validate 미호출). `frontmatter_data` 전달 시 기존 meta를 병합이 아닌 **대체**해 `created`/tags 소실(write.py:391). FileLock 미사용, provenance는 `actor:` 스칼라(core는 `agents:` 리스트) |
| **A#2** | MCP 쓰기 후 재색인이 **영구 no-op** | mcp/tools/write.py:63-81 | `<vault>/scripts/build_db.py`를 찾음 — 레포 루트가 아닌 vault 내부. 일반 vault엔 없으므로 조용히 return. delete/rename의 "rebuild" docstring 약속이 거짓이 됨 |
| **A#3** | frontmatter 커스텀 파서가 **블록 스타일 YAML 파괴** (실행 재현됨) | core/frontmatter.py:68, contracts.py:169-249 | 들여쓴 줄 전부 skip → `tags:\n  - alpha` 왕복 시 alpha 소실, `agents:` 이력 초기화. Obsidian 표준 문법 페이지를 core 경로로 1회 업데이트하면 메타데이터 조용히 삭제. build_db는 진짜 YAML을 쓰므로 읽기/쓰기가 서로 다른 문법을 이해 |
| **A#4** | 락 이원화 — CLI/API(FileLock) vs MCP(advisory) **상호배제 없음** + stale lock 영구 고착 | core/lock.py:13-41, mcp/tools/__init__.py:321 | FileLock에 TTL/PID 부재: 락 보유 중 프로세스 사망 시 해당 파일 write가 영원히 TimeoutError. MCP 쓰기는 어느 락에도 안 걸림 |
| **A#5** | CORS `allow_origins=["*"]` + 인증 전무 + 파괴적 엔드포인트 | server.py:41-46, 1808-1812, 2561 | 127.0.0.1 바인딩은 원격만 차단 — 브라우저의 악성 페이지가 cross-origin으로 `DELETE /api/vaults/{name}?force=true`(rmtree)·raw 쓰기 호출 가능 |
| **A#6** | migrate `--apply`가 **정상 링크까지 `?` 강등** + 항상 False인 죽은 헬퍼 | migrate.py:224-246 | broken만 고르지 않고 페이지 내 전체 무접미사 링크에 `?` 부착, `risk="safe"`로 자동 실행. `_has_intent_suffix`는 루프 즉시 종료로 항상 False. `[[x]]?`(target 존재)는 어떤 lint도 안 잡아 영구 은닉 |
| **A#7** | 죽은 엔드포인트: `POST /log/rotate` 본문이 docstring뿐 | server.py:2202-2205 | 항상 null 반환. 실제 구현은 `post_debug_log`의 return 뒤 데드코드(2240-2255)로 유실 — 2650줄 모놀리스 편집 사고의 물증 |
| **A#8** | wiki.db 빌드 무락 + `connect()` stale 무시 + inline 폴백 스키마 비호환 | db.py:88-166, scripts/build_db.py:242 | unlink→재생성 사이 레이스, WAL 미적용(curator만 적용). 폴백 스키마는 FTS/links/컬럼 부재로 index_builder·garden 쿼리가 실패 — 패키지 설치 환경에서 코어 반신불수 |
| **A#9** | 죽은 테스트 스위트 2개 + 기동 불가 deploy | raven/mcp/tests(37 skip+수집 충돌), scripts/tests(FAILED), deploy/systemd(구 모듈 경로 `-m mcp.cli`+포트 충돌) | 어떤 표준 경로에서도 실행되지 않거나 실행하면 실패 — CI 부재의 직접 결과 |

### P1 — 중간 (구조 부채·일관성)

| # | 발견 | 위치 |
|---|---|---|
| B#1 | 표면 간 동작 분기: 보호 경로(raw/·_meta/)가 **CLI에서만 뚫림**(actor=None 조건), llm-wiki 스키마 가드도 CLI/API 미적용 | contracts.py:194,210, cli:522 |
| B#2 | 비즈니스 로직의 역의존: rename+링크 재작성·FTS 질의·advisory lock이 MCP 레이어에 살고 CLI/API가 이를 import | cli:1002,1219, server.py:2387 |
| B#3 | server.py 모놀리스: 그래프 레이아웃 알고리즘 ~450줄(O(n²) 물리 시뮬)·git 연산·fuzzy slug·연합 해석이 HTTP 핸들러 파일에 동거. `/build`는 lint 2~3회 중복 실행 | server.py:776-1228, 2106 |
| B#4 | `_note_create`는 contracts 미경유 5번째 쓰기 경로 + 개인 프로젝트명 하드코딩(`harumoa`, `resume`...) | cli:688-741 |
| B#5 | MCP 아카이브 평면화 → restore가 잘못된 위치로 복원(`content/sub/foo` → 루트 `foo`) | write.py:691, archive.py:110 |
| B#6 | log.md "append-only"가 실제론 전체 재작성(비원자, crash 시 유실 가능), 페이지 쓰기도 tmp+rename 없음 | log.py:240-246, contracts.py:251 |
| B#7 | garden이 lint private 심볼 import + orphan/stale 판정 이중 구현(FS vs DB), db↔index_builder↔lint 소프트 순환 | garden.py:13,73-110, db.py:64-79 |
| B#8 | lint 성능: 체크당 전 파일 재스캔(~10회 rglob), 쓰기 1회 = 전량 재색인+전량 lint. digest도 매 요청 반복 | lint.py:116-134, digest.py:224-275 |
| B#9 | 프론트 Graph 타입이 백엔드 현실과 **반대**로 선언(`slug`/`source_slug` vs 실제 `id`/`source`), `as any` 봉합 산재 | types.ts:39-55 ↔ server.py:1252, GraphCanvas.tsx:382 |
| B#10 | 프론트 데이터 페칭: react-query 부재 → /stats 3중 fetch, vault 전환 레이스 가드 비일관(PageView/GraphPage/Layout 무가드), refreshKey 수동 배선 | Layout.tsx:100-119, PageView.tsx:159-199 |
| B#11 | api.ts가 26개 중 절반만 커버(나머지는 컴포넌트 내 raw fetch), 응답 untyped(`Promise<any>`), 백엔드 Pydantic 응답 모델 0개 | api.ts:132, server.py 전체 |
| B#12 | 죽은 의존성: zustand(import 0건), minisearch(DEPRECATED 파일만 참조). VaultManage 테이블/카드 완전 이중 렌더링, isMobile 훅 5벌(breakpoint 744/1024 혼재) | package.json:22, VaultManage.tsx:327-702 |
| B#13 | Makefile 헤더 "Docker 우선"이 현행 정책과 정반대 + Docker 핀 테스트 16개가 폐기 아티팩트를 영구화 | Makefile:2-8, tests/test_v0_7_12_docker.py |
| B#14 | `__version__ = "0.5.7"`(현행 0.7.66), git tag 0개, changelog 결번 3개 | raven/__init__.py:13 |
| B#15 | vendor 중립성 가드가 5개 파일만 스캔 — AGENTS.md·docs/architecture.md엔 vendor명 잔존 | test_vendor_neutrality.py:89 |
| B#16 | MCP `_default_vault()`가 raven 패키지 디렉터리를 vault로 간주(구조 잔재, 잠복 결함) | mcp/db.py:17-19 |
| B#17 | REST 관례 혼재: `POST /vaults/create`, 에러 응답 3종(HTTPException str/dict + 200 OK `{ok:false}`), 버저닝 없음 | server.py:527, 1795 |

### P2 — 경미 (대표만)

- `Vault.load()`가 읽기 경로에서 파일 rename 수행(읽기의 쓰기 부작용) — vault.py:66-73
- `db.connect()` → 미존재 시 build+lint+log append — "검색했더니 로그가 늘어난다" — db.py:88-92
- 부트스트랩 파일 목록 4곳 중복(vault.py×2, verify.py, sync_meta) + dead 상수 — vault.py:39-48
- curator log 위치가 core와 불일치(`_meta/log.md` vs 루트 `log.md`) — sync.py:296
- 프론트: 이중 debug 로거, 에러 삼킴(`return []` — 서버 다운과 빈 vault 구분 불가), `<a href>` full reload, hover DOM 직접 조작
- 고아 디렉터리 `templates/ai-agent-wiki-1.0.0/`(참조 0건), AGENTS.md의 자기모순 stale 주석(§14)

---

## 4. 강점 (실증된 것만)

1. **curator 서브시스템의 트랜잭션 설계가 코어보다 한 수 위** — WAL + `BEGIN IMMEDIATE` + "ok일 때만 sha advance" invariant + canonical-JSON 멱등성 키(curator/db.py:138-191). **코어가 배울 패턴이 같은 레포 안에 이미 있다.**
2. **slug.py 경로 방어는 방어적으로 완결적** — NUL/`..`/절대경로 거부 + resolve 후 containment 재확인 이중 방어(slug.py:29-75). API가 페이지·raw·workspace 경로에 일관 재사용. (아이러니: MCP 쓰기만 이 규율에서 빠짐)
3. **4 진입점 전부 실동작 테스트 그린이고 빠름** — Python 604개 31s + vitest 117개 6s. write 계약 시맨틱이 test_contracts.py로 집행되고 AGENTS.md §8이 계약 변경 시 최소 테스트 수를 규정 — 아키텍처 원칙→집행 메커니즘 연결이 실재.
4. **결정 고고학의 밀도** — changelog 110개 + ADR 5개 + 테스트 docstring의 사용자 발화 인용. 27k 라인 규모 대비 "왜 이렇게 됐는가" 추적 가능성이 탁월. 방향 전환(v0.6.37 north star)을 회귀 가드로 영구화하는 패턴은 독창적.
5. **정직한 자기 문서화** — contracts.py의 scope 한계 자인, README의 멀티에이전트 experimental 자인, MCP 도구 설명의 "advisory-only, last-writer-wins" 명시. 이 평가의 심각 발견 다수를 코드 주석이 이미 예고하고 있었다.
6. **프론트 배포 결합도 청결** — 전 API 호출이 상대경로 + dev proxy 단일 지점. MCP 멱등성 저장(temp+`os.replace`, fingerprint 충돌 감지, TTL GC)도 수준급.

---

## 5. 권고 로드맵

### P0 (데이터 안전 — 즉시)
1. **MCP `wiki_update`를 `contracts.write_page`로 교체** (A#1) — traversal 차단 + created 보존 + FileLock + provenance 통일이 **한 번에** 해결됨. contracts.py:28-31의 20버전 묵은 TODO 이행.
2. **frontmatter.py를 python-frontmatter로 교체 또는 블록 YAML 지원** (A#3) — 현재 조용한 데이터 손실 중. build_db와 파서 통일이 겸사 해결.
3. **MCP `_rebuild_db` 경로를 `core.db.build_db`로 교체** (A#2) + `db.connect()`에 stale 검사 연결 (A#8).
4. **migrate `apply_broken_to_missing` 수리** (A#6) — broken 대상만 선별, 죽은 헬퍼 제거. `risk="safe"` 재분류.

### P1 (구조 수렴 — 다음 사이클)
5. FileLock에 TTL/PID 기록 + MCP advisory와 통합 (A#4). 페이지/로그 쓰기에 tmp+`os.replace` 원자성 (B#6).
6. CORS 축소(Origin 화이트리스트) 또는 최소 토큰 인증 (A#5). `/log/rotate` 데드코드 복원 (A#7).
7. 아카이브 4벌 → core/archive.py 수렴 (B#5), 검색 3벌 → FTS5 단일화, mcp/db.py 질의 헬퍼를 core로 내려 역의존 제거 (B#2).
8. 죽은 스위트 2개 처분 + deploy/systemd 삭제 또는 수리 (A#9). Makefile 헤더 정정 (B#13).

### P2 (품질 — 여유 시)
9. 프론트: types.ts를 백엔드 실응답에 맞게 교정(B#9) + 공용 useApi 훅 또는 react-query(B#10) — 이 둘로 프론트 발견 절반이 구조적으로 해소.
10. server.py에서 그래프 레이아웃·git 연산을 core로 추출 (B#3). lint 스캔 캐싱 (B#8). `__version__` SOT 연결 (B#14).

---

*평가 방법론: 병렬 심층 분석 4트랙(core/진입점/대시보드/테스트·운영), 각 트랙 증거 기반 file:line 인용 필수, 핵심 주장(frontmatter 손실)은 실행 재현. 분석 커버리지: raven/ 전 모듈 + dashboard/src 주요 파일 + tests 실측 실행.*
