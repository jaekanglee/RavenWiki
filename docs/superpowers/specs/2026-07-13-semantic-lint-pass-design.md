# Semantic Lint Pass — 실행 메커니즘 Design Spec

> **BLUF**: `raven/core/lint.py`의 23개 체크는 전부 규칙 기반(정규식/임계값/존재 여부)이라 모순·낡음·synthesis 품질처럼 실제 이해가 필요한 판단을 못 한다. `_meta/agents/CURATION.md`(이미 구현됨)가 그 판단 기준을 정의하지만, 이 기준을 실제로 적용하는 실행 경로가 없었다. 이 spec은 새 MCP tool `wiki_semantic_lint_queue` 1개로 그 경로를 만든다 — Raven은 "판단이 필요한 후보 큐"만 만들고, 실제 판단(CURATION.md §1 결정트리 적용, §3/§4의 조치)은 이 세션을 운영하는 **외부 에이전트**가 수행한다.

---

## 0. 배경

- 선행 완료: `_meta/agents/CURATION.md` (판단 기준 문서) + `raven docs show agent-curation` 와이어링 (b9d68e8..3d303cc).
- `raven/core/lint.py`의 23개 `check_*`는 결정론적/빠름/무료. semantic 판단은 비결정론적/LLM 호출 비용/느림 — 성격이 완전히 다르므로 같은 파이프라인에 섞지 않는다 (사용자 명시 제약).
- `raven/curator/curator.py`("Stateless Curator")는 git diff 기반 변경분 추적기일 뿐, semantic 판단 로직이 없다 — 확인됨.
- `raven/core/ai_advice.py` / `raven/core/contradiction.py`에 이미 Raven 내부 LLM 직접 호출 선례(Gemini API, `GEMINI_API_KEY` fallback)가 존재한다는 것도 확인했으나, 이번 설계는 그 패턴을 따르지 않기로 사용자가 명시적으로 재확인했다 (아래 §1 참조).

---

## 1. 핵심 결정: 실행 주체 = 외부 에이전트

Raven 자체는 이번 기능을 위해 내부 LLM 호출 코드를 추가하지 않는다. 판단 주체는 **이 Raven MCP 서버에 연결된 외부 LLM 클라이언트(예: Claude Code 세션)** 이며, Raven의 역할은 다음 두 가지로 한정된다:

1. **후보 큐 제공**: "지금 어떤 페이지가 판단을 기다리고 있는지" (신규 read-only MCP tool).
2. **쓰기 계약 제공**: 판단 결과를 vault에 반영하는 경로 — 이미 존재하는 `wiki_update`(frontmatter/본문 수정), `wiki_generate_draft` + `wiki_commit_draft`(§3 #17 duplicate-title RFC, §4 contradiction issue 문서 생성)로 충분하다. **새 write tool은 추가하지 않는다.**

`ai_advice.py`/`contradiction.py`의 내부 API 호출 선례는 다른 기능(네트워크 진단 조언 문구 생성, 인접 노드 쌍 모순 탐지)의 구현 방식일 뿐이며, 이 semantic lint pass는 그 패턴을 재사용하지 않는다 — 실행 주체를 라이브 세션의 에이전트로 두는 것이 이 기능의 핵심 설계 목표(외부 API 키/벤더 종속성 없이, 이미 세션을 운영 중인 에이전트의 판단력을 재사용)이기 때문이다.

---

## 2. 진입점: MCP tool 1개만 추가

Raven은 4개 진입점(CLI/HTTP API/Dashboard/MCP)만 허용하며 5번째 진입점 추가는 금지된다 (AGENTS.md §2). 이번 기능은 **MCP에만** 새 tool을 추가한다 — CLI 서브커맨드는 만들지 않는다.

이유: MCP는 이미 "LLM 클라이언트 표준 진입점"이고, semantic 판단의 실제 소비자(외부 에이전트)가 MCP를 통해 Raven과 통신하는 것이 자연스럽다. CLI에 동등 커맨드를 겸용 구현하면 로직이 두 곳에 분산되므로, 이번 설계 범위에서는 만들지 않는다 (필요해지면 후속 spec으로 분리).

---

## 3. Tool 설계: `wiki_semantic_lint_queue`

### 3.1 배치

새 파일 `raven/mcp/tools/semantic_lint.py` (기존 `tools/guide.py`, `tools/stale.py`와 같은 레벨). `raven/mcp/cli.py`에 다른 read tool들(`wiki_search`, `wiki_lint`, `wiki_get_advice` 등)과 같은 방식으로 등록. **read 모드에서도 사용 가능** (쓰기가 없으므로 `mode in ("write","admin")` 게이트 불필요).

### 3.2 시그니처

```python
def wiki_semantic_lint_queue(
    vault: str,
    checks: Optional[list[str]] = None,   # 허용목록 부분집합. 생략 시 6개 전부.
    limit: int = 20,                       # LLM 호출 비용 보호용 상한
) -> dict:
```

**허용목록 (CURATION.md §1.1 신호 테이블과 1:1 대응)**: `#4`(orphan), `#5`(contradiction), `#6`(confidence low), `#7`(stale), `#17`(duplicate-title), `#20`(placeholder).

### 3.3 동작

1. `lint.run_all(vault)` 실행 — 새 스캔 경로를 만들지 않고 기존 `_ScanCache`를 그대로 재사용한다.
2. 결과 issue들 중 허용목록에 속하는 것만 필터링. `checks` 인자로 더 좁힐 수 있고, 허용목록 밖 id를 요청하면 `ValueError`(허용목록 6개를 메시지에 나열)로 즉시 실패시켜 에이전트가 자가 교정하게 한다 (`wiki_get_guide`의 whitelist 에러 패턴과 동일 관례).
3. slug 단위로 그룹핑한다. 한 페이지가 여러 체크(예: stale + confidence low)에 동시에 걸릴 수 있다.
4. 각 slug의 frontmatter에서 CURATION.md §1 신호 테이블이 참조하는 필드만 뽑아 첨부: `status`, `confidence`, `updated`, `sources`. **새 frontmatter 필드는 만들지 않는다.**
5. `limit`으로 자르고 `truncated: true/false`로 알린다 — 조용히 버리지 않는다.
6. 판단 기준 자체(⛔/⚠️/✅ 결정트리)는 **응답에 포함하지 않고 참조만 남긴다** (`guide_ref` 필드). 이 결정트리 로직을 Python으로 재구현하지 않는 것은 의도적 선택이다 — CURATION.md §1이 이미 "새 frontmatter 필드 불필요, 기존 신호만 조합"이라 명시했고, 같은 로직이 텍스트와 코드 두 곳에 있으면 향후 어긋난다. 판단은 전적으로 호출한 에이전트가 CURATION.md를 근거로 수행한다.

### 3.4 응답 스키마

```json
{
  "ok": true,
  "vault": "default",
  "checks_considered": ["#4", "#5", "#6", "#7", "#17", "#20"],
  "guide_ref": "raven docs show agent-curation §1 (판정 기준 SoT)",
  "candidate_count": 3,
  "truncated": false,
  "candidates": [
    {
      "slug": "content/some-page",
      "title": "...",
      "frontmatter": {"status": null, "confidence": "low", "updated": "2026-03-01", "sources": []},
      "matched_checks": [
        {"id": "#6", "severity": "warning", "message": "confidence: low"},
        {"id": "#7", "severity": "warning", "message": "updated 2026-03-01 (134일 경과)"}
      ]
    }
  ]
}
```

`#5`(contradiction), `#17`(duplicate-title)은 페이지 쌍 단위 체크이므로 해당 `matched_checks` 항목에 `paired_with: <slug>` 필드가 추가된다.

---

## 4. 알려진 한계 (이번 범위에서 해결 안 함)

- **CURATION.md §1 결정트리는 참조로만 전달된다.** 이 Raven 코드베이스 위에서 동작하는 에이전트(AGENTS.md 관례상 세션 시작 시 관련 문서를 읽음)에게는 문제 없지만, 파일시스템/CLI 접근이 전혀 없는 **순수 MCP-only 외부 클라이언트**는 `raven docs show agent-curation`으로 CURATION.md를 가져올 방법이 없다 (CURATION.md는 Tier 1 문서이며, MCP의 `wiki_get_guide`는 Tier 2 Lite bootstrap 3종만 화이트리스트되어 있음). 이 gap은 이번 spec의 범위 밖으로 남기고, 필요해지면 별도 spec(예: Tier 1 문서의 MCP 노출)으로 다룬다.
- 판단 결과의 재방문 상태(예: "이 슬러그는 이미 이번 라운드에 판단받음")를 추적하는 새 DB/상태는 만들지 않는다. 에이전트가 조치(본문 수정/RFC 발의/status 전이) 후에는 다음 `lint.run_all()` 결과에서 해당 신호가 자연히 사라지거나 바뀌므로, 다음 큐 호출에서 자동으로 걸러진다.

---

## 5. 에러 처리

| 상황 | 동작 |
|---|---|
| 미등록 vault | 기존 `resolve_vault_path` 위임 (다른 tool과 동일 에러 형태) |
| `checks`에 허용목록 밖 id | `ValueError`, 메시지에 허용목록 6개 나열 |
| `lint.run_all()` 내부 예외 | 그대로 전파 (MCP 레이어가 tool error로 변환, 별도 try/except로 삼키지 않음) |
| candidate 0개 | 에러 아님 — `candidate_count: 0` 정상 반환 |

---

## 6. 테스트 전략

`tests/test_mcp_semantic_lint_queue.py` 신규:

- 6개 체크 각각을 유발하는 fixture 페이지로 candidate 그룹핑/필드 추출 검증.
- 한 슬러그가 2개 체크에 동시 걸릴 때 `matched_checks`에 둘 다 모이는지.
- `checks=["#5"]`로 필터링 시 다른 체크 후보가 빠지는지.
- 허용목록 밖 id 요청 시 `ValueError` + 메시지에 6개 id 전부 포함되는지.
- `limit` 초과 시 `truncated: true` + 정확히 `limit`개만 반환.
- candidate 0개 vault에서 정상 응답(에러 아님).
- `#5`/`#17` 페어 후보의 `paired_with` 필드 존재 검증.

기존 `tests/test_lint_check_registry.py`는 변경하지 않는다 — 허용목록은 새 모듈 안 상수로 별도 관리하고, `lint.py`의 `CHECK_REGISTRY`에 새 키를 추가하지 않는다 (이 tool은 새 체크가 아니라 기존 체크의 뷰이므로).

---

## 7. 이번 spec이 만들지 않는 것 (범위 확정)

- 새 CLI 서브커맨드 ❌
- 새 write MCP tool ❌ (기존 `wiki_update`/`wiki_generate_draft`/`wiki_commit_draft`로 충분)
- 새 frontmatter 필드 ❌
- 새 SQLite 테이블/상태 추적 ❌
- CURATION.md 결정트리의 Python 재구현 ❌ (참조만)
- `lint.py`의 `CHECK_REGISTRY`에 항목 추가 ❌
