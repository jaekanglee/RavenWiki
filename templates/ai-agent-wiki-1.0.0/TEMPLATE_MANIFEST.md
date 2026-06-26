# TEMPLATE_MANIFEST.md — AI-Agent-Wiki-Template v1.0.0

> 이 템플릿을 "정상 설치됨"으로 인정받기 위해 존재해야 하는 파일/디렉토리 목록.
> `scripts/verify-raven-vault.sh` 가 이 manifest 를 기준으로 검사한다.

---

## 필수 파일 (10)

| 경로 | 용도 |
|---|---|
| `README.md` | 사람용 안내서 |
| `AGENTS.md` | 에이전트용 운영 규칙 (vendor-agnostic) |
| `START_HERE.md` | 신규 사용자/에이전트 진입 가이드 |
| `index.md` | vault 지도 (사람 + 에이전트 공용) |
| `log.md` | 작업 로그 (append-only) |
| `VERSION` | 템플릿 버전 (예: `1.0.0`) |
| `LICENSE.md` | 라이선스 |
| `TEMPLATE_MANIFEST.md` | 이 파일 |
| `.gitignore` | OS metadata / secrets 제외 규칙 |
| `scripts/verify-raven-vault.sh` | 배포 전 검증 스크립트 |

## 필수 디렉토리 (1)

| 경로 | 내용 |
|---|---|
| `prompts/` | 5개 프롬프트 (`first-setup.md`, `save.md`, `ingest.md`, `query.md`, `lint.md`) |

## prompts/ 내부 파일 (5)

| 경로 | 용도 |
|---|---|
| `prompts/first-setup.md` | 신규 vault 부트스트랩 프롬프트 |
| `prompts/save.md` | 단일 노트 저장 프롬프트 |
| `prompts/ingest.md` | 외부 자료 일괄 ingest 프롬프트 |
| `prompts/query.md` | 검색/질의 프롬프트 |
| `prompts/lint.md` | 무결성 검사 프롬프트 |

## 합계

- 파일: 15개 (위 두 표의 합)
- 디렉토리: 2개 (`prompts/`, `scripts/`)

---

## 사용자 vault 에서는 **자동 복사되지 않아야 하는** 템플릿 파일

이 템플릿 자체는 vault bootstrap 대상이 아닙니다. 사용자 vault는 비어 있는 상태에서 시작하며,
Raven Lite bootstrap은 다음 4종만 자동 복사합니다 (이 manifest 의 일부가 아님):

```
SCHEMA.md     # Raven SCHEMA 정의
RULES.md      # vault 운영 규칙
log.md        # 작업 로그
_meta/        # 메타데이터 디렉토리
```

> 절대 자동 복사 ❌: `OPERATIONS.md`, `agent/*`, `raven-policy.md`. 그리고 이 템플릿의 모든 파일(`README.md`, `AGENTS.md`, `START_HERE.md`, `index.md`, `prompts/`, `scripts/`, `VERSION`, `LICENSE.md`, `TEMPLATE_MANIFEST.md`, `.gitignore`).

---

## 검증 방법

```bash
bash scripts/verify-raven-vault.sh
```

종료 코드:

- `0` — PASS
- `1` — 필수 경로 누락
- `2` — OS metadata 발견 (자동 정리 안 함)
- `3` — secrets 패턴 의심
- `4` — `raven lint run --no-log` 실패
- `5` — 사용 오류

---

## 변경 규칙

이 manifest 의 항목을 추가/삭제할 때:

1. `scripts/verify-raven-vault.sh` 의 `REQUIRED_PATHS` 배열도 함께 갱신.
2. `README.md` 의 "폴더 구조" 섹션도 함께 갱신.
3. PR 본문에 manifest 변경 사유 명시.