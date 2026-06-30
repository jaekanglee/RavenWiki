# raven v0.7.26 — 대시보드 사이드바 UI/UX 개편 및 리팩토링

> **핵심**: 대시보드 사이드바의 정보 계층과 스타일 구조를 개편했습니다. 다중 Vault 트리의 동시 렌더링으로 인한 리렌더링 부하를 줄이기 위해 **단일 활성 Vault 집중 렌더링** 구조와 드롭다운 선택기를 도입했으며, **세로 계층 가이드선(Indent Guidelines)** 및 **듀얼 스위치 테마 스위처**를 적용하여 비주얼과 조작 편의성을 크게 향상시켰습니다.

릴리스 일자: 2026-06-30
이전: v0.7.25

---

## 1. 변경 사항

### 1-1. 단일 활성 Vault 집중형 트리 및 선택기 도입
* **`dashboard/src/components/Sidebar.tsx`**:
  * 모든 보관소(Vault)의 폴더 트리를 한 화면에 동시에 나열하고 필터링하던 루프 렌더링 로직을 제거했습니다.
  * 상단에 보관소를 미려하게 고를 수 있는 **Native Select 드롭다운**을 배치하여 정보 맥락을 완전히 격리했습니다.
  * 검색 필터 입력 시 현재 활성화된 보관소의 트리만 필터링하도록 연산을 제한하여, 문서 수가 많아도 스크롤/타이핑 렉이 없는 쾌적한 피드백 속도를 보장합니다.
* **`raven/api/server.py`**:
  * 보관소의 대문 역할을 담당하는 파일(확장자를 제외한 파일명이 index, readme, home 등인 파일)은 폴더 및 다른 일반 파일들보다 무조건 탐색기 트리의 가장 최상단(0순위)에 위치하도록 정렬 예외 규칙을 구현하여 탐색 접근성을 높였습니다.

### 1-2. 수직 계층 안내선 (Indent Guidelines) 구현
* **`dashboard/src/styles/globals.css`**:
  * 트리 계층이 1 depth 이상 깊어질 때 해당 깊이만큼 세로 안내선을 그릴 수 있는 `.sidebar-indent-line` 및 컨테이너 스타일을 추가했습니다.
* **`dashboard/src/components/Sidebar.tsx`**:
  * 재귀적으로 호출되는 `TreeLeaf` 컴포넌트 내부에서 `depth` 만큼 루프를 돌며 세로 계층 라인을 렌더링하여, 다층 디렉토리 구조에서 문서의 상속 관계와 소속감을 직관적으로 식별할 수 있도록 개선했습니다.

### 1-3. 플레이스홀더 한국어화 및 테마 토글 스위처 리디자인
* **`dashboard/src/components/Sidebar.tsx`**:
  * 기존 영어로 고정되어 있던 검색창 플레이스홀더를 한국어(`파일 또는 폴더 필터...`) 및 레이블로 전면 통일하여 한국어 네비게이션 탭과의 조화를 맞췄습니다.
  * 투박한 전체 가로폭 직사각형 버튼 스타일의 테마 전환기를 제거하고, 구석에 세련되게 어울리는 듀얼 토글 스위치 형태의 버튼(`☀️ 라이트 / 🌙 다크`)으로 리디자인하여 하단 레이아웃의 완성도를 높였습니다.

---

## 2. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| tsc compile | **Success** | `npx tsc -b --noEmit` 타입 에러 검증 통과 |
| vite build | **Success** | Production 빌드 및 PWA 캐싱 파일 빌드 확인 |
| backend pytest | **482 passed, 1 skipped** | 기존의 전체 백엔드 API & Core 테스트 100% 회귀 방지 ✅ |

---

## 2026-07-01 추가 패치 — Karpathy contract alignment

* **MCP immutable write guard 복구**:
  * `raven/mcp/tools/write.py`의 `wiki_update`에 `raw/`, `_meta/`, `log.md` 보호 경계를 추가했습니다.
  * 이제 에이전트는 Karpathy LLM Wiki의 raw 불변성과 Raven의 메타/로그 보호 계약을 MCP 표면에서도 우회할 수 없습니다.
* **LLM Wiki 구조 신호 감지 보강**:
  * `raven/core/vault.py`의 `is_llm_wiki`가 `features.llm_wiki=true` 외에도 `_meta/agents/` 존재를 structural opt-in 신호로 인식하도록 보강했습니다.
  * `raw/` 와 `log.md` 단독 존재는 운영/수집 노이즈일 수 있어 감지 신호에서 제외했습니다.
* **문서 표면 정합성 복구**:
  * `README.md`에서 제거된 `raven/agents/` 경로 흔적을 제거했습니다.
  * `docs/vault-patterns.md`와 vault 사용자 가이드에서 실제 구현과 맞지 않던 auto-detect / path-scope / index 위치 설명을 현행 구현 기준으로 재정렬했습니다.
* **회귀 테스트 추가**:
  * MCP `wiki_update`가 `raw/`와 `_meta/system/` 경로를 거부하는지 검증하는 테스트 2건을 추가했습니다.
  * `is_llm_wiki`가 `_meta/agents/`는 감지하고 `raw/`, `log.md` 단독 존재는 감지하지 않는지 검증하는 테스트 3건을 추가했습니다.
* **에이전트 문서 포맷 최종안 정리**:
  * 과도하게 agentic한 본문을 피하기 위해 `PROJECT-WORKFLOW.md`를 **사람 가독성 우선 + 얇은 공통 포맷** 기준으로 재정렬했습니다.
  * type 8종 템플릿은 유지하되, 강한 ADR식 강제 대신 `BLUF + 내용 + 관련` 중심의 최소 뼈대로 완화했습니다.
  * `SCHEMA.md`에도 Human-First Writing Contract를 추가해 frontmatter는 구조화, 본문은 자연어 중심이라는 원칙을 명시했습니다.
* **감사 반영 추가 정리**:
  * 이중 헤더의 영문 괄호 표기를 제거하고, `PROJECT-WORKFLOW.md`에서 순수 자연어 헤더를 권장하도록 수정했습니다.
  * `SCHEMA.md`의 집필 원칙 중복 선언을 삭제해 데이터 계약 문서 역할로 다시 축소했습니다.
  * `#13 cognitive governance`와 write-time gardening validation을 advisory 중심으로 완화해, 템플릿의 인간 친화성 방향과 실제 lint/write 규칙이 충돌하지 않도록 맞췄습니다.

---

## 3. 다음 단계
* **v0.7.27**: 대시보드 내 Gardening Center UI 구현 (웹 페이지에서 일괄 아카이빙 및 링크 매핑)
