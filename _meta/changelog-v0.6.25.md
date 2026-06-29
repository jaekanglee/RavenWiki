# raven v0.6.25 — 회귀 검증 종합 통과

> **핵심**: v0.6.17 ~ v0.6.24 누적 변경 (8 commit) frontend/backend 종합 회귀 검증 — 전부 통과.

릴리스 일자: 2026-06-29
이전: v0.6.24 (DeleteButton/EditButton Portal)

---

## 한 줄 요약

vitest (17 파일 / 84 tests pass + 1 skip) + tsc -b (exit 0) + pytest (397 passed) + 브라우저 smoke (4 모달 + PageMetaRow + path picker + 폴더 hover 메뉴) — **모두 통과**.

## 1. 검증 매트릭스

### 1-1. Frontend

| 검증 | 결과 |
|---|---|
| vitest | 17 파일 / 84 tests pass + 1 skip |
| tsc -b | exit 0 |
| 브라우저 HomePage 로딩 | h1="🐦 Raven", 활성 vault=raven-dev |

### 1-2. Python (Raven CLI/API)

| 검증 | 결과 |
|---|---|
| pytest tests/ | **397 passed** (5.89s) |

### 1-3. UI 기능 smoke

| 기능 | 결과 |
|---|---|
| 📑 PageMetaRow Index 마커 | `concept \| 📑 Index \| updated \| #raven #home` |
| NewPageButton 모달 Portal | parent=document.body ✓ |
| Path picker (폴더 클릭 → slug prefix) | `content/concept/` 자동 주입 ✓ |
| DeleteButton 모달 Portal | parent=document.body ✓ |
| EditButton 모달 Portal | parent=document.body ✓ |
| Sidebar 폴더 hover 메뉴 | 3개 페이지 만들기 버튼 (vault + concept + decision) ✓ |

## 2. 누적 변경 요약 (v0.6.17 ~ v0.6.24, 8 commit)

| 버전 | 핵심 |
|---|---|
| v0.6.17 | 사이드바 drawer 자동 close on modal open (onOpen prop) |
| v0.6.18 | React Portal — 모달 viewport 기준 진짜 중앙 |
| v0.6.19 | vault 트리 path picker — 직접 타이핑 제거 |
| v0.6.20 | TextField 공통 컴포넌트 + 좌우 패딩 14px |
| v0.6.21 | PageMetaRow + 📑 Index 마커 |
| v0.6.22 | Sidebar 폴더 hover 메뉴 (인라인 페이지 만들기) |
| v0.6.23 | TextField 사용처 4개 확장 |
| v0.6.24 | DeleteButton/EditButton Portal 누락 fix |

## 3. 회귀 검증 의미

이번 8 commit 동안 **사용자 UX 피드백 4건 처리**:
1. "모달이 사이드바 안에 있다" → v0.6.18 Portal
2. "직접 타이핑 별로" → v0.6.19 path picker
3. "좌우 패딩 답답" → v0.6.20 padding + TextField
4. "재사용 컴포넌트/토큰화" → v0.6.20 §13 + v0.6.23 확장

각 피드백 → **RED test → GREEN 구현 → 브라우저 smoke → commit** 사이클 4-5번 반복. 누적 회귀 0.

## 4. 후속 작업 후보

- (즉시) `<Modal>` 공통 컴포넌트 (4개 모달이 같은 backdrop/dim-click 패턴) — 사용자 원칙 §13.1
- (중기) `<Button>` 공통 컴포넌트 (`.btn-primary`/`.btn-secondary`/`.btn-pill-primary`/`.btn-tertiary` 인스턴스 다수)
- (중기) `<SelectField>` 공통 컴포넌트 (TextField select 지원)
- (지속) Raven 코드 변경 시 ADR/concept 자가 사용 — wiki-self-user에게 위임
- (다음 세션) 새 작업 큐 — 사용자 입력 대기