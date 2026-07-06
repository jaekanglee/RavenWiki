# Changelog v0.7.74 — PROJECT-WORKFLOW.md 진입 가이드 강화 + Wizard MCP snippet (2026-07-06)

> **BLUF**: 사용자 정확한 진단 — "PROJECT-WORKFLOW.md를 보고 vault 진입한 외부 에이전트가 MCP 연결 법을 모름". Tier 1 leak signpost (`raven docs show agent-tools`)를 표준 MCP `tools/list` discovery로 전환, §1.5 신설로 vault 진입 가이드 강화, NewVaultWizard에 transport별 snippet + 복사 버튼. per-feature commit 2개.
>
> 이전 changelog: `_meta/changelog-v0.7.73.md`

---

## §0 — commit 2개

| commit | 항목 | 파일 | 변경 |
|---|---|---|---|
| `51456d0` | A. PROJECT-WORKFLOW.md — vault 진입 가이드 강화 (§1.5 신설) | `raven/core/templates/agent/PROJECT-WORKFLOW.md` | +53/−13 |
| `aaa3163` | B. NewVaultWizard — MCP 설정 snippet + 클립보드 복사 버튼 | `dashboard/src/components/NewVaultWizard.tsx` | +165/−9 |

---

## §A — 진단 배경

**사용자 정확한 진단 (2026-07-06)**:
> "PROJECT-WORKFLOW.md는 vault에 진입했을 때 활용법에 대해 가장 잘 알려줘야할 문서다.
> 다른 에이전트가 따라하려는데 MCP 연결 법을 모르겠나봐."

**RAG 발견**:
1. 기존 PROJECT-WORKFLOW.md 53줄: "MCP 연결 정보(엔드포인트/포트)와 전체 도구 목록은 `raven docs show agent-tools` 참고."
2. **`raven docs show`는 Tier 1 (raven 패키지 내부 CLI)** — 외부 에이전트는 호출 불가 (Tier 1 leak).
3. §1 표는 4 키워드(`save/ingest/query/lint`)만 — 실제 9개 MCP 도구 중 4개만 가리킴. `wiki_stale_detect`/`wiki_archive`/`wiki_graph`/`wiki_log` 누락 (stale, 2026-07-06 ADR §1.3 미반영).
4. **외부 에이전트가 vault 받으면 "어떻게 도달하지?"에서 막힘** — north star 2026-07-06 (외부 LLM이 표준 protocol로만 도달) 정신과 충돌.

**사용자 추가 결론**:
- 파일 분할/인덱싱 검토 → **Lite bootstrap 정책 §4 (v0.7.65+) — 2종+log.md 고정** → 분할은 over-scope
- 별도 skill.md → **Lite bootstrap 정책 §4 + Tier 1 leak + 정책 §4.0** → 부적합
- **방안 C + Wizard 보강** 결정: PROJECT-WORKFLOW.md를 *vault 진입 가이드*로 강화 + Wizard가 snippet 자동 생성

---

## A. PROJECT-WORKFLOW.md — vault 진입 가이드 강화 (`51456d0`)

**Lite bootstrap 정책 (v0.7.65+)**: 이 문서는 외부 MCP 에이전트가 vault 받을 때 자동 주입되는 Tier 2 (raven-v1, 4종 bootstrap 중 2종).

### 변경 사항

| 위치 | 변경 전 | 변경 후 |
|---|---|---|
| frontmatter title | "Project Workflow — 운영 사실" | "Project Workflow — vault 진입 가이드" |
| frontmatter updated | 2026-07-03 | 2026-07-06 |
| tags | `[system, workflow, meta]` | `[system, workflow, meta, mcp]` |
| H1 헤딩 | "Project Workflow — 운영 사실" | "Project Workflow — vault 진입 가이드" |
| §1 표 | 4 키워드 (save/ingest/query/lint) | **9 도구** (wiki_search/get_page/lint/graph/log/stale_detect, wiki_update/ingest/archive, wiki_delete/rename) |
| §1 signpost | "raven docs show agent-tools 참고" (🚨 Tier 1 leak) | "각 도구의 full 시그니처는 클라이언트의 `tools/list` 응답(MCP 표준 자동 discovery)으로 확인" |
| §1.5 (신설) | — | **MCP 도달법** — stdio / streamable-http transport 추상 정보 + vault 인자 필수 + mode 3종 |
| §1.5 마지막 단락 | — | "왜 Tier 1 내부 CLI를 가리키지 않는가" 명시 (Lite bootstrap 정책 부합) |

### §1.5 신설 내용 요약

- transport 2종 표 (stdio 권장 / streamable-http)
- 서버 실행 명령 (Tier 1 leak 없는 vendor-neutral 표현)
- "연결 후 즉시 할 일" — `tools/list` 자동 discovery 안내
- 구체적 endpoint snippet은 Dashboard 신규 vault 마법사 결과에서 자동 생성 (signpost)
- 운영자가 다른 환경(CLI/Tailscale/Docker) 운영 시 README.md 또는 vault 운영자에게 직접 요청

### stale 해소

- **2026-07-06 ADR §1.3 wiki_stale_detect/wiki_archive**가 §1 표에 누락 → 9 도구로 갱신
- **Tier 1 leak (raven docs show)** → 표준 MCP tools/list로 전환 (Lite bootstrap 정책 §4 부합)

**검증**: 변경 라인 수만 (md 파일, TypeScript/Python 무관).

---

## B. NewVaultWizard — MCP 설정 snippet + 복사 버튼 (`aaa3163`)

PROJECT-WORKFLOW.md §1.5 signpost ("snippet은 Dashboard 신규 vault 마법사 결과에서")를 구체화. wizard의 Step 2 결과 화면 "Agent 연결 (MCP)" 카드에:

### 추가된 구성

1. **stdio snippet (권장)** — `<pre>` 블록 + `<Button variant="secondary" size="sm">복사</Button>`
   ```json
   {
     "command": "python",
     "args": ["-m", "raven.mcp.cli", "--transport", "stdio", "--mode", "read"]
   }
   ```

2. **streamable-http snippet (원격)** — 동일 패턴
   ```json
   { "url": "<vault-host>:8765/mcp" }
   ```

3. **클립보드 복사 핸들러** — `navigator.clipboard.writeText` + Toast (v0.7.71 race-free auto-close 패턴 재사용)

4. **하단 안내 카드** — "tools/list 자동 discovery — 별도 문서 참조 불필요" + 권한 모드 3종 한 줄

### §13 적용

- **§13.1**: `<Button>` 컴포넌트 (v0.6.28+) 사용, 인라인 `<button>` ❌
- **§13.2**: 색/배경/테두리 모두 CSS 변수(`var(--color-surface-soft)`, `var(--color-hairline)` 등), 인라인은 구조(grid/flex/gap)만

### 데이터 속성

- `<pre data-testid="mcp-stdio-snippet">` / `<pre data-testid="mcp-http-snippet">` — 테스트 selector 용이

**검증**: tsc -b --noEmit clean.

---

## §1 — 검증 종합

| 검증 | 결과 |
|---|---|
| `tsc -b --noEmit` (dashboard) | clean |
| `git push origin master` | 완료 |

---

## §2 — 외부 에이전트 walkthrough (검증 시나리오)

> "새 vault 받고 외부 에이전트가 `PROJECT-WORKFLOW.md`만 읽고 MCP 연결 가능한가?"

1. **vault 받음** → `_meta/agents/SCHEMA.md` + `_meta/agents/PROJECT-WORKFLOW.md` 자동 주입
2. **§0 읽기 순서 따라**: log.md → index.md → 본 문서
3. **§1**: 9개 MCP 도구 표 + 사용 규약
4. **§1.5**: transport 2종 (stdio 권장) — "당신의 MCP 클라이언트가 다음 transport 중 하나로 자동 도달"
5. **§1.5 signpost**: "구체적 endpoint는 vault 운영자에게 받거나 wizard 결과에서"
6. **wizard 결과 화면** (운영자가 본인 vault 만들 때 자동 노출): 환경별 snippet + 복사 버튼
7. **연결 완료** → `tools/list` 호출 → 9 도구 schema 자동 discovery → 즉시 작업 가능

→ 외부 에이전트가 PROJECT-WORKFLOW.md를 보고 자기 MCP 클라이언트 표준 흐름으로 도달 가능.

---

## §3 — 사이클 연속성

| 사이클 | 항목 |
|---|---|
| v0.7.69-73 | Dashboard §13 통일 (5-7 사이클) |
| v0.7.74 | **PROJECT-WORKFLOW.md vault 진입 가이드 강화 + Wizard MCP snippet** |

→ Lite bootstrap 정책 (v0.7.65+) — Tier 1 leak 회피 + 외부 에이전트 도달 흐름 명확화. vendor-neutral re-alignment 정책과 정합.