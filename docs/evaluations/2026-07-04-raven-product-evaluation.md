# Raven 제품 평가 (2026-07-04)

> **결론(BLUF): 종합 3.3/5.** 뼈대(SoT 원칙, 4 진입점, 복원/증명 체계, 테스트 문화)는 개인 도구로서 수준급.
> 그러나 "성공이라고 말하면서 실패하는" 지점 3곳(export, frontmatter 오염, 생성 경로 모순)이
> 제품 스스로 내건 정직성 원칙(AGENTS.md §9)과 정면충돌. P0 3건 해소 시 4점대.

- 평가 관점: **본인용 개인 도구** (제작자 1인이 매일 쓰는 도구로서의 완성도)
- 평가 깊이: **실행 검증 포함** (격리 vault 생성 후 CLI/API/MCP 시나리오 실주행)
- 사용자 축: 사람 PKM / 에이전트 LLM Wiki **동등 가중**
- Dashboard: API/코드 수준만 검증 (시각 UX는 사용자 직접 확인 필요)
- 평가 시점 버전: v0.7.65 (commit `a176737`)

---

## 1. 평가 기준 (합의된 6축)

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

---

## 3. 보충 평가: 에이전트 문서 운영 지침 레이어

| 질문 | 점수 | 판정 |
|---|---|---|
| ① 언제 문서를 생성하는가 | 4/5 | 저장 결정 4신호는 실판단 가능한 절차. 단, 통과해도 생성 수단이 없음(P0#2), §4 "사람 review 후"와 draft/review/final 태그 미연결 |
| ② 어떤 기준으로 작성하는가 | 4/5 | type 9종 템플릿 + 안티슬롭 규칙(빈 섹션/TBD/운영 메타 금지)은 수준급. wiki_update의 content=본문-only 규약이 문서에 없음 |
| ③ 어떻게 관리하는가 | 2.5/5 | 감지(lint 14종)는 충실하나 조치 도구(garden/curator/rotate)가 전부 사람 CLI 전용. 경계 선언이 에이전트가 실행 불가한 도구를 "당신 판단으로 돌려라"고 오안내 |

**공통 결함 패턴**: 지침이 약속한 행동을 도구 권한이 뒷받침하지 못하는 지점에서 문서가 침묵하거나 오안내 (생성→불가, 정리→CLI 전용, 태그 승격→수정 금지와 모순).

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

## 5. 보완 백로그 (P0 3 / P1 11 / P2 10)

### P0 — 데이터 위험 / 핵심 루프 차단
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

1. `wiki_lint` 실행 → critical(#1 깨진 링크, #2 intent 오표기, #14 Tier leak) 0건 확인 — content/ 링크는 `wiki_update`로 직접 수리, Tier leak은 즉시 보고
2. #5 모순 — 덮어쓰지 말고 양쪽에 `contested: true` + `contradictions` 상호 링크, 원인은 log.md 역추적
3. #4 orphan(유예 경과) — 인바운드 링크 연결 시도, 불가 시 아카이브 후보로 `type: issue` 발의
4. #7 stale — 재검증 목록화, 사실 변경분 갱신, 판단 불가 시 issue
5. #10 frontmatter 불완전 — `wiki_update` frontmatter 파라미터로 직접 보수
6. #8 200줄 초과 — 분할안 제안
7. #12 log 500건 도달 — 사람에게 `raven log rotate` 요청 (에이전트 실행 불가)
8. 점검 결과가 저장 4신호 통과 시 journal로 기록
