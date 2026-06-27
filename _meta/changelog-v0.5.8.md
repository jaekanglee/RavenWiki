# raven v0.5.8 — git 위생 P0-2 (`tsconfig.tsbuildinfo` 추적 해제)

> **핵심**: v0.5.6 §9에서 "사용자 확인 필요"로 미뤄뒀던 dashboard 빌드 산출물 추적 문제를 1줄 .gitignore + `git rm --cached`로 해소. 회귀 0.

릴리스 일자: 2026-06-27
이전: v0.5.7 (외부 배포 P0 6건)

---

## 한 줄 요약

`dashboard/tsconfig.tsbuildinfo` (TypeScript 빌드 캐시, 824 bytes) git 추적 해제. **빌드 산출물은 `.gitignore` 대상**이라는 표준 패턴 복원.

---

## 1. 발견 (v0.5.6 §9 follow-up)

| 항목 | 상태 |
|---|---|
| 추적 중 | `dashboard/tsconfig.tsbuildinfo` (1줄, 824 bytes) |
| `.gitignore` | `dashboard/.gitignore`에 `dist/` / `*.local` / `.vite/` 등 다른 빌드 산출물은 이미 등록됨 |
| 누락 | `*.tsbuildinfo` 패턴만 빠져있음 |

→ 외부 신규 사용자가 `git clone` 받으면 빌드 산출물까지 받게 됨 (clone 비대화 + PWA stale 위험).

---

## 2. 패치

```diff
--- a/dashboard/.gitignore
+++ b/dashboard/.gitignore
@@ -1,5 +1,6 @@
 node_modules/
 dist/
+*.tsbuildinfo
 *.local
 .vite/
 .DS_Store
```

```bash
git rm --cached dashboard/tsconfig.tsbuildinfo
# → 파일 자체는 로컬에 유지, 추적만 해제. 다음 `tsc -b` 실행 시 자동 재생성.
```

### 의도적 선택

- **dashboard/.gitignore** (repo root .gitignore 아님): TypeScript 빌드 산출물은 dashboard 영역 한정 → 영역별 .gitignore에 격리
- **`*.tsbuildinfo` (일반 패턴)**: 향후 다른 tsconfig.* 추가되어도 자동 적용

---

## 3. 변경 사항 요약

| 파일 | 변경 |
|---|---|
| `dashboard/.gitignore` | +1줄 (`*.tsbuildinfo`) |
| `dashboard/tsconfig.tsbuildinfo` | 추적 해제 (파일 자체는 유지) |
| **`_meta/changelog-v0.5.8.md`** | **이 문서** |

코드 변경: 0줄, 설정 변경: 1줄, 추적 해제: 1파일.

---

## 4. 검증

```bash
$ git ls-files dashboard/ | grep tsbuildinfo
(0 matches)  ✅ 추적 해제 확인

$ ls -la dashboard/tsconfig.tsbuildinfo
-rw-r--r-- ... 824 bytes  ✅ 로컬 파일 유지

$ PYTHONPATH=. scripts/.venv/bin/python -m pytest tests/ -q
354 passed, 1 warning in 5.46s  ✅ 회귀 0 (Python 변경 없음)
```

---

## 5. AGENTS.md §10 정책 검토

**사전 점검**: Raven repo `AGENTS.md §10`이
> ❌ `.vault.json`, `wiki.db`, `.pyc`, `*.db-journal` 등 gitignore 수정/추가 ❌

로 명시. 그러나:

| 이유 | 적용 |
|---|---|
| **사용자 명시 결정** | clarify 응답 "추적 ❌ — `.gitignore` 추가 + `git rm --cached`" |
| **v0.5.6 §9가 "사용자 확인 필요"로 명시 대기** | 이 항목이 정확히 그 케이스 |
| **dashboard 영역 한정** | repo root .gitignore가 아닌 `dashboard/.gitignore` 격리 |
| **신규 라인, 기존 패턴 변경 없음** | 회귀 0 |

→ 사용자 명시 결정 + 기존 v0.5.6 §9 흐름의 정당한 후속. 진행.

---

## 6. 다음 사이클 후보 (v0.6.0)

1. **P0-4 MCP 네임스페이스 핵** (ADR + `mcp/` → `raven/mcp/` 이동, 100~200줄, **큰 결정**)
2. **P1-1 write-path 단일화** (`raven.core.contracts.write_page()`, 50~100줄)
3. **P1-2 SCHEMA.md sync 충돌 정책** (ADR + 3-way merge vs skip+warn)
4. **P1-3 SQLite WAL + aiosqlite** (멀티 에이전트 동시성, experimental 한계 명시 유지)

---

## 7. 작업 보고

- **무엇**: `dashboard/.gitignore` +1줄 + `dashboard/tsconfig.tsbuildinfo` 추적 해제
- **왜 (저장 신호)**: ① 인수인계 (다음 세션/사람이 clone 시 빌드 산출물 안 받음), ② 결정 추적 (v0.5.6 §9의 정당한 후속), ③ 실패 기록 (재발 방지)
- **검증**: pytest 354 passed (영향 0), 파일 로컬 유지, 추적 해제 확인
- **다음 가능**: P0-4 MCP 네임스페이스 핵 (ADR 필요), P1-1 write-path 단일화
