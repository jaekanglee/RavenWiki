"""Theme B — 태세/열화 정직화 (계획 docs/superpowers/plans/2026-07-29-raven-concept-reinforcement.md §3).

두 가지 무성 거짓말을 잡는다:

1. `/api/system/info`가 `allow_all_cors: True`를 하드코딩해, 보안 태세를 알려주는
   유일한 endpoint가 실제 CORS 정책과 무관한 값을 보고했다.
2. `sentence-transformers` 부재 시 `LocalEmbeddingEngine`이 sha256 mock 벡터로
   조용히 fallback하면서도 랭킹된 결과를 정상처럼 반환했다 — 의미 검색이
   무의미해진 사실이 어디에도 드러나지 않았다.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from raven.api import server as server_module
from raven.core import hybrid_search as hs_module
from raven.core.vault import Vault


@pytest.fixture
def client():
    return TestClient(server_module.app)


@pytest.fixture
def vault(monkeypatch):
    reg_root = Path(tempfile.mkdtemp(prefix="raven-deg-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-deg-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    v = Vault.create("deg-test", target_root / "deg-test")
    yield v
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


def test_system_info_reports_actual_cors_policy(client, monkeypatch):
    """보고값이 실제 정책을 따라가야 한다 — 하드코딩 True는 태세를 숨긴다."""
    monkeypatch.setattr(server_module, "_allow_all_cors", False)
    assert client.get("/api/system/info").json()["allow_all_cors"] is False

    monkeypatch.setattr(server_module, "_allow_all_cors", True)
    assert client.get("/api/system/info").json()["allow_all_cors"] is True


def test_system_info_reports_actual_bind_host(client, monkeypatch):
    """실제로 바인딩된 호스트를 보고해야 한다 — env 기본값 추측은 거짓일 수 있다."""
    monkeypatch.setenv("RAVEN_BOUND_HOST", "100.64.1.2")
    assert client.get("/api/system/info").json()["bind_host"] == "100.64.1.2"


def test_embedding_health_marks_mock_as_degraded(monkeypatch):
    """모델이 없으면 degraded=True, 있으면 False. 이 구분이 없으면 아래 표면들이 거짓말한다."""
    monkeypatch.setattr(hs_module.LocalEmbeddingEngine, "_lazy_init", lambda self: None)
    health = hs_module.embedding_health()
    assert health["degraded"] is True
    assert health["reason"]


def test_hybrid_search_endpoint_surfaces_degraded_embedding(client, vault, monkeypatch):
    """검색 응답이 열화 사실을 실어야 한다 — 결과만 주면 사용자는 알 수 없다."""
    monkeypatch.setattr(hs_module.LocalEmbeddingEngine, "_lazy_init", lambda self: None)
    body = client.get(
        f"/api/vaults/{vault.meta.name}/hybrid-search", params={"query": "anything"}
    ).json()
    assert body["ok"] is True
    assert body["embedding"]["degraded"] is True


def test_rag_endpoint_surfaces_degraded_embedding(client, vault, monkeypatch):
    """RAG는 검색 위에 서 있으므로 같은 열화를 물려받아 노출해야 한다."""
    monkeypatch.setattr(hs_module.LocalEmbeddingEngine, "_lazy_init", lambda self: None)
    body = client.get(
        f"/api/vaults/{vault.meta.name}/rag/query", params={"query": "anything"}
    ).json()
    assert body["embedding"]["degraded"] is True

def test_system_info_reports_actual_bound_port(client, monkeypatch):
    """실제 바인딩된 포트를 보고해야 한다 — QA에서 :8799 구동 중 8765를 보고했다."""
    monkeypatch.setenv("RAVEN_BOUND_PORT", "8799")
    assert client.get("/api/system/info").json()["port"] == 8799
