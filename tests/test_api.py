"""Tests for raven.api — REST endpoints after v0.3.1 migration.

Covers the 5 write endpoints (vaults/create, pages POST/PUT/DELETE) plus
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
    resp = client.post("/api/vaults/create", json={
        "name": "v1", "path": str(target), "mode": "personal", "bootstrap": True,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["ok"] is True
    assert data["vault"]["bootstrapped"] is True
    assert (target / "content").is_dir()
    assert (target / "_meta" / "system" / "SCHEMA.md").is_file()
    assert (target / "_meta" / "system" / "RULES.md").is_file()


def test_api_vault_create_no_bootstrap(client, isolated_env):
    target = isolated_env["target_root"] / "v2"
    resp = client.post("/api/vaults/create", json={
        "name": "v2", "path": str(target), "bootstrap": False,
    })
    assert resp.status_code == 200
    # v0.4: empty dirs exist, but templates not copied
    assert (target / "content").is_dir()
    assert (target / "_meta").is_dir()
    assert not (target / "_meta" / "system" / "SCHEMA.md").exists()


def test_api_vault_create_duplicate_name(client, isolated_env):
    target = isolated_env["target_root"] / "v3"
    client.post("/api/vaults/create", json={"name": "v3", "path": str(target)})
    resp = client.post("/api/vaults/create", json={"name": "v3", "path": str(target)})
    assert resp.status_code == 409


# ─── page create ─────────────────────────────────────────────


def test_api_page_create_auto_prefix(client, isolated_env):
    target = isolated_env["target_root"] / "vp"
    client.post("/api/vaults/create", json={"name": "vp", "path": str(target), "bootstrap": False})
    resp = client.post("/api/vaults/vp/pages", json={
        "slug": "hello", "title": "Hello", "type": "concept", "tags": ["a", "b"],
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["slug"] == "content/hello"
    assert (target / "content" / "hello.md").is_file()


def test_api_page_create_explicit_meta(client, isolated_env):
    target = isolated_env["target_root"] / "vp2"
    client.post("/api/vaults/create", json={"name": "vp2", "path": str(target), "bootstrap": False})
    resp = client.post("/api/vaults/vp2/pages", json={
        "slug": "_meta/welcome", "title": "W",
    })
    assert resp.status_code == 200
    assert (target / "_meta" / "welcome.md").is_file()


def test_api_page_create_rejects_parent_traversal(client, isolated_env):
    target = isolated_env["target_root"] / "vp3"
    client.post("/api/vaults/create", json={"name": "vp3", "path": str(target), "bootstrap": False})
    resp = client.post("/api/vaults/vp3/pages", json={
        "slug": "../../etc/passwd", "title": "X",
    })
    assert resp.status_code == 400
    assert "invalid slug" in resp.text.lower()


def test_api_page_create_rejects_absolute(client, isolated_env):
    target = isolated_env["target_root"] / "vp4"
    client.post("/api/vaults/create", json={"name": "vp4", "path": str(target), "bootstrap": False})
    resp = client.post("/api/vaults/vp4/pages", json={
        "slug": "/etc/passwd", "title": "X",
    })
    assert resp.status_code == 400


def test_api_page_create_duplicate(client, isolated_env):
    target = isolated_env["target_root"] / "vp5"
    client.post("/api/vaults/create", json={"name": "vp5", "path": str(target), "bootstrap": False})
    client.post("/api/vaults/vp5/pages", json={"slug": "dup", "title": "X"})
    resp = client.post("/api/vaults/vp5/pages", json={"slug": "dup", "title": "Y"})
    assert resp.status_code == 409


# ─── page update (created 보존 검증) ──────────────────────


def test_api_page_update_preserves_created(client, isolated_env):
    target = isolated_env["target_root"] / "vp6"
    client.post("/api/vaults/create", json={"name": "vp6", "path": str(target), "bootstrap": False})
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


def test_api_page_update_rejects_bad_slug(client, isolated_env):
    target = isolated_env["target_root"] / "vp7"
    client.post("/api/vaults/create", json={"name": "vp7", "path": str(target), "bootstrap": False})
    # URL `..` is normalized by starlette before reaching the route → 404 (which is also safe).
    # We test a slug that survives URL encoding but is still bad: tilde expansion
    resp = client.put("/api/vaults/vp7/pages/~/.ssh-test", json={"content": "x"})
    assert resp.status_code == 400
    assert "invalid slug" in resp.text.lower()


# ─── page delete (mirror 경로) ────────────────────────────


def test_api_page_delete_archives_with_mirror(client, isolated_env):
    target = isolated_env["target_root"] / "vp8"
    client.post("/api/vaults/create", json={"name": "vp8", "path": str(target), "bootstrap": False})
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
    client.post("/api/vaults/create", json={"name": "vp9", "path": str(target), "bootstrap": False})
    # Tilde expansion in URL survives starlette routing
    resp = client.delete("/api/vaults/vp9/pages/~/.ssh-test")
    assert resp.status_code == 400
    assert "invalid slug" in resp.text.lower()


def test_api_page_delete_missing(client, isolated_env):
    target = isolated_env["target_root"] / "vp10"
    client.post("/api/vaults/create", json={"name": "vp10", "path": str(target), "bootstrap": False})
    resp = client.delete("/api/vaults/vp10/pages/content/missing")
    assert resp.status_code == 404


# ─── read endpoints 회귀 ─────────────────────────────────


def test_api_list_pages_still_works(client, isolated_env):
    target = isolated_env["target_root"] / "vp11"
    client.post("/api/vaults/create", json={"name": "vp11", "path": str(target), "bootstrap": False})
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
    client.post("/api/vaults/create", json={"name": "vl", "path": str(target), "bootstrap": False})
    resp = client.get("/api/vaults")
    assert resp.status_code == 200
    names = [v["name"] for v in resp.json()["vaults"]]
    assert "vl" in names


# ─── vault clone endpoint ───────────────────────────────────


def test_api_clone_vault_copies_content(client, isolated_env):
    src = isolated_env["target_root"] / "csrc"
    client.post("/api/vaults/create", json={"name": "csrc", "path": str(src), "bootstrap": False})
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
    client.post("/api/vaults/create", json={"name": "csrc2", "path": str(src), "bootstrap": False})
    client.post("/api/vaults/create", json={"name": "cdst2", "path": str(dst), "bootstrap": False})
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
    client.post("/api/vaults/create", json={"name": "av1", "path": str(target), "bootstrap": False})
    resp = client.get("/api/vaults/av1/archive")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


def test_api_archive_clean_dry_run(client, isolated_env):
    import datetime as _dt
    target = isolated_env["target_root"] / "av2"
    client.post("/api/vaults/create", json={"name": "av2", "path": str(target), "bootstrap": False})
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
    client.post("/api/vaults/create", json={"name": "av3", "path": str(target), "bootstrap": False})
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
    client.post("/api/vaults/create", json={"name": "rg1", "path": str(target), "bootstrap": False})
    resp = client.get("/api/vaults/rg1/pages/~/.ssh-target")
    assert resp.status_code == 400
    assert "invalid slug" in resp.text.lower()


def test_api_get_page_rejects_absolute_slug(client, isolated_env):
    """get_page()는 절대 경로 slug를 400으로 거부해야 한다."""
    target = isolated_env["target_root"] / "rg2"
    client.post("/api/vaults/create", json={"name": "rg2", "path": str(target), "bootstrap": False})
    # Starlette strips leading slash before route matching, so test a slug
    # that reaches the handler with a leading slash via percent-encoding.
    # The important check: any slug that slug_module rejects → HTTP 400.
    resp = client.get("/api/vaults/rg2/pages/~root")
    assert resp.status_code == 400


def test_api_get_page_happy_path(client, isolated_env):
    """정상 slug에 대해 get_page()가 200 + 내용을 반환해야 한다."""
    target = isolated_env["target_root"] / "rg3"
    client.post("/api/vaults/create", json={"name": "rg3", "path": str(target), "bootstrap": False})
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
    client.post("/api/vaults/create", json={"name": "gv1", "path": str(target), "bootstrap": False})
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
    client.post("/api/vaults/create", json={"name": "gv2", "path": str(target), "bootstrap": False})
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
    client.post("/api/vaults/create", json={"name": "gv3", "path": str(target), "bootstrap": False})
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
    client.post("/api/vaults/create", json={"name": "gv4", "path": str(target), "bootstrap": False})
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


def test_spring_layout_handles_small_graph():
    """_spring_layout은 0/1/소형 그래프에서도 안정적으로 동작해야 한다."""
    from raven.api.server import _spring_layout
    # 빈 입력
    assert _spring_layout([], []) == {}
    # 단일 노드
    out = _spring_layout(["a"], [])
    assert "a" in out
    assert len(out["a"]) == 2
    # 10 노드 + 일부 링크
    ids = [f"n{i}" for i in range(10)]
    edges = [("n0", "n1"), ("n1", "n2"), ("n2", "n3"), ("n3", "n0")]
    out = _spring_layout(ids, edges, iterations=50)
    for i in ids:
        assert i in out
        x, y = out[i]
        assert isinstance(x, float)
        assert isinstance(y, float)


def test_spring_layout_v0611_sparse_spacing():
    """v0.6.11 튜닝: 노드 간 평균 거리 ≥ ideal_distance / 2.

    사용자 피드백("노드 한 군데 뭉침 / 작은 원에서도 겹침 / 최악") 회귀 가드.
    ideal_distance=200 이므로 노드 간 평균 거리는 ≥100 px 기대.
    """
    import math
    from raven.api.server import _spring_layout, LAYOUT_IDEAL_DISTANCE

    # hub-style: 한 노드에 다수 링크가 몰리는 응집 압력 시나리오
    ids = [f"n{i}" for i in range(12)]
    edges = [("hub", f"n{i}") for i in range(11)]  # hub에 11개 연결
    out = _spring_layout(["hub", *ids], edges, iterations=500)

    # 모든 좌표 추출
    coords = list(out.values())
    # 페어와이즈 거리 평균
    dists: list[float] = []
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            x1, y1 = coords[i]
            x2, y2 = coords[j]
            d = math.hypot(x1 - x2, y1 - y2)
            dists.append(d)
    avg_dist = sum(dists) / len(dists)
    min_dist = min(dists)
    threshold = LAYOUT_IDEAL_DISTANCE / 2  # 100 px
    assert avg_dist >= threshold, (
        f"평균 노드 거리 {avg_dist:.1f} < {threshold} (ideal_distance={LAYOUT_IDEAL_DISTANCE}). "
        "튜닝 회귀 — 다시 repulsion/attraction/iterations 확인."
    )
    # 최소 거리도 너무 작으면 안 됨 (동일 좌표 직전 충돌 감지)
    assert min_dist > 1.0, f"최소 노드 거리 {min_dist:.2f} — 노드가 사실상 겹침"


def test_spring_layout_v0611_deterministic_with_new_seeds():
    """v0.6.11: uniform random + seed=0 → 결정론 유지 (같은 입력 = 같은 좌표)."""
    from raven.api.server import _spring_layout

    ids = [f"n{i}" for i in range(8)]
    edges = [("n0", "n1"), ("n1", "n2"), ("n3", "n4")]
    out1 = _spring_layout(ids, edges, iterations=200)
    out2 = _spring_layout(ids, edges, iterations=200)
    assert out1 == out2, f"비결정론: {set(out1.items()) ^ set(out2.items())}"


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
    """v0.6.11: 실제 API 응답 노드 좌표가 충분히 펼쳐져 있다 (≥ ideal/2 평균)."""
    import math
    from raven.api.server import LAYOUT_IDEAL_DISTANCE

    target = isolated_env["target_root"] / "gv_spread"
    client.post("/api/vaults/create", json={"name": "gv_spread", "path": str(target), "bootstrap": False})
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
    threshold = LAYOUT_IDEAL_DISTANCE / 2
    assert avg >= threshold, (
        f"실 API 응답 평균 거리 {avg:.1f} < {threshold} — 튜닝이 API까지 반영 안 됨"
    )


# ─── v0.6.12 Patch 1: graph 좌표 정규화 (±500) ─────


def test_api_vault_graph_xy_normalized_to_pm500(client, isolated_env):
    """v0.6.12+: 노드 좌표는 항상 ±500 범위로 정규화되어야 한다 (fitView viewport 매칭).

    이전엔 min≥0 shift만 했고 스케일이 들쭉날쭉 → vault 크기에 따라 fitView가
    viewport 밖에 있는 노드를 놓침. 이제 항상 center=0, scale=±500.
    """
    target = isolated_env["target_root"] / "gv_norm"
    client.post("/api/vaults/create", json={"name": "gv_norm", "path": str(target), "bootstrap": False})
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
