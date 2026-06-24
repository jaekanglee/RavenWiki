---
title: React SPA 아키텍처
created: 2026-06-25
updated: 2026-06-25
type: concept
tags: [concept, ui, system, react, dashboard]
sources: [_meta/system-design.md]
confidence: high
---

# React SPA 아키텍처

## 정의

> SPA (Single Page Application) — 단일 HTML 페이지 + 클라이언트 라우팅.
> 서버는 API/JSON만, 렌더링은 브라우저 JS가 담당.

vs MPA (Multi Page App, 전통적 서버 렌더):
- MPA: 매 링크 클릭 = 서버 라운드트립 + 전체 페이지 새로 로드
- SPA: 라우터가 컴포넌트만 교체 (URL만 바뀜)

## 우리 선택 이유 (vault = stateful)

[[content/llm-wiki]] 패턴 = **위키는 영구적, 누적적**:
- 사용자가 같은 페이지를 **수십 번 다시 방문** (북마크/검색/탐색)
- 마지막 scroll 위치 / 사이드바 선택 / 검색어 → **상태 복원** 필요
- 인덱스(`wiki.db`) 로드는 1회 → 클라이언트가 메모리에 보관

→ SPA 적합 (상태 유지 + 빠른 탐색)
→ SSG 불리 (페이지 빌드/배포마다 index 재생성)

[[content/ssg-vs-spa]]에서 7가지 차원 비교.

## React 19 + Vite + TypeScript

| 선택지 | 이유 |
|---|---|
| **React 19** | use, Server Components, Actions (필요 시 fetch-as-you-render) |
| **Vite** | 빌드 1초, HMR 즉각, ESBuild 기반 |
| **TypeScript** | wiki 데이터 구조(frontmatter, links)를 타입으로 강제 |
| **React Router 7** | SPA 표준 라우팅 |
| **TanStack Query** | MCP/API 호출 결과 캐싱 (선택) |

→ 결정 근거는 [[_meta/system-design]] §2.3에서 Svelte → React로 변경된 이유.

## 컴포넌트 구조 (제안)

```
src/
├── app/
│   ├── App.tsx              # 라우터 + 프로바이더
│   ├── routes.tsx           # /page/:slug, /graph, /search
│   └── providers.tsx        # ThemeProvider, QueryClient
├── features/
│   ├── sidebar/             # 페이지 트리 (frontmatter 기반)
│   ├── reader/              # markdown 렌더 (remark + rehype)
│   ├── search/              # BM25 클라이언트 (miniSearch)
│   ├── graph/               # D3 force 시각화
│   └── editor/              # CodeMirror 6 (P2)
├── lib/
│   ├── api/                 # wiki-mcp 호출 (HTTP) 또는 wiki.db 직접
│   ├── markdown/            # wikilink 파서, frontmatter 추출
│   └── theme/               # dark/light + hotkey
└── ui/                      # 공용 버튼/모달/입력 (shadcn 또는 자체)
```

**핵심 원칙**:
- **features 단위로 격리** (sidebar/search/reader는 서로 모름)
- **위키 데이터는 props로 흐름** (전역 store ❌)
- **api 호출은 lib/api에 모음** (MCP 직접 vs wiki.db 직접 — 환경별 분기)

## PWA (오프라인)

폰/외부에서 사용할 때 필수:
- **Service Worker**: 위키 페이지 캐싱 → 오프라인 read
- **Manifest**: "홈 화면에 추가" → 앱처럼 실행
- **Background Sync**: 변경사항 오프라인 큐잉 → 온라인 시 push

→ [[_meta/system-design]] N4 (폰에서 사용) 니즈의 핵심 구현.

## 상태 관리 선택

| 후보 | 적합도 | 이유 |
|---|---|---|
| **React state (useState/useReducer)** | ✅ 1차 | 위키 데이터는 props로 흐름 |
| Zustand | 🟡 선택 | 사이드바 선택/검색어 등 UI 상태 |
| Jotai | 🟡 선택 | atom 단위 fine-grained |
| Redux | ❌ | 오버스펙 |
| Recoil | ❌ | Facebook 의존, 유지보수 불확실 |

**결론**: 1차 = React state + Zustand (필요 시). Redux 사용 안 함.

## 스타일링

| 후보 | 결정 | 이유 |
|---|---|---|
| **Tailwind CSS** | ✅ 1차 | 빠르고 일관적, 디자인 토큰 자동화 |
| CSS Modules | ❌ | 반복 많음 |
| styled-components | ❌ | 런타임 비용 |
| Vanilla Extract | 🟡 선택 | 타입 안정, 빌드타임 |

## 위키 특화 기능 (M3+)

- **백링크 패널**: `[[링크]]` 자동 추출 → 페이지 하단에 "이 페이지를 가리키는 N개"
- **그래프 뷰**: D3 force layout, 노드 = 페이지, 엣지 = wikilink
- **인라인 검색**: `/` 키 → 명령 팔레트 (cmdk) → 페이지 즉시 점프
- **태그 필터**: 사이드바에서 `concept`/`person` 등 태그별 필터
- **mermaid 다이어그램**: 코드블록으로 즉시 렌더

## 한계 / 미결정

- 초기 JS 번들 큼 (위키용 ~200KB) → 코드 스플리팅으로 완화
- SEO 불필요 (개인 위키) → 메타 태그 최소화
- React Server Components vs 풀 SPA → 우리는 wiki.db 직접 쿼리하므로 풀 SPA로 충분

## 관련

- [[content/ssg-vs-spa]] — SSG vs SPA 비교 (우리 선택)
- [[content/mcp-server]] — React UI가 호출할 MCP
- [[_meta/system-design]] — Layer 3 (Dashboard) 설계
- [[SCHEMA]] — frontmatter가 dashboard 데이터 모델
