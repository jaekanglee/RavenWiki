# raven v0.7.39 — 문서 뷰어 상단 파일 절대 경로 표시 기능 추가

> **핵심**: 사용자가 대시보드에서 마크다운 문서를 읽을 때, 현재 보고 있는 파일이 로컬 디스크 상의 어떤 경로에 위치해 있는지 쉽게 인지할 수 있도록 문서 제목 위에 전체 파일 경로(absolute path)를 표시해주는 기능을 추가했습니다.

릴리스 일자: 2026-07-01
이전: v0.7.38

---

## 1. 배경 및 기획

* **사용자 피드백**: "문서별로, 제목 위에 작게 지금 파일의 풀 경로를 알려주는게 좋지않을까."
* **목적**: 대시보드는 로컬에 저장된 마크다운 파일을 기반으로 동작하는 Wiki 엔진이므로, 사용자가 현재 편집하거나 조회하고 있는 마크다운 파일의 실제 물리 경로를 한눈에 식별할 수 있도록 함으로써 로컬-퍼스트(local-first) PKM으로서의 사용성을 강화합니다.

---

## 2. 변경 사항

### 2-1. 백엔드 페이지 조회 API 응답 확장 (`raven/api/server.py`)

* **`file_path` 필드 추가**: `GET /api/vaults/{name}/pages/{slug:path}` API의 반환 데이터에 `file_path` 키를 추가하고, 해당 페이지 마크다운 파일의 절대 경로(`str(fp.resolve())`)를 반환하도록 수정했습니다.

### 2-2. 대시보드 인터페이스 확장 및 경로 렌더링 (`types.ts`, `PageView.tsx`)

* **타입 추가 (`types.ts`)**: `Page` 인터페이스에 선택적 필드로 `filePath?: string;`를 추가했습니다.
* **상태 매핑 및 화면 표시 (`PageView.tsx`)**:
  * API로 받아온 `d.file_path` 값을 Page의 `filePath` 상태로 매핑했습니다.
  * 문서 헤더 영역에서 제목(`<h1>`) 바로 위에 `fontFamily: "ui-monospace"`, `fontSize: 11`의 작고 정돈된 모노스페이스 스타일로 파일의 전체 경로를 출력하도록 UI를 개선했습니다.

### 2-3. API 테스트 코드 보완 (`tests/test_api.py`)

* **`test_api_page_update_preserves_created` 내 검증**: 페이지 조회 API 응답 시 `file_path` 키가 정상적으로 포함되어 있으며, 유효한 마크다운 파일 경로로 끝나는지 검증하는 assertion을 보강했습니다.

---

## 3. 검증 결과

| 항목 | 결과 | 비고 |
|---|---|---|
| `npm run build` (tsc 포함) | **Success** | 대시보드 컴파일 및 프로덕션 빌드 정상 완료 |
| `pytest tests/` 전체 | **490 passed, 1 skipped** | 백엔드 API 테스트 전체 통과 |
| `git status` 변경 목록 일치 | **Success** | `server.py`, `types.ts`, `PageView.tsx`, `test_api.py`, `changelog-v0.7.39.md` 변경 |

---

## 4. 다음 단계

* 경로 복사 편의성을 위한 클립보드 복사 버튼 추가 검토.
