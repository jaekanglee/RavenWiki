# 검색 로직 통합 + Alias 구조적 지원 + 그래프 라벨 개선

날짜: 2026-07-10

## 배경

대시보드에는 문서를 찾는 두 가지 UI가 있다:

1. 사이드바 전체 문서 검색 (`SearchBar.tsx`, `variant="sidebar"`)
2. `PropertiesPanel`의 연결 문서 검색 (문서 간 relation 추가 시 사용)

두 UI는 서로 다른 백엔드 검색 로직을 쓰고 있었다:

- 사이드바 → `/api/vaults/{name}/search` (`raven/api/server.py:2549`): 프론트매터+본문 전체 텍스트에서 단어 등장 횟수를 세는 단순 로직. 필드 가중치 없음.
- PropertiesPanel → `/api/vaults/{name}/hybrid-search` (`raven/core/hybrid_search.py`): BM25(FTS5, weight 0.6) + 벡터 유사도(weight 0.4) 결합. sqlite-vec 미사용 환경에서는 BM25-only로 폴백.

또한 `aliases` 필드는 백엔드/DB/타입에는 이미 존재하지만(`raven/core/node_meta.py`, `dashboard/src/types.ts`), PropertiesPanel에 편집 UI가 없고 검색 인덱스(FTS)에도 포함되어 있지 않다. 사용자는 alias를 "Raven 구조 설계에 정식으로 반영돼야 할 메타 정보"로 취급하길 원한다.

그래프 뷰(`GraphCanvas.tsx`)는 노드 라벨을 자르지 않고 전체 문자열을 그리기 때문에, 제목이 긴 문서는 라벨이 다른 노드/UI와 겹치거나 화면 밖으로 나가 사실상 보이지 않는다.

## 목표

1. 사이드바 검색과 PropertiesPanel 연결 문서 검색이 완전히 동일한 로직/결과를 반환하도록 통합한다. 보일러플레이트(중복 fetch/debounce 코드) 없이, 공용 로직을 재사용한다.
2. 문서별 alias를 대시보드에서 정식으로 편집할 수 있게 하고, alias로도 검색이 되도록 만든다.
3. 그래프에서 긴 제목이 안 보이는 문제를 해결한다.

## 비목표

- LLM 볼트 운영자(에이전트)가 발행 시 메타정보/관계를 더 적극적으로 채우도록 지침(`SCHEMA.md` 등)을 강화하는 것은 이번 스펙의 범위가 아니다. 별도 후속 작업으로 분리한다 (사용자 확인 완료). 이유: 이번 작업은 대시보드 프론트엔드 + 검색 인덱스 스키마 변경이고, 저건 에이전트 지침 문서 변경으로 성격이 다르며 독립적으로 검토하는 게 낫다.
- 기존 `/api/vaults/{name}/search` (단순 검색) 엔드포인트를 다른 호출자가 없다고 확인되면 제거하되, 사용처가 남아있다면 존치한다 (계획 단계에서 확인).

## 설계

### A. 검색 로직 통합

- 신규 공용 훅 `useHybridSearch(vault, query, opts)` (위치: `dashboard/src/lib/` 하위, 기존 lib 구조에 맞춤)를 만든다.
  - 내부에서 쿼리 디바운스(220ms, 기존 두 컴포넌트가 쓰던 것과 동일 지연시간), `fetch('/api/vaults/{vault}/hybrid-search?query=...&limit=...')` 호출, 로딩/에러 상태, 결과 배열을 반환한다.
  - `opts.limit` (기본 8), `opts.excludeSlug` (PropertiesPanel이 현재 문서 자신을 결과에서 제외하던 로직, 기존 131행 `hits.filter(h => h.slug !== page.slug)`)을 지원한다.
- `SearchBar.tsx`와 `PropertiesPanel.tsx` 둘 다 이 훅으로 교체하고, 기존에 각자 갖고 있던 `useDebounced`+`fetch` 중복 코드를 제거한다.
- `raven/api/server.py`의 단순 `/search` 엔드포인트는 계획 단계에서 다른 호출자가 있는지 확인 후, 없으면 제거하고 있으면 존치한다.
- 결과: 두 UI가 동일한 코드 경로로 동일한 검색 결과를 얻는다.

### B. Alias 구조적 지원

**프론트엔드**
- `PropertiesPanel.tsx`에 기존 `tags` 칩 편집 UI(현재 구현부 참고)와 동일한 UX로 `aliases` 칩 편집을 추가한다. 저장은 기존 프론트매터 갱신 API를 재사용한다 (신규 엔드포인트 불필요, `aliases` 필드가 이미 `Page` 타입/백엔드 정규화 로직에 존재하므로).

**백엔드 (검색 인덱스 마이그레이션)**
- `raven/core/db.py`의 `pages_fts` FTS5 가상 테이블 정의를 `fts5(slug, title, tags_concat, content)` → `fts5(slug, title, tags_concat, content, aliases)`로 변경한다.
- 인라인 DB 빌더와 `scripts/build_db.py` 양쪽의 인덱싱 로직에 `aliases` 컬럼 채우기를 추가한다 (`aliases_to_json`/`normalize_aliases`로 이미 정규화된 값을 재사용).
- `raven/core/hybrid_search.py`의 BM25 쿼리가 `aliases` 컬럼도 매칭 대상에 포함하도록 수정 — title과 동등하게 취급되어 alias로 검색해도 문서가 나오고 관련도 점수에 반영된다.
- 기존에 빌드된 vault DB는 스키마가 바뀌므로 재빌드(마이그레이션)가 필요하다 — 계획에 마이그레이션/재빌드 스크립트 실행 단계를 포함한다.

### C. 그래프 라벨 축약 + 호버 툴팁

- `GraphCanvas.tsx`의 라벨 렌더 로직(노드 페인트 콜백 내부)에서 `ctx.measureText(label)`로 폭을 측정하고, 노드 크기(`nodeSize()`)에 비례한 최대 허용 폭을 넘으면 문자열을 잘라 말줄임표(`...`)를 붙인다.
- 이미 존재하는 hover 상태(`hoveredNode`/`hoveredNodeRef`, `onNodeHover` 콜백)를 그대로 활용해, hover 중이거나 focus된 노드는 잘리지 않은 전체 제목을 캔버스에 배경 박스 + 텍스트로 그려서 툴팁처럼 보여준다.
- 기존 `shouldShowLabel()`의 줌 레벨/가중치 기반 표시 여부 로직은 그대로 둔다 — 이번 변경은 "보이는 라벨을 어떻게 그릴지"와 "호버 시 전체 제목 노출"에 한정된 범위다.

## 테스트 관점

- 사이드바 검색과 PropertiesPanel 검색에 동일한 쿼리를 입력했을 때 동일한 문서 목록/순서가 나오는지 확인.
- alias만 일치하는 검색어로 문서를 찾을 수 있는지 확인 (title에는 없고 alias에만 있는 단어).
- PropertiesPanel에서 alias를 추가/삭제 후 저장하면 프론트매터에 반영되고, 재빌드 후 검색에 반영되는지 확인.
- 그래프에서 긴 제목 노드가 잘려서 표시되고, 호버 시 전체 제목이 보이는지 확인. 짧은 제목은 기존과 동일하게 표시되는지(회귀 없음) 확인.
