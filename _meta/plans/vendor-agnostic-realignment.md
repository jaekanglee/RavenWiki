# Vendor-agnostic 재정렬 plan (Raven v0.6.36+)

> **사용자 정정 (2026-06-30)**: "헤르메스인지 코덱스인지 클로드든지 그거 자체를 표기하지말고 추상화하라고, llm wiki 개념을 베이스로"
>
> **north star 재정렬**: README §North Star + AGENTS.md §0.5에 명시된 "Karpathy LLM Wiki 패턴의 self-host 구현체" 위에서, **에이전트 vendor는 추상화**. "LLM 에이전트" / "외부 LLM cross-check" / "Python adapter" / "scope 기반 provenance" 같은 vendor-neutral 용어로 통일.

---

## 0. 핵심 결정

| 항목 | 결정 |
|---|---|
| **추상 용어** | "LLM 에이전트" (vendor 무관) - `LLMClient` 또는 `Worker` |
| **외부 cross-check 호출** | "외부 LLM cross-check" (vendor-neutral) - Codex/Antigravity 표기 ❌ |
| **adapter 모듈** | `raven/agents/` 유지 (의미: "agent 어댑터"), docstring에서 vendor 표기 ❌ |
| **예시 (선택적)** | docstring에 "e.g. ..." 형태로 vendor 예시는 OK (이해 보조), 본문 vendor 표기 ❌ |

---

## 1. 영향 받는 파일 (전수조사 결과)

### 🔴 즉시 수정 (north star 위반, 라이브 정책)

#### 1-A. `raven/core/templates/agent/README.md`

- **현재 (v0.6.34)**:
  - L70-79: 외부 위임 backend 섹션 - Codex CLI / Antigravity CLI 표
  - L72: "Gemini-family cross-check"
- **After**:
  - 섹션 헤더: "외부 LLM cross-check (선택, v0.6.36+)"
  - 표: "어떤 LLM CLI든" - JSON/plain-text/markdown 모두 vendor에 따라 다름
  - 트리거: "사용자 명시 또는 cross-check 요청 시점에만"
  - 호출 예: 추상화된 한 줄 (`terminal(command="<llm-cli> -p '...'", workdir=...)`)
- **effort**: ~10 lines patch

#### 1-B. `tests/test_external_delegation_contract.py`

- **현재**:
  - L4: "Codex/Antigravity CLI 한 줄 가이드 보존 확인"
  - L7: "'외부 위임' 또는 'Antigravity' / 'Codex' 키워드"
  - L21-25: `has_codex or has_agy` (vendor 키워드 회귀)
- **After**:
  - L4 docstring: "agent/README.md 외부 LLM cross-check 가이드 보존 확인"
  - 회귀 가드 3개 vendor-neutral 키워드로 재작성:
    1. "외부 LLM" 또는 "cross-check" 키워드
    2. wrap-up 단계 fix 침습 금지 (유지)
    3. "사용자 명시" 또는 "cross-check" 트리거 (유지)
- **effort**: ~10 lines patch

#### 1-C. `_meta/changelog-v0.6.34.md`

- **현재**: L1 헤더 "agent/README.md 외부 위임 backend 한 줄 가이드 (Antigravity/Codex)", 본문 vendor명 다수
- **After**: 헤더 vendor-neutral, 본문 vendor명 제거, "v0.6.36에서 vendor-neutral 재정렬됨" 1줄 노트 추가
- **effort**: ~5 lines patch

### 🟡 부분 수정 (예시는 OK, 본문 정책 강화)

#### 1-D. `raven/agents/__init__.py`

- **현재 L1**: `"""raven.agents — adapters for non-human vault users (Hermes/Claude/Codex)."""`
- **After**: `"""raven.agents — adapters for non-human (LLM) vault users with scope + provenance."""`
- **effort**: 1 line

#### 1-E. `raven/__init__.py`

- **현재 L5**: `raven.agents    — agent adapters (Hermes / Claude / Codex workers)`
- **After**: `raven.agents    — agent adapters (LLM workers with scope + provenance)`
- **effort**: 1 line

#### 1-F. `raven/mcp/cli.py` (참고용 transport 설명)

- **현재 L5, L231, L263**: "Hermes" 언급 (stdio transport)
- **After**: transport 설명에 vendor-neutral - "local process client" 또는 "in-process transport"
- **effort**: ~5 lines
- **판단**: mcp는 stdio/HTTP transport 기술적 설명이라 vendor-neutral 표현 가능 ("local process" / "HTTP client"). 사용자 vendor명 제거.

#### 1-G. `raven/mcp/README.md`

- **현재 L17**: `### stdio (local Hermes / desktop MCP client)`
- **After**: `### stdio (local process / desktop MCP client)`
- **effort**: 1 line

### 🟢 보존 (역사/예시/사실)

- `_meta/raw/articles/karpathy-llm-wiki-2026.md` - Karpathy 원본 (불변, 보존)
- `_meta/decisions-d7-d9-multivault.md` L96 - ADR 본문 (예: 결정 근거로 vendor명 OK)
- `_meta/changelog-v0.5.5.md`, `v0.5.6.md`, `v0.5.7.md` - historical critique (vendor명 = 누가 발견했는지 사실)
- `_meta/changelog-v0.6.5.md` L3, L26 - Codex/Claude 위임자 발견 (역사 사실)
- `_meta/changelog-v0.6.31~33.md` - vendor example 언급 (역사)
- `_meta/architecture-5layer.md` - 다이어그램 설명 (예)
- `_meta/architecture.html` - 시각화
- `raven/curator/*.py` docstring - "v3 합의안" (역사적 critique 출처)
- `raven/curator/__init__.py` L3 - 보존
- `log.md` L340 - 운영 사실
- `dashboard/tests/wikilink.test.ts` L44, L48 - wikilink 테스트 fixture (예)
- `scripts/tests/test_lint.py` L528 - 테스트 fixture (예)
- `AGENTS.md` L144, L156, L217, L241 - Codex/Claude critique 결과 (역사), §11 "Codex/Claude/Cursor"는 추상화 표현으로 OK (이미 vendor 목록이 아님)

### 🟡 정책 검증 (회귀 가드 신규)

#### 1-H. `tests/test_vendor_neutrality.py` (신규)

- vendor 이름 (Codex, Claude, Antigravity, Hermes 등) 코드베이스 정책 문서에서 직접 검출
- 예외: `raw/`, `_meta/decisions/`, `_meta/raw/`, `raven/curator/*.py` (역사/예시), 테스트 fixture
- 정책 = "정책 문서 / 라이브 README / vendor-facing docstring은 vendor-neutral"
- 회귀 가드 ~5 tests

---

## 2. 변경 순서 (5단계, verify-in-loop)

### Phase 1: 핵심 패치 (라이브 정책)

```
1. raven/core/templates/agent/README.md        # 1-A
2. tests/test_external_delegation_contract.py # 1-B
3. _meta/changelog-v0.6.34.md                  # 1-C
   ↓ pytest tests/test_external_delegation_contract.py -v
```

### Phase 2: 모듈 docstring/vendor-facing 정리

```
4. raven/agents/__init__.py    # 1-D
5. raven/__init__.py           # 1-E
6. raven/mcp/cli.py            # 1-F
7. raven/mcp/README.md         # 1-G
   ↓ python -c "from raven.agents import Agent; from raven.mcp import server"
```

### Phase 3: 회귀 가드 (north star 영구화)

```
8. tests/test_vendor_neutrality.py (신규)  # 1-H
   ↓ pytest tests/ -q
```

### Phase 4: 검증 + changelog

```
9. _meta/changelog-v0.6.36.md (신규)
   - vendor-agnostic 재정렬
   - 8개 패치 + 신규 회귀 가드
   - "Karpathy LLM Wiki north star 재정렬"
10. pytest tests/ -q (전체)
11. ruff/typo 체크
```

### Phase 5: commit (사용자 승인 후)

```
12. "commit할까요?" → 승인 → git add + commit
```

---

## 3. 위험도 분석

| 패치 | 위험도 | 이유 |
|---|---|---|
| 1-A (agent/README) | 🟢 낮음 | 정책 문서, 런타임 영향 0 |
| 1-B (테스트) | 🟢 낮음 | 테스트만 영향, 기존 vendor 가드 회귀 가능 (pytest로 검증) |
| 1-C (changelog) | 🟢 낮음 | history-only |
| 1-D, 1-E (docstring) | 🟢 낮음 | 런타임 영향 0 |
| 1-F, 1-G (mcp) | 🟡 중간 | CLI help / README 표시 변경, 사용자 화면 영향 |
| 1-H (회귀 가드) | 🟡 중간 | vendor-neutral 정책 강제, 너무 엄격하면 false positive |

---

## 4. YAGNI 체크

- ❌ "에이전트 vendor 추상화 어댑터" (현재 작업 ❌, 메모리 §next #5 다음 세션)
- ❌ "Tier 1 leak hook" (현재 작업 ❌, 다음 세션)
- ❌ ADR 신규 작성 (없음 - README + AGENTS.md에 이미 vendor-agnostic 표기 ✅)
- ❌ Karpathy 원본 수정 (불변)

---

## 5. 성공 기준

- ✅ `pytest tests/ -q` 통과 (회귀 가드 신규 + 기존 414 통과)
- ✅ `tests/test_external_delegation_contract.py` vendor-neutral 통과
- ✅ `tests/test_vendor_neutrality.py` (신규) 통과
- ✅ `agent/README.md` "Codex" / "Antigravity" / "agy" / "Gemini" 단어 0회
- ✅ `raven/agents/__init__.py` vendor 단어 0회
- ✅ `raven/__init__.py` vendor 단어 0회
- ✅ changelog v0.6.36 추가

---

## 6. 작업 시작 (사용자 승인 후)

1. 위 plan대로 Phase 1~5 순차 실행
2. 각 phase 후 verify-in-loop
3. commit은 "commit할까요?" 명시 후 사용자 승인 시에만

---

## 7. 후속 작업 (현재 작업 외부, 메모리 §next)

- **Worker result 어댑터** (에이전트 vendor-neutral WorkerResult normalize)
- **Tier 1 leak pre-commit hook** (lint #14 git hook 보완)
- **에이전트 작업록 어댑터 패턴** (raven-dev vault 자동 작성)
- **lint #15**: "north star drift" - README/AGENTS.md/wikisys-policy.md §North Star 누락 감지