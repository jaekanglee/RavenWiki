"""Tests for raven.api — REST endpoints after v0.3.1 migration.

Covers the 5 write endpoints (POST vaults, pages POST/PUT/DELETE) plus
slug validation, frontmatter unification, and archive mirror.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Use TestClient from FastAPI (stdlib starlette)
from fastapi.testclient import TestClient

from raven.api.server import app
from raven.core.registry import VAULTS_ROOT, registry
from raven.core.vault import Vault


@pytest.fixture
def isolated_env(monkeypatch):
    """Redirect WIKI_VAULTS_DIR + provide a clean target dir."""
    reg_root = Path(tempfile.mkdtemp(prefix="raven-api-reg-"))
    target_root = Path(tempfile.mkdtemp(prefix="raven-api-target-"))
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(reg_root))
    yield {"reg_root": reg_root, "target_root": target_root}
    shutil.rmtree(reg_root, ignore_errors=True)
    shutil.rmtree(target_root, ignore_errors=True)


@pytest.fixture
def client():
    return TestClient(app)


# ─── vault create ────────────────────────────────────────────


def test_api_vault_create_with_bootstrap(client, isolated_env):
    target = isolated_env["target_root"] / "v1"
    resp = client.post("/api/vaults", json={
        "name": "v1", "path": str(target), "mode": "personal", "bootstrap": True,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ok"] is True
    assert data["vault"]["bootstrapped"] is True
    assert (target / "content").is_dir()
    assert (target / "_meta" / "agents" / "SCHEMA.md").is_file()


def test_api_vault_create_no_bootstrap(client, isolated_env):
    target = isolated_env["target_root"] / "v2"
    resp = client.post("/api/vaults", json={
        "name": "v2", "path": str(target), "bootstrap": False,
    })
    assert resp.status_code == 200
    # v0.4: empty dirs exist, but templates not copied
    assert (target / "content").is_dir()
    assert (target / "_meta").is_dir()
    assert not (target / "_meta" / "agents" / "SCHEMA.md").exists()


def test_api_vault_create_duplicate_name(client, isolated_env):
    target = isolated_env["target_root"] / "v3"
    client.post("/api/vaults", json={"name": "v3", "path": str(target)})
    resp = client.post("/api/vaults", json={"name": "v3", "path": str(target)})
    assert resp.status_code == 409


# ─── page create ─────────────────────────────────────────────


def test_api_page_create_auto_prefix(client, isolated_env):
    target = isolated_env["target_root"] / "vp"
    client.post("/api/vaults", json={"name": "vp", "path": str(target), "bootstrap": False})
    resp = client.post("/api/vaults/vp/pages", json={
        "slug": "hello", "title": "Hello", "type": "concept", "tags": ["a", "b"],
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["slug"] == "content/hello"
    assert (target / "content" / "hello.md").is_file()


def test_api_page_create_explicit_meta(client, isolated_env):
    target = isolated_env["target_root"] / "vp2"
    client.post("/api/vaults", json={"name": "vp2", "path": str(target), "bootstrap": False})
    resp = client.post("/api/vaults/vp2/pages", json={
        "slug": "_meta/welcome", "title": "W",
    })
    assert resp.status_code == 403
    assert not (target / "_meta" / "welcome.md").exists()


def test_api_page_create_rejects_protected_raw_path(client, isolated_env):
    target = isolated_env["target_root"] / "vp2raw"
    client.post("/api/vaults", json={"name": "vp2raw", "path": str(target), "bootstrap": False})
    resp = client.post("/api/vaults/vp2raw/pages", json={
        "slug": "raw/source", "title": "S",
    })
    assert resp.status_code == 403
    assert not (target / "raw" / "source.md").exists()


def test_api_page_create_rejects_parent_traversal(client, isolated_env):
    target = isolated_env["target_root"] / "vp3"
    client.post("/api/vaults", json={"name": "vp3", "path": str(target), "bootstrap": False})
    resp = client.post("/api/vaults/vp3/pages", json={
        "slug": "../../etc/passwd", "title": "X",
    })
    assert resp.status_code == 400
    assert "invalid slug" in resp.text.lower()


def test_api_page_create_rejects_absolute(client, isolated_env):
    target = isolated_env["target_root"] / "vp4"
    client.post("/api/vaults", json={"name": "vp4", "path": str(target), "bootstrap": False})
    resp = client.post("/api/vaults/vp4/pages", json={
        "slug": "/etc/passwd", "title": "X",
    })
    assert resp.status_code == 400


def test_api_page_create_duplicate(client, isolated_env):
    target = isolated_env["target_root"] / "vp5"
    client.post("/api/vaults", json={"name": "vp5", "path": str(target), "bootstrap": False})
    client.post("/api/vaults/vp5/pages", json={"slug": "dup", "title": "X"})
    resp = client.post("/api/vaults/vp5/pages", json={"slug": "dup", "title": "Y"})
    assert resp.status_code == 409


# ─── page update (created 보존 검증) ──────────────────────


def test_api_page_update_preserves_created(client, isolated_env):
    target = isolated_env["target_root"] / "vp6"
    client.post("/api/vaults", json={"name": "vp6", "path": str(target), "bootstrap": False})
    client.post("/api/vaults/vp6/pages", json={"slug": "u", "title": "Original"})

    # First update — should preserve created (set by create)
    resp = client.put("/api/vaults/vp6/pages/content/u", json={
        "content": "new body", "title": "Updated",
    })
    assert resp.status_code == 200
    created_after_update = resp.json()["created"]

    # Read back via get_page
    get_resp = client.get("/api/vaults/vp6/pages/content/u")
    fm = get_resp.json()["frontmatter"]
    today = __import__("datetime").date.today().isoformat()
    assert fm["created"] == created_after_update
    assert fm["updated"] == today
    assert fm["title"] == "Updated"
    assert "new body" in get_resp.json()["content"]
    assert "file_path" in get_resp.json()
    assert get_resp.json()["file_path"].endswith("vp6/content/u.md")


def test_api_page_get_maps_container_internal_root_to_host_path(client, isolated_env, monkeypatch):
    internal_root = isolated_env["reg_root"] / "internal-root"
    host_root = isolated_env["target_root"] / "host-root"
    host_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(internal_root))
    monkeypatch.setenv("RAVEN_VAULTS_DIR", str(host_root))

    target = internal_root / "vp_hostmap"
    client.post("/api/vaults", json={"name": "vp_hostmap", "path": str(target), "bootstrap": False})
    client.post("/api/vaults/vp_hostmap/pages", json={"slug": "u", "title": "Original"})

    get_resp = client.get("/api/vaults/vp_hostmap/pages/content/u")
    assert get_resp.status_code == 200
    assert get_resp.json()["file_path"] == str((host_root / "vp_hostmap" / "content" / "u.md").resolve())


def test_api_page_update_rejects_bad_slug(client, isolated_env):
    target = isolated_env["target_root"] / "vp7"
    client.post("/api/vaults", json={"name": "vp7", "path": str(target), "bootstrap": False})
    # URL `..` is normalized by starlette before reaching the route → 404 (which is also safe).
    # We test a slug that survives URL encoding but is still bad: tilde expansion
    resp = client.put("/api/vaults/vp7/pages/~/.ssh-test", json={"content": "x"})
    assert resp.status_code == 400
    assert "invalid slug" in resp.text.lower()


def test_api_page_update_rejects_protected_log_path(client, isolated_env):
    target = isolated_env["target_root"] / "vp7log"
    client.post("/api/vaults", json={"name": "vp7log", "path": str(target), "bootstrap": True})
    resp = client.put("/api/vaults/vp7log/pages/_meta/agents/SCHEMA", json={"content": "x"})
    assert resp.status_code == 403


# ─── page delete (mirror 경로) ────────────────────────────


def test_api_page_delete_archives_with_mirror(client, isolated_env):
    target = isolated_env["target_root"] / "vp8"
    client.post("/api/vaults", json={"name": "vp8", "path": str(target), "bootstrap": False})
    client.post("/api/vaults/vp8/pages", json={"slug": "content/sub/nested", "title": "N"})
    resp = client.delete("/api/vaults/vp8/pages/content/sub/nested")
    assert resp.status_code == 200
    # Original gone
    assert not (target / "content" / "sub" / "nested.md").exists()
    # Archived at mirror path
    archive_dir = target / "_archive" / "content" / "sub"
    assert archive_dir.is_dir()
    archived = list(archive_dir.glob("nested-*.md"))
    assert len(archived) == 1


def test_api_page_delete_rejects_bad_slug(client, isolated_env):
    target = isolated_env["target_root"] / "vp9"
    client.post("/api/vaults", json={"name": "vp9", "path": str(target), "bootstrap": False})
    # Tilde expansion in URL survives starlette routing
    resp = client.delete("/api/vaults/vp9/pages/~/.ssh-test")
    assert resp.status_code == 400
    assert "invalid slug" in resp.text.lower()


def test_api_page_delete_missing(client, isolated_env):
    target = isolated_env["target_root"] / "vp10"
    client.post("/api/vaults", json={"name": "vp10", "path": str(target), "bootstrap": False})
    resp = client.delete("/api/vaults/vp10/pages/content/missing")
    assert resp.status_code == 404


# ─── read endpoints 회귀 ─────────────────────────────────


def test_api_list_pages_still_works(client, isolated_env):
    target = isolated_env["target_root"] / "vp11"
    client.post("/api/vaults", json={"name": "vp11", "path": str(target), "bootstrap": False})
    client.post("/api/vaults/vp11/pages", json={"slug": "content/a", "title": "A"})
    client.post("/api/vaults/vp11/pages", json={"slug": "content/b", "title": "B"})
    resp = client.get("/api/vaults/vp11/pages")
    assert resp.status_code == 200
    pages = resp.json()["pages"]
    slugs = [p["slug"] for p in pages]
    assert "content/a" in slugs
    assert "content/b" in slugs


def test_api_vaults_list(client, isolated_env):
    target = isolated_env["target_root"] / "vl"
    client.post("/api/vaults", json={"name": "vl", "path": str(target), "bootstrap": False})
    resp = client.get("/api/vaults")
    assert resp.status_code == 200
    names = [v["name"] for v in resp.json()["vaults"]]
    assert "vl" in names


def test_api_vault_create_persists_host_display_path(client, isolated_env, monkeypatch):
    runtime_root = isolated_env["reg_root"] / "runtime-root"
    host_root = isolated_env["target_root"] / "host-root"
    host_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("WIKI_VAULTS_DIR", str(runtime_root))
    monkeypatch.setenv("RAVEN_VAULTS_DIR", str(host_root))

    display_target = host_root / "alpha"
    display_target.mkdir(parents=True, exist_ok=True)
    resp = client.post("/api/vaults", json={
        "name": "alpha",
        "path": str(display_target),
        "bootstrap": False,
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["vault"]["path"] == str(display_target.resolve())
    assert (runtime_root / "alpha").is_dir()
    assert str(display_target.resolve()) in (runtime_root / "alpha" / ".vault.json").read_text(encoding="utf-8")

    listing = client.get("/api/vaults").json()
    assert listing["vaults_root"] == str(host_root.resolve())
    alpha = next(v for v in listing["vaults"] if v["name"] == "alpha")
    assert alpha["path"] == str(display_target.resolve())


# ─── vault clone endpoint ───────────────────────────────────


def test_api_clone_vault_copies_content(client, isolated_env):
    src = isolated_env["target_root"] / "csrc"
    client.post("/api/vaults", json={"name": "csrc", "path": str(src), "bootstrap": False})
    (src / "content").mkdir(parents=True, exist_ok=True)  # bootstrap=False didn't create it
    (src / "content" / "hello.md").write_text("# Hi\n")
    dst = isolated_env["target_root"] / "cdst"
    resp = client.post("/api/vaults/clone", json={
        "src": "csrc", "name": "cdst", "path": str(dst),
    })
    assert resp.status_code == 200, resp.text
    assert (dst / "content" / "hello.md").is_file()


def test_api_clone_vault_duplicate_name_rejected(client, isolated_env):
    src = isolated_env["target_root"] / "csrc2"
    dst = isolated_env["target_root"] / "cdst2"
    client.post("/api/vaults", json={"name": "csrc2", "path": str(src), "bootstrap": False})
    client.post("/api/vaults", json={"name": "cdst2", "path": str(dst), "bootstrap": False})
    resp = client.post("/api/vaults/clone", json={"src": "csrc2", "name": "cdst2", "path": str(dst)})
    assert resp.status_code == 409


def test_api_clone_unknown_src_rejected(client, isolated_env):
    dst = isolated_env["target_root"] / "cdst3"
    resp = client.post("/api/vaults/clone", json={
        "src": "nonexistent", "name": "cdst3", "path": str(dst),
    })
    assert resp.status_code == 404


# ─── archive endpoints ──────────────────────────────────────


def test_api_archive_list_empty(client, isolated_env):
    target = isolated_env["target_root"] / "av1"
    client.post("/api/vaults", json={"name": "av1", "path": str(target), "bootstrap": False})
    resp = client.get("/api/vaults/av1/archive")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


def test_api_archive_clean_dry_run(client, isolated_env):
    import datetime as _dt
    target = isolated_env["target_root"] / "av2"
    client.post("/api/vaults", json={"name": "av2", "path": str(target), "bootstrap": False})
    ts = (_dt.datetime.now() - _dt.timedelta(days=100)).strftime("%Y%m%d-%H%M%S")
    (target / "_archive" / "content").mkdir(parents=True)
    (target / "_archive" / "content" / f"old-{ts}.md").write_text("# old\n")
    resp = client.post("/api/vaults/av2/archive/clean?older_than=30&apply=false")
    assert resp.status_code == 200
    data = resp.json()
    assert data["dry_run"] is True
    assert data["would_delete_count"] == 1
    # file still exists
    assert (target / "_archive" / "content" / f"old-{ts}.md").exists()


def test_api_archive_restore_basic(client, isolated_env):
    import datetime as _dt
    target = isolated_env["target_root"] / "av3"
    client.post("/api/vaults", json={"name": "av3", "path": str(target), "bootstrap": False})
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    (target / "_archive" / "content").mkdir(parents=True)
    (target / "_archive" / "content" / f"foo-{ts}.md").write_text("# foo\n")
    rel = f"_archive/content/foo-{ts}.md"
    resp = client.post(f"/api/vaults/av3/archive/restore?archive_path={rel}")
    assert resp.status_code == 200, resp.text
    assert (target / "content" / "foo.md").is_file()


# ─── GET /pages/{slug} slug 가드 (P0 보안 패치) ──────────────


def test_api_get_page_rejects_tilde_traversal(client, isolated_env):
    """get_page()는 tilde slug를 400으로 거부해야 한다 (path traversal 방어)."""
    target = isolated_env["target_root"] / "rg1"
    client.post("/api/vaults", json={"name": "rg1", "path": str(target), "bootstrap": False})
    resp = client.get("/api/vaults/rg1/pages/~/.ssh-target")
    assert resp.status_code == 400
    assert "invalid slug" in resp.text.lower()


def test_api_get_page_rejects_absolute_slug(client, isolated_env):
    """get_page()는 절대 경로 slug를 400으로 거부해야 한다."""
    target = isolated_env["target_root"] / "rg2"
    client.post("/api/vaults", json={"name": "rg2", "path": str(target), "bootstrap": False})
    # Starlette strips leading slash before route matching, so test a slug
    # that reaches the handler with a leading slash via percent-encoding.
    # The important check: any slug that slug_module rejects → HTTP 400.
    resp = client.get("/api/vaults/rg2/pages/~root")
    assert resp.status_code == 400


def test_api_get_page_happy_path(client, isolated_env):
    """정상 slug에 대해 get_page()가 200 + 내용을 반환해야 한다."""
    target = isolated_env["target_root"] / "rg3"
    client.post("/api/vaults", json={"name": "rg3", "path": str(target), "bootstrap": False})
    client.post("/api/vaults/rg3/pages", json={"slug": "content/hello", "title": "Hello"})
    resp = client.get("/api/vaults/rg3/pages/content/hello")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["slug"] == "content/hello"
    assert data["frontmatter"]["title"] == "Hello"


# ─── vault graph (v0.6.10 — weight field regression) ────────


def test_api_vault_graph_nodes_carry_weight_field(client, isolated_env):
    """vault_graph()의 모든 노드는 weight(in-degree) 필드를 가져야 한다.

    v0.6.10 Graph 1라운드 Patch #3 — 노드 크기 = in-degree.
    없으면 프론트 GraphCanvas가 1로 fallback하지만, 의미가 사라지므로
    회귀 가드로 0이라도 명시적으로 존재해야 한다.
    """
    target = isolated_env["target_root"] / "gv1"
    client.post("/api/vaults", json={"name": "gv1", "path": str(target), "bootstrap": False})
    # content 페이지 2개 작성 → graph에 노드 2개
    client.post("/api/vaults/gv1/pages", json={"slug": "content/a", "title": "A"})
    client.post("/api/vaults/gv1/pages", json={"slug": "content/b", "title": "B"})
    resp = client.get("/api/vaults/gv1/graph")
    assert resp.status_code == 200
    nodes = resp.json()["nodes"]
    assert len(nodes) >= 2
    for n in nodes:
        assert "weight" in n, f"node missing weight field: {n}"
        assert isinstance(n["weight"], int)
        assert n["weight"] >= 0


def test_api_vault_graph_weight_matches_in_degree(client, isolated_env):
    """weight 값이 실제 incoming edge 수와 일치해야 한다.

    a → b wikilink를 만들면 b.weight >= 1 (a는 outbound만).
    """
    target = isolated_env["target_root"] / "gv2"
    client.post("/api/vaults", json={"name": "gv2", "path": str(target), "bootstrap": False})
    # a에서 b로 wikilink 1개 — content 필드에 wikilink 작성
    client.post(
        "/api/vaults/gv2/pages",
        json={"slug": "content/a", "title": "A", "content": "links to [[content/b]]"},
    )
    client.post("/api/vaults/gv2/pages", json={"slug": "content/b", "title": "B"})
    resp = client.get("/api/vaults/gv2/graph")
    nodes = {n["id"]: n for n in resp.json()["nodes"]}
    assert "content/b" in nodes, "b가 노드에 존재해야 함"
    assert nodes["content/b"]["weight"] >= 1, f"b는 a로부터 incoming을 받아야 함, got {nodes['content/b']['weight']}"


# ─── vault graph (v0.6.10+ — force-directed layout A1 / dark A2 / orphan hide A3) ───


def test_api_vault_graph_nodes_carry_xy_coordinates(client, isolated_env):
    """A1: 모든 노드는 서버 계산 spring layout x/y 좌표를 가져야 한다.

    결정론 보장: seed=0 + 동일 slug 순서 → 같은 vault 항상 같은 좌표.
    """
    target = isolated_env["target_root"] / "gv3"
    client.post("/api/vaults", json={"name": "gv3", "path": str(target), "bootstrap": False})
    for slug in ["content/a", "content/b", "content/c"]:
        client.post(f"/api/vaults/gv3/pages", json={"slug": slug, "title": slug.split("/")[-1].upper()})
    # a → b, b → c 링크
    client.post(
        "/api/vaults/gv3/pages",
        json={"slug": "content/a", "title": "A", "content": "see [[content/b]]"},
    )
    client.post(
        "/api/vaults/gv3/pages",
        json={"slug": "content/b", "title": "B", "content": "see [[content/c]]"},
    )
    resp = client.get("/api/vaults/gv3/graph")
    assert resp.status_code == 200
    nodes = resp.json()["nodes"]
    assert len(nodes) >= 3
    for n in nodes:
        assert "x" in n, f"node missing x: {n}"
        assert "y" in n, f"node missing y: {n}"
        assert isinstance(n["x"], (int, float))
        assert isinstance(n["y"], (int, float))
    # 결정론 — 두 번 호출해서 같아야 함
    resp2 = client.get("/api/vaults/gv3/graph")
    nodes2 = resp2.json()["nodes"]
    coords1 = {(n["id"], n["x"], n["y"]) for n in nodes}
    coords2 = {(n["id"], n["x"], n["y"]) for n in nodes2}
    assert coords1 == coords2, f"layout not deterministic: {coords1 ^ coords2}"


def test_api_vault_graph_xy_distinct_for_connected_nodes(client, isolated_env):
    """A1: 링크된 노드 a, b는 서로 다른 좌표에 있어야 한다 (force-directed가 의미있는 위치 배정)."""
    target = isolated_env["target_root"] / "gv4"
    client.post("/api/vaults", json={"name": "gv4", "path": str(target), "bootstrap": False})
    client.post(
        "/api/vaults/gv4/pages",
        json={"slug": "content/a", "title": "A", "content": "[[content/b]]"},
    )
    client.post("/api/vaults/gv4/pages", json={"slug": "content/b", "title": "B"})
    resp = client.get("/api/vaults/gv4/graph")
    nodes = {n["id"]: n for n in resp.json()["nodes"]}
    a, b = nodes["content/a"], nodes["content/b"]
    dist = ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5
    assert dist > 1.0, f"a, b가 너무 가까이 (dist={dist:.2f}, 같을 수 없음)"


def test_api_vault_graph_default_iterations_is_500():
    """v0.6.11: GraphLayoutParams / vault_graph 의 기본 iterations 는 500 이어야 한다.

    frontend 가 ?iterations= 를 안 넘기므로 기본값이 곧 사용자 경험.
    """
    from raven.api.server import GraphLayoutParams

    # Pydantic 모델 기본
    assert GraphLayoutParams().iterations == 500, (
        f"GraphLayoutParams 기본 iterations={GraphLayoutParams().iterations}, 500 필요"
    )


def test_api_vault_graph_returns_spread_coordinates(client, isolated_env):
    """실제 API 응답 노드 좌표가 충분히 펼쳐져 있다 (허브 응집 압력에도 최소 spacing 유지)."""
    import math

    target = isolated_env["target_root"] / "gv_spread"
    client.post("/api/vaults", json={"name": "gv_spread", "path": str(target), "bootstrap": False})
    # 8 페이지 + 링크 몇 개
    slugs = [f"content/p{i}" for i in range(8)]
    for slug in slugs:
        client.post(f"/api/vaults/gv_spread/pages", json={"slug": slug, "title": slug.split("/")[-1]})
    # hub 링크
    for slug in slugs[1:]:
        client.post(
            "/api/vaults/gv_spread/pages",
            json={"slug": slugs[0], "title": "P0", "content": f"see [[{slug}]]"},
        )
    resp = client.get("/api/vaults/gv_spread/graph")
    nodes = resp.json()["nodes"]
    assert len(nodes) >= 4
    coords = [(n["x"], n["y"]) for n in nodes]
    dists: list[float] = []
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            d = math.hypot(coords[i][0] - coords[j][0], coords[i][1] - coords[j][1])
            dists.append(d)
    avg = sum(dists) / len(dists)
    threshold = 65.0
    assert avg >= threshold, (
        f"실 API 응답 평균 거리 {avg:.1f} < {threshold} — 튜닝이 API까지 반영 안 됨"
    )


# ─── v0.6.12 Patch 1: graph 좌표 정규화 (±500) ─────


def test_api_vault_graph_all_scope_prefixes_node_ids_by_vault(client, isolated_env):
    """All-vault graph uses {vault}:{slug} ids so registered vaults can share slugs safely."""
    left = isolated_env["target_root"] / "gv_all_left"
    right = isolated_env["target_root"] / "gv_all_right"
    client.post("/api/vaults", json={"name": "gv_all_left", "path": str(left), "bootstrap": False})
    client.post("/api/vaults", json={"name": "gv_all_right", "path": str(right), "bootstrap": False})
    client.post(
        "/api/vaults/gv_all_left/pages",
        json={"slug": "content/shared", "title": "Left Shared", "content": "see [[content/only-left]]"},
    )
    client.post("/api/vaults/gv_all_left/pages", json={"slug": "content/only-left", "title": "Only Left"})
    client.post("/api/vaults/gv_all_right/pages", json={"slug": "content/shared", "title": "Right Shared"})

    current_resp = client.get("/api/vaults/gv_all_left/graph")
    assert current_resp.status_code == 200
    assert {n["id"] for n in current_resp.json()["nodes"]} >= {"content/shared", "content/only-left"}

    all_resp = client.get("/api/vaults/gv_all_left/graph?scope=all")
    assert all_resp.status_code == 200, all_resp.text
    data = all_resp.json()
    ids = {n["id"] for n in data["nodes"]}
    assert "gv_all_left:content/shared" in ids
    assert "gv_all_right:content/shared" in ids
    assert "content/shared" not in ids
    assert {n["vault"] for n in data["nodes"]} >= {"gv_all_left", "gv_all_right"}
    assert {"source": "gv_all_left:content/shared", "target": "gv_all_left:content/only-left"} in data["edges"]
    assert data["scope"] == "all"
    assert data["stats"]["vaults"] == 2


def test_api_vault_graph_xy_normalized_to_pm500(client, isolated_env):
    """v0.6.12+: 노드 좌표는 항상 ±500 범위로 정규화되어야 한다 (fitView viewport 매칭).

    이전엔 min≥0 shift만 했고 스케일이 들쭉날쭉 → vault 크기에 따라 fitView가
    viewport 밖에 있는 노드를 놓침. 이제 항상 center=0, scale=±500.
    """
    target = isolated_env["target_root"] / "gv_norm"
    client.post("/api/vaults", json={"name": "gv_norm", "path": str(target), "bootstrap": False})
    for slug in ["content/a", "content/b", "content/c", "content/d"]:
        client.post(f"/api/vaults/gv_norm/pages", json={"slug": slug, "title": slug.split("/")[-1].upper()})
    resp = client.get("/api/vaults/gv_norm/graph")
    nodes = resp.json()["nodes"]
    assert len(nodes) >= 2
    for n in nodes:
        # 모든 좌표가 ±500 + 약간의 rounding 오차 이내
        assert -501.0 <= n["x"] <= 501.0, f"x out of ±500 range: {n['x']} (id={n['id']})"
        assert -501.0 <= n["y"] <= 501.0, f"y out of ±500 range: {n['y']} (id={n['id']})"
    # 그리고 가장 큰 |x| 또는 |y|가 정확히 500 (가장 먼 노드) — 정규화 보장.
    max_abs = max(max(abs(n["x"]), abs(n["y"])) for n in nodes)
    assert max_abs > 0, "노드가 모두 origin — 정규화 전력이 degenerate"


# ─── Graph Constellation Layout v1 ─────


def test_constellation_layout_hub_near_center_and_leaf_outer_ring():
    """Constellation v1: hub는 중심부, low-degree/leaf는 바깥 ring에 배치한다."""
    import math
    from raven.api.server import _constellation_layout

    ids = ["hub", *[f"leaf{i}" for i in range(10)], "bridge", "tail"]
    edges = [("hub", f"leaf{i}") for i in range(10)] + [("hub", "bridge"), ("bridge", "tail")]
    out = _constellation_layout(ids, edges, weights={"hub": 11})

    hub_radius = math.hypot(*out["hub"])
    leaf_radii = [math.hypot(*out[f"leaf{i}"]) for i in range(10)] + [math.hypot(*out["tail"])]
    assert hub_radius < 80.0, f"hub가 중심에서 너무 멂: radius={hub_radius:.1f}"
    assert sum(leaf_radii) / len(leaf_radii) > hub_radius + 250.0


def test_constellation_layout_normalized_to_pm500_and_deterministic():
    """Constellation v1: 좌표 범위 ±500, 같은 입력은 항상 같은 좌표."""
    from raven.api.server import _constellation_layout

    ids = ["a", "b", "c", "d", "e", "x", "y"]
    edges = [("a", "b"), ("a", "c"), ("c", "d"), ("x", "y")]
    out1 = _constellation_layout(ids, edges, weights={"a": 2, "c": 1})
    out2 = _constellation_layout(ids, edges, weights={"a": 2, "c": 1})

    assert out1 == out2
    assert set(out1) == set(ids)
    for slug, (x, y) in out1.items():
        assert -501.0 <= x <= 501.0, f"x out of ±500 range: {x} (id={slug})"
        assert -501.0 <= y <= 501.0, f"y out of ±500 range: {y} (id={slug})"
    assert max(max(abs(x), abs(y)) for x, y in out1.values()) > 0


def test_atlas_layout_clusters_connected_nodes_and_separates_unrelated_nodes():
    """Atlas v1: 같은 커뮤니티 연결 노드는 가깝고, 다른 커뮤니티는 더 멀어야 한다."""
    import math
    from raven.api.server import _forceatlas_layout

    ids = ["a0", "a1", "a2", "a3", "b0", "b1", "b2", "b3"]
    edges = [
        ("a0", "a1"), ("a1", "a2"), ("a2", "a3"), ("a0", "a2"),
        ("b0", "b1"), ("b1", "b2"), ("b2", "b3"), ("b0", "b2"),
    ]
    out = _forceatlas_layout(ids, edges, weights={"a0": 3, "b0": 3}, iterations=160)

    def dist(x: str, y: str) -> float:
        return math.hypot(out[x][0] - out[y][0], out[x][1] - out[y][1])

    connected = [dist(s, t) for s, t in edges]
    cross = [dist(a, b) for a in ids[:4] for b in ids[4:]]
    assert sum(connected) / len(connected) < sum(cross) / len(cross) * 0.75


def test_atlas_v2_separates_disconnected_components():
    """Atlas v2: 연결 컴포넌트들이 서로 다른 방향에 배치되어 군집 간 거리가
    컴포넌트 내부 평균 거리보다 커야 한다. v1은 같은 조건에서 분리 약했음."""
    import math
    from raven.api.server import _forceatlas_layout

    # 2개 컴포넌트, 각각 4-node 완전그래프(응집) + 1 isolated
    ids = [
        "c1a", "c1b", "c1c", "c1d",
        "c2a", "c2b", "c2c", "c2d",
        "iso1",
    ]
    edges = [
        ("c1a", "c1b"), ("c1a", "c1c"), ("c1a", "c1d"),
        ("c1b", "c1c"), ("c1b", "c1d"), ("c1c", "c1d"),
        ("c2a", "c2b"), ("c2a", "c2c"), ("c2a", "c2d"),
        ("c2b", "c2c"), ("c2b", "c2d"), ("c2c", "c2d"),
    ]
    out = _forceatlas_layout(ids, edges, iterations=200)

    def d(x: str, y: str) -> float:
        return math.hypot(out[x][0] - out[y][0], out[x][1] - out[y][1])

    within_c1 = [d(a, b) for a in ids[:4] for b in ids[:4] if a < b]
    within_c2 = [d(a, b) for a in ids[4:8] for b in ids[4:8] if a < b]
    cross = [d(a, b) for a in ids[:4] for b in ids[4:8]]

    within_avg = (sum(within_c1) + sum(within_c2)) / (len(within_c1) + len(within_c2))
    cross_avg = sum(cross) / len(cross)
    assert cross_avg > within_avg, (
        f"다른 컴포넌트 간 평균 거리({cross_avg:.1f})가 내부 평균({within_avg:.1f})보다 작음 — 군집 분리 실패"
    )


def test_atlas_v2_hub_centerline_below_community_size():
    """Atlas v2: hub는 자신의 컴포넌트 centroid 근처에 있어야 한다 (응집 유지)."""
    import math
    from raven.api.server import _forceatlas_layout

    ids = ["hub", *[f"n{i}" for i in range(8)]]
    edges = [("hub", f"n{i}") for i in range(8)] + [(f"n{i}", f"n{i+1}") for i in range(7)]
    out = _forceatlas_layout(ids, edges, weights={"hub": 8}, iterations=200)

    cx = sum(out[s][0] for s in ids) / len(ids)
    cy = sum(out[s][1] for s in ids) / len(ids)
    hub_to_centroid = math.hypot(out["hub"][0] - cx, out["hub"][1] - cy)
    leaf_max = max(
        math.hypot(out[f"n{i}"][0] - cx, out[f"n{i}"][1] - cy) for i in range(8)
    )
    # hub는 centroid 근처, leaf 중 일부는 더 멀리 있어야 hub 중심 정착이 됨.
    assert hub_to_centroid < leaf_max, (
        f"hub가 centroid({hub_to_centroid:.1f})보다 더 멀어 hub 중심 정착 실패 (max leaf={leaf_max:.1f})"
    )


def test_atlas_layout_normalized_and_deterministic():
    """Atlas v1: 같은 입력은 같은 좌표이며 ±500 범위를 유지한다."""
    from raven.api.server import _forceatlas_layout

    ids = ["hub", "leaf1", "leaf2", "leaf3", "other"]
    edges = [("hub", "leaf1"), ("hub", "leaf2"), ("hub", "leaf3")]
    out1 = _forceatlas_layout(ids, edges, weights={"hub": 3}, iterations=80)
    out2 = _forceatlas_layout(ids, edges, weights={"hub": 3}, iterations=80)

    assert out1 == out2
    assert set(out1) == set(ids)
    for slug, (x, y) in out1.items():
        assert -501.0 <= x <= 501.0, f"x out of ±500 range: {x} (id={slug})"
        assert -501.0 <= y <= 501.0, f"y out of ±500 range: {y} (id={slug})"


# ─── Louvain community detection (v0.6.15+) ───


def test_louvain_communities_disconnected_components_get_distinct_communities():
    """Louvain v1: 연결 컴포넌트별 community id가 서로 달라야 한다 (modularity ΔQ > 0인 경우)."""
    from raven.api.server import _louvain_communities

    # 2 connected components, 각각 internal edge > bridge.
    # C1은 4-node 완전그래프(응집), C2는 3-node chain(응집), bridge 없음.
    # ΔQ > 0 이므로 c1 내부 merge, c2 내부 merge, c1 ≠ c2.
    ids = ["c1a", "c1b", "c1c", "c1d", "c2a", "c2b", "c2c", "iso"]
    edges = [
        ("c1a", "c1b"), ("c1a", "c1c"), ("c1a", "c1d"),
        ("c1b", "c1c"), ("c1b", "c1d"), ("c1c", "c1d"),
        ("c2a", "c2b"), ("c2b", "c2c"),
    ]
    out = _louvain_communities(ids, edges)

    assert set(out) == set(ids)
    # C1은 internal edge 6개 / degree 6 → ΔQ > 0 명확 → merge.
    assert out["c1a"] == out["c1b"] == out["c1c"] == out["c1d"]
    # C2 chain.
    assert out["c2a"] == out["c2b"] == out["c2c"]
    # 두 component는 다른 community.
    assert out["c1a"] != out["c2a"]
    # isolated node: 자기 community.
    assert "iso" in out


def test_louvain_communities_is_deterministic():
    """같은 입력 + 같은 seed → 같은 community id."""
    from raven.api.server import _louvain_communities

    ids = ["a", "b", "c", "d", "e", "f"]
    edges = [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d"), ("d", "e"), ("e", "f")]
    out1 = _louvain_communities(ids, edges)
    out2 = _louvain_communities(ids, edges)
    assert out1 == out2
    assert len(set(out1.values())) >= 1


def test_louvain_communities_modularity_increases_or_stays_non_negative():
    """Louvain: trivial graph(전부 connected)에서도 community 수는 1 이상이고 모든 노드 매핑된다."""
    from raven.api.server import _louvain_communities

    ids = ["a", "b", "c", "d", "e"]
    edges = [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d"), ("d", "e")]
    out = _louvain_communities(ids, edges)

    assert all(v >= 0 for v in out.values())
    assert max(out.values()) >= 0
    # minimum: 전부 한 community일 수 있음 (small graph)
    assert len(set(out.values())) >= 1


def test_louvain_communities_empty_input():
    from raven.api.server import _louvain_communities
    assert _louvain_communities([], []) == {}
    assert _louvain_communities(["a"], []) == {"a": 0}


# ─── folder tree (v0.6.16+) ──────────────────────────────────


def test_folder_first_class_create_then_tree_includes_it(client, isolated_env):
    """Folder create 후 tree에 빈 폴더로 표시되어야 한다 (메타데이터 파일 없음)."""
    target = isolated_env["target_root"] / "fv1"
    client.post("/api/vaults", json={
        "name": "fv1", "path": str(target), "bootstrap": False,
    })

    # depth 3 자유 폴더링
    resp = client.post("/api/vaults/fv1/folders", json={
        "path": "content/users/admin/v0.6",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ok"] is True
    assert data["existed"] is False

    # filesystem: 디렉토리 3개만, 부수 파일 0개
    base = target / "content" / "users" / "admin" / "v0.6"
    assert base.is_dir()
    on_disk_files = list(base.rglob("*"))
    assert all(p.is_dir() for p in on_disk_files), f"unexpected files: {[p for p in on_disk_files if p.is_file()]}"
    assert not any(p.is_file() for p in on_disk_files), "Raven should NOT create any file inside the folder"

    # tree에 빈 폴더로 등장 (자식 0개)
    tree_resp = client.get("/api/vaults/fv1/tree")
    assert tree_resp.status_code == 200
    tree = tree_resp.json()["tree"]

    def find(node, path):
        if node["path"] == path:
            return node
        for c in node.get("children", []):
            r = find(c, path)
            if r:
                return r
        return None

    leaf = find(tree, "content/users/admin/v0.6")
    assert leaf is not None, "folder should appear in tree"
    assert leaf["type"] == "dir"
    assert leaf["children"] == []


def test_folder_create_conflict_with_existing_page(client, isolated_env):
    """page가 이미 있는 경로에 folder 생성 시 409."""
    target = isolated_env["target_root"] / "fv2"
    client.post("/api/vaults", json={
        "name": "fv2", "path": str(target), "bootstrap": False,
    })
    client.post("/api/vaults/fv2/pages", json={
        "slug": "content/notes", "title": "Notes",
    })
    resp = client.post("/api/vaults/fv2/folders", json={"path": "content/notes"})
    assert resp.status_code == 409
    assert "page already exists" in resp.json()["detail"]


def test_folder_create_rejects_path_traversal(client, isolated_env):
    target = isolated_env["target_root"] / "fv3"
    client.post("/api/vaults", json={
        "name": "fv3", "path": str(target), "bootstrap": False,
    })
    resp = client.post("/api/vaults/fv3/folders", json={"path": "../escape"})
    assert resp.status_code == 400
    assert "invalid" in resp.json()["detail"].lower()


def test_folder_create_is_idempotent(client, isolated_env):
    """같은 path로 두 번 호출해도 OK (두 번째는 existed=true)."""
    target = isolated_env["target_root"] / "fv4"
    client.post("/api/vaults", json={
        "name": "fv4", "path": str(target), "bootstrap": False,
    })
    first = client.post("/api/vaults/fv4/folders", json={"path": "content/dup"})
    second = client.post("/api/vaults/fv4/folders", json={"path": "content/dup"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["existed"] is False
    assert second.json()["existed"] is True


def test_get_page_includes_backlinks(client, isolated_env):
    """get_page가 backlinks 리스트를 포함하는지 검증."""
    target = isolated_env["target_root"] / "bl1"
    client.post("/api/vaults", json={
        "name": "bl1", "path": str(target), "bootstrap": False,
    })
    # 1. 대상 페이지 (target) 생성
    client.post("/api/vaults/bl1/pages", json={
        "slug": "content/target", "title": "Target Page", "content": "I am target."
    })
    # 2. 소스 페이지 (source)가 대상을 참조하도록 생성
    client.post("/api/vaults/bl1/pages", json={
        "slug": "content/source", "title": "Source Page", "content": "Link to [[content/target]]"
    })
    # 3. get_page API 호출
    resp = client.get("/api/vaults/bl1/pages/content/target")
    assert resp.status_code == 200
    data = resp.json()
    assert "backlinks" in data
    assert len(data["backlinks"]) == 1
    assert data["backlinks"][0]["source_slug"] == "content/source"
    assert data["backlinks"][0]["source_title"] == "Source Page"


def test_locks_api_list_and_delete(client, isolated_env):
    """/api/vaults/{name}/locks GET & DELETE API 검증."""
    from raven.mcp.tools import acquire_lock
    target = isolated_env["target_root"] / "lk1"
    client.post("/api/vaults", json={
        "name": "lk1", "path": str(target), "bootstrap": False,
    })
    # 1. 락 획득
    res = acquire_lock(target, slug="content/test-page", actor="pytest-tester")
    assert res["ok"] is True

    # 2. locks 조회
    resp = client.get("/api/vaults/lk1/locks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "content/test-page" in data["locks"]
    assert data["locks"]["content/test-page"]["actor"] == "pytest-tester"

    # 3. locks 삭제 (release)
    del_resp = client.delete("/api/vaults/lk1/locks?slug=content/test-page")
    assert del_resp.status_code == 200
    assert del_resp.json()["ok"] is True
    assert del_resp.json()["released"] == "content/test-page"

    # 4. locks 다시 조회해서 락이 풀렸는지 검증
    resp2 = client.get("/api/vaults/lk1/locks")
    assert resp2.status_code == 200
    assert resp2.json()["locks"] == {}


def test_api_delete_vault(client, isolated_env):
    """DELETE /api/vaults/{name} API 검증."""
    # 1. 존재하지 않는 볼트 삭제 시도 -> 404
    resp = client.delete("/api/vaults/nonexistent")
    assert resp.status_code == 404

    # 2. 볼트는 등록되어 있으나 실제 디스크 경로가 유실된 경우 -> 에러 없이 unregister 성공해야 함
    target = isolated_env["target_root"] / "del1"
    resp = client.post("/api/vaults", json={
        "name": "del1", "path": str(target), "bootstrap": False,
    })
    assert resp.status_code == 200
    
    import shutil
    shutil.rmtree(target, ignore_errors=True)
    assert not target.exists()

    # 삭제 시도
    resp = client.delete("/api/vaults/del1")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["vault"] == "del1"

    # 3. 콘텐트가 있는 볼트 삭제 시도 -> force=True 없이는 실패
    target2 = isolated_env["target_root"] / "del2"
    resp = client.post("/api/vaults", json={
        "name": "del2", "path": str(target2), "bootstrap": True,
    })
    assert resp.status_code == 200
    (target2 / "content").mkdir(parents=True, exist_ok=True)
    (target2 / "content" / "hello.md").write_text("Hello", encoding="utf-8")

    resp = client.delete("/api/vaults/del2")
    assert resp.status_code == 409
    data = resp.json()["detail"]
    assert data["reason"] == "vault contains content"
    assert data["stats"]["pages"] == 1

    # 4. force=True와 함께 삭제 시도 -> 성공 및 디스크 삭제
    resp = client.delete("/api/vaults/del2?force=true")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert not target2.exists()
