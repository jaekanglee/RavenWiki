---
title: Vault Patterns — Karpathy LLM Wiki +α Guide
created: 2026-06-30
updated: 2026-06-30
type: rule
audience: human, agent
confidence: high
tags: [system, patterns, llm-wiki, optional]
---

# Vault Patterns — Karpathy LLM Wiki +α Guide

> **Raven = Zettelkasten-inspired PKM 도구.** 기본은 사람 1차 자유 vault:
> 작은 생각 단위, 자기 언어화, wikilink 연결, 누적/재조합.
> Dashboard는 Obsidian-style 앱 표면이고,
> 이 문서는 **선택적 +α 패턴** — Karpathy LLM Wiki (2026)의 3-Layer 구조를
> vault 안에서 활성화하고 싶을 때 참조.
>
> **강제 ❌.** 원하지 않으면 이 문서 무시해도 됩니다.

---

## 0. Quick check — 이 패턴이 필요한가?

| 질문 | YES → 패턴 | NO → 기본 유지 |
|---|---|---|
| vault에 변하지 않는 source를 따로 보관하고 싶다 | **raw/ 패턴** | 그냥 content/ |
| 누가 언제 무엇을 했는지 자동으로 기록하고 싶다 | **log.md 패턴** | 안 필요 |
| 에이전트가 자기 작업 폴더를 따로 가져야 한다 | **_meta/agents/ 패턴** | vault 전체 자유 |
| LLM Wiki의 "compounding knowledge"를 활성화하고 싶다 | **3개 모두 켜기** | 안 켜도 됨 |

→ **3개 모두 opt-in. 안 켜면 vault는 그냥 Obsidian-style 자유 폴더.**

---

## 1. 활성화 방법 (3가지)

### 방법 A — `features` flag (v0.6.39+ 권장)

`vault/.vault.json`에 추가:

```json
{
  "features": {
    "llm_wiki": true
  }
}
```

Raven은 `llm_wiki: true` 감지 시 raw/ log.md _meta/agents/ 패턴을 인식합니다.
**다른 raven 기능 (build/lint/search) 동작은 동일**.

### 방법 B — 구조 신호 존재 (자동 감지)

`vault/_meta/agents/` 가 존재하면 Raven이 LLM Wiki 패턴 활성화로
간주합니다. 사용자가 자연스럽게 켜는 방식입니다.

`raw/` 와 `log.md` 단독 존재는 자동 감지 신호로 쓰지 않습니다. 일부
non-wiki 흐름에서도 source 저장소나 운영 로그가 생성될 수 있기 때문입니다.

### 방법 C — 안 켜기 (기본)

`features` flag 없음 + _meta/agents/ 폴더 없음 → vault는 그냥
Obsidian-style 자유 vault. Raven은 어떤 패턴도 강제하지 않음.

---

## 2. raw/ 패턴 (immutable source)

Karpathy 원본 L24-26: "Raw sources — your curated collection of source
documents. These are immutable — the LLM reads from them but never modifies
them."

```
vault/
├── raw/                    ← immutable source (read-only for agent)
│   ├── articles/
│   │   └── 2026-06-15-karpathy-llm-wiki.md
│   └── papers/
│       └── 2026-arxiv-rag.pdf
├── content/
│   ├── concept/
│   │   └── llm-wiki.md     ← compiled note, sources: frontmatter로 raw 연결
```

**규약 (사용자 자유, 이 패턴 켰을 때 권장)**:
- `raw/` 안 파일은 절대 자동 수정 ❌
- content/ 페이지는 `sources:` frontmatter로 raw 파일 참조
- lint는 raw/ 안 파일을 wikilink로 backref 추적

**Agent 표준 인터페이스 (MCP, v0.7.8+)**:

> **에이전트 ↔ Raven = MCP 단일**. Python adapter (`raven.agents`)는 v0.7.9+ 제거됨.

에이전트(MCP client: 표준 protocol 지원하는 어떤 agent든)는 **MCP 표준 protocol**로 Raven과 통신. `tools/list`로 도구 자동 발견, `tools/call`로 호출.

```python
# MCP client 측 (Python 예시 — using `mcp` SDK)
from mcp import Client

async def harumoa_compiler():
    client = Client("http://127.0.0.1:8766/mcp")  # Raven MCP server
    tools = await client.list_tools()  # 자동 발견 (wiki_search, wiki_get_page, wiki_update, wiki_lint)
    # → 예: wiki_update (slug, content, frontmatter_data)

    # compiled/만 write 허용 (raw/는 deny)
    result = await client.call_tool(
        "wiki_update",
        slug="content/compiled/foo",
        content="...",
        frontmatter_data={"title": "...", "type": "concept", "tags": ["compiled"]},
    )
    # raw/ write 시도 시 Result(ok=False) — path scope 강제
```

## 3. log.md 패턴 (append-only work log)

Karpathy 원본 L56: "log.md is chronological. It's an append-only record
of what happened and when — ingests, queries, lint passes."

```
vault/
├── log.md                  ← 자동 생성/유지
```

**자동 append 시점** (Raven):
- `raven build` → action=build
- `raven page new` → action=create
- `raven lint run --log` → action=lint
- `raven meta sync` → action=meta

**포맷** (Karpathy 권장, Raven 표준):
```
## [YYYY-MM-DD] <action> | <subject>
- file: <path>
- run_id: <agent run>
- note: <free text>
```

**규약**:
- append-only — 기존 줄 수정 ❌
- 500 entries 도달 시 rotate 권장 (`raven log rotate`)
- vault 안 `log.md` 없으면 → Lite bootstrap 또는 v0.6.38+ `llm-wiki` profile에서 자동 생성

**Agent 어댑터**:
```json
// log.md는 자동 append되므로 에이전트가 직접 작성 안 함
// 대신 자신의 결정/관찰은 wiki_update MCP 툴을 통해 journal로 작성
{
  "name": "wiki_update",
  "arguments": {
    "slug": "content/journal/2026-06-30-finding",
    "content": "...",
    "frontmatter": {"title": "Finding Note", "type": "journal"}
  }
}
```

---

## 4. _meta/agents/ 패턴 (에이전트 행동 지침)

```
vault/
├── _meta/
│   └── agents/
│       ├── README.md       ← 에이전트 진입점
│       └── YOUR-AGENT.md   ← 사용자 정의 에이전트 지침
```

**Tier 1 주의**: `raven/core/templates/agent/*` (raven 패키지 내부)와
**완전히 다름**. `_meta/agents/`는 vault 사용자 정의.

**기본 vs 사용자 정의**:
- 기본 — Raven MCP 도구가 강제하는 공통 안전 규칙 (provenance, immutable path guard 등)
- 사용자 정의 — vault마다 다른 정책 (어떤 type만 쓸지, 어떤 wikilink 패턴 등)

**Tier 1 leak과의 관계**:
- `_meta/agents/`는 vault-native → **Tier 1 leak 아님**
- `agent/` (Tier 1 패턴)는 raven internal doc leak → 기본 critical
- 사용자가 둘 다 켜고 싶으면 `allow_tier1_leak: true` (v0.6.39+)

---

## 5. compounding knowledge (3-Layer 통합)

Karpathy 원본 L20: "the wiki is a persistent, compounding artifact."

3개 패턴 동시 활성화 시:

```
Layer 1 (raw/)        ← immutable source
        ↓
Layer 2 (content/)    ← compiled note (에이전트/사람 작성)
        ↓
Layer 3 (log.md)      ← work audit trail
        ↓
Layer 4 (_meta/agents/) ← 에이전트 행동 규칙
```

**flow**:
1. 사용자가 raw/에 새 article 저장 (예: PDF, web clipping)
2. 에이전트가 raw/ 읽고 → content/concept/x.md 작성 (sources: frontmatter)
3. raven build가 index/lint 갱신
4. log.md에 build entry 자동 append
5. 다음 세션에서 에이전트가 _meta/agents/ 규칙 따라 일관성 유지

---

## 6. 사용자 시나리오 모음

### 시나리오 A — 순수 Obsidian 사용자 (LLM Wiki 패턴 ❌)
```
vault/
├── content/
│   └── 자유.md
└── (다른 폴더 자유)
```
→ Raven이 자동화해주는 건 build/index/lint 정도. log.md 안 박음.

### 시나리오 B — 일반 LLM Wiki 사용자 (3 패턴 다 켜기)
```bash
raven vault create my-vault ~/Raven/my-vault --profile llm-wiki
# → Lite bootstrap 5종 자동 복사 (v0.7.3+ profile)
# → log.md는 raven이 자동 관리
# → _meta/agents/TOOLS.md는 MCP 도구 surface (도구 목록 + 입출력 schema)
```

### 시나리오 C — 고급 사용자 (custom)
```bash
raven vault create draft ~/Raven/draft --profile basic
# → WELCOME.md 1장만
# → 나중에 raw/ log.md _meta/agents/ 만들고 싶으면 자유 생성
# → features flag로 raven이 인식
```

### 시나리오 D — 에이전트 협업 (raw/ 보호)

> **에이전트는 MCP client로만 Raven과 통신** (v0.7.8+). Python adapter ❌.

```
# MCP client 설정 (Claude Desktop / Cursor / Hermes)
# → Raven MCP server (port 8766) 연결
# → tools 자동 발견: wiki_update, wiki_get_page, wiki_search, wiki_lint, wiki_log
# → write 도구는 raw/, _meta/, log.md 보호 규칙을 자동 강제
```

**내장 보호 규약**:
- `raw/**` — 에이전트 수정 ❌
- `_meta/**` — 에이전트 수정 ❌
- `log.md` — 직접 수정 ❌ (엔진 자동 append only)
- 세부 path allowlist/denylist 확장은 향후 후보이며, 현재는 vault 규약과 MCP mode가 경계를 이룸

## 7. 비활성화 / 다시 켜기

### 끄기
```bash
# .vault.json에서 features 제거
jq 'del(.features)' ~/Raven/my-vault/.vault.json > tmp && mv tmp ~/Raven/my-vault/.vault.json
# 또는
echo '{}' > ~/Raven/my-vault/.vault.json
# → raw/ log.md _meta/agents/ 폴더는 그대로 남음 (사용자 데이터 보존)
# → raven은 더 이상 패턴 인식 안 함
```

### 다시 켜기
```bash
# features.llm_wiki: true 다시 박기
# 또는 raw/ log.md _meta/agents/ 폴더 재생성
```

→ **켜고 끄기 자유, 켠 흔적은 데이터로 남음** (lock-in ❌).

---

## 8. 다음 패턴 (v0.7.x+ 후보)

| 패턴 | 의미 | 의존 |
|---|---|---|
| `compiled/` 분리 | 에이전트 작성 vs 사람 작성 분리 | v0.6.40 path scope |
| `claims/` 노트 | 명제 단위 분리 (Karpathy 인용) | v0.7.0+ 예정 |
| `_meta/queries/` | 자주 묻는 질문 vault | 예정 |
| `agents/<name>.md` | 에이전트별 행동 지침 | 사용자 자유 |

---

## 9. Karpathy 원본과의 정직한 거리

| Karpathy 원본 | Raven +α 구현 | 비고 |
|---|---|---|
| raw/ immutable | ✅ 그대로 | 패턴 활성화 후 source layer로 사용 |
| LLM이 wiki 쓰기 | ✅ MCP write tools | immutable path guard + provenance |
| 사람이 source curate | ✅ 사용자 자유 | Raven 강제 ❌ |
| log.md append-only | ✅ raven 자동 | action=create/build/lint |
| CLAUDE.md / AGENTS.md | ✅ _meta/agents/ | Tier 1 leak과 분리 (v0.6.39) |
| schema (e.g. CLAUDE.md) | ✅ SCHEMA.md (lite) | 사용자가 직접 작성 가능 |

→ **Raven은 Karpathy LLM Wiki를 vault 안에서 +α로 실현할 수 있는 도구**.
   안 켜도 OK, 켜도 OK.

---

## 10. 결론 (한 줄)

> **Raven은 Obsidian-style 자유 vault가 기본. LLM Wiki 패턴은 켜고 끄기 자유. 강제 ❌.**
