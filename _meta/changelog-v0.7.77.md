# Changelog v0.7.77 — PROJECT-WORKFLOW §1.5.1 표준 MCP 패턴 + Wizard 동기화 (2026-07-06)

> **BLUF**: 사용자 정확한 진단 (2026-07-06) — "어떤 에이전트든 표준이니까 MCP 표준 흐름으로 vault에 자동 도달할 수 있어야". PROJECT-WORKFLOW.md §1.5에 §1.5.1 신설 (vendor-neutral 표준 클라이언트 설정 패턴 + 첫 호출 흐름 + 트러블슈팅), Wizard 결과 화면 안내 카드 강화 (3섹션 구조).
>
> 이전 changelog: `_meta/changelog-v0.7.76.md`

---

## §0 — commit 2개

| commit | 항목 | 파일 | 변경 |
|---|---|---|---|
| `d90c54f` | A. PROJECT-WORKFLOW.md §1.5.1 표준 MCP 클라이언트 설정 패턴 + 첫 호출 흐름 | `raven/core/templates/agent/PROJECT-WORKFLOW.md` | +53 |
| `71229c8` | B. NewVaultWizard 결과 화면 안내 카드 vendor-neutral + 표준 흐름 강화 | `dashboard/src/components/NewVaultWizard.tsx` | +25/−3 |

---

## §A — 진단 배경

**사용자 정확한 진단 (2026-07-06)**:
> "어떤 에이전트든 표준이니까 — 어떤 에이전트가 vault 내 _meta를 분석해도 MCP 표준 형식으로 연결할 수 있게."

**v0.7.74의 한계**:
- §1.5 신설했으나 transport 정보 위주 — 표준 MCP 클라이언트가 받는 *설정 형식* (JSON 스니펫) 없음
- "vault 운영자에게 받으세요" signpost만 있고, *어떤 패턴으로 요청/설정하는지* 안내 부재
- 트러블슈팅 가이드 없음 — 연결 실패 시 에이전트가 자기 행동 결정 근거 부족

**Lite bootstrap 정책 부합 (vendor-neutral)**:
- §1.5.1 본문에 vendor 명 표기 0건 (Claude/Cursor/Hermes/Codex/Antigravity 일체 ❌)
- JSON-RPC 표준 형식만 노출 — MCP 호환 클라이언트라면 *어떤 것이든* 동일하게 동작

---

## A. PROJECT-WORKFLOW.md §1.5.1 신설 (`d90c54f`)

### 구성

| 항목 | 내용 |
|---|---|
| **두 표준 패턴 표** | `command` 기반 (stdio, 로컬 sub-process) + `url` 기반 (streamable-http, 원격) — JSON 스니펫 |
| **첫 도구 호출 흐름** | `tools/list` → 9개 도구 schema 자동 discovery → 첫 호출 시 `vault=<이름>` 인자 필수 |
| **권한 모드 3종 표** | read (6종) / write (+3종, 페이지 CRUD/격리) / admin (+2종, 사람 운영자 전용) |
| **트러블슈팅 4가지** | `command not found: python` / `address already in use` / `permission_denied` / `vault not found` |

### §1.5.1의 vendor-neutral 검증

- vendor 명 표기 0건
- "어떤 MCP 클라이언트든 동일하게 동작" 추상 표현
- 표준 MCP 클라이언트 설정 형식 (JSON-RPC)만 노출
- 트러블슈팅은 command/permission_denied 같은 **MCP 표준 응답 메시지** 기반 (vendor 무관)

**검증**: 변경 라인 수만 (md 파일, TypeScript/Python 무관).

---

## B. NewVaultWizard 결과 화면 안내 카드 강화 (`71229c8`)

PROJECT-WORKFLOW.md §1.5.1과 동기화 — wizard 결과 화면의 "Agent 연결 (MCP)" 카드 하단 안내가 §1.5.1과 같은 흐름을 안내.

### 변경 (1줄 → 3섹션)

| 섹션 | 내용 |
|---|---|
| **표준 MCP 연결 흐름** | 3 steps: 설정 추가 → tools/list → vault 인자 |
| **권한 모드** | read/write/admin 한 줄로 압축 + 사람 운영자 전용 명시 |
| **연결 안 될 때** | 4가지 증상 + 해결 (트러블슈팅) |

### §13 적용

- §13.2: 색/배경 모두 CSS 변수, 구조(grid/gap)만 인라인
- fontWeight 600 / fontSize 12 — 기존 §1.5.1과 시각적 정합

### vendor-neutral 검증

- vendor 명 표기 0건
- §1.5.1과 1:1 sync

**검증**: tsc -b --noEmit clean.

---

## §1 — 검증 종합

| 검증 | 결과 |
|---|---|
| `tsc -b --noEmit` | clean |
| `git push origin master` | 완료 |

---

## §2 — 외부 에이전트 walkthrough (검증 시나리오, v0.7.74 + v0.7.77 통합)

> "새 vault 받고 외부 에이전트가 표준 MCP 클라이언트로 자동 도달"

1. **vault 받음** → `_meta/agents/SCHEMA.md` + `_meta/agents/PROJECT-WORKFLOW.md` 자동 주입
2. **§0 읽기 순서**: log.md → index.md → 본 문서
3. **§1**: 9개 MCP 도구 표 + 사용 규약
4. **§1.5**: transport 2종 (stdio 권장 / streamable-http)
5. **§1.5.1** (v0.7.77): 표준 MCP 클라이언트 설정 패턴 2종 + JSON 스니펫
   - "command 기반" 또는 "url 기반" 둘 중 하나를 자기 클라이언트 설정에 추가
6. **첫 도구 호출**: `tools/list` (자동 discovery) → `wiki_search(vault="<이름>", ...)`
7. **vault 운영자 안내**: wizard 결과 화면 "Agent 연결 (MCP)" 카드가 §1.5.1과 동기화된 3섹션 안내

→ 외부 에이전트가 *어떤 MCP 클라이언트든* 표준 흐름으로 vault에 도달 가능. vendor 명 의존 0.

---

## §3 — 사이클 연속성

| 사이클 | 항목 |
|---|---|
| v0.7.74 | PROJECT-WORKFLOW.md §1.5 신설 + Wizard MCP snippet |
| v0.7.75 | VaultManage 자동 verify-all + 일괄 업뎃 banner |
| v0.7.76 | CDS 토큰 30곳 정리 + label 이모지 + 즐겨찾기 hover |
| v0.7.77 | **§1.5.1 표준 MCP 패턴 + Wizard 동기화 (vendor-neutral 강화)** |

→ Lite bootstrap 정책 (v0.7.65+) + vendor-agnostic 정책 (v0.6.36+) 일관성 유지.
MCP 표준 흐름으로 *어떤 에이전트든* vault 도달 가능.