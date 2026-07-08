---
title: Vault Curation & Cleansing Guidelines — 에이전트 지식 정제 규칙
created: 2026-07-08
updated: 2026-07-08
type: rule
tags: [system, workflow, curation, meta]
audience: agent
confidence: high
---

# Vault Curation & Cleansing Guidelines — 에이전트 지식 정제 규칙

> **BLUF**: 에이전트가 볼트의 지식 신호 대 잡음비(SNR)를 높이기 위해 주기적으로 수행해야 하는 큐레이션 및 클렌징의 구체적 조치 기준과 절차를 정의합니다.

---

## 1. 큐레이션 및 클렌징의 3대 대원칙

에이전트는 린트 경고를 해결하거나 볼트를 정리할 때 단순히 형식적인 린트 오류 통과를 목적으로 해선 안 되며, 다음 대원칙을 준수해야 합니다.

1. **원문 보존 + 증분 누적 (Layer 1 존중)**: 사람이 작성한 문맥과 핵심 주장은 절대 임의로 지우거나 훼손하지 않습니다.
2. **플레이스홀더(TBD) 박멸**: 알맹이 없는 껍데기 문서는 RAG 임베딩 및 탐색 시 불필요한 토큰 소비와 할루시네이션을 유발하므로 철저히 격리하거나 완성해야 합니다.
3. **맥락적 연결 (Semantic Wikilink)**: 기계적인 위키링크 연결을 금지하고, 링크 간의 의미적 관계를 문장으로 기술하여 RAG 추론 성능을 향상시킵니다.

---

## 2. 린트 규칙별 세부 클렌징 및 조치 가이드

`wiki_lint()` 실행 시 검출되는 오류에 대해 에이전트는 다음과 같이 큐레이션을 수행합니다.

### 1) Lint #20: empty or placeholder text (플레이스홀더 발견)
* **상황**: 본문이나 frontmatter 내에 `TBD`, `N/A`, `추후 작성`, `임시` 등의 플레이스홀더가 포함되어 `🔴 critical` 오류가 발생한 경우.
* **조치 기준**:
  * **정보 보완**: 에이전트가 알고 있는 RAG 컨텍스트 또는 Raw Source에서 해당 부분의 세부 내용을 찾아내어 내용을 실제로 채워 넣고 문서를 완성합니다.
  * **내용 삭제 (Cleansing)**: 채울 만한 정보가 없고 단순히 형식적으로 만들어진 섹션인 경우, `TBD` 문구만 지우는 것이 아니라 **해당 문단/섹션 전체를 물리적으로 삭제**하여 정리합니다.

### 2) Lint #21: contextless wikilinks (맥락 없는 링크 발견)
* **상황**: 본문에 `[[wikilink]]`만 단독으로 나열되어 `🟡 warning` 경고가 발생한 경우.
* **조치 기준**:
  * **꼬리표(Anchor Context) 덧붙이기**: 해당 링크 뒤에 하이픈(`—`)을 적고, Target 문서와의 개념적 연관성과 참고 이유를 최소 8자 이상의 자연어 문장으로 기술합니다.
  * *나쁜 예*: `* [[memory-management]]`
  * *좋은 예*: `* [[memory-management]] — Ollama API 설정 시 local-host 상의 메모리 압축 스펙 참고`

### 3) Lint #22: journal/issue summary completeness (요약 불량)
* **상황**: `journal` 또는 `issue` 타입 문서의 `# 요약` 섹션이 누락되었거나, 3줄을 초과하거나, 단순 빌드 에러 로그 등 기계적 출력이 복사된 경우.
* **조치 기준**:
  * **정보 중심 압축**: 에이전트가 발생한 상황에 대해 `해결 목적 / 취한 조치 / 도출된 팩트` 3대 요소를 3줄 이내의 간결한 인간 중심 명사구 문장으로 요약하여 기재합니다.
  * **로그 격리**: 수십 줄에 달하는 상세 에러 로그나 CLI 컴파일 출력은 문서 본문에서 지우고, `raw/logs/` 하위에 텍스트 파일로 저장한 뒤 관련 링크만 걸어둡니다.

### 4) Lint #17: duplicate title candidate (유사 제목/중복 개념 발견)
* **상황**: 제목 유사도가 0.8 이상인 문서가 중복 검출되어 `🟡 warning` 경고가 발생한 경우.
* **조치 기준**:
  * **독단적 병합 금지**: 에이전트가 자율적으로 어느 한쪽 문서를 지우거나 합쳐서는 안 됩니다.
  * **병합안 RFC 발의**: `type: issue`, `status: draft`로 새 문서를 생성하여 두 문서의 중복 상태를 분석하고, 어떻게 병합할지(A를 살리고 B를 aliases로 둘지 등)에 대한 **병합 제안서(RFC)**를 작성하여 사람의 컨펌을 대기합니다.

---

## 3. 변증법적 갈등 해소 (Dialectic Contradiction Resolver)

에이전트가 다른 정보원으로부터 기존 볼트 문서(특히 사람이 작성한 `rule`, `concept`)와 명백한 사실적 모순을 발견했을 때의 행동 프로토콜입니다.

1. **상호 contested 처리**: 모순된 두 문서의 frontmatter에 `status: contested` 및 `contradictions: [상대방slug]`를 적어 상호 크로스 링크합니다.
2. **지시 문서(Issue) 발의**: `issues/issue-contradiction-{slug}` 문서를 생성하여 모순의 배경, 양측의 데이터 신뢰도(Confidence), 에이전트가 제안하는 판정안을 작성합니다.
3. **인간 판정 대기**: 사람이 해당 이슈를 검토하고 최종 판정을 내려 하나의 지식을 확정할 때까지 에이전트는 대기합니다.

---

## 4. 지식 계보 및 기원(Provenance) 보존

에이전트가 큐레이션을 수행하며 문서를 수정하거나 상태를 전이시킬 때, Frontmatter의 `sources` 필드와 `agents` 이력 필드를 다음과 같이 엄격하게 작성해야 지식의 신뢰성이 유지됩니다.

* **sources**: 해당 지식을 유도하는 데 참고한 1차 Immutable Raw Source의 경로를 기재합니다.
  ```yaml
  sources: [raw/articles/karpathy-llm-wiki-2026.md]
  ```
* **agents**: 상태 전이나 큐레이션 조치 이력을 기록합니다.
  ```yaml
  agents:
    - name: hermes-cleanser
      timestamp: 2026-07-08T23:26:00Z
      intent: Lint #20 및 #21 위반 사항 자동 수리 및 클렌징
      run_id: run-2026-07-08-01
  ```
