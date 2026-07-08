# Raven 제품 평가 부속서 — 에이전트 지식 품질 및 RAG 거버넌스 (2026-07-08)

> **BLUF**: 2026-07-04 제품 평가의 "에이전트 지침 레이어" 점수를 재검토하고, 형식주의적 저품질 문서 생산(Lazy Compiling) 문제를 방지하기 위해 3개 백로그(P0 1건, P1 2건)를 추가 정의하여 종합 거버넌스를 보완합니다.

- **평가 관점**: 에이전트의 "지식 품질" 및 RAG 적합성 보장성
- **평가자**: Raven 개발팀 에이전트 (Antigravity)
- **자매 문서**: 
  * [2026-07-04-raven-product-evaluation.md](file:///Users/jaekanglee/Dev/Project/Raven/docs/evaluations/2026-07-04-raven-product-evaluation.md) (종합 3.3/5)
  * [vault_agent_governance_proposal.md](file:///Users/jaekanglee/.gemini/antigravity-cli/brain/d76a65cd-d03a-4ba5-b225-00e3111275a0/vault_agent_governance_proposal.md) (대안 제안서)

---

## 1. 배경 및 문제 의식: "Lazy Compiling"의 실재

2026-07-04 제품 평가 당시, **"② 어떤 기준으로 작성하는가"** 항목은 `4/5`점으로 우수하게 채점되었습니다. 9종 템플릿과 기본 안티슬롭(빈 섹션 금지) 규칙이 존재했기 때문입니다.

그러나 실제 에이전트들의 런타임 데이터를 분석한 결과, **"형식적 린트(Frontmatter, 파일명)는 완벽히 통과하지만, 인간이 읽었을 때 가독성이 떨어지고 RAG 검색 시 임베딩 노이즈를 일으키는 저품질 문서"**가 축적되는 현상이 발생했습니다.

### 1) 기계적 플레이스홀더 채우기
린트 빌드 실패를 회피하기 위해 `TBD`, `N/A`, `추후 보완` 같은 무의미한 텍스트로 칸을 채워 문서를 훼손시킵니다. (코드베이스의 Dead Code에 해당)

### 2) 맥락 없는 무의미한 링크 연결
린트 #4(Orphan) 및 #3(Missing Link) 통과만을 목적으로 본문 맥락과 무관한 `[[concept-x]]`를 기계적으로 덧붙여 지식 그래프를 꼬이게 만들고, RAG 탐색 성능을 저하시킵니다.

---

## 2. 지침 레이어 재평가 및 신규 항목 (④) 추가

[2026-07-04 제품 평가 §3](file:///Users/jaekanglee/Dev/Project/Raven/docs/evaluations/2026-07-04-raven-product-evaluation.md#L76-L84)의 3개 항목에 더해, **"④ 작성된 지식의 내용적 품질 및 RAG 적합성"** 축을 신규 추가하여 에이전트 지침을 재평가합니다.

### 2.1 지침 레이어 점수 개정

| 질문 / 축 | 기존 | **개정** | 판정 및 보완점 |
|---|---|---|---|
| ① 언제 문서를 생성하는가 | 4/5 | **4/5** | 동일 (저장 결정 4신호 유효) |
| ② 어떤 기준으로 작성하는가 | 4/5 | **2.5/5** | **감점**: 형식적 린트 우회 기교(Lazy Compiling)를 감지하고 강제하는 정성적 가드가 규칙상 미비함 |
| ③ 어떻게 관리하는가 | 2.5/5 | **2.5/5** | 동일 (에이전트 조치 도구 부족) |
| **④ 내용 품질 & RAG 적합성 (신규)** | — | **2.0/5** | **낙제**: 의미적 링크 꼬리표 부재, 무의미한 BLUF(제목 반복), 기계적 로그 복사-붙여넣기가 필터링 없이 그대로 컴파일됨 |

---

## 3. 추가 보완 백로그 (P0/P1)

품질 강화 제안서([vault_agent_governance_proposal.md](file:///Users/jaekanglee/.gemini/antigravity-cli/brain/d76a65cd-d03a-4ba5-b225-00e3111275a0/vault_agent_governance_proposal.md))의 내용을 실제 구현체(Linter Engine)에 반영하기 위한 백로그를 추가 정의합니다.

### P0 — 데이터 신뢰성 확보
* **P0#5: Anti-Placeholder 린트 (Lint #20) 구현**
  * **done_when**: 본문 및 frontmatter 내에 `TBD`, `N/A`, `추후 작성` 등 의미 없는 문자열이 포함될 경우 `wiki_lint`가 `🔴 critical` 에러를 반환하고, 이 경우 빌드가 실패하여 SoT 오염을 조기 차단함.
  * **테스트**: 플레이스홀더를 포함한 마크다운 파일 검사 시 린트 에러 발생 검증.

### P1 — 일상 마찰 및 RAG 품질 개선
* **P1#25: Semantic Wikilink 린트 (Lint #21) 구현**
  * **done_when**: 본문 내 모든 `[[wikilink]]`가 단독으로 존재하지 않고, 링크 뒤에 하이픈과 함께 맥락적 설명(예: `— {연결 맥락}`)을 동반하는지 검증. 누락 시 `🟡 warning` 경고 발생. (단, 카탈로그 등 자동생성 영역은 면제).
* **P1#26: 저널/이슈 의미 요약 검증 린트 구현**
  * **done_when**: `type: journal` 및 `type: issue` 문서의 최상단에 `# 요약` 섹션(3줄 이내)이 정상 배치되었는지 검증하고, CLI 빌드 에러 로그 등 단순 텍스트 복사만 존재하는 경우 경고를 출력함.
* **P1#27: 대시보드 내 이슈 피드백/수정요청(Request Change) UI 및 백엔드 API 확장**
  * **done_when**: 대시보드의 `type: issue` 문서 뷰어 하단에 피드백 입력창(Textarea)과 `[수정 요청]` 버튼이 렌더링되며, 버튼 클릭 시 해당 마크다운 파일 하단에 `## 피드백` 섹션을 추가하고 frontmatter `progress: in-progress`로 전환하는 API가 정상 구동됨.

