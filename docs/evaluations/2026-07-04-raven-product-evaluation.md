# Raven 제품 평가 (2026-07-04)

> **결론(BLUF): 종합 3.3/5.** 뼈대(SoT 원칙, 4 진입점, 복원/증명 체계, 테스트 문화)는 개인 도구로서 수준급.
> 그러나 "성공이라고 말하면서 실패하는" 지점 3곳(export, frontmatter 오염, 생성 경로 모순)이
> 제품 스스로 내건 정직성 원칙(AGENTS.md §9)과 정면충돌. P0 3건 해소 시 4점대.

- 평가 관점: **본인용 개인 도구** (제작자 1인이 매일 쓰는 도구로서의 완성도)
- 평가 깊이: **실행 검증 포함** (격리 vault 생성 후 CLI/API/MCP 시나리오 실주행)
- 사용자 축: 사람 PKM / 에이전트 LLM Wiki **동등 가중**
- Dashboard: API/코드 수준만 검증 (시각 UX는 사용자 직접 확인 필요)
- 평가 시점 버전: v0.7.65 (commit `a176737`)
- **근본 평가 기준 (사용자 north star, 2026-07-06 확인)**: "사람이 최초 작성한 문서를, 에이전트가 스테일/모순/링크깨짐을
  발견하여 **갱신(부분 overwrite + provenance)** 또는 **격리(archive 이동)** 액션으로 vault를 최신 정합화 상태로 유지한다.
  본문 대규모 재작성은 ❌, 원문 보존 + 증분 누적만 ⭕." — 이 기준 미반영 시 평가는 부적합.

---

## 1. 평가 기준 (합의된 6축)

> 가중치 근거: 시나리오·신뢰성 각 25% (개인 도구의 "동작 + 데이터 안심" 핵심), 일상 사용성 20% (반복 마찰),
> 문제-해결 적합성 15% (north star 정합), 1인 지속가능성 10%, 차별성 5% (본인 결정 정당화 보조 지표).

| # | 기준 | 가중치 | 평가 방법 |
|---|---|---|---|
| 1 | 핵심 시나리오 완성도 | 25% | 실행 검증 (사람 루프 + 에이전트 루프) |
| 2 | 신뢰성/데이터 안전 | 25% | 실행 + 코드 검증 |
| 3 | 일상 사용성 | 20% | 실행 검증 |
| 4 | 문제-해결 적합성 | 15% | North Star 선언 vs 구현 대조 |
| 5 | 1인 지속가능성 | 10% | 코드/테스트 구조 분석 |
| 6 | 차별성 | 5% | 컨셉 분석 |

---

## 2. 채점표 — 종합 **3.3 / 5**

| # | 기준 (가중치) | 점수 | 근거 |
|---|---|---|---|
| 1 | 핵심 시나리오 완성도 (25%) | **3.0** | 사람 루프(작성→링크→빌드→검색→링크체크)와 에이전트 루프(발견→읽기→수정→lint→log)는 실제로 동작. 그러나 `raven export` 완파(빠른 시작 5단계가 거짓), 에이전트 신규 페이지 생성 경로 부재 |
| 2 | 신뢰성/데이터 안전 (25%) | **3.0** | 삭제→아카이브→복원, MCP write 자동 log(provenance), vault verify 체크섬, vault git 자동 초기화, lock/idempotency는 탄탄. silent failure 2건(export 성공 위장, frontmatter 이중화 오염)이 자기 원칙(§9) 위반 |
| 3 | 일상 사용성 (20%) | **3.5** | 명령 일관성·에러 메시지·한글 슬러그 언어 보존 양호. 새 vault부터 lint 노이즈 8건, `archive restore`가 slug 미수용, CLI 검색 부재 |
| 4 | 문제-해결 적합성 (15%) | **3.5** | "사람 1차 PKM"은 선언-구현 정합. "에이전트 compounding knowledge"는 신규 생성 불가로 반쪽. wiki_update 에러 메시지와 ADR-2026-07-02 상호 모순 |
| 5 | 1인 지속가능성 (10%) | **4.0** | 테스트 581개/29초, 13.6k LOC 대비 테스트 9.6k LOC, ADR/changelog 체계. 감점: scripts/ legacy 이중 구조, watchfiles 미명시로 클린 체크아웃 테스트 red |
| 6 | 차별성 (5%) | **4.0** | 본인 요구(4 진입점, MCP 1급, 자유 커스텀) 기준 "직접 만든다" 결정 유효. 객관적 근접 대체재는 Obsidian+MCP 플러그인 |

### 2.1 평가자 위치 + 커버리지 한계 (자가 점검)

> **자가 점검 (AGENTS.md §15)**: §15.1 (4/4) + §15.2 (4/4) — 통과.
> §15.1.1 "저장 4신호" — P0 3건 + P1 11건 모두 재사용성·실패기록에 trace.
> §15.1.2 "구조 일관성" — 파일명 = title 1:1, SCHEMA 9종 타입 준수.
> §15.1.3 "BLUF" — §0 메타 첫 줄 + §2 채점표 결론 명시.
> §15.1.4 "연결성" — 자매 문서 cross-link + §6 점검 흐름이 SCHEMA/RULES와 상호참조.
> §15.2.1-4 — 평가자가 "검색·도구 권한·SCHEMA 등 실제 위치 확인 → 코드 file:line 인용 → 사용자가 요구한 north star 성공 기준 추출 → silent failure/모순 발견 시 log.md 역추적" 절차로 작성.

- **평가자 = Raven 개발자 본인.** 자기 제품 자기 평가의 메타 한계(확증 편향·blind spot) 있음.
- **직접 실행한 검증**: 격리 vault 1회 생성, CLI/API/MCP 기본 시나리오, lint 14룰 전수, export 실패 재현.
  미실행: 시각 UX 사용자 시나리오, 멀티에이전트 동시성, 90일 stale 자동 감지 실제 트리거, `/log/rotate` 응답.
- **미커버 영역**: dashboard 디자인(한국 원티드/Jira/Notion UX 미비교), MCP 도구 전수, scripts/ 하위, vendor 예시 잔존,
  Lite bootstrap 후 30일 이상 운영 데이터.
- **실패한 검증 / 의미 미분석**: "13.6k LOC 대비 테스트 9.6k LOC"은 측정됐지만 "13.6k 중 raw/ 비중"·"scripts/ 비중" 분해 없음.
- **평가의 한계 = 권고의 한계**: "에이전트 큐레이션 루프" 4축(정의/권한/도구/테스트) 자체가 누락 — 사용자 north star(2026-07-06 확인) 기준 본 평가 §3에서 별도 보강.

### 2.2 산출식

Σ(가중치 × 점수) = 3.0×0.25 + 3.0×0.25 + 3.5×0.20 + 3.5×0.15 + 4.0×0.10 + 4.0×0.05
= 0.75 + 0.75 + 0.70 + 0.525 + 0.40 + 0.20 = **3.325** → 반올림 **3.3/5** (정성 보정 0)

- 정성 보정 미적용 근거: 제품 평가는 silent failure 3건(export 위장·frontmatter 오염·에이전트 생성 경로 부재)이 자기 원칙(§9) 정면충돌이라 가점 없이 그대로 표기.

---

## 3. 보충 평가: 에이전트 문서 운영 지침 레이어

| 질문 | 점수 | 판정 |
|---|---|---|
| ① 언제 문서를 생성하는가 | 4/5 | 저장 결정 4신호는 실판단 가능한 절차. 단, 통과해도 생성 수단이 없음(P0#2), §4 "사람 review 후"와 draft/review/final 태그 미연결 |
| ② 어떤 기준으로 작성하는가 | 4/5 | type 9종 템플릿 + 안티슬롭 규칙(빈 섹션/TBD/운영 메타 금지)은 수준급. wiki_update의 content=본문-only 규약이 문서에 없음 |
| ③ 어떻게 관리하는가 | 2.5/5 | 감지(lint 14종)는 충실하나 조치 도구(garden/curator/rotate)가 전부 사람 CLI 전용. 경계 선언이 에이전트가 실행 불가한 도구를 "당신 판단으로 돌려라"고 오안내 |

**공통 결함 패턴**: 지침이 약속한 행동을 도구 권한이 뒷받침하지 못하는 지점에서 문서가 침묵하거나 오안내 (생성→불가, 정리→CLI 전용, 태그 승격→수정 금지와 모순).

### 3.1 사용자 north star 누락 시나리오 — "에이전트 스테일 갱신·격리 루프" (2026-07-06 확인)

사용자 의도: "사람이 최초 작성한 문서를, 에이전트가 스테일/모순/링크깨짐을 발견하여 **갱신(부분 overwrite + provenance)** 또는 **격리(archive 이동)** 액션으로 vault를 최신 정합화 상태로 유지한다."

본 제품이 이 루프를 4축으로 뒷받침하는가:

| 축 | 현 상태 | 격차 |
|---|---|---|
| **정의** | `stale`/`archive`/`contested` 3상태 미정의. lint #7 stale 룰은 있으나 상태 머신 없음 | 평가·구현의 기준선 자체 부재 |
| **권한** | ADR 부재. P0#2(신규 페이지 생성) · P0#3(frontmatter 오염) 처럼 갱신/격리 권한도 불명 | north star 실행 불가 |
| **도구** | 갱신 = `wiki_update`(결함 동반), 격리 = `archive` CLI만 사람 영역 | MCP 경로 없음 |
| **테스트** | 시나리오 0건 (90일 stale, 사실 변경, 링크 깨짐) | 검증·회귀 가드 부재 |

→ §5 P0에 #0으로 추가 (가장 우선). §6 점검 흐름에 "발견 → 갱신 or 격리 발의" 명시.

---

## 4. 린트 엔진 점검 (14룰 전수 실측)

룰 위반 트랩 페이지를 심어 전수 검증. **탐지력 100%** (#1/#2/#14 critical, #4~#10 계층 정확).

| 확정 결함 | 내용 |
|---|---|
| 태그 승격 루프 사망 | `_core_tags()`가 옛 경로 `_meta/SCHEMA.md`를 읽음 → 항상 fallback 상수 사용. vault SCHEMA.md에 태그를 추가해도 무효 — lint 메시지 자신이 안내하는 절차가 무효 |
| 승격 추천 미구현 | SCHEMA.md의 "3+ 페이지 태그 → core 승격 추천 알림"이 lint 코드에 없음 |
| lint↔garden 소스 불일치 | lint=파일시스템, garden=wiki.db 기준. 빌드가 낡으면 garden이 경고 없이 "정리 대상 없음"으로 거짓 안심 |
| #11 영구 오탐 | `log` 슬러그가 몇 번을 빌드해도 "재build 필요" — 경고 무시 습관 유발 |
| 자기 생성물 self-noise | build가 만드는 `content/index`/`_index/*`의 태그(`index`,`home`)가 자체 core taxonomy에 없어 새 vault부터 경고 |

---

## 5. 보완 백로그 (P0 4 / P1 11 / P2 10)

### 5.1 발견 ↔ 권고 매핑 매트릭스

> §3.1/P0#0 + P0#1~#3 (4건) + P1#4~#14 (11건) + P2#15~#24 (10건) = **25건 발견 → 권고 25건**. 본 평가는 1:1 매핑 기본.

| 발견 → 권고 | 비고 |
|---|---|
| **§3.1 / P0#0** → **#0** | ADR-2026-07-06 (north star 결정) |
| **P0#1~#3 + P1#4~#14** → **#1~#14** | 14건 1:1 (P0#3+P1#9만 N:1로 #3 흡수) |
| **P2#15~#24** → **#15~#24** | 품질 9건 1:1 |

### 5.2 권고별 done_when (검증 기준, Karpathy §6 ④)

done_when 형식: **테스트/시나리오가 그린이면 통과**. 상세는 ADR-2026-07-06 §4 수용 기준 참조.

| # | 권고 | done_when (1줄) |
|---|---|---|
| **#0** | 스테일 루프 4종 | ADR accept + 시나리오 4종 pass + 회귀 2종 pass |
| **#1** | export 수리 | 격리 vault exit 0 + 결과 파일 존재 + 실패 시 거짓 "exported" 출력 금지 |
| **#2** | 신규 페이지 경로 | 신규 slug 호출 성공 + provenance 기록 + ADR-2026-07-02 메시지 교정 |
| **#3** | frontmatter 오염 방어 | `content="---\ntags: ..."` 시 tags 보존 또는 명시적 거절 (오염 금지) |
| **#4** | lint #11 log 오탐 | vault 내 `log` 슬러그 페이지 lint #11 0건 |
| **#5** | build 1회 수렴 | index.md + DB + lint = 1회 빌드 |
| **#6** | 시스템 태그 면제 | `index`/`home` core taxonomy 추가 또는 lint #9 면제 |
| **#7** | archive restore slug | `foo` 또는 `foo.md` 둘 다 동작 |
| **#8** | 검색 감점 | `raven search "실제 단어"` 결과에 `_index/*` 없음 |
| **#10** | 경계 선언 정직화 | PROJECT-WORKFLOW "에이전트 경로 = wiki_lint → issue 발의" 명시 |
| **#11** | `_core_tags()` 경로 | vault SCHEMA.md 태그 추가 시 lint 반영 |
| **#12** | garden FS↔DB 감지 | stale DB → 진입 시 경고 + 자동 rebuild 옵션 |
| **#13** | 큐레이션 점검 §6 | PROJECT-WORKFLOW §6 "큐레이션 기본 점검" 섹션 존재 |
| **#14** | watchfiles 명시 | 클린 체크아웃 pytest 0 red |

### P0 — 데이터 위험 / 핵심 루프 차단

0. **에이전트 스테일 갱신·격리 루프 정의·권한·도구·테스트 4종 구축** (사용자 north star, §3.1)
   - 정의: `_meta/SCHEMA.md` 또는 `_meta/RULES.md`에 `stale`/`archive`/`contested` 3상태 명시 + 전이 규칙
   - 권한: ADR로 "에이전트가 stale 발견 → 갱신(부분) 또는 격리(이동)" 권한 명시
   - 도구: MCP `wiki_stale_detect`(stale 후보 목록 반환) + `wiki_archive`(이동 + frontmatter stamp) 2개 추가 또는 기존 CLI MCP 노출
   - 테스트: 시나리오 3종 (90일 stale / 사실 변경 / 링크 깨짐 → 갱신) + 격리 1종 — `tests/scenarios/test_stale_loop.py`
1. **`raven export` 수리** — `scripts/export_static.py` `__main__`이 argv를 무시하고 저장소 루트를 vault로 간주, 실패해도 exit 0 → CLI/API 모두 "✅ exported" 위장.
2. **에이전트 신규 페이지 생성 경로** — `wiki_update`를 스키마 가드 통과 조건부 upsert로 확장. "Use wiki_ingest for new pages" 오안내(ADR-2026-07-02와 모순) 수정.
3. **`wiki_update` content 내 frontmatter 오염 방어** — content가 `---`로 시작하면 파싱해 검증에 태울 것. 현재는 기존 메타로 검증을 통과시킨 뒤 frontmatter 블록을 본문에 박제(SoT 조용히 오염).

### P1 — 일상 마찰
4. lint #11 `log` 영구 오탐 수정
5. build 1회 수렴 (index.md 생성 후 DB 재반영 — 현재 2회 빌드 필요)
6. 시스템 생성 파일 태그(`index`/`home`)를 core taxonomy에 추가하거나 시스템 파일 #9 면제
7. `archive restore`가 원래 slug도 수용
8. 검색 랭킹에서 자동 생성 `_index/*` 페이지 감점/제외 (실제 노트보다 상위 노출 문제)
9. PROJECT-WORKFLOW §1에 wiki_update content/frontmatter 분리 규약 명시 (P0#3의 문서 짝)
10. 경계 선언·관리 루프 정직화 — garden/curator/rotate가 사람 CLI 전용임을 명시, 에이전트 경로는 "wiki_lint 감지 → `type: issue` 발의"로 재기술
11. `_core_tags()` 경로를 `_meta/agents/SCHEMA.md`로 수정 (태그 승격 루프 부활)
12. garden 진입 시 FS↔DB 불일치 감지 → 경고 또는 자동 rebuild
13. PROJECT-WORKFLOW에 "큐레이션 기본 점검" 섹션 추가 (§6 참조)
14. `watchfiles` 의존성 명시 (클린 체크아웃 테스트 green)

### P2 — 개선
15. CLI `raven search` 추가 (사람의 CLI 검색 경로 부재)
16. `raven meta --help`의 "RULES.md" 잔재 제거
17. #9 커스텀 태그 경고 severity 재고 ("custom은 OK"라면서 warning — info가 적절)
18. 모순 발견 시 사실 절차 1줄 (덮어쓰기 금지, `contested` + `contradictions` 상호 링크)
19. §4 분업표와 `draft`/`review`/`final` 태그 연결
20. 태그 승격 절차를 issue 발의 경로로 수정 (§8 SCHEMA 수정 금지와 모순 해소)
21. `aliases` 사용 시점 / 200줄 초과 분할 절차 안내
22. "3+ 태그 승격 추천" 구현 또는 SCHEMA 문구 삭제
23. `curator run` COLLECTION_ID 필수 인자를 README/AGENTS 명령표에 반영
24. #13이 frontmatter 없는 페이지에서 #10과 이중 보고되는 노이즈 정리

---

## 6. 에이전트 큐레이션 기본 점검 (PROJECT-WORKFLOW 반영용 초안)

각 항목은 에이전트가 **실제로 할 수 있는 조치**(수리 가능 / 발의만 가능 / 사람 요청)를 명시한다.

0. **north star 루프 (가장 우선, §3.1/P0#0)**: `wiki_lint --stale` 실행 → stale 후보 목록 확보 →
   - (a) 갱신 가능 = `wiki_update`로 부분 overwrite + provenance 기록 (P0#3 결함 해결 후)
   - (b) 격리 필요 = `type: issue` 발의 후 사람 CLI `archive` 호출 (현재 권한 부재 — north star 미실행)
   - (c) 갱신·격리 모두 MCP 도구 미지원 시 **즉시 보고** (P0#0 권한·도구 결함 표면화)
1. `wiki_lint` 실행 → critical(#1 깨진 링크, #2 intent 오표기, #14 Tier leak) 0건 확인 — content/ 링크는 `wiki_update`로 직접 수리, Tier leak은 즉시 보고
2. #5 모순 — 덮어쓰지 말고 양쪽에 `contested: true` + `contradictions` 상호 링크, 원인은 log.md 역추적
3. #4 orphan(유예 경과) — 인바운드 링크 연결 시도, 불가 시 아카이브 후보로 `type: issue` 발의
4. #7 stale — 재검증 목록화, 사실 변경분 갱신, 판단 불가 시 issue
5. #10 frontmatter 불완전 — `wiki_update` frontmatter 파라미터로 직접 보수
6. #8 200줄 초과 — 분할안 제안
7. #12 log 500건 도달 — 사람에게 `raven log rotate` 요청 (에이전트 실행 불가)
8. 점검 결과가 저장 4신호 통과 시 journal로 기록
