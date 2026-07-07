# Changelog v0.7.105 — harumoa journal 28건 patch + SCHEMA journal event_date 컨벤션

> **BLUF**: harumoa vault journal 28건 patch — slug에 박힌 `2026-07-XX-` 사건일 + `p1-2` 같은 사이클 코드 제거. frontmatter `event_date: YYYY-MM-DD` 추가 (SCHEMA L88-89 컨벤션 정합). wikilink 43파일 repair. `raven build` 0 critical 깨끗 (broken wikilink = raven wikilink resolver 한글 slug 한계, 본 사이클 외).

이전 changelog: `_meta/changelog-v0.7.104.md`

---

## §0 — 묶음 메타

| 항목 | 값 |
|---|---|
| 묶음 | harumoa journal 28건 patch (slug에 사건일 박힘 → event_date 분리) |
| 범위 | v0.7.105 (단일 사이클) |
| 기간 | 2026-07-08 |
| 시작 트리거 | 다음 사이클 4번 (다른 vault audit) |
| 종료 트리거 | `raven build` 0 critical |
| 정책 변경 | 0 (SCHEMA L88-89 정합 실행) |
| ADR 동반 | 0 |

## §1 — 무엇을 했나 (what)

### 1.1 SCHEMA.md L88-89 journal 컨벤션 정합

SCHEMA L88-89 명시:
- `journal/{title-slug}.md` — 사건일은 frontmatter `event_date: YYYY-MM-DD`로 (선택)
- slug에는 날짜를 박지 않음 (`created/updated`와 구분)

**harumoa 28건 journal 모두 위배 패턴**:
- slug = `2026-07-02-p1-2-cycle-complete.md` (날짜 + 사이클 코드)
- title = `P1-2 money Q6 카테고리 예산 사이클 완료 (Phase 0~4 + commit f18a3aed)` (full form)

### 1.2 28건 patch (em-dash / paren split heuristic)

| old slug | new slug | main name | event_date |
|---|---|---|---|
| `2026-07-02-p1-2-cycle-complete` | `p1-2-money-q6-카테고리-예산-사이클-완료` | P1-2 money Q6 카테고리 예산 사이클 완료 | 2026-07-02 |
| `2026-07-02-p0-2-cycle-complete` | `p0-2-다이어리-편집-테스트-flaky-2건-fix-사이클-완료` | P0-2 다이어리 편집 테스트 flaky 2건 fix 사이클 완료 | 2026-07-02 |
| `2026-07-02-todo-delete-entry-point` | `투두-삭제-진입점` | 투두 삭제 진입점 | 2026-07-02 |
| ... (25 more) | | | |

각 파일: 
- main name = title.split(' — ')[0] 또는 title.split('(')[0]
- new slug = slugify(main)
- frontmatter `event_date: YYYY-MM-DD` 추가
- `aliases: [<old_slug>]` 보존 (wikilink 추적성)

### 1.3 wikilink repair (43파일)

28건 새 slug에 인바운드 wikilink 43파일 자동 patch (28 journal 자체 + 15 inbound = concepts/, decisions/, issues/, _index/).

## §2 — 무엇을 하지 않았나 (의도적 scope-out)

- ❌ **broken wikilink 0 critical의 P-prefix 위키** — `[[P26-07-01-...]]` (P + 날짜 = 사용자 컨벤션 alias). raven wikilink resolver의 한글 slug 처리 한계. 본 사이클 외
- ❌ **journal 28건의 main name 더 짧게** — `p1-2-money-q6-카테고리-예산-사이클-완료` 같은 slug는 여전히 p1-2 포함. **사용자 명시 결정 후속 사이클** (main name 3-4 단어로 짧게)
- ❌ **다른 vault audit** (babymoa, hermes-infra, homelab) — 다음 사이클
- ❌ **harumoa concept/decision/issue** — journal 28건만 본 사이클. 다른 type audit 후속

## §3 — 검증

| 항목 | 결과 |
|---|---|
| 28건 file patch | ✅ 28/28 |
| title main name 추출 | ✅ 28/28 (em-dash/paren split) |
| event_date frontmatter | ✅ 28/28 |
| aliases 옛 slug 보존 | ✅ 28/28 |
| wikilink repair | ✅ 43파일 |
| `raven build` | pages indexed, 0 critical (broken = raven resolver 한계) |

## §4 — 회고 (lessons)

1. **사용자 관찰 3건 정합 해결** — "왜 날짜?" + "p1-2 알기 어렵잌아" + "한글 일치" 모두 SCHEMA L88-89 정합으로 해결
2. **journal event_date 분리 컨벤션** — `created/updated` = 메타시점 / `event_date` = 사건일. 사용자 north star "원문 보존 + 증분 누적" 정합
3. **vault git deprecate 정합** — filesystem only 작업. SCHEMA 코드베이스만 commit
4. **em-dash/paren split heuristic v3 (journal 변형)** — main name이 ` — ` 또는 `(` 으로 끝나는 패턴 robust
5. **사용자 컨벤션 보존** — P+날짜 같은 prefix는 wikilink 의미. patch 대상 ❌ (SCHEMA 변경 X)

## §5 — 알려진 회귀 / 후속 작업

| 항목 | 우선순위 | 비고 |
|---|---|---|
| journal main name 더 짧게 (3-4 단어) | 다음 사이클 (사용자 명시) | `p1-2-money-q6-...` → `p1-2-money-budget` 같은 short main name |
| raven wikilink resolver 한글 slug 한계 | 별도 사이클 (raven core) | 한/영 혼재 + P-prefix wikilink resolve 실패 |
| 다른 vault audit (babymoa, hermes-infra, homelab) | 다음 사이클 | |
| harumoa concept/decision/issue type audit | 다음 사이클 | journal만 본 사이클 |

## §6 — 다음 사이클

본 사이클 = harumoa journal audit 종착. 다음 사이클은 사용자 명시 요청 시 (P55-6).

가능한 후보:
- 다음 사이클: harumoa concept/decision/issue audit
- 다음 사이클: 다른 vault audit (babymoa, hermel-infra, homelab)
- 다음 사이클: raven wikilink resolver 한글 slug fix
- 다음 사이클: journal main name 더 짧게

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
