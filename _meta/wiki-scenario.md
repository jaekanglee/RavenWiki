---
title: MVP 사용자 시나리오
created: 2026-06-24
updated: 2026-06-24
type: scenario
tags: [scenario, system, harumoa, meta]
sources: [raw/articles/karpathy-llm-wiki-2026.md]
confidence: medium
---

# MVP 사용자 시나리오

## S1. 📥 새 소스 ingest (Primary)

### 액터
- **Jake (사용자)**
- **wiki-orchestrator** (Telegram 라우터)
- **wiki-writer** (문서 작성)
- **wiki-curator** (인덱스/링크 정리)

### 사전 조건
- vault 초기화 완료 ([[SCHEMA]] 존재)
- harumoa 프로젝트 디렉토리 존재

### 플로우
1. **Jake**: Telegram으로 "https://spring.io/guides/tutorial-rest 이거 위키에 넣어줘" 입력
2. **`wiki-orchestrator`**: 의도 분류 → "ingest" → `wiki-writer`로 위임
3. **wiki-writer**:
   - URL fetch → markdown 변환 → `raw/articles/spring-rest-tutorial.md` 저장
   - frontmatter 추가 (`source_url`, `ingested`, `sha256`)
   - **Discussion with Jake**: "이 아티클의 핵심 3가지는 A, B, C 인데, 어디에 어떻게 정리할까요?" (대화형)
4. **wiki-writer**:
   - 새 페이지 생성: `concepts/rest-api.md`
   - 기존 페이지 업데이트: `entities/spring-framework.md`, `harumoa/backend-stack.md`
   - 모든 페이지에 outbound `[[wikilinks]]` ≥ 2
5. **wiki-curator**:
   - `index.md` 업데이트
   - `log.md`에 append
   - dead link 검사
6. **wiki-orchestrator**:
   - "✅ ingest 완료. 변경 파일 N개: ..." 보고

### 사후 조건
- 1개 raw + N개 wiki 페이지 생성/갱신
- 모두 SCHEMA frontmatter 보유
- `log.md`에 기록

### 변형 (Variations)
- **V1.1**: 소스가 PDF → text 추출 + 동일 플로우
- **V1.2**: 한 번에 URL 10개 → 배치 ingest (curator가 1회 처리)
- **V1.3**: 사용자가 "그냥 요약만 만들어줘" → 새 페이지 1개만 (기존 페이지 수정 X)

---

## S2. 🔍 위키 탐색 (Primary)

### 액터
- **Jake**
- **wiki-dashboard** (자체 뷰어)

### 사전 조건
- vault에 페이지 ≥ 10개

### 플로우
1. **Jake**: 로컬 뷰어 열기 (`http://localhost:5173` or 자체 앱)
2. **wiki-dashboard**:
   - `entities/`, `concepts/`, `comparisons/` 트리 렌더
   - 그래프 뷰: 노드 = 페이지, 엣지 = `[[wikilinks]]`
   - 검색: BM25 인덱스 (자체 빌드)
3. **Jake**: 검색창에 "JWT 인증" 입력
4. **wiki-dashboard**:
   - 점수 기반 결과 5개
   - 각 결과에 inbound/outbound 링크 미리보기
5. **Jake**: 결과 클릭 → 마크다운 렌더 (자체 뷰어)
6. **Jake**: 그래프 탭 → "JWT 인증" 노드 중심 subgraph

### 사후 조건
- Jake가 5초 이내에 원하는 페이지 도달
- 그래프로 "관련 엔티티 5개" 시각화

### 변형
- **V2.1**: 명령줄 (`wiki search "JWT"`) — terminal tool
- **V2.2**: Mermaid 다이어그램 자동 렌더

---

## S3. ⚠️ 모순 발견 (Secondary)

### 액터
- **Jake**
- **wiki-curator** (lint)
- **wiki-writer** (재작성)

### 사전 조건
- vault에 50+ 페이지
- `contested: true` 또는 `contradictions:` 보유 페이지 ≥ 1

### 플로우
1. **Jake**: `wiki lint` 실행 (또는 cron이 일주일 1회 자동)
2. **wiki-curator**:
   - 모든 페이지 frontmatter 스캔
   - `contested: true` / `confidence: low` / orphan / broken link / stale 페이지 발견
3. **wiki-curator**: lint report 작성 (`_meta/lint-2026-07-01.md`)
4. **wiki-orchestrator**: Telegram으로 "🔴 3건 발견. 가장 중요한 건 X인데 어떻게 할까요?" 알림
5. **Jake**: "그거 wiki-writer한테 시키고 보고해줘" 명령
6. **wiki-writer**: 두 페이지 비교, 모순 명시, frontmatter 업데이트, 사용자에게 confirm
7. **Jake**: 결정 (페이지 A 선택 / 양쪽 유지 / 통합)

### 사후 조건
- 모순 해결 or 명시적 양쪽 보존
- `log.md`에 결정 기록

---

## S4. 🆕 새 프로젝트 시작 (Future)

### 액터
- **Jake**
- **wiki-architect** (스키마)
- **wiki-curator** (이관)

### 사전 조건
- harumoa 프로젝트가 잘 동작 중

### 플로우
1. **Jake**: Telegram "새 프로젝트 `homeauto` 시작할 건데 같은 시스템으로 세팅해줘"
2. **`wiki-orchestrator`** → `wiki-architect`
3. **wiki-architect**:
   - 기존 [[SCHEMA]] 검토
   - homeauto 도메인에 맞는 tag 추가 (예: `zigbee`, `homekit`, `mqtt`)
   - 새 디렉토리: `homeauto/`
   - RULES.md 작성 (프로젝트별 컨벤션)
4. **wiki-curator**:
   - 빈 `index.md` 섹션 추가
   - `log.md`에 "homeauto 시작" 기록
5. **Jake**: homeauto 첫 ingest → S1과 동일

### 사후 조건
- homeauto가 harumoa와 **독립적으로** 같은 시스템 동작
- 두 프로젝트는 같은 [[SCHEMA]] 공유

---

## S5. 🛠️ 자체 뷰어 빌드 (Dev scenario)

### 액터
- **Jake**
- **wiki-dashboard** (개발)

### 사전 조건
- vault 페이지 ≥ 30
- S1, S2 반복으로 콘텐츠 풍성해짐

### 플로우
1. **Jake**: "자체 뷰어 만들어줘. 검색 + 그래프 + 마크다운 렌더"
2. **wiki-dashboard**:
   - 기술 스택 제안 (정적 사이트 vs SPA)
   - 마크다운 렌더 (markdown-it or remark)
   - 검색 (lunr.js or MiniSearch — 자체 빌드 BM25)
   - 그래프 (D3 force or vis-network)
3. MVP 완성 → `npm run dev` → localhost
4. **Jake**: 피드백 → 반복

### 비범위 (Out of scope for v1)
- 모바일 반응형
- 실시간 동기화 (CRDT 등)
- 플러그인 시스템

---

## 시나리오 ↔ Phase 매핑

| 시나리오 | wiki-architect | wiki-curator | wiki-writer | wiki-dashboard |
|---|:---:|:---:|:---:|:---:|
| S1. ingest | | ✅ | ✅ | |
| S2. 탐색 | | | | ✅ |
| S3. lint/모순 | | ✅ | ✅ | |
| S4. 새 프로젝트 | ✅ | ✅ | | |
| S5. 뷰어 빌드 | | | | ✅ |
