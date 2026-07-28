"""Tests for Multi-Host Vault Repository & Register endpoints."""
from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from raven.api.server import app
from raven.core.registry import registry

client = TestClient(app)


def test_register_vault_endpoint():
    registry().remove("test-registered-vault")
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "my-existing-vault"
            tmp_path.mkdir(parents=True, exist_ok=True)
            (tmp_path / "content").mkdir(exist_ok=True)

            res = client.post(
                "/api/vaults/register",
                json={
                    "name": "test-registered-vault",
                    "path": str(tmp_path),
                    "mode": "personal",
                    "owner": "user",
                },
            )
            assert res.status_code == 200
            data = res.json()
            assert data["ok"] is True
            assert data["vault"]["name"] == "test-registered-vault"
            assert registry().get("test-registered-vault") is not None
    finally:
        registry().remove("test-registered-vault")


def test_register_vault_nonexistent_directory():
    res = client.post(
        "/api/vaults/register",
        json={
            "name": "nonexistent-vault",
            "path": "/path/to/nonexistent/directory/xyz123",
            "mode": "personal",
            "owner": "user",
        },
    )
    assert res.status_code == 400
