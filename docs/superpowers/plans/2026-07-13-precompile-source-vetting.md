# 컴파일 전 소스 검증 체크리스트 + CURATION.md 와이어링 수정 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** `raven/core/templates/agent/CURATION.md`를 `raven docs show`로 접근 가능하게 와이어링하고, 그 안에 "합성 전 소스 신뢰도 판정" 체크리스트(신호 테이블 + 결정 트리)를 새 섹션으로 추가한다.

**Architecture:** (1) `raven/cli/__main__.py`의 `docs_list`/`docs_show` topic 딕셔너리에 항목 1개 추가. (2) `CURATION.md`에 새 §1(Pre-Compile Source Vetting Checklist)을 BLUF 직후에 삽입하고 기존 §1-4를 §2-5로 renumber. 두 작업 모두 기존 `LITE_BOOTSTRAP_FILE_MAP`(vault bootstrap 대상 파일 목록)에는 손대지 않는다.

**Tech Stack:** Python 3 / Typer CLI / pytest / `typer.testing.CliRunner`

## Global Constraints

- `LITE_BOOTSTRAP_FILE_MAP`(`raven/core/vault.py`)에 `CURATION.md`를 추가하지 않는다 — vault에 자동 복사되지 않아야 한다 (spec 승인 사항).
- Lite bootstrap 파일 개수 "2종(SCHEMA.md + PROJECT-WORKFLOW.md) + log.md" 불변식은 변경하지 않는다.
- 새 frontmatter 필드를 발명하지 않는다 — `status`/`confidence`/`last_verified`와 기존 lint #4/#5/#6/#7/#17/#20만 참조한다.
- CURATION.md 본문 수정 시 기존 §1-4의 실제 내용(문장)은 한 글자도 바꾸지 않는다 — 섹션 번호만 밀리고 새 섹션 하나만 추가된다.

---

### Task 1: `raven docs show agent-curation` 와이어링

**Files:**
- Modify: `raven/cli/__main__.py:1780-1816` (`docs_list()`의 `items` 리스트, `docs_show()`의 `topic_map` 딕셔너리 및 `topic` 인자 `help` 문자열)
- Test: `tests/test_docs_show_curation.py` (신규)

**Interfaces:**
- Consumes: 기존 `app` (Typer 인스턴스, `raven/cli/__main__.py`에서 import), 기존 `docs_app` 서브커맨드 그룹(`raven docs list` / `raven docs show <topic>`)
- Produces: CLI topic `"agent-curation"` → `raven.core`의 `templates/agent/CURATION.md` 리소스. Task 2가 이 파일의 본문을 수정하므로, Task 1은 파일 경로 매핑만 책임진다.

- [x] **Step 1: 실패하는 테스트 작성**

`tests/test_docs_show_curation.py` 신규 생성:

```python
"""raven docs list/show가 CURATION.md(agent-curation topic)을 노출하는지 검증.

배경: raven/core/templates/agent/CURATION.md는 작성됐지만 docs_show의
topic_map에도, vault bootstrap의 LITE_BOOTSTRAP_FILE_MAP에도 연결되지
않아 어떤 경로로도 도달 불가능한 고아 파일이었다 (2026-07-13 스펙).
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from typer.testing import CliRunner

from raven.cli.__main__ import app
from raven.core.vault import LITE_BOOTSTRAP_FILE_MAP, Vault

runner = CliRunner()


def test_docs_list_includes_agent_curation():
    result = runner.invoke(app, ["docs", "list"])
    assert result.exit_code == 0, result.stdout
    assert "agent-curation" in result.stdout


def test_docs_show_agent_curation_prints_file_content():
    result = runner.invoke(app, ["docs", "show", "agent-curation"])
    assert result.exit_code == 0, result.stdout
    assert "Vault Curation" in result.stdout


def test_docs_show_unknown_topic_lists_agent_curation_as_valid_choice():
    result = runner.invoke(app, ["docs", "show", "no-such-topic"])
    assert result.exit_code == 1
    combined = result.stdout + (result.stderr or "")
    assert "agent-curation" in combined


def test_curation_not_in_lite_bootstrap_file_map():
    """CURATION.md는 docs_show 전용 — vault에 자동 복사되면 안 된다."""
    assert "_meta/agents/CURATION.md" not in LITE_BOOTSTRAP_FILE_MAP


def test_vault_create_does_not_copy_curation_md(monkeypatch):
    vaults_root = Path(tempfile.mkdtemp(prefix="raven-curation-vaults-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-curation-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(vaults_root))
    try:
        v = Vault.create("curation-test", target_root / "curation-test", bootstrap=True)
        assert not (v.root / "_meta" / "agents" / "CURATION.md").exists()
    finally:
        shutil.rmtree(vaults_root, ignore_errors=True)
        shutil.rmtree(target_root, ignore_errors=True)
```

- [x] **Step 2: 테스트 실행해서 실패 확인**

Run: `scripts/.venv/bin/python -m pytest tests/test_docs_show_curation.py -v`
Expected: `test_docs_list_includes_agent_curation`, `test_docs_show_agent_curation_prints_file_content`, `test_docs_show_unknown_topic_lists_agent_curation_as_valid_choice` 3개는 FAIL (topic 없음). `test_curation_not_in_lite_bootstrap_file_map`, `test_vault_create_does_not_copy_curation_md` 2개는 이미 PASS (아직 아무것도 안 건드렸으므로).

- [x] **Step 3: `docs_list()`의 `items`에 항목 추가**

`raven/cli/__main__.py`에서 다음 블록을 찾는다:

```python
    items = [
        ("operations", "templates/system/OPERATIONS.md", "Raven 빌드/lint/마이그레이션 운영"),
        ("agent-readme", "templates/agent/README.md", "에이전트 행동 지침 (진입점)"),
        ("agent-tools", "templates/agent/TOOLS.md", "에이전트 인터페이스 + scope"),
        ("agent-workflow", "templates/agent/WORKFLOW.md", "트리거 / Phase 게이트"),
        ("agent-safety", "templates/agent/SAFETY.md", "에이전트 절대 금지"),
        ("policy", "templates/wikisys-policy.md", "raven 운영 정책"),
    ]
```

다음으로 교체한다 (`agent-safety` 다음, `policy` 앞에 삽입):

```python
    items = [
        ("operations", "templates/system/OPERATIONS.md", "Raven 빌드/lint/마이그레이션 운영"),
        ("agent-readme", "templates/agent/README.md", "에이전트 행동 지침 (진입점)"),
        ("agent-tools", "templates/agent/TOOLS.md", "에이전트 인터페이스 + scope"),
        ("agent-workflow", "templates/agent/WORKFLOW.md", "트리거 / Phase 게이트"),
        ("agent-safety", "templates/agent/SAFETY.md", "에이전트 절대 금지"),
        ("agent-curation", "templates/agent/CURATION.md", "에이전트 지식 정제 + 컴파일 전 소스 검증 기준"),
        ("policy", "templates/wikisys-policy.md", "raven 운영 정책"),
    ]
```

- [x] **Step 4: `docs_show()`의 `topic_map` 및 `help` 문자열에 항목 추가**

다음 블록을 찾는다:

```python
def docs_show(
    topic: str = typer.Argument(
        ...,
        help="operations | agent-readme | agent-tools | agent-workflow | agent-safety | policy",
    ),
) -> None:
    """Print a Tier 1 doc to stdout. Never writes to disk."""
    from importlib import resources

    topic_map = {
        "operations": "templates/system/OPERATIONS.md",
        "agent-readme": "templates/agent/README.md",
        "agent-tools": "templates/agent/TOOLS.md",
        "agent-workflow": "templates/agent/WORKFLOW.md",
        "agent-safety": "templates/agent/SAFETY.md",
        "policy": "templates/wikisys-policy.md",
    }
```

다음으로 교체한다:

```python
def docs_show(
    topic: str = typer.Argument(
        ...,
        help="operations | agent-readme | agent-tools | agent-workflow | agent-safety | agent-curation | policy",
    ),
) -> None:
    """Print a Tier 1 doc to stdout. Never writes to disk."""
    from importlib import resources

    topic_map = {
        "operations": "templates/system/OPERATIONS.md",
        "agent-readme": "templates/agent/README.md",
        "agent-tools": "templates/agent/TOOLS.md",
        "agent-workflow": "templates/agent/WORKFLOW.md",
        "agent-safety": "templates/agent/SAFETY.md",
        "agent-curation": "templates/agent/CURATION.md",
        "policy": "templates/wikisys-policy.md",
    }
```

- [x] **Step 5: 테스트 실행해서 통과 확인**

Run: `scripts/.venv/bin/python -m pytest tests/test_docs_show_curation.py -v`
Expected: 5개 전부 PASS.

- [x] **Step 6: 커밋**

```bash
git add raven/cli/__main__.py tests/test_docs_show_curation.py
git commit -m "fix(cli): raven docs show가 CURATION.md(agent-curation)를 노출하도록 와이어링

CURATION.md는 작성됐지만 docs_show topic_map에도 vault bootstrap file map에도
연결되지 않아 고아 상태였다. docs_show에만 연결하고 bootstrap 대상에는 넣지 않는다
(Lite bootstrap 2종+log.md 불변식 유지)."
```

---

### Task 2: CURATION.md에 Pre-Compile Source Vetting Checklist 섹션 추가

**Files:**
- Modify: `raven/core/templates/agent/CURATION.md` (전체 83줄 — frontmatter `updated` 갱신, BLUF 직후 신규 §1 삽입, 기존 §1-4 → §2-5 renumber)
- Test: `tests/test_curation_precompile_vetting.py` (신규)

**Interfaces:**
- Consumes: Task 1에서 이미 통과하는 `raven docs show agent-curation` (이 태스크는 파일 내용만 바꾸므로 Task 1의 CLI 와이어링에 의존하지 않고 독립적으로도 테스트 가능 — 파일을 직접 `read_text()`)
- Produces: 이후 어떤 태스크도 이 섹션 번호를 참조하지 않음 (본 계획의 마지막 태스크)

- [x] **Step 1: 실패하는 테스트 작성**

`tests/test_curation_precompile_vetting.py` 신규 생성:

```python
"""CURATION.md의 Pre-Compile Source Vetting Checklist 섹션 회귀 가드.

기존 §1-4 내용은 문장 단위로 보존되어야 하고(번호만 밀림), 새 §1은
frontmatter 신호(status/confidence/lint 번호)만으로 판정 가능해야 한다
(2026-07-13 스펙 — 새 frontmatter 필드 발명 금지).
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURATION = ROOT / "raven" / "core" / "templates" / "agent" / "CURATION.md"


def _content() -> str:
    return CURATION.read_text(encoding="utf-8")


def test_new_precompile_section_exists_as_section_1():
    content = _content()
    assert "## 1. 컴파일 전 소스 검증 체크리스트 (Pre-Compile Source Vetting)" in content


def test_precompile_section_uses_existing_signals_only():
    content = _content()
    for signal in (
        "status: contested",
        "status: archived",
        "confidence: low",
        "lint #7",
        "lint #4",
        "lint #20",
        "lint #17",
    ):
        assert signal in content, f"신호 '{signal}'이 체크리스트에 없음"


def test_precompile_section_defines_three_verdicts():
    content = _content()
    assert "⛔ 인용 금지" in content
    assert "⚠️ 캐비어 달고 인용" in content
    assert "✅ 그대로 인용" in content


def test_existing_sections_preserved_and_renumbered():
    content = _content()
    assert "## 2. 큐레이션 및 클렌징의 3대 대원칙" in content
    assert "## 3. 린트 규칙별 세부 클렌징 및 조치 가이드" in content
    assert "## 4. 변증법적 갈등 해소 (Dialectic Contradiction Resolver)" in content
    assert "## 5. 지식 계보 및 기원(Provenance) 보존" in content
    # 옛 번호는 더 이상 헤딩으로 존재하면 안 됨
    assert "## 1. 큐레이션 및 클렌징의 3대 대원칙" not in content
    assert "## 3. 변증법적 갈등 해소" not in content


def test_existing_body_text_untouched():
    content = _content()
    # §2(구 §1) 대원칙 3개 문구가 그대로 남아있는지
    assert "원문 보존 + 증분 누적 (Layer 1 존중)" in content
    assert "플레이스홀더(TBD) 박멸" in content
    assert "맥락적 연결 (Semantic Wikilink)" in content
    # §4(구 §3) 변증법 프로토콜 3단계가 그대로 남아있는지
    assert "상호 contested 처리" in content
    assert "지시 문서(Issue) 발의" in content
    assert "인간 판정 대기" in content
```

- [x] **Step 2: 테스트 실행해서 실패 확인**

Run: `scripts/.venv/bin/python -m pytest tests/test_curation_precompile_vetting.py -v`
Expected: `test_new_precompile_section_exists_as_section_1`, `test_precompile_section_uses_existing_signals_only`, `test_precompile_section_defines_three_verdicts`, `test_existing_sections_preserved_and_renumbered`의 renumber 관련 assertion들은 FAIL. `test_existing_body_text_untouched`만 PASS (아직 원문 그대로이므로).

- [x] **Step 3: frontmatter `updated` 날짜 갱신**

`raven/core/templates/agent/CURATION.md` 상단에서:

```yaml
created: 2026-07-08
updated: 2026-07-08
```

를 다음으로 교체:

```yaml
created: 2026-07-08
updated: 2026-07-13
```

- [x] **Step 4: BLUF 직후에 신규 §1 삽입 + 옛 §1 헤딩을 §2로 변경**

파일에서 다음 블록을 찾는다:

```markdown
> **BLUF**: 에이전트가 볼트의 지식 신호 대 잡음비(SNR)를 높이기 위해 주기적으로 수행해야 하는 큐레이션 및 클렌징의 구체적 조치 기준과 절차를 정의합니다.

---

## 1. 큐레이션 및 클렌징의 3대 대원칙
```

다음으로 교체한다 (신규 섹션 전체 삽입 + 옛 섹션 헤딩만 `## 2.`로 변경, 그 아래 본문은 그대로 둔다):

```markdown
> **BLUF**: 에이전트가 볼트의 지식 신호 대 잡음비(SNR)를 높이기 위해 주기적으로 수행해야 하는 큐레이션 및 클렌징의 구체적 조치 기준과 절차를 정의합니다.

---

## 1. 컴파일 전 소스 검증 체크리스트 (Pre-Compile Source Vetting)

> 볼트에 쌓인 기존 문서(사람 작성 + 에이전트 작성 포함)를 참고해 새 문서를 합성(synthesis)하기 **전에**, 소스로 쓰려는 각 후보 문서가 그대로 인용해도 될 만큼 신뢰할 수 있는지 먼저 판정합니다. 판정에 새 frontmatter 필드는 필요 없습니다 — 이미 `SCHEMA.md`에 있는 신호만 조합합니다.

### 1.1 신호 테이블

| 신호 | 확인 방법 | 의미 |
|---|---|---|
| `status: contested` | frontmatter | 모순 미해결 |
| `status: archived` | frontmatter | 의도적 폐기 |
| `confidence: low` | frontmatter | 단일 출처/미검증 |
| stale | `status: stale` 또는 lint #7 (`updated` > 90일) | 사실이 바뀌었을 가능성 |
| orphan | lint #4 (inbound wikilink 0) | 교차검증된 적 없음 |
| placeholder | lint #20 | 소스 자체가 미완성 |
| duplicate-title 미해결 | lint #17 | 어느 쪽이 정본인지 아직 불명 |

### 1.2 판정 결정 트리

합성에 쓰려는 소스 후보마다 아래 순서로 평가합니다:

1. `status: contested` (§4 변증법적 갈등 해소 대상) → **⛔ 인용 금지**. 먼저 §4 절차로 모순을 해소하거나 사람 판정을 기다립니다.
2. `status: archived` → **⛔ 인용 금지**. 의도적으로 퇴장시킨 지식이므로, 필요하면 `archive_reason`을 확인하고 복원 여부는 사람에게 문의합니다.
3. placeholder(lint #20) 존재 또는 duplicate-title(lint #17) 미해결 → **⛔ 인용 금지**. 소스 자체가 아직 컴파일되지 않은 상태이므로 §3 절차로 소스부터 정리한 뒤 재시도합니다.
4. 아래 "약한 신호" 중 **2개 이상 동시 발생** → **⛔ 인용 금지** (누적 시 근거 부족):
   - `confidence: low`
   - stale (`status: stale` 또는 lint #7)
   - orphan (lint #4)
5. 약한 신호가 **정확히 1개** → **⚠️ 캐비어 달고 인용**:
   - 새로 쓰는 문서의 `confidence`는 인용한 소스들 중 **최솟값을 상속**합니다.
   - 본문에 "근거가 약함(사유)"을 한 문장으로 명시합니다. 예: "이 결론은 90일 이상 미검증된 소스에 기반함."
6. 위 어느 것도 해당하지 않음 (status: current, confidence: medium 이상, 최근 검증됨, inbound backlink 존재) → **✅ 그대로 인용**.

### 1.3 다중 소스 규칙

여러 소스를 종합해 하나의 새 문서를 합성할 때:
- ⛔ 판정을 받은 소스는 배제하고, 남은 ✅/⚠️ 소스만으로 합성을 진행합니다.
- 배제 후 남는 근거가 결론을 지지하기에 불충분해지면(예: 핵심 주장 하나가 배제된 소스에만 있었던 경우), 억지로 합성을 강행하지 않고 사람에게 "이 주제는 아직 컴파일 근거가 부족하다"고 보고합니다.

---

## 2. 큐레이션 및 클렌징의 3대 대원칙
```

- [x] **Step 5: 옛 §2/§3/§4 헤딩을 §3/§4/§5로 변경**

다음 세 개의 헤딩 라인을 각각 찾아 교체한다 (본문은 그대로 두고 헤딩 텍스트만 변경):

`## 2. 린트 규칙별 세부 클렌징 및 조치 가이드` → `## 3. 린트 규칙별 세부 클렌징 및 조치 가이드`

`## 3. 변증법적 갈등 해소 (Dialectic Contradiction Resolver)` → `## 4. 변증법적 갈등 해소 (Dialectic Contradiction Resolver)`

`## 4. 지식 계보 및 기원(Provenance) 보존` → `## 5. 지식 계보 및 기원(Provenance) 보존`

- [x] **Step 6: 테스트 실행해서 통과 확인**

Run: `scripts/.venv/bin/python -m pytest tests/test_curation_precompile_vetting.py tests/test_docs_show_curation.py -v`
Expected: 두 파일의 테스트 전부 PASS (10개).

- [x] **Step 7: 전체 회귀 테스트 실행**

Run: `scripts/.venv/bin/python -m pytest tests/ -q`
Expected: 기존 테스트 스위트 전부 PASS, 신규 10개 포함해 총 개수 증가. 실패 시 원인 파악 후 수정.

- [x] **Step 8: 커밋**

```bash
git add raven/core/templates/agent/CURATION.md tests/test_curation_precompile_vetting.py
git commit -m "feat(curation): 컴파일 전 소스 검증 체크리스트(Pre-Compile Source Vetting) 추가

기존 status/confidence/lint 신호를 조합해 합성 전 소스 신뢰도를
'그대로 인용/캐비어 달고 인용/인용 금지' 3단계로 판정하는 결정 트리를
CURATION.md 새 §1로 추가. 기존 §1-4는 §2-5로 renumber (본문 내용 불변)."
```

---

## 완료 조건

- `raven docs show agent-curation`이 CURATION.md 전체(신규 §1 포함)를 출력한다.
- `raven docs list` 출력에 `agent-curation`이 나열된다.
- `raven vault create` 이후에도 vault 안에 `_meta/agents/CURATION.md`가 생성되지 않는다 (bootstrap 비대상 확정).
- `tests/` 전체 스위트가 회귀 없이 통과한다.
