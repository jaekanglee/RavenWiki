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
- 자매 문서: [2026-07-04-raven-product-evaluation.md](2026-07-04-raven-product-evaluation.md) (제품 관점 3.3/5, **2026-07-06 보완 v2→v3 적용**)
- **근본 평가 기준 (사용자 north star, 2026-07-06 확인)**: "사람이 최초 작성한 문서를, 에이전트가 스테일/모순/링크깨짐을
  발견하여 **갱신(부분 overwrite + provenance)** 또는 **격리(archive 이동)** 액션으로 vault를 최신 정합화 상태로 유지한다.
  본문 대규모 재작성은 ❌, 원문 보존 + 증분 누적만 ⭕." — 이 기준 미반영 시 평가는 부적합.

---

## 1. 채점표 — 종합 **3.0 / 5**

> 가중치 근거: 계층 규율·SoT 일관성·데이터 안전 각 20% (코어 계약·정합성·안전이 아키텍처 1차 가치),
> 모듈 응집·테스트/문서 15% (문화·결정 추적), 진입점 표면 10% (개별 품질은 1·2·3의 결과물).

| # | 축 (가중치) | 점수 | 근거 요약 |
|---|---|---|---|
| 1 | 계층 규율 — 진입점이 core를 경유하는가 (20%) | **2.5** | CLI/API 쓰기는 contracts 경유 ✅. MCP는 전면 우회(A#1). CLI→MCP, API→MCP 역의존. 인덱스 빌더·export가 core 밖 `scripts/`에 존재 |
| 2 | SoT→파생 일관성 계약 (20%) | **2.0** | 쓰기가 인덱스를 갱신하지 않고, `connect()`는 stale 무시, MCP 재색인은 경로 오류로 영구 no-op(A#2), inline 폴백은 스키마 비호환 |
| 3 | 데이터 안전·동시성 구조 (20%) | **2.0** | frontmatter 블록 YAML 왕복 파괴 재현됨(A#3), 락 2체계 상호배제 실패, stale lock 영구 고착, 페이지/로그 쓰기 비원자. 단 curator 서브시스템은 모범(5점감) |
| 4 | 모듈 응집·중복 통제 (15%) | **2.5** | frontmatter 파서 5벌, 아카이브 4벌, 검색 3벌, slug 해석 3벌, wikilink regex 4벌. 프론트도 타입 3중 선언·isMobile 훅 5벌 |
| 5 | 진입점 표면 각자의 설계 품질 (10%) | **3.5** | slug.py 경로 방어·MCP 멱등성 설계·raw 경로 다층 가드는 수준급. REST 관례 혼재, CORS `*`+무인증, 죽은 엔드포인트 1개 |
| 6 | 테스트·문서·결정 추적 구조 (15%) | **4.5** | 4 진입점 전부 실동작 테스트 그린(721개, 37s), write 계약이 테스트로 집행, changelog 110개+ADR 5개. 감점: 죽은 스위트 2개, CI 부재 |

**핵심 진단 한 줄**: 이 코드베이스의 문제는 설계가 없어서가 아니라, **좋은 설계(contracts, slug, curator, archive)가 이미 레포 안에 있는데 절반의 코드가 그걸 안 쓰고 자기 버전을 만든 것**이다.

### 1.1 평가자 위치 + 커버리지 한계 (자가 점검)

> **자가 점검 (AGENTS.md §15)**: §15.1 (지식밀도·구조·가독성·연결성 4/4) + §15.2 (Think/Surgical/Goal-Driven/Root-Cause 4/4) — 통과.
> §15.1.1 "저장 4신호" — 권고 항목들이 재사용성·인수인계·맥락·실패기록 중 최소 1개 이상 부합.
> §15.1.2 "구조 일관성" — 파일명 `2026-07-04-raven-*-evaluation.md` ↔ title 일치.
> §15.1.3 "BLUF" — §0 메타 첫 줄에 결론 명시.
> §15.1.4 "연결성" — 자매 문서 cross-link + 권고 ID 인용.
> §15.2.1-4 — 본 평가 자체가 "검색 전 사색 → 외과식 → 목표 추출 → 원인 조사" 절차로 작성됨을 §1.1에 자인.

- **평가자 = Raven 개발자 본인.** 자기 코드 자기 평가의 메타 한계(확증 편향·blind spot) 있음.
- **직접 실행한 검증**: `tests/` pytest 1회 (604 passed), vitest 1회 (117 passed), frontmatter 블록 YAML 손실 재현 1회.
  미실행: MCP path traversal 실제 악용, CORS cross-origin 공격, 죽은 엔드포인트 `/log/rotate` 응답 검증.
- **미커버 영역**: dashboard 시각 UX(요구사항 미수신), `scripts/` 하위 전수, raw/ 폴더(ADR 2026-07-02로 사람 영역),
  MCP 도구 23종 중 실측 ~6종, vendor 중립성 테스트의 5파일 외 잔존.
- **실패한 검증 / skip의 의미**: A#9의 "37 skip" = 어떤 테스트인지 분해 안 됨. FAILED 1건 = 분석 없이 나열.
- **평가의 한계 = 권고의 한계**: 정량 측정값(쓰기당 재색인 시간·메모리·O(n²) 임계점) 부재로 권고 우선순위는 정성적.
- **평가→코드 검증 갭 (v4)**: A#1·A#3·A#4는 v0.7.67+ 코드 차원 이미 해결 (path traversal→contracts.write_page / frontmatter→contracts merge / lock TTL→FileLock PID 회수). 평가 시점(v0.7.66)과 현재(v0.7.68) 사이 silent 해소 — A#0만 Plan B-2로 자명히 종결. 다음 평가(v0.7.69+)에서 done_when #1/#2/#5 status 명시 필요.

### 1.2 산출식

Σ(가중치 × 점수) = 2.5×0.20 + 2.0×0.20 + 2.0×0.20 + 2.5×0.15 + 3.5×0.10 + 4.5×0.15
= 0.50 + 0.40 + 0.40 + 0.375 + 0.35 + 0.675 = **2.70** → 정성 보정 +0.30 = **3.0/5**

- 정성 보정 +0.30 근거: §4 강점 #1(curator 패턴이 같은 레포 내 모범) + #4(결정 고고학 밀도 탁월) — 가중치로 환산 어려운 시스템 차원의 가치를 보정.

---

## 2. 구조적 테마 (개별 버그를 관통하는 4가지)

### 테마 5 — "에이전트 스테일 갱신·격리 루프"의 정의·권한·도구·테스트 부재 (사용자 north star 핵심, 2026-07-06 확인)

사용자 의도: "사람이 최초 작성한 문서를, 에이전트가 스테일/모순/링크깨짐을 발견하여 **갱신(부분 overwrite + provenance)** 또는 **격리(archive 이동)** 액션으로 vault를 최신 정합화 상태로 유지한다. 본문 대규모 재작성은 ❌."

본 코드베이스가 이 루프를 4축으로 뒷받침하는가:

| 축 | 현 상태 | 격차 |
|---|---|---|
| **정의** | `stale`/`archive`/`contested` 3상태가 SCHEMA/RULES에 명시되지 않음. lint #7 "stale"은 룰 존재하나 상태 머신 없음 | north star를 만족하는 상태 정의 자체가 부재 — 평가·구현의 기준선 없음 |
| **권한** | ADR 부재. MCP `wiki_update`는 부분 overwrite 가능하나 archive 액션 미노출 | 에이전트가 "격리"를 트리거할 수 있는 공식 경로 없음 |
| **도구** | 갱신 = `wiki_update` (P0#3 frontmatter 오염 결함 동반), 격리 = `archive` CLI만 사람 영역 | MCP에서 갱신·격리 모두 호출 가능해야 north star 동작 |
| **테스트** | 시나리오 테스트 0건 — "90일 stale 자동 감지 → 갱신" / "사실 변경 → 재검증" 등 미실증 | 루프 자체가 검증되지 않음, 회귀 가드 없음 |

→ 본 평가는 이 루프를 별도 누락 시나리오로 명시한다. 권고 §5 P0#1로 흡수.

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
| **A#0** | **에이전트 스테일 갱신·격리 루프 부재** (사용자 north star, 2026-07-06 확인) | `SCHEMA.md`/`RULES.md`/`raven/mcp/tools/`/`tests/` 전역 | 정의(stale/archive/contested 3상태)·권한(ADR)·도구(MCP 갱신/격리)·테스트(시나리오) 4축 모두 미비. 본 평가의 별도 누락 시나리오(테마 5)로 명시. §5 권고 #0으로 흡수 |

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

### 5.1 발견 ↔ 권고 매핑 매트릭스

> A#0~A#9 (10건) + B#1~B#17 (17건) = **27건 발견 → 권고 11건으로 수렴**. N:1 흡수 多 = "수렴 + cleanup" 묶음 작업 (Karpathy §3 surgical).

| 발견 → 권고 | # | 비고 |
|---|---|---|
| **A#0** (테마 5, 스테일 루프) | **#0** 1:1 | ADR-2026-07-06 |
| A#1 | **#1** 1:1 | contracts.write_page |
| A#2·A#8 | **#3** 1:1 동시 | db.connect stale |
| A#3 | **#2** 1:1 | 파서 통일 |
| A#4·B#6 | **#5** N:1 | TTL + 원자성 |
| A#5·A#7 | **#6** N:1 | CORS + /log/rotate |
| A#6 | **#4** 1:1 | broken-only |
| A#9·B#13 | **#8** N:1 | 죽은 스위트 + Makefile |
| B#1·B#2·B#4·B#5·B#7·B#16 | **#7** N:1 | core 수렴 |
| B#3·B#8·B#14 | **#10** N:1 (P2) | server.py 추출 + 캐싱 |
| B#9·B#10·B#11·B#12·B#15·B#17 | **#9** N:1 (P2) | 프론트 cleanup |

### 5.2 권고별 done_when (검증 기준, Karpathy §6 ④)

done_when 형식: **테스트/시나리오가 그린이면 통과**. 상세는 ADR-2026-07-06 §4 수용 기준 참조.

| # | 권고 | done_when (1줄) |
|---|---|---|
| **#0** | 스테일 루프 4종 | ADR-2026-07-06 accepted (2026-07-06) + Lite bootstrap `templates/agent/SCHEMA.md` status 4종 정의 + 시나리오 13종 pass + 회귀 2종 pass (Plan B-2, 5b84a8e) |
| **#1** | MCP wiki_update → contracts | `slug='../../etc/passwd'` 400 + `created` 보존 + FileLock 3종 테스트 |
| **#2** | frontmatter.py 교체 | `tests/regressions/test_frontmatter_block_yaml.py` pass + build_db와 동일 모듈 |
| **#3** | MCP `_rebuild_db` + db.connect stale | MCP write → 검색 즉시 반영 + stale 시 자동 rebuild |
| **#4** | migrate broken-only | 정상 링크 무손상 + `_has_intent_suffix` false negative 0건 |
| **#5** | FileLock TTL/PID + 원자성 | TTL 경과 자동 해제 + tmp+os.replace atomic |
| **#6** | CORS 축소 + `/log/rotate` | Origin 화이트리스트 + `/log/rotate` 응답 = docstring |
| **#7** | 아카이브/검색/락 수렴 | 동일 입력 → 동일 결과 (3종 진입점 비교) |
| **#8** | 죽은 스위트 + Makefile | pytest collections 죽은 스위트 0개 + 헤더 정책 일치 |
| **#9** | 프론트 types/useApi | types.ts Graph 타입 = 백엔드 1:1 + `/stats` 1회 fetch |
| **#10** | server.py 추출 + lint 캐싱 + version | server.py -450 LOC + lint < 100ms + `__version__` = 최신 changelog |

---

*평가 방법론: 병렬 심층 분석 4트랙(core/진입점/대시보드/테스트·운영), 각 트랙 증거 기반 file:line 인용 필수, 핵심 주장(frontmatter 손실)은 실행 재현. 분석 커버리지: raven/ 전 모듈 + dashboard/src 주요 파일 + tests 실측 실행.*
