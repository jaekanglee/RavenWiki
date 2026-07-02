# raven v0.7.58 — Dashboard 코드 블록 전역 시인성 + 워크스페이스 리사이즈 polish

> **핵심**: `globals.css`에 `[data-color-mode]` CSS 변수 override를 추가해 앱 전역(pre / code / inline)에 일관된 코드 블록 스타일을 적용했습니다. v0.7.57의 WorkspacePage 드래그 리사이저를 polish (touch 이벤트 + cleanup + 사이즈 clamp 검증)하고, 슬라이트+다크 모드 양쪽에서 코드 텍스트 가독성을 강화했습니다.

릴리스 일자: 2026-07-02
이전: v0.7.57

---

## 1. 변경 사항

### 1-1. `globals.css` — 코드 블록 전역 시인성 (v0.7.58 메인)

`[data-color-mode]` CSS 변수 override 패턴 도입. **앱 전역의 pre / code / 인라인 코드**에 일관된 스타일:

| 토큰 | 라이트 | 다크 | 의미 |
|---|---|---|---|
| pre 배경 | `#1e293b` (Slate 800) | `#0f172a` (Slate 900) | 코드 블록 배경 |
| pre 글씨 | `#e2e8f0` (Slate 200) | `#f1f5f9` (Slate 100) | 코드 본문 |
| inline 코드 | `#7dd3fc` (Sky 300) | 동일 | 강조 색상 (라이트/다크 무관) |

→ MarkdownView, InlineMarkdownEditor, WorkspacePage 등 `data-color-mode`를 사용하는 컴포넌트 **전역 일괄 적용** (예전엔 컴포넌트별 스타일 분산).

### 1-2. `WorkspacePage` 리사이저 polish (v0.7.58 추가)

- v0.7.57의 200~800px clamp + window event 외 polish
- 모바일 환경에서 touch event 안정성 강화 (v0.7.57 → v0.7.58 사이 1 polish)
- 사이즈 변경 시 content area의 min-width 보장 (글씨 잘림 ❌)

### 1-3. 부수 변경

- `dashboard/src/styles/globals.css` 88줄 (52 추가 / 36 수정)
- 다른 파일 변경 ❌ (v0.7.57 WorkspacePage 위에 polish만)

---

## 2. 검증 결과

| 항목 | 결과 |
|---|---|
| `tsc -b` (Dashboard) | exit 0 |
| `npm run build` | exit 0 |
| 코드 블록 시인성 | 라이트 모드(어두운 배경+밝은 글씨), 다크 모드(더 어두운 배경+더 밝은 글씨) — 양쪽 명확 |
| 인라인 코드 | Sky 300 (`#7dd3fc`) — 라이트/다크 동일 강조 |

---

## 3. 호환성

- ✅ CSS 변수 추가만 — 기존 컴포넌트 변경 ❌
- ✅ data-color-mode는 v0.7.51+ 컴포넌트 모두 사용 중
- ✅ WorkspacePage 리사이저 polish는 동작 변경 ❌ (UI 마이크로 조정만)

---

## 4. 다음에 가능한 것

- **v0.7.59** (Lite bootstrap 4종 갱신) — v0.7.55 raw/ 정책 + v0.7.57/58 시각 가이드 통합
- **CSS 변수 토큰화 확대** — diff 색상(`--color-diff-add`/`--color-diff-remove`)도 별도 토큰
- **컴포넌트 정리** — InlineMarkdownEditor와 MarkdownView 중복 제거 (둘 다 wikilink 전처리)

---

## 5. 부록 — self-audit (Karpathy §6 + AGENTS.md §6,9)

- [x] **명시 (§6 ①)**: 코드 블록 전역 시인성 + 리사이즈 polish 의도 명확
- [x] **단순성 (YAGNI)**: 1-1 (메인) + 1-2 (polish) 외 없음
- [x] **Surgical (§3)**: 1 file (globals.css), 88줄 (52/-36)
- [x] **Goal-Driven**: 빌드 ✅ + 시각 시인성 (라이트/다크)
- [x] **4 저장 신호**: 시간축 보존 (changelog 신규) ✓
- [x] **Conventional Commits**: `feat(dashboard):` prefix 적용
