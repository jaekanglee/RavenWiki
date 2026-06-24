---
title: SSG vs SPA (위키 프론트엔드)
created: 2026-06-25
updated: 2026-06-25
type: comparison
tags: [comparison, ui, system, react]
sources: [_meta/system-design.md]
confidence: high
---

# SSG vs SPA (위키 프론트엔드)

## 7가지 차원 비교

| 차원 | SSG (Astro, Hugo, Jekyll) | SPA (React, Svelte, Vue) |
|---|---|---|
| **빌드 시점** | 빌드 타임에 HTML 생성 | 런타임에 JS로 렌더 |
| **페이지 로드** | 즉시 (HTML 완성) | JS 다운로드 후 렌더 |
| **첫 paint** | 매우 빠름 | 보통 (200-500ms JS 파싱) |
| **내비게이션** | 전체 페이지 다시 로드 | 클라이언트 라우팅 (즉시) |
| **상태 유지** | ❌ (매번 리셋) | ✅ (메모리에 유지) |
| **검색 성능** | 정적 HTML grep | 클라이언트 인덱스 (BM25/vector) |
| **빌드 비용** | 페이지 N개 = N초 | 1회 빌드 (수초) |

## 우리 선택 (React SPA, 왜?)

[[content/react-spa-architecture]]에서 결정.

**핵심 이유**:
1. **상태 유지** — 위키는 stateful ([[content/llm-wiki]]: "영구적이고 누적적")
   - 사이드바 선택 / 검색어 / scroll 위치 복원
   - SSG = 매번 리셋 → 사용성 저하
2. **빠른 내비게이션** — 위키는 탐색이 핵심
   - wikilink 클릭 = 클라이언트 라우팅 (즉시)
   - SSG = 서버 라운드트립 + 전체 페이지 새로 로드
3. **빌드 의존성 제거** — SSG는 페이지 추가/수정마다 빌드 필요
   - 우리 시스템: curator가 push → VPS가 즉시 반영
   - SSG였다면: push → VPS 빌드 (1분+) → 반영
4. **검색 인덱스 클라이언트** — BM25/MiniSearch를 브라우저에
   - SSG는 서버 사이드 검색 필요 → API 의존
5. **PWA 친화** — service worker로 오프라인 read (N4 니즈)

## SSG가 더 나은 경우

| 상황 | 추천 |
|---|---|
| 블로그 / 마케팅 페이지 (대부분 read-only) | SSG |
| 문서 (read-only + SEO 중요) | SSG |
| **stateful** wiki / 대시보드 | **SPA** |
| 외부 검색 엔진 노출이 핵심 | SSG |
| 빌드 인프라 견딤 + 페이지 적음 | SSG |

## 우리가 SSG를 안 고른 결정적 이유

### 결정 1: stateful 인터페이스
[[content/llm-wiki]] 패턴 = "유상태 (위키에 누적)".
- 사용자가 같은 위키에 **수십 번 재방문**
- 사이드바 확장 상태 / 검색 히스토리 / 마지막 scroll 위치 → **복원 필수**

### 결정 2: 빌드 의존성 제거
- 우리 시스템은 "wiki.db = 빌드 산출물 (gitignore)"
- 마크다운 = SoT (git 추적)
- curator가 push → VPS가 git pull → **즉시 반영**
- SSG였다면: push → VPS build → 1분+ → 반영 (R5 리스크: 휴가 시 자동화 필요)

### 결정 3: PWA + 오프라인
- 폰에서 사용 ([[_meta/system-design]] N4)
- service worker로 페이지 캐싱 → 오프라인 read
- SSG도 PWA 가능하지만 SPA가 더 자연스러움

## 트레이드오프 인정

| SPA의 단점 | 우리 완화 |
|---|---|
| 첫 페이지 로드 느림 (JS 파싱) | code splitting + lazy import |
| SEO 불필요 (개인 위키) | 무관 |
| JS 번들 큼 | 위키용 ~200KB 목표 |
| 보안 (XSS 표면) | wikilink 화이트리스트, React 기본 escape |

## 결정 사항

| # | 결정 | 선택 |
|---|---|---|
| D-FE-1 | Frontend 종류 | SPA |
| D-FE-2 | 프레임워크 | React 19 (Svelte에서 변경, [[_meta/system-design]] §8 결정 후) |
| D-FE-3 | 빌드 도구 | Vite |
| D-FE-4 | 언어 | TypeScript |
| D-FE-5 | 라우터 | React Router 7 |

## 우리 시스템에서의 위치

```
사용자 (Jake)
    ↓ 브라우저 (React SPA)
   ┌─────────┐
   │ Wiki UI │
   └────┬────┘
        │ fetch (XHR/fetch)
        ▼
   ┌──────────────┐
   │ wiki-mcp     │ 또는 wiki.db 직접 (개발 시)
   │ :8765        │
   └──────────────┘
```

## 관련

- [[content/react-spa-architecture]] — React SPA 상세
- [[content/llm-wiki]] — stateful 패턴의 근거
- [[content/mcp-server]] — UI가 호출하는 백엔드
- [[_meta/system-design]] — Layer 3 설계
