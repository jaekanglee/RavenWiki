# raven v0.6.37 — North Star 재정렬 (Obsidian 1차 + LLM Wiki +α)

> **핵심**: 사용자 정정 (2026-06-30) — "Raven은 Obsidian 대체제 자체 구현이 본질. LLM Wiki 개념은 vault 안에서 +α로 선택적 도입. mode 개념이 맞았는데, vault 전체 강제가 아니라 vault 안 영역에 +α로 적용."
>
> Codex CLI + Antigravity CLI 검토 (취합) 후 재정렬. 본 릴리스는 north star 박힌 곳 4+ 마이그레이션 + 회귀 가드 8개 갱신 + 문서 일관성 (진입점 4개 통일, vault root `~/Raven` 정정).

릴리스 일자: 2026-06-30
이전: v0.6.36 (vendor-agnostic 재정렬)

---

## 한 줄 요약

north star 박힌 곳(README/AGENTS.md/wikisys-policy.md/test_north_star_contract.py) 재정렬:
- v0.6.31 톤: "Karpathy LLM Wiki self-host 구현체"
- v0.6.37 톤: **"사람 1차 Obsidian 대체체 + LLM Wiki +α 옵션"**

+ README `5개 진입점` → `4개 진입점` 오류 정정
+ README vault root `~/vaults/` → `~/Raven/` (v0.6.3+ 표준) 정정

## 1. 변경 사항

### 1-1. README.md North Star 재정렬

**Before (v0.6.31~36)**:
```markdown
## North Star (v0.6.31+)
> "LLM의 휘발성 메모리를 git-tracked 영속 markdown으로 변환해,
>  매 세션 재구성하지 않고 compounding knowledge를 누적한다."
> — Karpathy LLM Wiki (2026) 패턴의 self-host 구현체. ...
```

**After (v0.6.37)**:
```markdown
## North Star (v0.6.37 재정렬)
> "Raven은 사람을 1차 사용자로 하는 local-first markdown PKM vault이며,
>  원하는 vault 영역에만 LLM Wiki 패턴을 +α로 켜 compounding knowledge를 누적한다."
> — Obsidian 모티브 (자유 vault) + Karpathy LLM Wiki (2026) 영감 + 자체 구현체. ...
```

### 1-2. README.md vs Obsidian 표 재정렬

| 항목 | Before | After |
|---|---|---|
| 진입점 | GUI + CLI + Python + HTTP + MCP **5개** | CLI + HTTP API + Dashboard + MCP **4개** |
| 사용자 | 사람 + 단일 에이전트 동시 1차 | **사람 1차, 에이전트 옵션** (LLM Wiki +α로 켤 수 있음) |
| 에이전트 | vault 1급 시민 | **vault 옵션 시민** (scope/provenance 강제는 opt-in) |

### 1-3. README.md vault root 정정

- L21, L80, L225, L421: `~/vaults/` → `~/Raven/` (v0.6.3+ 표준)
- L228: `.vault.json (name, mode, owner)` → `.vault.json (name, path)` (mode 표시용 metadata로 강등 예정, v0.6.38+)

### 1-4. AGENTS.md §0.5 재정렬

north star 박음 + 호환 노트 추가:
> ⚠️ v0.6.31~v0.6.36 호환 노트: v0.6.31~36은 "LLM Wiki self-host 구현체" 톤으로 박혀 있었음. v0.6.37에서 사용자 north star 재정렬.

### 1-5. `raven/core/templates/wikisys-policy.md` §0 재정렬

vault 운영 정책 문서의 North Star도 동일 톤으로 재정렬.

### 1-6. `tests/test_north_star_contract.py` (회귀 가드 8개 갱신)

**Before (v0.6.31, 7 tests)**:
- "Karpathy LLM Wiki (2026)" 필수 인용
- "compounding knowledge" 필수 문구

**After (v0.6.37, 8 tests)**:
- "사람을 1차 사용자로" 필수 (human-first)
- "Obsidian" 모티브 명시
- "+α" / "원하는 vault 영역에만" / "원하면" 중 하나 필수 (LLM Wiki opt-in)
- "컴파일 후 reuse" / "매번 재구성" (v0.6.31 톤 보존)

### 1-7. `_meta/changelog-v0.6.31.md` / `v0.6.36.md` 재정렬 노트

역사 보존: 본문 그대로 유지, 상단에 "⚠️ v0.6.37 재정렬 노트" 한 줄 추가.

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **426 passed, 1 skipped** (v0.6.36: 425 → v0.6.37: 426, +1) |
| test_north_star_contract.py | **8 passed** (재정렬 가드 8개) |
| README 진입점 일관성 | ✅ 4개로 통일 |
| README vault root 일관성 | ✅ `~/Raven` 통일 |
| 변경 라인 trace | 모든 변경이 사용자 north star 정정에 직접 trace |

## 3. 의도

사용자가 "Raven = Obsidian 대체 자체 구현"이라는 출발점을 다시 한번 강조함.
v0.6.31~36은 "Karpathy LLM Wiki self-host" 톤이 강해서 Raven이 LLM Wiki의
self-host 구현체처럼 보였음. 하지만 Raven의 본질은:

1. **Obsidian 모티브** (사용자 출발점) — `마크다운 SoT, 자유 vault, 자체 뷰어`
2. **Karpathy LLM Wiki** (영감) — `에이전트 옵션, scope/provenance, log.md 작업 이력, raw/source 분리`
3. **자체 구현체** — Obsidian 의존 ❌, 4 진입점, multi-vault

LLM Wiki의 핵심 개념 (에이전트 옵션 시민, raw/ 폴더, log.md, scope 격리)은
이미 Raven에 적용되어 있음. 별도 "도입" 작업 불필요. **명시적으로 재정렬**만 함.

## 4. 다음 단계 (메모리 §next)

이 north star 재정렬 후 안전해진 작업들:
- **v0.6.38**: Lite bootstrap 프로파일화 (`--profile basic` = WELCOME.md 1장, `--profile llm-wiki` = 현재 4종). `_meta/system/features.json` 도입.
- **v0.6.39**: mode 메타데이터 강등 (코드 분기 0건 확인됨, 단순 데이터 정리). Tier 1 leak lint 옵션화 (`allow_tier1_leak`).
- **v0.6.40**: AgentScope resource scope (`allowed_paths`/`deny_paths`).
- **v0.7.0**: Karpathy LLM Wiki +α 본격 도입 가이드 (`docs/vault-patterns.md` — `raw/`, `log.md`, `_meta/agents/` convention).

## 5. 보존

- `_meta/raw/articles/karpathy-llm-wiki-2026.md` — Karpathy 원본 (불변)
- `_meta/decisions-d7-d9-multivault.md` — ADR 본문 (예/근거로 LLM Wiki 언급 OK)
- `_meta/changelog-v0.5.5~v0.6.36.md` — 역사 보존 (v0.6.31/36만 재정렬 노트 추가)
- `_meta/architecture.html`, `_meta/architecture-5layer.md` — 다이어그램 (예)
- `raven/curator/*.py` — v3 합의안 docstring (역사)