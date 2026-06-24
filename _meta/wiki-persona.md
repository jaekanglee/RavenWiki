---
title: 사용자 페르소나
created: 2026-06-24
updated: 2026-06-24
type: persona
tags: [persona, system, meta]
sources: []
confidence: medium
---

# 사용자 페르소나

## Primary: 🧑‍💻 Jake — 혼자 일하는 개발자 (alias: 삐질 리)

### 배경
- 30대, 풀스택/백엔드 위주, 10년차
- 진행 프로젝트 여러 개 동시 (harumoa, homeauto 등)
- Telegram으로 `wiki-orchestrator`와 소통
- macOS 로컬, Obsidian **구매 의향 없음**
- git 사용, CLI 편함

### 통증 (Pain Points)
1. **메모가 사방에 흩어짐**: 노션, 메모앱, 마크다운 파일, 트윗, 채팅 — 검색 안 됨
2. **"예전에 그거 본 거 같은데"** — 출처도 못 찾음
3. **위키 직접 만들면 진작 질림** — cross-reference 업데이트가 싫음
4. **Obsidian은 좋은데 유료 확장/플러그인 망설임**
5. **AI 요약은 늘 평범함** — 그냥 검색 잘 되는 백과사전

### 목표 (Goals)
- "내 머릿속 + 본 자료를 한 곳에"
- **Obsidian 없이** 그에 준하는 경험
- "AI가 정리해주는 위키" — 내가 직접 손대지 않아도 계속 최신
- git으로 백업/버전관리 자연스럽게

### 성공 기준
- 새 자료 1개 떨궈도 vault가 알아서 풍성해짐
- "이거 3달 전에 본 거 같은데" → 5초 안에 찾음
- 새 프로젝트 시작해도 **같은 시스템 재사용**

### 핵심 워크플로우
```
Telegram: "https://... 이거 위키에 넣어줘"
↓
wiki-orchestrator가 wiki-writer에게 ingest 위임
↓
raw/에 저장, 10-15 페이지 자동 업데이트
↓
"완료, 업데이트된 파일: ..." 보고
↓
`wiki-dashboard`에서 그래프/검색으로 확인
```

### 인용 (Quote)
> "옵시디언 안 사고, 모티브만 빌려서 내가 직접 만들 거야."

---

## Secondary: 📚 Riya — 리서치 애호가 (가상)

### 배경
- 박사과정, ML/인지과학 분야
- arXiv 논문 + 책 + 팟캐스트를 매일 소비
- 메모는 Obsidian에 수동으로 정리 중 (지쳐감)

### 통증
- 논문 100개 읽고 1개 synthesis 하기 힘듦
- 인용/링크 수동 = 밤새는 일
- "내 해석"이 일반 AI 요약에 묻혀버림

### 목표
- **"읽은 것들의 살아있는 연결망"**
- 시간 지나도 진화하는 synthesis
- 인용 자동 관리

### 우리 시스템이 줄 수 있는 것
- `wiki-curator`가 cross-reference 자동 갱신
- lint가 "이거 6개월 전 자료, 신버전 있음" 알림
- `wiki-architect`가 "이 두 엔티티 페이지 통합해도 됨" 제안

---

## Anti-Persona: ❌ 대규모 팀

### 왜 안 맞나
- 동시 편집 5명+ → git conflict 폭증
- 권한 관리 없음 (ACL)
- audit log 없음
- LLM 유지보수 비용 누가 부담?

### 권장
- 위키 시스템 **무료 OSS**로 공개 시 self-host로 소규모 팀은 가능
- 대규모는 Notion/Confluence가 정답 (그걸 대체하려는 게 아님)

---

## 페르소나 ↔ 기능 매핑

| 페르소나 | 주로 쓰는 Phase |
|---|---|
| Jake (Primary) | `wiki-orchestrator` (Telegram) → 4 Phase 전부 |
| Riya (Secondary) | `wiki-writer` (직접 ingest 호출) + `wiki-curator` |
| Anti-persona | (지원 안 함) |
