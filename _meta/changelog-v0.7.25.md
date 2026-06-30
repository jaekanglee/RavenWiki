# raven v0.7.25 — Knowledge Gardening (Stale/Orphan 정제 및 CLI) 및 에이전트 Write Guardrail 구현

> **핵심**: 에이전트의 무분별한 문서 생성(Bloat)을 제어하기 위해 WIP 격리 및 엄격한 스키마 검사(Write Guardrail)를 MCP 및 Core 계약 레이어에 구현했으며, 인지 거버넌스 린트의 위험도를 격상시켰습니다. 또한 방치된 Stale/Orphan 문서를 반자동으로 정리하고 링크를 추천해주는 `raven garden` 대화형 CLI 명령을 도입했습니다.

릴리스 일자: 2026-06-30
이전: v0.7.24

---

## 한 줄 요약

에이전트의 오염 방지를 위한 WIP 격리 및 Strict Schema 검사 파이프라인을 구축하고, `#13 cognitive governance` 린트의 등급을 `warning`으로 격상시켰으며, Stale 및 Orphan 문서를 대화형으로 정제/아카이빙/연결할 수 있는 `raven garden` CLI 명령어를 구현하여 482개 백엔드 테스트를 모두 통과시켰습니다.

---

## 1. 변경 사항

### 1-1. 에이전트 쓰기 제한 및 WIP 격리 (Write Guardrail)
* **`raven/core/vault.py`**:
  * Vault가 LLM Wiki 기능을 켜고 있는지 판단하는 `is_llm_wiki` 프로퍼티를 추가했습니다 (`.vault.json` 및 registry metadata features 연동).
* **`raven/core/contracts.py`**:
  * 에이전트가 메인 `content/` 디렉토리에 쓸 때 Frontmatter(type, confidence) 및 필수 콘텐츠 구조(Why it matters, opposing view)를 완비했는지 검사하는 `validate_gardening_schema()` 검증 헬퍼를 추가했습니다.
  * `contracts.write_page()`에서 에이전트(`actor`가 지정된 경우)가 불완전한 상태로 메인 위키 작성을 시도하면 쓰기 요청을 차단(`strict_schema_violated`)하도록 가드레일을 적용했습니다. 임시 작업은 `content/wip/` 또는 `content/scratch/` 아래에서만 자유롭게 허용됩니다.
  * Provenance(`actor`)에 `timestamp`가 없을 경우 KeyError가 발생하는 구조를 개선하여 자동으로 현재 시간을 채워 넣도록 보완했습니다.
* **`raven/mcp/tools/write.py`**:
  * MCP `wiki_update` 도구에서 대상 Vault가 `llm_wiki` 모드이고 WIP 영역이 아닌 메인 위키에 쓸 때 `validate_gardening_schema`를 통해 불완전한 내용의 작성을 사전에 원천 차단하도록 보강했습니다.

### 1-2. 인지 거버넌스 린트 위험도 격상
* **`raven/core/lint.py`**:
  * `llm_wiki` 기능이 활성화된 Vault의 경우, 이전 `info` 수준이던 `#13 cognitive governance` (Why it matters 누락, 반대 입장 누락) 이슈의 심각도를 `warning`으로 자동 승격시켜 에이전트가 이를 보완하게 유도하도록 수정했습니다.

### 1-3. 지식 정원 가꾸기 (Knowledge Gardening) CLI 명령어
* **`raven/core/garden.py` (신설)**:
  * Stale 문서(90일 이상 미갱신), Orphan 문서(인바운드 링크 0)를 판별하고, SQLite DB 인덱스를 활용하여 공통 태그 또는 FTS(Full Text Search) 기반의 연결 대상 문서 추천(Link Candidate Suggestion) 알고리즘을 구현했습니다.
* **`raven/cli/__main__.py`**:
  * `raven garden` 대화형 CLI 명령을 추가했습니다.
  * **Stale 모드**: 보완(`[u]pdate`), 아카이빙(`[a]rchive` - Git mv 및 alias 자동 적용), 건너뛰기(`[s]kip`) 옵션을 대화형으로 제공합니다.
  * **Orphan 모드**: 추천 문서를 동적으로 띄워주며 바로 링크를 연결하는 `[l]ink` 기능과 아카이빙 등을 지원합니다.

---

## 2. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| pytest | **482 passed, 1 skipped** | 백엔드 테스트 및 Gardening 검증용 9개 신규 테스트(test_gardening.py) 100% 성공 ✅ |

---

## 3. 다음 단계
* **v0.7.26 (후보)**: Dashboard 내 Gardening Center UI 구현 (웹 페이지에서 일괄 아카이빙 및 링크 매핑)
