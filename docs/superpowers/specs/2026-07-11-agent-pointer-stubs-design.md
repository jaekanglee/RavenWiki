---
title: 에이전트 포인터 스텁 (AGENTS.md/CLAUDE.md/GEMINI.md/.cursorrules/.windsurfrules)
created: 2026-07-11
type: rule
audience: agent
confidence: high
---

# 에이전트 포인터 스텁 (AGENTS.md/CLAUDE.md/GEMINI.md/.cursorrules/.windsurfrules)

## BLUF

Claude Code(`CLAUDE.md`), Codex류(`AGENTS.md`), Gemini CLI(`GEMINI.md`), Cursor/Windsurf(`.cursorrules`/`.windsurfrules`)는 각자 다른 파일명을 관례적으로 자동 로드한다. vault를 여는 코딩 에이전트 도구가 무엇이든 `_meta/agents/PROJECT-WORKFLOW.md`(Tier 2 canonical 운영 지침)로 안내받도록, vault 루트에 5개의 **얇은 포인터 스텁 파일**을 자동 생성한다. 스텁은 항상 동일한 1줄 콘텐츠이며, `_meta/agents/PROJECT-WORKFLOW.md`가 존재하는 순간 자동으로 함께 존재하도록 만든다 — vault가 `basic` 프로필로 시작했다가 나중에 `raven meta sync`로 Tier 2 문서를 얻게 되는 경우까지 포함해서.

## 배경

- Raven vault는 `llm-wiki`(기본) 또는 `basic` 프로필로 생성된다. `llm-wiki`는 `_meta/agents/SCHEMA.md` + `PROJECT-WORKFLOW.md` + `log.md`를 복사하고, `basic`은 `WELCOME.md`만 복사한다 (`raven/core/vault.py: Vault.create()`, `_bootstrap_lite()`, `_bootstrap_basic()`).
- `profile`은 `.vault.json`에 저장되지 않는 **일회성 생성 파라미터**일 뿐이다. `Vault.sync_meta()`는 이미 지금도 프로필과 무관하게 3종 파일(SCHEMA/PROJECT-WORKFLOW/log.md)을 "없으면 생성" 방식으로 무조건 시도한다 — 즉 `basic` vault도 `raven meta sync` 한 번으로 이미 `llm-wiki` 상태로 전환 가능하다 (기존 동작, 이번 작업으로 새로 생기는 게 아님).
- `_bootstrap_lite()`의 `template_map`과 `sync_meta()`의 `file_map`은 완전히 동일한 3-entry dict를 각자 중복 정의하고 있고, 코드 주석이 "must match template_map in `_bootstrap_lite()`"라고 명시적으로 drift 위험을 경고하고 있다.
- lint `#19 check_guide_freshness`가 이미 SCHEMA/PROJECT-WORKFLOW의 SHA256 stamp 기반 최신성을 검증하는 유사 패턴을 갖고 있다.

## 설계

### 1. 스텁 콘텐츠 — 단일 상수 (`raven/core/vault.py`)

```python
AGENT_POINTER_STUB_FILES: tuple[str, ...] = (
    "AGENTS.md", "CLAUDE.md", "GEMINI.md", ".cursorrules", ".windsurfrules",
)

AGENT_POINTER_STUB_CONTENT = (
    "이 vault의 에이전트 운영 지침은 `_meta/agents/PROJECT-WORKFLOW.md` 참조.\n"
    "(자동 생성 파일 — 직접 편집 금지. `raven meta sync`가 매번 덮어씁니다.)\n"
)
```

5개 파일 모두 vault 루트(콘텐츠 폴더 밖, `.vault.json`과 같은 레벨)에 **완전히 동일한 콘텐츠**로 생성한다. 벤더별 톤 차이 없음 — 단일 템플릿에서 파생되므로 drift 여지가 없다.

### 2. 기존 중복 dict 통합

`_bootstrap_lite()`의 `template_map`과 `sync_meta()`의 `file_map`(SCHEMA.md/PROJECT-WORKFLOW.md/log.md, 완전히 동일한 3-entry dict)을 모듈 레벨 상수 하나로 합친다:

```python
LITE_BOOTSTRAP_FILE_MAP: dict[str, str] = {
    "_meta/agents/SCHEMA.md":            "templates/agent/SCHEMA.md",
    "_meta/agents/PROJECT-WORKFLOW.md":  "templates/agent/PROJECT-WORKFLOW.md",
    "log.md":                            "templates/log.md",
}
```

`_bootstrap_lite()`와 `sync_meta()`가 각자의 로컬 dict 대신 이 상수 하나만 참조한다. `_bootstrap_basic()`의 `WELCOME.md` 매핑은 완전히 다른 파일 집합(다른 프로필)이라 통합 대상이 아니다 — 그대로 둔다.

### 3. 스텁 생성 트리거 — profile이 아니라 "PROJECT-WORKFLOW.md 존재 여부"로 판단

**핵심 설계 결정**: profile은 vault의 영구적 상태가 아니라 생성 시점의 선택일 뿐이고, `sync_meta()`가 이미 profile 무관하게 Tier 2 파일을 채워 넣을 수 있으므로, 스텁 생성 조건도 정적 profile 플래그가 아니라 **그 순간 `_meta/agents/PROJECT-WORKFLOW.md`가 실제로 존재하는가**라는 동적 조건으로 건다.

```python
def _write_agent_pointer_stubs(path: Path) -> None:
    """PROJECT-WORKFLOW.md가 존재하면 5개 포인터 스텁을 (무조건 덮어써서) 생성.

    profile이 아니라 파일 존재 여부로 트리거 — basic→llm-wiki 전환도
    sync_meta() 재실행 한 번으로 스텁까지 같이 따라오게 하기 위함.
    """
    if not (path / "_meta" / "agents" / "PROJECT-WORKFLOW.md").exists():
        return
    for rel_target in AGENT_POINTER_STUB_FILES:
        (path / rel_target).write_text(AGENT_POINTER_STUB_CONTENT, encoding="utf-8")
```

호출 지점:
- **`_bootstrap_lite()` 끝**: PROJECT-WORKFLOW.md가 이 함수 안에서 이미 만들어졌으므로 `_write_agent_pointer_stubs(path)` 호출 시 항상 스텁 생성됨.
- **`_bootstrap_basic()`**: 호출하지 않음 (PROJECT-WORKFLOW.md 자체가 없는 프로필).
- **`sync_meta()` 끝**: `LITE_BOOTSTRAP_FILE_MAP` 복사 루프가 끝난 **직후** `_write_agent_pointer_stubs(self.root)` 호출. 이러면 원래 `basic`이었던 vault가 `sync_meta()` 실행으로 이번에 처음 PROJECT-WORKFLOW.md를 얻는 경우, **같은 호출 안에서** 스텁도 함께 생성된다.

스텁은 기존 3종 파일(SCHEMA/PROJECT-WORKFLOW/log.md)의 "존재하면 skip" 정책과 별개로 **항상 무조건 덮어쓴다** — 콘텐츠가 상수 하나뿐이라 사용자가 커스터마이징할 이유가 없고, 매번 최신 상태를 유지하는 게 이득이기 때문이다. `sync_meta()`의 `force` 파라미터는 스텁 쓰기에 영향을 주지 않는다(스텁은 force 여부와 무관하게 항상 씀).

### 4. Lint 연동 — `#19 check_guide_freshness` 확장

`raven/core/lint.py`의 `check_guide_freshness()`에 검사 추가:

- `_meta/agents/PROJECT-WORKFLOW.md`가 존재하는 vault에 한해서만 검사(존재하지 않으면 애초에 스텁도 없는 게 정상이므로 skip).
- `AGENT_POINTER_STUB_FILES` 5개 각각에 대해 "파일이 존재하는가" + "내용이 `AGENT_POINTER_STUB_CONTENT`와 정확히 일치하는가"를 확인.
- SCHEMA/PROJECT-WORKFLOW처럼 SHA256 stamp 비교가 아니라 **결정론적 문자열 비교**로 충분하다(콘텐츠가 상수 하나뿐이라 "버전이 여러 개 있을 수 있는" 문제가 없음).
- 위반 시 기존 `#19`와 동일하게 `info` 등급 1건 (silent warn, lint 통과 여부에 영향 없음).

### 5. 테스트

- `Vault.create(profile="llm-wiki")` → vault 루트에 5개 스텁 파일이 정확한 콘텐츠로 존재하는지 검증.
- `Vault.create(profile="basic")` → 5개 스텁 파일이 전혀 생성되지 않았는지 검증.
- `Vault.create(profile="basic")` 후 `sync_meta()` 호출 → PROJECT-WORKFLOW.md가 새로 생기면서 같은 호출 안에서 5개 스텁도 함께 생성되는지 검증 (basic→llm-wiki 전환 시나리오).
- 스텁 파일 내용을 수동으로 변조한 뒤 `sync_meta()` 재호출 → 항상 원래 콘텐츠로 덮어써지는지 검증(SCHEMA/PROJECT-WORKFLOW와 달리 skip되지 않음을 확인).
- `check_guide_freshness()`가 스텁 누락/변조를 감지하는지 검증.
- `LITE_BOOTSTRAP_FILE_MAP` 통합 후 기존 `_bootstrap_lite()`/`sync_meta()` 관련 테스트가 회귀 없이 통과하는지 확인.

## 영향 범위

파일 2개 수정 (`raven/core/vault.py`, `raven/core/lint.py`) + 테스트 추가. 신규 CLI/API/대시보드 표면 없음 — 기존 `vault create` / `raven meta sync` / `raven vault bootstrap`(CLI) / `POST /api/vaults/{name}/bootstrap`(API) 흐름에 얹힌다 (전부 내부적으로 `_bootstrap_lite()` 또는 `sync_meta()`를 호출). 신규 진입점 아님, ADR 불필요.

**정정 (2026-07-12)**: 최초 설계 시 "raven build 실행 시에도 트리거"라고 적었으나, 실제 코드 확인 결과 `raven build`는 `db_module.build_db()`만 호출하고 `sync_meta()`를 호출하지 않는다 (SCHEMA/PROJECT-WORKFLOW/log.md 3종도 지금까지 build가 건드린 적 없음). 이번 스텁 기능만을 위해 `raven build`의 기존 동작 범위를 넓히지 않기로 결정 — 스텁은 PROJECT-WORKFLOW.md와 동일한 생명주기(vault create + meta sync/vault bootstrap)만 따른다. 기존 vault는 `raven meta sync` 또는 `raven vault bootstrap`을 한 번 실행하면 자동으로 스텁을 얻으므로 별도 마이그레이션 스크립트는 필요 없다.
