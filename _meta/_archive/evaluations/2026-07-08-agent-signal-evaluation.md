# Raven — 에이전트 Write/Read 신호 평가 (Claude 관점)

> **평가 기준**: Raven vault 컨셉 = **Layer 2 (사람 1차 운영 인덱스)**, north star = **원문 보존 + 증분 누적**
> **평가 대상**: Raven SOT 6종 병행 review
> **작성**: raven-orchestrator subagent (Claude 관점)
> **관련 SOT**: SCHEMA.md, PWW, AGENTS.md, ADR-2026-07-02/06/08

---

## 1. 에이전트 Write/Read 신호 전류 매핑

### 1.1 Write 신호

#### 명시적 (사람 turn)

| 신호 | SOT 라인 | 동작 |
|---|---|---|
| §3 4가지 신호 — 1개 이상 통과 | PWW L236-243, AGENTS.md §5/121-130 | `wiki_update` 호출 전 통과 여부 체크 |
| 사람 명시 명령 | PWW L111, ADR-2026-07-02 L43 | `wiki_ingest(user_command=True)` — 자율 호출 ❌ |
| draft → final 승격 (사람 review) | PWW L312-313 | `type: rule/concept/person` 작성 시 `draft` 태그 → 사람 `review` → `final` |

#### 자율 (에이전트 단독 실행 가능)

| 신호 | SOT 라인 | 동작 |
|---|---|---|
| **4 진입점**: lint #15 (slug 불일치) → `wiki_rename` | PWW L301-303, ADR-2026-07-08 L31 | 자동 수리 (aliases 추적성 보존) |
| **4 진입점**: lint #5 (모순) → `contested: true` 상호 링크 | PWW L293-294, SCHEMA.md L109 | 양쪽 cross-link, 덮어쓰지 않음 |
| **4 진입점**: lint #4 (orphan 유예 경과) → 인바운드 연결 시도 | PWW L295-296 | 불가 시 `type: issue` 발의 |
| **4 진입점**: lint #7 (stale) → 사실 변경 페이지 `wiki_update` | PWW L297 | 판단 불가 시 `type: issue` 발의 |
| **4 진입점**: lint #10 (frontmatter 불완전) → `wiki_update` 보수 | PWW L298 | frontmatter_data 파라미터 |
| lint #1/2 (frontmatter 오류/破链接) → `wiki_update` 수리 | PWW L292, SCHEMA.md L210-211 | 직접 수리 가능 |
| **ADR-2026-07-06**: stale 감지 → `wiki_update(revalidate=true)` 또는 `wiki_archive` | ADR-2026-07-06 L67-71, PWW L134-136 | 부분 overwrite + provenance 기록, 1.5배 가드 |
| **ADR-2026-07-06**: `wiki_stale_detect` → 후보 목록 → 에이전트 자율 판단 | ADR-2026-07-06 L67, PWW L107 | read-only에서 출발, write 액션은 에이전트 판단 |

#### 쓰기 진입 경로

| 경로 | 권한 | SOT |
|---|---|---|
| `content/` | 에이전트 read/write 자유 | PWW L227, §2 |
| `raw/` | 에이전트 **read-only** (`wiki_ingest`만 사람 명령 시) | PWW L226, ADR-2026-07-02 |
| `_meta/` | 에이전트 **read-only** (직접 수정 ❌) | PWW L228 |
| `log.md` | append-only (도구 자동 기록) | PWW L229 |

### 1.2 Read 신호

#### 명시 (search/query — 에이전트 또는 사람 요청)

| 신호 | SOT 라인 | 동작 |
|---|---|---|
| `wiki_search(query, top_k=10)` | PWW L102 | BM25 전문 검색 |
| `wiki_get_page(slug)` | PWW L103 | 본문/frontmatter/backlinks 조회 |
| `wiki_log(tail_n=20)` | PWW L106 | log.md 최근 N개 구조화 JSON |
| `wiki_graph(project?)` | PWW L105 | 페이지 간 링크 그래프 |
| `wiki_get_guide(kind)` | PWW L108 | Lite bootstrap 3종 read-only viewer |
| `wiki_get_guide_diff(kind)` | PWW L109 | Lite bootstrap vs raven 설치 템플릿 diff |

#### 자동 (시스템/Uptime 시 작동)

| 신호 | SOT 라인 | 동작 |
|---|---|---|
| **`wiki_lint()` — 14개+1 무결성 검사** | PWW L104, SCHEMA.md L208-226 | #1 frontmatter / #2 broken_link / #3 missing_link / #4 orphan / #7 stale / #13 cognitive governance / #14 tier integrity / **#15 slug-title 1:1** |
| **`wiki_stale_detect()`** — ADR-2026-07-06 | PWW L107, ADR-2026-07-06 L83-109 | 90일+ 후보 + evidence + suggested_action 반환 |
| **wikilink resolve** (read 시 자동) | SCHEMA.md L165-169 | `[[link]]` / `[[link!]]` / `[[link?]]` intent 해석 |
| lint #5 (contested) 자동 감지 | SCHEMA.md L109 | 모순 발견 시 `contested: true` + `contradictions: [slug]` |
| lint #9 (90일+ 미갱신 + 새 출처 → stale 경고) | SCHEMA.md L219 | 90일 + 새 출처 동시 만족 |

---

## 2. Raven Vault 컨셉 (Layer 1/2) 정합성 검토

### 2.1 Layer 경계 정의

| 구분 | 정의 | SOT |
|---|---|---|
| **Layer 1** (Raven 제품) | Raven 본체. 사람 1차 PKM. 에이전트 없이도 완성. vault 구조·north star 정의. | PWW L48, AGENTS.md L33 |
| **Layer 2** (에이전트 활용) | 에이전트가 cwd 산출물·인사이트를 vault에 위키화. 사람 curation은 옵션. | PWW L49, AGENTS.md L34-35 |

### 2.2 각 신호의 Layer 경계 정합성

#### ✅ 정합된 신호

| 신호 | 정합 논거 |
|---|---|
| **4 신호 (PWW §3)** | Layer 2의 "증분 누적" 판단 기준 — 사람turn/자율 모두 적용. north star 직접 구현. ✅ |
| **raw/ read-only (ADR-2026-07-02)** | Layer 1이 정의한 사람 1차 영역, Layer 2는 read-only. ✅ |
| **_meta/ read-only (PWW §2)** | Layer 1 내부 문서, Layer 2가 임의 수정 불가. ✅ |
| **1.5배 가드 (ADR-2026-07-06)** | north star "원문 보존"의 실행 가드. Layer 1이 정의, Layer 2가 따름. ✅ |
| **status 4상태 머신 (ADR-2026-07-06)** | Layer 1 스키마 정의, Layer 2 자율 정합화 루프 실행. ✅ |
| **#15 slug-title 1:1** | Layer 1의 naming contract, Layer 2가 위반 시 `wiki_rename`으로 수리. north star "보존" 경계선. ✅ |

#### ⚠️ 정합 불안정 신호

| 신호 | 불안정 이유 |
|---|---|
| **lint 자동 write 수리 (#1/2/10 등)** | PWW §6.5 L292: "content/ 내 링크는 `wiki_update`로 직접 수리" — Layer 2가 Layer 1 영역(`_meta/`) 수리는 "즉시 보고"로 구분. 그러나 Layer 2의 content/ 범위가 모호. |
| **stale → `wiki_archive` 에이전트 자율성** | ADR-2026-07-06 §3: "자동 archive (사람 승인 없는 격리) ❌" vs §1.2: "멀티 에이전트: `wiki_archive` ✅ (사용자 책임)" — 경계 모호. |
| **#13 cognitive governance 강화** | SCHEMA.md L223: "v0.7.66+ 강화" — 어떤 조건에서 어떤 자율 write가 트리거되는지 구체적 미정의. |

### 2.3 north star "원문 보존 + 증분 누적" 정합

| north star 구성 | 현재 신호 지원 | 비고 |
|---|---|---|
| **원문 보존** | 1.5배 가드, raw/ read-only, Tier 1 수정 금지 | ✅ 잘 지원됨 |
| **증분 누적** | 4 신호 (§3), log.md append-only, stale update provenance | ✅ 잘 지원됨 |
| **Layer 2 = 사람 1차 운영 인덱스** | raw/ 사람 1차, content/ 에이전트 쓰기, lint 큐레이션 | ⚠️ "사람 1차 운영" 강조이나, content/의 자율 write 범위와 큐레이션 주체가 불분명 |

**판단**: north star的两축("원문 보존" + "증분 누적")는 SOT에서 충분히 정의됨. Layer 2의 **"사람 1차 운영"** 성격은 raw/ 정책으로 잘 표현되나, content/의 자율 write가 "사람 1차 운영 인덱스"의 정체성(누가 무엇을 1차로 curated 하는가)과 정합성 있는지 추가 명확화가 필요.

---

## 3. 빠진 신호 (Gap) — 관찰

### Gap 1: `vault 성장률` 모니터링 신호 없음
- **문제**: vault에 페이지가 급격히 증가(예: 1주일内に 50+ 페이지)할 때, 이 것이 "증분 누적"인지 "에이전트 과잉 생성"인지 판단할 기준이 없음.
- **필요 위치**: PWW §6 (검증 절차) 또는 SCHEMA.md (lint #16 후보)
- **권고**: 7일/30일 growth rate lint (info 레벨) — "증가 속도가平常치 이상" 알림

### Gap 2: `중복/유사 페이지` 감지 신호 없음
- **문제**: 같은topic을 다루는 2개+ 페이지가 존재할 때 lint가 감지하지 않음. wiki_search로 찾더라도 "중복"이라는 명시적 판단 체계 없음.
- **필요 위치**: SCHEMA.md (lint #16 후보) 또는 PWW §6.5 큐레이션
- **권고**: title 유사도 기반 중복 감지 lint — `[[ 같은slug ]]` 상호 link로 합병 유도

### Gap 3: `inbound 0 + 신규 + 대량` 패턴 신호 없음
- **문제**: 新規作成 페이지가 inbound 0(orphan)이고 본문 크기가 대량(500줄+)인 경우 — orphan 가드(7일 유예)가 경과한 후에도 이萧條이 지속됨.
- **현재**: lint #4 orphan = 7일 + inbound 0, 但し "新建 + 大容量" 패턴은 명시적 트리거 없음.
- **권고**: orphanLint 확장 또는 큐레이션 절차에 명시

### Gap 4: `동일 질문 3회 반복` 감지 신호 없음
- **문제**: 사람/에이전트가 동일한 질문을 3회 이상 반복할 때, 해당 답변을永恒保存(새 페이지 생성)해야 한다는 판단 기준이 없음.
- **필요 위치**: PWW §3 저장 신호 보강 또는 §8 하지 말 것 확장
- **권고**: "동일 질문 3회+" = 새 `type: rule` 또는 `type: concept` 생성을 발의하는 신호로 추가

### Gap 5: `content/ 외 영역 변조` 탐지 신호 없음
- **문제**: 에이전트가 의도치 않게 `_meta/system/`, `raw/`, `log.md`를 변조하려 할 때 이를 탐지하고 차단하는 명시적 lint/가드.
- **현재**: API/MCP 수준에서 `permission_denied`로 차단되나, "어떤 에이전트가 어떤 경로에 쓰기 시도했는지" 감사 신호 없음.
- **필요 위치**: ADR-2026-07-02 권한 체계 + SCHEMA.md lint #14 tier integrity
- **권고**: audit log (log.md에 기록) — 차단 성공 시에도 `actor` + `vault` + `attempted_path` + `result: blocked` 레코드

---

## 4. 충돌 신호 (Conflict) — 관찰

### Conflict 1: "4 신호 모두 NO → 쓰기 금지" vs "lint 위반 → 자동 수리 write"

| 신호 | 규칙 | 출처 |
|---|---|---|
| §3 4신호 모두 NO | 쓰기 금지 | PWW L243, AGENTS.md L130 |
| lint #1/2/10 위반 | `wiki_update`로 직접 수리 | PWW L292, SCHEMA.md L210 |

**문제**: lint 자동 수리가 "쓰기"인데, §3 4신호가 "쓰기 금지" 트리거일 수 있음. lint 수리를 위해 4신호를绕过하는 것이 north star "증분 누적"에 부합하는가?

**분석**: 4신호는 "새로운 knowledge/산출물을 저장할 것인가"를 판단하는 것이고, lint 수리는 "기존 문서의 무결성 결함을 수정"하는 것. 두 동작의 성격이 다름. 그러나 SOT에 이 구분이 명시적으로 서술되어 있지 않음.

**권고**: SCHEMA.md 또는 PWW §3에 "lint 수리 write는 4신호 적용 면제"를 명시.

### Conflict 2: "원문 보존" vs "slug 자동 rename (#15)"

| 신호 | 규칙 | 출처 |
|---|---|---|
| north star: 원문 보존 | 파일명/내용 변경 최소화 | PWW L53, AGENTS.md §0.5 |
| lint #15: slug 불일치 | `wiki_rename(new_slug)` 자동 수리 | PWW L301-303, ADR-2026-07-08 |

**문제**: `wiki_rename`은 wikilink를 재작성하지만, 파일명의 변경 자체가 "원문 보존" 원칙에 반할 수 있음. ADR-2026-07-08 L31은 "north star '원문 보존 + 증분 누적' 위배 회피"라며 운영자 명시 결정 요구. 但し PWW §6.5 L301-303은 "에이전트 직접 rename ❌"로 운영자 결정이 필요. 然而 운영자 결정 없이도 aliases 보존으로 추적성은 유지.

**분석**: 이 충돌은 **ADR-2026-07-08 L31이 이미 해결**함 —运营자 명시 결정 요구 + aliases 보존. 다만 이 결정을 PWW §6.5와 SCHEMA.md에 모두 동일하게 표현할 필요 있음 (현재는 PWW에만 있고 SCHEMA.md에는 없음).

**권고**: SCHEMA.md L81-85에 " aliases 보존 시 north star '증분 누적' 원칙 충족" 명시.

### Conflict 3: "stale → archived 에이전트 자율" 경계 모호

| 신호 | 규칙 | 출처 |
|---|---|---|
| ADR-2026-07-06 §3 | 자동 archive (사람 승인 없는 격리) ❌ | ADR-2026-07-06 L174 |
| ADR-2026-07-06 §1.2 | wiki_archive: 사람 ✅ / 단일 에이전트 ✅ / 멀티 에이전트 ⚠️ | ADR-2026-07-06 L70 |
| PWW §6.5 #7 | "stale → 아카이브 후보" = 사람에게 `raven log rotate` 요청 | PWW L300 |

**문제**: ADR는 에이전트의 `wiki_archive`를 ✅ 허용하나, PWW §6.5는 아카이브 후보를 사람 운영자에게 맡김. 두 문서가 불일치.

**분석**: ADR-2026-07-06이 더 reciente (2026-07-06)이고, PWW의 "사람 전용"은旧的 표현일 가능성 높음. ADR §1.2의 표가 현재 적정한 권한 정의.

**권고**: PWW §6.5 L300을 "ADR-2026-07-06 §1.2의 권한 매트릭스에 따라 에이전트도 `wiki_archive` 가능"으로 갱신.

### Conflict 4: "cognitive governance (#10) 4신호 미달 감지" vs "orphans 7일 후 자동 통과"

| 신호 | 규칙 | 출처 |
|---|---|---|
| lint #10 | 4신호 미달 페이지 → info "not in core taxonomy" | SCHEMA.md L220 |
| lint #4 orphan | 7일 유예 후 inbound 0 페이지 → orphanLint 통과 | SCHEMA.md L213-214 |

**문제**: 4신호 미달 (재사용성/인수인계/근거/실패기록 모두 없음)인데 7일 후 orphanLint까지 통과하면, vault에 아무 관련 없는 페이지가累积될 수 있음.

**분석**: 이 충돌은 **실질적 위험이 낮음** — lint #10은 info 수준(즉 경고일 뿐)이므로 vault에 저장은 허용됨. 그러나 "north star 증분 누적" 관점에서는 아무 연관 없는 페이지가 쌓이는 것을 방지하는 메커니즘이 없음.

**권고**: PWW §6.5에 "orphaned 90일+ → stale 전이"를 명시 (현재는 90일 + 새 출처가 stale 조건이며, orphan 90일 경과만으로는 stale이 아닌 것이 불명확).

---

## 5. 권고 — SOT 보강/추가

### 5.1 권고: SCHEMA.md L220 (#10 cognitive governance) 해석 명시

**위치**: SCHEMA.md L220 (lint #10 설명 주변)

**추가 권고 문장**:
> **"lint #10 info는 쓰기 허용과 무관"** — 4신호 미달은 §3 저장 결정과 별개로 lint #10 info만 보고함. vault 저장이 금지되지 않으며, 해당 페이지의 품질은 사람 운영자의 판단에 따름.

**理由**: Conflict 1 해소. 4신호 vs lint 수리의 경계를 명확히.

### 5.2 권고: PWW §3에 "lint 수리 write는 4신호 면제" 명시

**위치**: PWW §3 저장 결정 (L234-243)

**추가**:
> **면제**: lint (#1/2/10/15 등)의 자동 수리를 위해 `wiki_update`를 호출하는 경우, §3 4신호 판단을跳过할 수 있음. 이는 "새 지식 저장이 아니라 기존 문서의 무결성 수정"이며 north star "원문 보존"에 부합함.

**理由**: Conflict 1 해소.

### 5.3 권고: SCHEMA.md L81-85에 aliases와 north star 정합성 설명 추가

**위치**: SCHEMA.md L81-85 (slug 규칙 주변)

**추가**:
> **aliases 보존 시 north star 충족**: `slug` 변경 시 `aliases: [옛slug]`을 설정하면, 기존 wikilink 추적성이 유지되며 이는 "증분 누적" 원칙을 충족함. 단, 파일명 자체의 변경은 north star "원문 보존"의 경계선에 있으며, 일괄 rename은 vault 운영자의 명시 결정이 필요함 (ADR-2026-07-08).

**理由**: Conflict 2 해소 + ADR-2026-07-08 결정을 SCHEMA.md에도 반영.

### 5.4 권고: PWW §6.5 L300 (archive) → ADR-2026-07-06 §1.2 참조로 교체

**위치**: PWW L300

**변경 전**:
```
8. #12 log 500건 도달 — 사람에게 `raven log rotate` 요청 (사람 전용)
```

**변경 후**:
```
8. #12 log 500건 도달 — 사람에게 `raven log rotate` 요청 (사람 전용)
9. stale → `wiki_archive` — ADR-2026-07-06 §1.2 권한 매트릭스参照 (에이전트도 가능, 단 archived→current 복귀는 사람 승인 필수)
```

**理由**: Conflict 3 해소.

### 5.5 권고: SCHEMA.md에 Gap 감지 lint 신규 2종 추가

**위치**: SCHEMA.md L208-226 lint 목록 끝

**추가 권고 (lint #16, #17)**:

```
16. 🟡 vault growth rate abnormal — 7일内有 pages 증가율 > 3σ (과거 30일 기준). info 수준. PWW §6.5 큐레이션참조.
17. 🟡 duplicate title candidates — title 유사도 > 0.8 (TF/IDF 또는 Levenshtein) 2개+ 페이지. 큐레이션: 상호 [[wikilink]] 연결 또는 합병 발의.
```

**理由**: Gap 1, 2 해소.

### 5.6 권고: Raven vault 컨셉 Layer 2 정합성 강화 — PWW §0.5 보강

**위치**: PWW §0.5 (L42-67)

**추가**:
> **Layer 2 = 사람 1차 운영 인덱스**:
> - vault는 Raven 제품(Layer 1)이 제공하는 "markdown git SoT" 위에, 사람运营자가 1차로 curate하는 Layer 2 운영 영역.
> - north star "원문 보존 + 증분 누적"의 실행 주체는 **사람运营자**이며, 에이전트는 그 영역에서 "증분"을 보조하는 자율 역할.
> - content/의 자율 write는 "증분 누적"의 일부이나, 모든 write는 §3 4신호 또는 lint 수리 동기가 있어야 함. 무신호 저장은 ❌.

**理由**: Layer 2의 "사람 1차 운영 인덱스" 정체성을 north star와 직접 연결. 현재 PWW §0.5 L46-54에 Layer 1/2 정의는 있으나, "사람 1차 운영 인덱스"와 north star의 관계가 명시되지 않음.

---

## 부록: Gap / Conflict 요약 목록

### Gap (빠진 신호)
| # | 신호 | 예상 위치 |
|---|---|---|
| G1 | vault 성장률 모니터링 | SCHEMA.md lint #16 또는 PWW §6 |
| G2 | 중복/유사 페이지 감지 | SCHEMA.md lint #17 또는 PWW §6.5 |
| G3 | inbound 0 + 신규 + 대량 패턴 | PWW §6.5 큐레이션 확장 |
| G4 | 동일 질문 3회 반복 → 새 페이지 발의 | PWW §3 저장 신호 보강 |
| G5 | content/ 외 영역 변조 감사 로그 | ADR-2026-07-02 권한 체계 + log.md |

### Conflict (충돌)
| # | 신호 A | 신호 B | 상태 |
|---|---|---|---|
| C1 | §3 4신호 모두 NO → 쓰기 금지 | lint #1/2/10 자동 수리 → wiki_update | **미해결** — 경계 구분 명시 필요 |
| C2 | north star 원문 보존 | lint #15 wiki_rename | **ADR-2026-07-08로 해결済み** — SCHEMA.md 반영 필요 |
| C3 | PWW §6.5: archive = 사람 전용 | ADR-2026-07-06 §1.2: 에이전트 ✅ | **미해결** — PWW 갱신 필요 |
| C4 | lint #10 4신호 미달 | lint #4 orphan 7일 후 통과 | **허용 가능** — 90일+ stale로 연결 명시 필요 |

---

*평가 기준: Raven vault 컨셉 (Layer 2 = 사람 1차 운영 인덱스, north star = 원문 보존 + 증분 누적)*
*관련 SOT: SCHEMA.md, PWW, AGENTS.md, ADR-2026-07-02/06/08*
