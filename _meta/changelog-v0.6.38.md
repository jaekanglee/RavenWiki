# raven v0.6.38 — Lite bootstrap 프로파일화 (basic | llm-wiki)

> **핵심**: 사용자 north star (v0.6.37) 적용 — "vault 자유, 정책 강제 ❌".
> `raven vault create`에 `--profile` 옵션 도입. **basic** = Obsidian-style 사람 1차 (WELCOME.md 1장만), **llm-wiki** = 현재 Lite bootstrap (4종). LLM Wiki 패턴은 더 이상 강제되지 않음 — 사용자 선택.

릴리스 일자: 2026-06-30
이전: v0.6.37 (North Star 재정렬)

---

## 한 줄 요약

Lite bootstrap(4종 강제 복사)을 프로파일화:
- `--profile basic` (신규 권장 기본값): Obsidian-style 사람 1차, `content/` + `_meta/` + `WELCOME.md` 1장만
- `--profile llm-wiki` (v0.6.37 호환 기본값): 기존 Lite bootstrap (SCHEMA + RULES + AGENTS + log.md)

신규: `WELCOME.md` 템플릿 (사람 1차 친화적 안내), `_bootstrap_basic()` 메서드, CLI/API `--profile` 옵션, 회귀 가드 8개.

## 1. 변경 사항

### 1-1. `raven/core/templates/system/WELCOME.md` (신규)

사람 1차 친화적 welcome 가이드. 3가지 핵심:
1. 아무 폴더에 마크다운 작성 시작
2. Dashboard 띄우기 (`python -m raven.api` + `dashboard`)
3. (선택) LLM Wiki 패턴 활성화: `_meta/system/features.json` 생성

→ 사용자가 즉시 무얼 해야 할지 압니다 (정책 강제 ❌).

### 1-2. `raven/core/vault.py` 프로파일화

- `_BASIC_BOOTSTRAP_FILES` 상수 추가 (WELCOME.md 1개)
- `_bootstrap_basic()` 클래스 메서드 신규 — basic profile 부트스트랩
- `Vault.create()` 에 `profile: str = "llm-wiki"` 파라미터 추가 (기본값 = 후방 호환)
- `profile == "basic"`이면 `_bootstrap_basic()` 호출 + log.md 자동 append skip

### 1-3. `raven/cli/__main__.py` CLI 옵션

```bash
raven vault create <name> <path> --profile basic     # 사람 1차 Obsidian-style
raven vault create <name> <path> --profile llm-wiki  # v0.6.37 호환 (Lite 4종)
raven vault create <name> <path> --no-bootstrap      # 기존 폴더 등록
```

잘못된 profile은 즉시 거부 (`❌ invalid profile: ...`).

### 1-4. `tests/test_basic_profile_bootstrap.py` (신규, 8 tests)

회귀 가드:
1. WELCOME.md 템플릿 존재
2. WELCOME.md human-first 메시지 (Obsidian + "you decide")
3. `_bootstrap_basic()` 메서드 존재
4. `_BASIC_BOOTSTRAP_FILES` 상수 정의
5. `Vault.create()` profile 파라미터
6. CLI `--profile` 옵션 존재
7. CLI profile 검증 (invalid 거부)
8. basic profile에서 log.md append skip

## 2. 검증

| 항목 | 결과 |
|---|---|
| pytest | **434 passed, 1 skipped** (v0.6.37: 426 → v0.6.38: 434, +8) |
| test_basic_profile_bootstrap.py | **8 passed** (신규) |
| 기존 vault 호환 | ✅ `--profile` 미지정 시 `llm-wiki` 기본 = v0.6.37과 동일 동작 |
| Runtime 영향 | vault.create() 시그니처 확장만, 기존 호출자 100% 호환 |

## 3. 의도

v0.6.37 재정렬 ("Raven = Obsidian 대체, LLM Wiki = +α 옵션")을 코드 레벨에서 실현.

**Before (v0.6.37)**:
- 새 vault = 무조건 4종 Lite bootstrap (SCHEMA/RULES/AGENTS/log.md 강제 복사)
- "사람이 그냥 메모장처럼 쓰고 싶은데 SCHEMA.md가 왜 있지?" 문제

**After (v0.6.38)**:
- 새 vault = `--profile basic` 또는 `--profile llm-wiki` 명시
- **basic**: WELCOME.md 1장, 사람 1차 친화적
- **llm-wiki**: 기존 4종 (v0.6.37 호환)
- LLM Wiki 패턴을 켜고 싶으면 → `_meta/system/features.json` 생성 (다음 phase)

## 4. 사용자 시나리오

### 시나리오 A — 신규 사용자 (Obsidian식 메모장)
```bash
raven vault create personal ~/Raven/personal --profile basic
# → WELCOME.md + content/ + _meta/ 만 생성
# → SCHEMA/RULES/AGENTS 안 박힘
# → log.md 안 박힘 (사람 자유)
```

### 시나리오 B — LLM Wiki 패턴 도입
```bash
raven vault create harumoa ~/Raven/harumoa --profile llm-wiki
# → 기존 v0.6.37과 동일 (4종 Lite bootstrap)
```

### 시나리오 C — basic으로 만들고 나중에 LLM Wiki 켜기
```bash
raven vault create draft ~/Raven/draft --profile basic
# 나중에:
cat > ~/Raven/draft/_meta/system/features.json << EOF
{ "llm_wiki": true }
EOF
# (v0.6.39에서 features.json 도입 예정 — 현재는 placeholder)
```

## 5. 다음 단계

- **v0.6.39**: mode 메타데이터 강등 (코드 분기 0건 확인됨, 단순 데이터 정리) + Tier 1 leak lint 옵션화 (`allow_tier1_leak`)
- **v0.6.40**: AgentScope resource scope (`allowed_paths` / `deny_paths`)
- **v0.7.0**: `docs/vault-patterns.md` — Karpathy LLM Wiki +α 본격 도입 가이드

## 6. 호환성

- ✅ **v0.6.37 사용자**: `--profile` 미지정 시 `llm-wiki` 기본값 → 기존 vault과 동일
- ✅ **기존 vault (raven-dev 등)**: 영향 없음 (vault create만 변경, 기존 vault 변경 ❌)
- ✅ **CLI 사용자**: `--profile basic`만 추가 옵션, 기존 사용법 그대로
- ⚠️ **API 서버**: `Vault.create()` 호출자가 profile 인자 안 줘도 OK (기본값 = llm-wiki)