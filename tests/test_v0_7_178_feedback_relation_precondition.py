"""피드백·관계 write도 precondition을 받는다 — Theme A 후속 (momus 라운드 2 blocker 1·2).

피드백 3종(추가/수정/삭제)과 관계 2종(추가/제거)은 모두 페이지를 읽어 본문이나
frontmatter를 재구성한 뒤 다시 쓴다 — 본문 편집과 동일한 read-modify-write 위험이다.
토큰 경로가 없으면 그 사이에 들어온 저장은 조용히 사라진다.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.api.server import app
from raven.core.contracts import page_precondition, write_page
from raven.core.vault import Vault
from raven.mcp.tools import VaultContext, WRITE
from raven.mcp.tools.write import wiki_relation_add, wiki_relation_remove

BASE_BODY = "base body paragraph long enough to stay comparable across writes"
INTERVENING = BASE_BODY + " plus another writer's appended sentence"


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def vault(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-fbrel-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-fbrel-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    v = Vault.create("fbrel", target_root / "fbrel")
    yield v
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def seed(vault: Vault, slug: str = "content/hello", body: str = BASE_BODY) -> None:
    write_page(vault, slug, body, title="Hello", type="concept", normalize=False)


def token(vault: Vault, slug: str = "content/hello") -> str:
    return page_precondition(vault, slug, normalize=False)


def page_text(vault: Vault, slug: str = "content/hello") -> str:
    return (vault.root / f"{slug}.md").read_text(encoding="utf-8")


def test_add_feedback_without_precondition_keeps_legacy_behavior(client, vault):
    """토큰 없는 피드백 추가는 기존 동작 그대로."""
    seed(vault)
    resp = client.post(
        f"/api/vaults/{vault.meta.name}/pages/content/hello/feedback",
        json={"feedback": "please clarify section 2", "actor": "user"},
    )
    assert resp.status_code == 200, resp.text
    assert "please clarify section 2" in page_text(vault)


def test_add_feedback_with_stale_precondition_returns_409(client, vault):
    """내가 읽은 뒤 남이 본문을 바꿨으면 피드백 추가는 거부되고 그 본문이 남는다."""
    seed(vault)
    stale = token(vault)
    write_page(vault, "content/hello", INTERVENING, title="Hello", normalize=False)

    resp = client.post(
        f"/api/vaults/{vault.meta.name}/pages/content/hello/feedback",
        json={"feedback": "lost feedback", "actor": "user", "precondition": stale},
    )
    assert resp.status_code == 409, resp.text

    text = page_text(vault)
    assert "plus another writer's appended sentence" in text
    assert "lost feedback" not in text


def test_update_feedback_with_stale_precondition_returns_409(client, vault):
    """피드백 수정도 같은 규칙을 따른다."""
    seed(vault)
    name = vault.meta.name
    client.post(
        f"/api/vaults/{name}/pages/content/hello/feedback",
        json={"feedback": "original comment", "actor": "user"},
    )
    stale = token(vault)
    write_page(
        vault,
        "content/hello",
        page_text(vault).split("---", 2)[-1] + "\n\nanother writer appended this line",
        title="Hello",
        normalize=False,
    )

    resp = client.put(
        f"/api/vaults/{name}/feedback/0",
        params={"slug": "content/hello"},
        json={"feedback": "edited comment", "precondition": stale},
    )
    assert resp.status_code == 409, resp.text
    assert "edited comment" not in page_text(vault)


def test_delete_feedback_with_stale_precondition_returns_409(client, vault):
    """피드백 삭제도 같은 규칙을 따른다 — 남의 편집을 되돌리지 않는다."""
    seed(vault)
    name = vault.meta.name
    client.post(
        f"/api/vaults/{name}/pages/content/hello/feedback",
        json={"feedback": "keep me", "actor": "user"},
    )
    stale = token(vault)
    write_page(
        vault,
        "content/hello",
        page_text(vault).split("---", 2)[-1] + "\n\nanother writer appended this line",
        title="Hello",
        normalize=False,
    )

    resp = client.delete(
        f"/api/vaults/{name}/feedback/0",
        params={"slug": "content/hello", "precondition": stale},
    )
    assert resp.status_code == 409, resp.text
    assert "keep me" in page_text(vault)


def test_relation_add_endpoint_with_stale_precondition_returns_409(client, vault):
    """관계 추가는 source 페이지 frontmatter를 재구성해 쓰므로 같은 위험을 갖는다."""
    seed(vault)
    seed(vault, "content/target", BASE_BODY)
    name = vault.meta.name
    stale = token(vault)
    write_page(vault, "content/hello", INTERVENING, title="Hello", normalize=False)

    resp = client.post(
        f"/api/vaults/{name}/relations",
        json={
            "source_slug": "content/hello",
            "target_slug": "content/target",
            "relation_type": "related",
            "evidence": ["both discuss the same topic"],
            "reason": "manual link",
            "actor": "user",
            "precondition": stale,
        },
    )
    assert resp.status_code == 409, resp.text
    assert "plus another writer's appended sentence" in page_text(vault)


def test_mcp_relation_add_with_stale_precondition_is_rejected(vault):
    """MCP 관계 추가도 토큰을 받아야 한다."""
    seed(vault)
    seed(vault, "content/target", BASE_BODY)
    stale = token(vault)
    write_page(vault, "content/hello", INTERVENING, title="Hello", normalize=False)

    result = wiki_relation_add(
        source_slug="content/hello",
        target_slug="content/target",
        relation_type="related",
        evidence=["shared topic"],
        reason="manual link",
        ctx=VaultContext(vault=vault.root, mode=WRITE),
        actor="agent-a",
        precondition=stale,
    )
    assert result.get("ok") is False, result
    assert result.get("error") == "stale_precondition"


def test_mcp_relation_remove_with_stale_precondition_is_rejected(vault):
    """MCP 관계 제거도 토큰을 받아야 한다."""
    seed(vault)
    seed(vault, "content/target", BASE_BODY)
    ctx = VaultContext(vault=vault.root, mode=WRITE)
    added = wiki_relation_add(
        source_slug="content/hello",
        target_slug="content/target",
        relation_type="related",
        evidence=["shared topic"],
        reason="manual link",
        ctx=ctx,
        actor="agent-a",
    )
    assert added.get("ok") is True, added

    stale = token(vault)
    write_page(vault, "content/hello", INTERVENING, title="Hello", normalize=False)

    result = wiki_relation_remove(
        source_slug="content/hello",
        target_slug="content/target",
        relation_type="related",
        ctx=ctx,
        actor="agent-a",
        precondition=stale,
    )
    assert result.get("ok") is False, result
    assert result.get("error") == "stale_precondition"


def test_relation_add_with_fresh_precondition_succeeds(client, vault):
    """최신 토큰이면 관계 추가가 정상 동작한다."""
    seed(vault)
    seed(vault, "content/target", BASE_BODY)
    resp = client.post(
        f"/api/vaults/{vault.meta.name}/relations",
        json={
            "source_slug": "content/hello",
            "target_slug": "content/target",
            "relation_type": "related",
            "evidence": ["both discuss the same topic"],
            "reason": "manual link",
            "actor": "user",
            "precondition": token(vault),
        },
    )
    assert resp.status_code == 200, resp.text
    assert "content/target" in page_text(vault)
