---
title: 컴파일 전 소스 검증 체크리스트 (Pre-Compile Source Vetting) + CURATION.md 와이어링 수정
created: 2026-07-13
type: rule
audience: agent
confidence: high
---

# 컴파일 전 소스 검증 체크리스트 (Pre-Compile Source Vetting) + CURATION.md 와이어링 수정

## BLUF

에이전트가 vault에 쌓인 기존 지식(사람 작성 + 에이전트 작성 포함)을 참고해 새 문서를 합성(synthesis)하기 전에, 각 소스 후보가 "그대로 인용 가능 / 캐비어 달고 인용 / 인용 금지"인지 판정하는 체크리스트를 `raven/core/templates/agent/CURATION.md`에 새 섹션으로 추가한다. 동시에, 이 파일 자체가 현재 **어디에도 연결되지 않은 고아 템플릿**이라는 사실을 고쳐 `raven docs show`로 접근 가능하게 만든다.

## 배경

- Raven vault의 frontmatter 스키마(`_meta/agents/SCHEMA.md`)는 이미 지식 신뢰도 판단에 필요한 신호를 충분히 갖고 있다: `status: draft|current|stale|contested|archived`, `confidence: high|medium|low`, `last_verified`, lint #4(orphan)/#5(contradiction)/#6(low confidence)/#7(stale)/#17(duplicate title)/#20(placeholder). 즉 **탐지 인프라는 이미 있다** — 없는 건 이 신호들을 조합해 "지금 이 소스를 믿고 합성해도 되는가"를 판정하는 **판단 규칙**이다.
- `AGENTS.md` §15.2 "Root-Cause Investigation prior to Compiling"가 이 문제의식을 한 줄로 짚고 있지만("모순되거나 충돌하는 정보가 발견되었을 때... 근본 원인을 파악한 뒤 지식을 업데이트"), 발견 이후의 사후 대응만 다루고 **합성을 시작하기 전에 선제적으로 소스를 거르는 절차**는 없다.
- `raven/core/templates/agent/CURATION.md`(83줄)는 이미 "3대 대원칙 + lint별 클렌징 가이드 + 변증법적 갈등 해소(§3, `status: contested` 프로토콜) + provenance 보존"을 다루는, 이번 작업과 정확히 같은 결의 문서다. 그런데 코드베이스 전수 조사 결과:
  - `raven/core/vault.py`의 `LITE_BOOTSTRAP_FILE_MAP`(SCHEMA.md/PROJECT-WORKFLOW.md/log.md 3-entry, v0.8.1+ 단일 상수화)에 포함되지 않음 → vault bootstrap이 절대 복사하지 않음.
  - `raven/cli/__main__.py`의 `docs_list`/`docs_show`의 `topic_map`(operations/agent-readme/agent-tools/agent-workflow/agent-safety/policy 6개)에도 없음 → `raven docs show`로도 절대 조회 불가능.
  - `_meta/changelog-v0.7.129.md` 기록을 보면 v0.7.128 시점엔 `tests/test_tier_boundary.py` whitelist에 `CURATION.md`가 있었던 흔적이 있으나, 이후 lite/full 프로필 통합 리팩터(v0.7.65+, "본 배포 대상을 2종+log.md로 고정") 과정에서 와이어링이 빠지고 템플릿 파일만 남았다.
  - 즉 CURATION.md는 **작성됐지만 어떤 에이전트도 도달할 수 없는 죽은 문서**다.
- `raven/core/templates/agent/` 안의 나머지 4개 파일(README.md/TOOLS.md/WORKFLOW.md/SAFETY.md)은 bootstrap에 포함되지 않고 `docs_show`로만 접근 가능한 것이 의도된 설계다(Tier 1 on-demand 문서). CURATION.md도 같은 패턴을 따르는 것이 최소 변경이며, README.md/AGENTS.md 여러 곳에서 반복 명시된 "Lite bootstrap = 2종 + log.md 고정" 불변식을 건드리지 않는다.

## 설계

### 1. 와이어링 수정 — `docs_show`에만 추가 (bootstrap 변경 없음)

`raven/cli/__main__.py`의 `docs_list()`와 `docs_show()` 양쪽 `topic_map`(및 `docs_list`의 안내 테이블)에 항목 추가:

```python
("agent-curation", "templates/agent/CURATION.md", "에이전트 지식 정제 + 컴파일 전 소스 검증 기준"),
```

```python
topic_map = {
    ...,
    "agent-curation": "templates/agent/CURATION.md",
}
```

`docs_show` 사용법 안내 문자열(`help=...`, 에러 메시지의 topic 목록)에도 `agent-curation`을 추가한다. **`LITE_BOOTSTRAP_FILE_MAP`은 건드리지 않는다** — CURATION.md는 여전히 vault에 자동 복사되지 않고, `raven docs show agent-curation`으로만 조회 가능한 Tier 1 온디맨드 문서로 남는다.

### 2. CURATION.md 신규 섹션 — Pre-Compile Source Vetting Checklist

기존 문서는 BLUF → §1(3대 대원칙) → §2(lint별 클렌징) → §3(변증법적 갈등 해소) → §4(provenance 보존) 순서다. 새 섹션은 논리상 "합성을 시작하기 전 가장 먼저 거치는 체크"이므로 **BLUF 직후, 새 §1**로 삽입하고 기존 §1-4는 §2-5로 밀린다.

#### 2.1 신호 테이블

기존 스키마 필드/lint 번호를 그대로 재사용한다 (새 frontmatter 필드 발명 없음):

| 신호 | 확인 방법 | 의미 |
|---|---|---|
| `status: contested` | frontmatter | 모순 미해결 |
| `status: archived` | frontmatter | 의도적 폐기 |
| `confidence: low` | frontmatter | 단일 출처/미검증 |
| stale | `status: stale` 또는 lint #7 (`updated` > 90일) | 사실이 바뀌었을 가능성 |
| orphan | lint #4 (inbound wikilink 0) | 교차검증된 적 없음 |
| placeholder | lint #20 | 소스 자체가 미완성 |
| duplicate-title 미해결 | lint #17 | 어느 쪽이 정본인지 아직 불명 |

#### 2.2 판정 결정 트리

합성에 쓰려는 소스 후보 각각에 대해 순서대로 평가:

1. `status: contested` 또는 이미 §4(변증법적 갈등 해소, 구 §3)에서 다루는 모순 상태 → **⛔ 인용 금지**. 먼저 §4 절차로 모순을 해소하거나 사람 판정을 기다린다.
2. `status: archived` → **⛔ 인용 금지**. 의도적으로 퇴장시킨 지식이므로, 필요하면 `archive_reason`을 확인하고 복원 여부는 사람에게 문의한다.
3. placeholder(lint #20) 존재 또는 duplicate-title(lint #17) 미해결 → **⛔ 인용 금지**. 소스 자체가 아직 컴파일되지 않은 상태이므로, §3(구 §2) 절차로 소스부터 정리한 뒤 재시도한다.
4. 아래 "약한 신호" 중 **2개 이상 동시 발생** → **⛔ 인용 금지**(누적 시 근거 부족으로 판단):
   - `confidence: low`
   - stale (`status: stale` 또는 lint #7)
   - orphan (lint #4)
5. 약한 신호가 **정확히 1개** → **⚠️ 캐비어 달고 인용**:
   - 새로 쓰는 문서의 `confidence`는 인용한 소스들 중 **최솟값을 상속**한다.
   - 본문에 "근거가 약함(사유)"를 한 문장으로 명시한다 (예: "이 결론은 90일 이상 미검증된 소스에 기반함").
6. 위 어느 것도 해당하지 않음 (status: current, confidence: medium 이상, 최근 검증됨, inbound backlink 존재) → **✅ 그대로 인용**.

#### 2.3 다중 소스 규칙

여러 소스를 종합해 하나의 새 문서를 합성할 때:
- ⛔ 판정을 받은 소스는 배제하고, 남은 ✅/⚠️ 소스만으로 합성을 진행한다.
- 배제 후 남는 근거가 결론을 지지하기에 불충분해지면(예: 핵심 주장 하나가 배제된 소스에만 있었던 경우), 억지로 합성을 강행하지 않고 사람에게 "이 주제는 아직 컴파일 근거가 부족하다"고 보고한다.

### 3. 파일 변경 범위

| 파일 | 변경 |
|---|---|
| `raven/cli/__main__.py` | `docs_list`/`docs_show`의 `topic_map` + 안내 문자열에 `agent-curation` 항목 추가 |
| `raven/core/templates/agent/CURATION.md` | 신규 §1(Pre-Compile Source Vetting Checklist) 삽입, 기존 §1-4 → §2-5로 renumber, 본문 내부 상호 참조("§3" 등) 갱신 |

신규 CLI/API/대시보드 표면 없음, ADR 불필요(진입점 추가가 아니라 기존 `raven docs show` 표면에 topic 1개 추가 + 템플릿 문서 내용 확장). Lite bootstrap 파일 개수("2종+log.md")는 변경되지 않는다.

## 테스트

- `raven docs list` 출력에 `agent-curation`이 나열되는지 확인.
- `raven docs show agent-curation`이 CURATION.md 전체 내용을 stdout에 출력하는지 확인 (`raven docs show operations` 등 기존 topic과 동일 패턴).
- `raven docs show unknown-topic`(존재하지 않는 topic) 에러 메시지에 `agent-curation`이 허용 topic 목록에 포함되는지 확인.
- `raven vault create` / `sync_meta()` 이후에도 vault 안에 `_meta/agents/CURATION.md`가 **생성되지 않는지**(bootstrap 비대상 확인) 회귀 테스트.
- CURATION.md 신규 섹션의 마크다운 렌더링(테이블/리스트) 수동 확인 — 코드 동작에 영향 없는 순수 문서 변경이므로 lint/pytest 대상 아님.

## 영향 범위 및 리스크

- 코드 변경은 `docs_show`/`docs_list` 딕셔너리 확장 1건뿐이라 리스크 낮음. 기존 topic 동작에 영향 없음(추가만, 기존 키 변경 없음).
- CURATION.md 본문 확장은 vault에 배포되지 않는 Tier 1 문서이므로 기존 vault 데이터/스키마에 영향 없음.
- 향후 후보(이번 범위 밖): CURATION.md를 Lite bootstrap에 포함시킬지(3종+log.md로 확장할지) 여부는 README.md/AGENTS.md의 "2종" 불변식을 전면 갱신해야 하는 별도 결정이므로, 필요해지면 별도 ADR + spec으로 분리한다.
