# raven v0.6.36 — vendor-agnostic 재정렬 (Karpathy LLM Wiki north star)

> **핵심**: 사용자 정정 (2026-06-30) — "에이전트는 Codex/Antigravity/Claude/Hermes 어느 것이든 동일하게 다룬다. vendor 이름 자체를 정책 문서에 박지 말고, LLM Wiki 개념을 베이스로 추상화."
>
> ⚠️ **v0.6.37 재정렬 노트**: 본 changelog은 역사 보존을 위해 v0.6.36 톤("Karpathy LLM Wiki north star")을 그대로 유지하지만, 라이브 north star는 **v0.6.37에서 재정렬됨** — LLM Wiki는 **영감/출발점**이며 Raven은 **Obsidian 대체 자체 구현체**. vendor-neutral 정책은 그대로 유지.
>
> 본 릴리스는 north star "LLM Wiki 패턴"의 1차 실현 중 하나 — **에이전트 vendor-agnostic**. 향후 어떤 LLM이 와도 raven 정책은 그대로 유지.

릴리스 일자: 2026-06-30
이전: v0.6.35 (AGENTS.md 보강)

---

## 한 줄 요약

`agent/README.md` 외부 위임 섹션, `tests/test_external_delegation_contract.py` 회귀 가드, `raven/agents/__init__.py` + `raven/__init__.py` + `raven/mcp/cli.py` + `raven/mcp/README.md`의 vendor명 박힘을 모두 vendor-neutral로 재정렬. **vendor-neutral 정책 자체를 회귀 가드로 영구화** (`tests/test_vendor_neutrality.py` 5 tests).

## 1. 변경 사항

### 1-1. `raven/core/templates/agent/README.md` (+5 lines, vendor-neutral 재작성)

**v0.6.34 (vendor 표기)** → **v0.6.36 (vendor-neutral)**:
- 섹션 헤더: `외부 위임 backend (선택, v0.6.34+)` → `외부 LLM cross-check (선택, v0.6.36+)`
- 표: Codex CLI / Antigravity CLI 행 → `외부 LLM CLI` (vendor 무관, 추상)
- 호출 예: `codex -p '...'` / `agy -p '...'` → `<llm-cli> -p '...'`
- 트리거: "Gemini-family cross-check" → "cross-check 요청"
- north star 명시 추가: "어떤 vendor가 와도 동일하게 동작"

### 1-2. `tests/test_external_delegation_contract.py` (회귀 가드 vendor-neutral 재작성)

- L4 docstring: "Codex/Antigravity" → vendor-neutral
- `has_codex or has_agy` → `VENDOR_NEUTRAL_KEYWORDS` ("외부 LLM" / "cross-check")
- 신규 가드 4번째: **외부 위임 섹션에 vendor명 (Codex/Antigravity/Gemini) 직접 표기 ❌**

### 1-3. `raven/agents/__init__.py` (docstring vendor-neutral)

```diff
-"""raven.agents — adapters for non-human vault users (Hermes/Claude/Codex).
+"""raven.agents — adapters for non-human (LLM agent) vault users with scope + provenance.
+
+v0.6.36+: vendor-neutral. raven does not bake specific vendor names into this
+module. Any LLM worker (CLI, IDE assistant, autonomous agent, etc.) can use
+this adapter as long as it can call Python directly.
```

### 1-4. `raven/__init__.py` (module docstring vendor-neutral)

```diff
-    raven.agents    — agent adapters (Hermes / Claude / Codex workers)
+    raven.agents    — agent adapters (LLM workers with scope + provenance, vendor-neutral)
```

### 1-5. `raven/mcp/cli.py` (transport 설명 vendor-neutral, 3 patches)

- module docstring: "(local Hermes)" → "(local in-process)"
- `--transport` help: "stdio (local Hermes)" → "stdio (local in-process)"
- runtime comment: "for Hermes / desktop clients" → "for desktop / local clients"

### 1-6. `raven/mcp/README.md` (transport 설명 vendor-neutral)

- L17: `### stdio (local Hermes / desktop MCP client)` → `### stdio (local process / desktop MCP client)`

### 1-7. `_meta/changelog-v0.6.34.md` (역사 보존 + 재정렬 노트 추가)

- 헤더에 vendor-neutral 재기록
- 본문에 `v0.6.36 재정렬 노트` 추가 — "본 changelog은 역사 보존을 위해 vendor명을 그대로 유지하지만, 라이브 정책은 vendor-neutral로 재정렬됨"

### 1-8. `tests/test_vendor_neutrality.py` (신규, 5 tests) — 정책 영구화

정책 회귀 가드:
1. `agent/README.md` 외부 위임 섹션 vendor-neutral
2. `raven/agents/__init__.py` docstring vendor-neutral
3. `raven/__init__.py` module docstring vendor-neutral
4. `raven/mcp/cli.py` + `README.md` transport 설명 vendor-neutral
5. `README.md` 정책/라이브 본문 vendor-neutral

예외 (보존 영역):
- `_meta/raw/` — Karpathy 원본
- `_meta/decisions/` — ADR 본문
- `_meta/changelog/` — 역사
- `raven/curator/` — v3 합의안 docstring

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **425 passed, 1 skipped** (v0.6.34: 414 → v0.6.36: 425, +11) |
| test_external_delegation_contract.py | **4 passed** (vendor-neutral 가드 4개) |
| test_vendor_neutrality.py (신규) | **5 passed** (정책 회귀 가드 5개) |
| python import smoke | raven.agents / raven.mcp.cli / raven 정상 |
| Runtime 영향 | 0 (정책/문서/테스트만 변경) |

## 3. 의도

north star (README §North Star) = "LLM의 휘발성 메모리를 git-tracked 영속 markdown으로 변환, compounding knowledge 누적" — **어떤 LLM이 와도 동일하게 동작**이 핵심.

- v0.6.34는 "Codex/Antigravity"라는 구체 vendor명을 정책 문서에 박았음 → 특정 vendor가 바뀌면 정책 갱신 필요
- v0.6.36은 "외부 LLM cross-check"으로 추상화 → **vendor 추가/제거/교체가 정책에 영향 0**
- 회귀 가드(`test_vendor_neutrality.py`)가 정책 자체를 영구화 → 누군가가 다시 vendor명을 박으면 즉시 실패

## 4. 보존 영역 (vendor 예시 OK)

다음은 **vendor 예시로만 사용**되므로 보존:
- `_meta/raw/articles/karpathy-llm-wiki-2026.md` — Karpathy 원본 (불변)
- `_meta/decisions-d7-d9-multivault.md` — ADR 본문 (결정 근거)
- `_meta/changelog-v0.5.5~v0.6.35.md` — 역사 보존 (v0.6.34만 재정렬 노트 추가)
- `raven/curator/*.py` — v3 합의안 docstring (역사)
- `_meta/architecture.html` + `_meta/architecture-5layer.md` — 다이어그램
- `log.md` — 운영 사실 기록

## 5. 후속 작업 (메모리 §next)

- Worker result 어댑터 (vendor-neutral WorkerResult normalize)
- Tier 1 leak pre-commit hook (lint #14 git hook 보완)
- lint #15 north star drift (README/AGENTS.md/wikisys-policy.md §North Star 누락 감지)

## 6. Karpathy LLM Wiki와의 관계

| Karpathy 원본 | Raven v0.6.36 |
|---|---|
| "OpenAI Codex, Claude Code, OpenCode / Pi, or etc." | **vendor 추상화: "외부 LLM cross-check"** |
| "CLAUDE.md for Claude Code or AGENTS.md for Codex" | **vendor 추상화: "agent/README.md" (모든 LLM 공통 진입점)** |
| agent = 위키 운영자 (any vendor) | **Raven agent = any LLM worker (vendor-neutral adapter)** |

→ **v0.6.36은 Karpathy의 "agent-as-writer" 모델을 vendor-neutral로 명시화한 첫 릴리스.**