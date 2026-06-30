# raven v0.7.23 — 시스템 아키텍처 문서화 및 시각화

> **핵심**: Raven의 4-Layer 시스템 아키텍처와 핵심 데이터 흐름을 상세화하고, 시각적 Mermaid 다이어그램을 포함하는 공식 문서를 구축했습니다.

릴리스 일자: 2026-06-30
이전: v0.7.22

---

## 한 줄 요약

Raven의 전체 계층 구조(Data, Engine, Interface, Client) 및 읽기/쓰기 데이터 흐름을 Mermaid 다이어그램으로 시각화하여 `docs/architecture.md`와 `_meta/raven-architecture.md`에 공식 문서화했습니다.

---

## 1. 변경 사항

### 1-1. 아키텍처 공식 문서 추가
* **`docs/architecture.md`**: Raven의 4개 계층(Data, Engine, Interface, Client/UX), 계층별 파일 및 데이터베이스 스키마, CRUD 데이터 흐름(Sequence Diagram), 주요 아키텍처 결정(D7-D9) 및 격리 정책(Lite Bootstrap, Tier Boundary)을 상세하게 기술한 공식 문서를 생성하였습니다.
* **`_meta/raven-architecture.md`**: 기존 `_meta/index.md`에서 깨진 링크로 남아있던 `[[raven-architecture]]` 대상을 생성하고, `docs/architecture.md`로 이어지도록 연동하여 위키 무결성을 복구했습니다.

---

## 2. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| pytest | **471 passed, 1 skipped** | 전체 테스트 성공 ✅ |

---

## 3. 다음 단계
* **v0.7.24 (후보)**: API 응답 `vaults: []` 디버깅
