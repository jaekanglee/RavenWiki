"""REST 표면의 충돌 표면화 — Theme A.2 (계획 §2).

MCP write는 이미 `_lock_holder` / `_advisory_conflict`를 응답에 붙이지만 REST
`PUT /pages/{slug}` 응답은 `{ok, vault, slug, created}`뿐이었다. Dashboard가
"남이 먼저 저장했다"를 알 수 없다는 뜻이다. 여기서는 GET이 토큰을 주고,
PUT이 낡은 토큰을 409로 거부하며, 락 보유자를 MCP와 같은 필드명으로 노출하는지
검증한다.
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
from raven.core.vault import Vault


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def vault(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-pre-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-pre-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    v = Vault.create("pre-test", target_root / "pre-test")
    yield v
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def seed(client, vault: Vault, slug: str, content: str) -> None:
    resp = client.post(
        f"/api/vaults/{vault.meta.name}/pages",
        json={"slug": slug, "title": "Hello", "content": content, "type": "concept"},
    )
    assert resp.status_code == 200, resp.text


def test_get_page_returns_precondition_token(client, vault):
    """GET이 토큰을 주지 않으면 클라이언트는 검사를 시작할 수조차 없다."""
    seed(client, vault, "content/hello", "base body")
    body = client.get(f"/api/vaults/{vault.meta.name}/pages/content/hello").json()
    assert body["ok"] is True
    assert body["precondition"]


def test_put_with_fresh_precondition_succeeds(client, vault):
    """최신 토큰으로는 정상 저장 — 검사가 정상 편집을 막지 않는다."""
    seed(client, vault, "content/hello", "base body")
    token = client.get(f"/api/vaults/{vault.meta.name}/pages/content/hello").json()[
        "precondition"
    ]
    resp = client.put(
        f"/api/vaults/{vault.meta.name}/pages/content/hello",
        json={"content": "edited body", "precondition": token},
    )
    assert resp.status_code == 200, resp.text
    assert "edited body" in (vault.root / "content" / "hello.md").read_text()


def test_put_with_stale_precondition_returns_409_and_keeps_other_edit(client, vault):
    """A가 읽은 뒤 B가 저장하면 A의 PUT은 409이고 B의 내용이 남는다."""
    seed(client, vault, "content/hello", "base body")
    name = vault.meta.name
    token_a = client.get(f"/api/vaults/{name}/pages/content/hello").json()["precondition"]

    assert (
        client.put(
            f"/api/vaults/{name}/pages/content/hello",
            json={"content": "B wrote a distinctly longer body here"},
        ).status_code
        == 200
    )

    resp = client.put(
        f"/api/vaults/{name}/pages/content/hello",
        json={"content": "A overwrote", "precondition": token_a},
    )
    assert resp.status_code == 409, resp.text

    text = (vault.root / "content" / "hello.md").read_text()
    assert "B wrote a distinctly longer body here" in text
    assert "A overwrote" not in text


def test_put_without_precondition_keeps_legacy_behavior(client, vault):
    """하위 호환: 토큰 없는 PUT은 pre-v0.7.178처럼 그대로 덮어쓴다."""
    seed(client, vault, "content/hello", "base body")
    resp = client.put(
        f"/api/vaults/{vault.meta.name}/pages/content/hello",
        json={"content": "legacy overwrite"},
    )
    assert resp.status_code == 200, resp.text
    assert "legacy overwrite" in (vault.root / "content" / "hello.md").read_text()


def test_put_surfaces_foreign_lock_holder_like_mcp(client, vault):
    """REST도 MCP와 같은 `_lock_holder` 이름으로 충돌을 노출해야 한다."""
    from raven.mcp.tools import acquire_lock

    seed(client, vault, "content/hello", "base body")
    acquire_lock(vault.root, "content/hello", actor="other-agent", ttl_seconds=60)

    resp = client.put(
        f"/api/vaults/{vault.meta.name}/pages/content/hello",
        json={"content": "human edit while agent holds lock"},
    )
    assert resp.status_code == 200, resp.text
    holder = resp.json().get("_lock_holder")
    assert holder is not None
    assert holder["actor"] == "other-agent"
    assert holder["_advisory_conflict"] is True
