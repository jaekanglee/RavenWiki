"""Digest feature must not return as a parallel Dashboard surface."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_has_no_digest_surface_or_backend_aggregator() -> None:
    assert not (ROOT / "dashboard/src/routes/DashboardDigest.tsx").exists()
    assert not (ROOT / "dashboard/src/components/DigestCard.tsx").exists()
    assert not (ROOT / "raven/core/digest.py").exists()

    app_source = (ROOT / "dashboard/src/App.tsx").read_text(encoding="utf-8")
    home_source = (ROOT / "dashboard/src/routes/HomePage.tsx").read_text(encoding="utf-8")
    api_source = (ROOT / "raven/api/server.py").read_text(encoding="utf-8")
    core_source = (ROOT / "raven/core/__init__.py").read_text(encoding="utf-8")

    assert 'path="/digest"' not in app_source
    assert 'to: "/digest"' not in home_source
    assert '"/api/vaults/{name}/digest"' not in api_source
    assert "digest_module" not in core_source
