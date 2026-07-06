# Changelog v0.7.81 — Raven MCP HTTP-only 재설계 (2026-07-06)

> **BLUF**: 사용자 정확한 진단 흐름 — "어짜피 B류(근본) 하면 심플한거 아냐?" + "stdio 완전 삭제". v0.7.74-80에서 stdio/HTTP 동등하게 다룬 가이드를 **HTTP only**로 통일. PROJECT-WORKFLOW.md §1.5 + NewVaultWizard + README.md 3 파일 동시 재설계. per-feature commit 3개.
>
> 이전 changelog: `_meta/changelog-v0.7.80.md`

---

## §0 — commit 3개

| commit | 항목 | 파일 | 변경 |
|---|---|---|---|
| `87128c5` | A. PROJECT-WORKFLOW.md §1.5 HTTP-only 재설계 | `raven/core/templates/agent/PROJECT-WORKFLOW.md` | +37/−61 |
| `d5ac752` | B. NewVaultWizard HTTP only (stdio snippet 완전 삭제) | `dashboard/src/components/NewVaultWizard.tsx` | +13/−80 |
| `418a773` | C. README.md §에이전트 인터페이스 HTTP only | `README.md` | +37/−49 |

---

## 진단 배경

### 사용자 진단 흐름 (대화)

1. "피그마 MCP는 왜 잘 되는데 Raven은 왜 복잡해?" → 사용자 진단 — Raven 가이드가 *방어적* 과잉
2. "Raven도 localhost http로 하면 안 돼?" → 외부 AI 검토 — HTTP가 *단순*
3. "에이전트 예시 중 하나가 헤르메스 다른 프로필일 뿐" → vendor-agnostic, 단순화 정당화
4. "어짜피 B류(근본) 하면 심플한거 아냐?" → **Raven 자체를 HTTP-first로** (가이드만 ❌)
5. "stdio 완전 삭제" → 진짜 단순화

### HTTP only의 진짜 장점 (외부 AI 검토 결과)

| 측면 | stdio | HTTP localhost |
|---|---|---|
| **클라이언트 의존성** | python 경로 / 패키지 위치 / vault 디렉토리 | URL 한 줄 |
| **sandbox 우회** | 일부 클라이언트 stdio spawn 차단 | 영향 없음 |
| **lifecycle** | 클라이언트가 spawn (자동) | 운영자가 띄움 (수동) — Dashboard 띄울 때와 동일 |
| **vendor 호환** | vendor별 spawn 정책 상이 | URL만 알면 표준 |
| **운영 복잡도** | 비슷 (모드 정함) | 비슷 (모드 정함) |

→ **HTTP가 더 단순 + 동일하게 안전**. 단일 흐름.

---

## A. PROJECT-WORKFLOW.md §1.5 HTTP-only 재설계 (`87128c5`)

### 변경 요약

| 변경 | 이전 | 이후 |
|---|---|---|
| §1.5 헤딩 | 'MCP 도달법' | 'MCP 도달법 — HTTP localhost (v0.7.81+)' |
| §1.5 + §1.5.1 | transport 표 2개 + 두 패턴 | '1단계 서버 띄우기 / 2단계 URL 등록 / 3단계 표준 흐름' 단일 흐름 |
| transport 패턴 | stdio + streamable-http | HTTP only |
| stdio 패턴 스니펫 | 있음 | 완전 제거 |
| 트러블슈팅 | 4가지 (stdio 관련 1개) | 3가지 (HTTP 관련만) |
| 권한 모드 표 / 운영자 전달 단락 / R9 cross-link | 유지 | 유지 |

### §1.5 본문 (v0.7.81+)

```
1단계: python -m raven.mcp.cli --transport http --host 127.0.0.1 --port 8765 --mode <...>
2단계: {"url": "http://localhost:8765/mcp"}
3단계: tools/list → 9개 도구 schema 자동 discovery → wiki_search(vault='<basename>', ...)
```

### vendor-neutral 검증

- vendor 명 0건 (Claude/Cursor/Codex/Antigravity/Hermes 일체)
- Lite bootstrap 정책 부합 (Tier 1 leak 0건)
- R9 cross-link 유지 (외부 에이전트가 Raven 소스 조회 시도 차단)

**LOC 압축**: −24줄 (37 insertions / 61 deletions).

---

## B. NewVaultWizard HTTP only (`d5ac752`)

### 제거

- `buildStdioSnippet` 함수 (12줄)
- stdio UI 블록 (50줄) — pre + 복사 버튼
- `stdioSnippet` 변수 정의
- 하단 안내 카드의 `'command not found: python'` 트러블슈팅

### 단순화

- HTTP 라벨: `'streamable-http (원격)'` → `'HTTP localhost (권장 — 단일 흐름)'`
- 안내 카드 헤딩: `'표준 MCP 연결 흐름'` → `'흐름 (v0.7.81+ HTTP only)'`
- 안내 카드 3단계 → 운영자 서버 띄우기 1단계 추가
- 트러블슈팅 4가지 → 3가지 (stdio 관련 제거)

**LOC 압축**: −67줄 (13 insertions / 80 deletions).

§13.1/13.2 적용 (Button 컴포넌트, CSS 변수, vendor-neutral 유지).

**검증**: tsc -b --noEmit clean.

---

## C. README.md §에이전트 인터페이스 HTTP only (`418a773`)

사람 운영자 가이드 — stdio 옵션을 *부록 1단락*으로 유지 (운영자가 자기 환경 판단), 본문은 HTTP 우선.

### 재구성

- 헤딩: `'에이전트 인터페이스 (MCP, v0.7.8+)'` → `'에이전트 인터페이스 (MCP, v0.7.81+ HTTP only)'`
- 3섹션 (client 설정 예시 / 서버 실행 / 첫 도구 호출) → `'흐름 (1-2-3)'` 단일 섹션
- stdio/HTTP 동등 → HTTP 권장 + stdio는 보조 1단락

### README 추가 정보 (사용자 운영자용)

"왜 HTTP only" 3가지 이유 명시:
- 의존성 0 (python 경로/패키지/vault 디렉토리)
- sandbox 우회 (stdio spawn 차단 클라이언트)
- lifecycle 단순 (운영자 관리)

**LOC 압축**: −12줄 (37 insertions / 49 deletions).

§1.5.1 cross-link → §1.5 (v0.7.81+ 통합)으로 갱신.

---

## §1 — 검증 종합

| 검증 | 결과 |
|---|---|
| `tsc -b --noEmit` (dashboard) | clean |
| `git push origin master` | 완료 |
| **LOC 압축 합계** | **−103줄** (가이드 단순화 효과) |

---

## §2 — 외부 에이전트 walkthrough (v0.7.81+ 단일 흐름)

> "vault 운영자가 외부 MCP 클라이언트 운영자에게 vault 전달"

1. 운영자가 `python -m raven.mcp.cli --transport http --port 8765 --mode read` 1회 띄움
2. 운영자가 외부 운영자에게 *vault 경로 + URL* 전달
3. 외부 운영자가 자기 MCP 클라이언트에 `{"url": "http://localhost:8765/mcp"}` 1줄 추가
4. 클라이언트가 tools/list 호출 → 9개 도구 schema 자동 discovery
5. `wiki_search(vault="<basename>", query="...")` 호출 → 즉시 사용

→ **stdio 패턴 의존성 / spawn sandbox / python 경로 의존성 0**. 단순.

---

## §3 — 사이클 연속성

| 사이클 | 항목 |
|---|---|
| v0.7.74 | PROJECT-WORKFLOW.md §1.5 + Wizard MCP snippet (stdio/HTTP 동등) |
| v0.7.75-80 | Wizard 안내 강화, §0 vault 경계, README vendor-neutral hotfix, R9 cross-link, 운영자 전달 명시 |
| v0.7.81 | **HTTP only 재설계 (3 파일 동시, stdio 완전 삭제, −103 LOC)** |

→ 사용자가 짚은 *Raven 가이드 복잡함의 근본 원인* 제거. Lite bootstrap + vendor-agnostic + R9 정책 일관성 유지하면서 단순화 달성.