"""server.py — FastAPI surface over raven.core + raven.agents.

Single source of truth for the GUI's HTTP calls. The dashboard used to read
static JSON (page-<slug>.json etc.); it now calls this server, which keeps
everything dynamic and supports multiple vaults.

Design:
    - stateless: every request resolves the vault fresh
    - CORS open (local dashboard only); production should add auth
    - errors return {ok: false, error: "..."} (never raw stack traces)
    - all write ops use the engine; no shortcuts
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from raven.core import registry, resolve_active_vault, link_module
from raven.core.registry import VAULTS_ROOT
from raven.core import db_module, lint_module, export_module
from raven.core import slug_module, frontmatter_module, archive_module
from raven.core import log_module, digest_module
from raven.core import contracts
from raven.core.vault import Vault


app = FastAPI(title="raven API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ────────────────────────── helpers ──────────────────────────


def _vault_or_404(name: str) -> Vault:
    meta = registry().get(name)
    if not meta:
        raise HTTPException(status_code=404, detail=f"vault {name!r} not found")
    return Vault.load(meta)


def _err(e: Exception) -> dict:
    return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def _safe_slug_or_400(slug: str, v: Vault) -> Path:
    """Validate slug and return absolute Path (without .md suffix).

    Raises HTTPException(400) on bad slug.
    """
    try:
        return slug_module.validate(slug, vault_root=v.root)
    except slug_module.SlugError as e:
        raise HTTPException(status_code=400, detail=f"invalid slug: {e}")


# ────────────────────────── models ──────────────────────────


class PageCreate(BaseModel):
    slug: str = Field(..., description="vault-relative path, e.g. 'content/foo'")
    title: str
    content: str = ""
    type: str = "concept"
    tags: list[str] = []


class PageUpdate(BaseModel):
    content: str
    title: Optional[str] = None
    type: Optional[str] = None
    tags: Optional[list[str]] = None


class LogAppend(BaseModel):
    action: str = Field(..., description="ingest|update|create|archive|delete|lint|build|migrate|chore")
    subject: str
    files: list[str] = []
    note: Optional[str] = None


# ────────────────────────── vault endpoints ──────────────────────────


@app.get("/api/vaults")
def list_vaults():
    """All registered vaults (with metadata).

    v0.6.3+: also returns the resolved `vaults_root` so the dashboard
    can show "Vaults root: ~/Raven" or wherever WIKI_VAULTS_DIR points.
    """
    out = []
    for v in registry().list():
        out.append({
            "name": v.name,
            "path": str(v.path),
            "mode": v.mode,
            "owner": v.owner,
            "default": v.default,
        })
    return {
        "ok": True,
        "vaults": out,
        "vaults_root": str(VAULTS_ROOT()),
    }


@app.get("/api/index.json")
def get_index_json() -> list:
    """Page index for the Dashboard HomePage.

    v0.6.5+: dev API now serves the same shape as `scripts/export_static.py`
    produces for the static `dashboard/public/api/index.json`. Previously
    the dev server returned 404 (no such route) — HomePage was always
    empty in `make dev` until the user ran `raven export` first.

    Shape (per page):
        {slug, title, type, path, created, updated, tags}

    Vault selection:
        - If a `default` is set in the registry, use it
        - Otherwise fall back to the first registered vault
        - 404 if no vaults are registered

    Filter rules match `export_static.py`:
        - skip hidden paths (start with `.`)
        - skip `node_modules/` and `dashboard/`
    """
    from fastapi import HTTPException

    # Pick default (or first) vault — same pattern as the Dashboard's
    # `GET /api/vaults` consumer.
    reg_data = registry()._data
    default_name = reg_data.get("default")
    vaults = registry().list()
    if not vaults:
        raise HTTPException(status_code=404, detail="no vaults registered")
    target_meta = None
    if default_name:
        target_meta = next((v for v in vaults if v.name == default_name), None)
    if target_meta is None:
        target_meta = vaults[0]
    # registry().list() returns VaultMeta objects; we need a live Vault
    # handle to access .content_root / .root for filesystem reads.
    target = Vault.load(target_meta)

    rows: list = []
    # Path components that must never be exposed via the page index
    # (mirrors `scripts/export_static.py` SQL filter on L120-124).
    hidden_top = {".", "..", "node_modules", "dashboard", ".git"}
    for fp in target.content_root.rglob("*.md"):
        rel = fp.relative_to(target.root)
        rel_str = str(rel).replace("\\", "/")
        # Skip if ANY path component is hidden (matches SQL's
        # `slug NOT LIKE '.%'` for the second-level component + the
        # explicit node_modules / dashboard blocklist).
        parts = rel_str.split("/")
        if any(p in hidden_top or p.startswith(".") for p in parts):
            continue

        text = fp.read_text(errors="replace")
        meta, _ = _split_fm(text)
        slug = rel_str[:-3]  # drop ".md"
        tags_str = meta.get("tags", "") or ""
        rows.append(
            {
                "slug": slug,
                "title": meta.get("title", slug.split("/")[-1]),
                "type": meta.get("type", "?"),
                "path": rel_str,
                "created": meta.get("created", ""),
                "updated": meta.get("updated", ""),
                "tags": tags_str,
            }
        )

    # Sort by (type, slug) — same as export_static L137.
    rows.sort(key=lambda p: (p["type"] or "", p["slug"]))
    return rows


@app.get("/api/vaults/{name}")
def vault_info(name: str):
    v = _vault_or_404(name)
    pages = list(v.content_root.rglob("*.md"))
    return {
        "ok": True,
        "vault": {
            "name": v.meta.name,
            "path": str(v.root),
            "mode": v.meta.mode,
            "owner": v.meta.owner,
            "created": v.meta.created,
            "pages": len(pages),
            "db_present": v.db_path.exists(),
        },
    }


@app.post("/api/vaults/{name}/select")
def select_vault(name: str):
    """Set the registry default to `name`."""
    if not registry().set_default(name):
        raise HTTPException(status_code=404, detail=f"vault {name!r} not found")
    return {"ok": True, "active": name}


class VaultCreate(BaseModel):
    name: str = Field(..., description="vault name (lowercase kebab-case 권장)")
    path: str = Field(..., description="absolute path to vault directory")
    mode: str = Field("personal", description="personal | shared | agent")
    owner: str = Field("user", description="user or agent name")
    description: str = Field("", description="free text")
    bootstrap: bool = Field(
        True,
        description=(
            "Lite bootstrap policy (v2026-06-26, 2-tier model): if True, copy ONLY "
            "user-facing essentials (SCHEMA, RULES, log.md). Tier 1 raven-internal "
            "docs (OPERATIONS, agent/*, raven-policy) are NEVER auto-copied. "
            "Use `raven docs` command to read raven-internal docs."
        ),
    )


@app.post("/api/vaults/create")
def create_vault(payload: VaultCreate):
    """Create a new vault on disk + register it.

    Mirrors `raven vault create <name> <path> --mode <mode>`.

    Tier boundary policy: regardless of bootstrap flag, raven-internal
    operational docs (OPERATIONS.md, agent/*, raven-policy.md) are NEVER
    copied into the user vault. This enforces the 2-tier boundary
    (Tier 1 = raven package, Tier 2 = user vault).
    """
    from raven.core.vault import Vault as _Vault

    # Validate: name not already taken
    if registry().get(payload.name):
        raise HTTPException(status_code=409, detail=f"vault {payload.name!r} already exists")

    try:
        v = _Vault.create(
            name=payload.name,
            path=Path(payload.path).expanduser(),
            mode=payload.mode,
            owner=payload.owner,
            description=payload.description,
            bootstrap=payload.bootstrap,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"create failed: {e}")

    return {
        "ok": True,
        "vault": {
            "name": v.meta.name,
            "path": str(v.root),
            "mode": v.meta.mode,
            "owner": v.meta.owner,
            "default": v.meta.name == registry()._data.get("default", ""),
            "bootstrapped": payload.bootstrap,
        },
    }


@app.post("/api/vaults/{name}/verify")
def verify_vault_bootstrap(name: str):
    """Verify the vault's Lite bootstrap files match source templates (SHA256).

    M4 F3 — Bootstrap Self-Test. Mirrors `raven vault verify <name>`.

    Returns:
        ok=True if all 4 Lite bootstrap files match the source templates.
        ok=False with per-file checks otherwise.
    """
    v = _vault_or_404(name)
    result = v.verify_bootstrap()
    payload = result.to_dict()
    if not result.ok:
        raise HTTPException(status_code=409, detail=payload)
    return payload


# ────────────────────────── page endpoints ──────────────────────────


@app.get("/api/vaults/{name}/pages")
def list_pages(
    name: str,
    type: Optional[str] = Query(None, description="filter by frontmatter type"),
    tag: Optional[str] = Query(None, description="filter by tag substring"),
):
    v = _vault_or_404(name)
    rows = []
    for fp in v.content_root.rglob("*.md"):
        text = fp.read_text(errors="replace")
        meta, _ = _split_fm(text)
        slug = str(fp.relative_to(v.root))[:-3]
        if type and meta.get("type") != type:
            continue
        if tag and tag not in meta.get("tags", ""):
            continue
        rows.append({
            "slug": slug,
            "title": meta.get("title", slug),
            "type": meta.get("type", "?"),
            "updated": meta.get("updated", ""),
        })
    return {"ok": True, "vault": name, "pages": rows}


class GraphLayoutParams(BaseModel):
    iterations: int = Field(500, ge=1, le=2000, description="spring iterations (FR-style)")
    layout: Literal["atlas", "constellation", "spring"] = Field(
        "atlas", description="graph layout: atlas, constellation, or spring"
    )


# Graph A2 (v0.6.11+): layout 튜닝 상수.
# 사용자 피드백 — "노드 한 군데 뭉침 / 작은 원에서도 겹침 / 최악" 대응.
# - iterations 120→500: 충분히 안정화, 작은 vault에서도 노드 간 spacing 확보
# - repulsion ×10: hub가 인접 노드를 끌어당기는 힘 > 비인접 척력 불균형 해소
# - attraction ×0.3: hub 중심으로 응집 압력 완화
# - ideal_distance=200 (FR의 k로 강제): vault 크기와 무관하게 일정 spacing 목표
# - uniform random 초기 위치 (FR 알고리즘 정석; 격자는 hub가 중앙에 모이는 패턴 유발)
# - t0 100→50: 초기 변위 폭 절반으로 좁혀서 미세 조정 위주로 수렴
LAYOUT_IDEAL_DISTANCE = 200.0  # 노드 간 목표 간격 (px)
LAYOUT_REPULSION_GAIN = 10.0  # FR 기본 척력(k^2/d) 대비 배율
LAYOUT_ATTRACTION_GAIN = 0.3  # FR 기본 인력(d^2/k) 대비 배율
LAYOUT_T0 = 50.0  # 초기 temperature (이전 100의 절반)


def _normalize_layout(
    ids: list[str],
    pos_x: list[float],
    pos_y: list[float],
    target: float = 500.0,
) -> dict[str, tuple[float, float]]:
    """그래프 좌표를 center=0, scale=±target 으로 정규화한다."""
    n = len(ids)
    if n == 0:
        return {}
    if n == 1:
        return {ids[0]: (0.0, 0.0)}
    min_x, max_x = min(pos_x), max(pos_x)
    min_y, max_y = min(pos_y), max(pos_y)
    cx = (min_x + max_x) / 2.0
    cy = (min_y + max_y) / 2.0
    span_x = max(abs(min_x - cx), abs(max_x - cx))
    span_y = max(abs(min_y - cy), abs(max_y - cy))
    span = max(span_x, span_y) or 1.0
    return {
        ids[i]: (
            round((pos_x[i] - cx) / span * target, 1),
            round((pos_y[i] - cy) / span * target, 1),
        )
        for i in range(n)
    }


def _stable_unit(slug: str, salt: str = "") -> float:
    """slug 기반 deterministic jitter: [0, 1)."""
    import hashlib

    h = hashlib.sha256(f"{salt}:{slug}".encode("utf-8")).digest()
    return int.from_bytes(h[:8], "big") / float(1 << 64)


def _louvain_communities(
    ids: list[str],
    edges: list[tuple[str, str]],
    weights: list[float] | None = None,
    seed: int = 0,
) -> dict[str, int]:
    """Louvain-style community detection (v0.6.15+).

    표준 Louvain (Blondel 2008)의 multi-level ΔQ 최적화는 dense subgraph에서
    ΔQ=0 tie가 많아 결정적인 merge가 안 되는 경향이 있다. v1은 다음 두 단계로
    robust + deterministic + 의존성 없음 결과를 보장한다:

      1) Connected components 분리: 각 연결 컴포넌트는 다른 community로 시작.
      2) Within-component label propagation: 각 노드가 인접 community의
         최다 라벨로 adopt. 8번 반복. ΔQ > 0 같은 미세 비교 대신 "인접 다수결"
         만으로 merge.

    이 방식은 dense subgraph에서도 명확한 merge가 일어나며, 결정론적이며,
    의존성이 없다. 표준 Louvain의 quality에 비하면 약간 떨어질 수 있지만
    PKM use case (수십~수백 노드)에서 시각적 가독성은 더 낫다.

    결정론: 입력과 seed가 같으면 같은 community id. 발견 순서로 renumber.
    """
    from collections import Counter, defaultdict

    n = len(ids)
    if n == 0:
        return {}
    if n == 1:
        return {ids[0]: 0}
    idx = {s: i for i, s in enumerate(ids)}

    # Build undirected adjacency.
    adj: dict[int, list[int]] = defaultdict(list)
    for e in edges:
        s, t = e[0], e[1]
        if s in idx and t in idx and s != t:
            adj[idx[s]].append(idx[t])
            adj[idx[t]].append(idx[s])

    # Step 1: connected components as initial community.
    community = list(range(n))
    seen = [False] * n
    for start in range(n):
        if seen[start]:
            continue
        seen[start] = True
        stack = [start]
        while stack:
            u = stack.pop()
            for nb in adj[u]:
                if not seen[nb]:
                    seen[nb] = True
                    stack.append(nb)
            # Mark all reachable as same community: but only the first node
            # in a component dictates the label. We'll renumber later, so this
            # is just an initial seed — label propagation below overrides.

    # Step 2: label propagation. Each node adopts the most frequent label
    # among its neighbors (ties: lowest label wins). Repeat up to 8 times or
    # until convergence.
    for _iteration in range(8):
        moved = 0
        for i in range(n):
            if not adj[i]:
                continue
            labels = [community[nb] for nb in adj[i]]
            if not labels:
                continue
            counts = Counter(labels)
            best_label, _ = counts.most_common(1)[0]
            if best_label != community[i]:
                # Tie-break: if two labels tie, prefer the lower one. Counter
                # preserves insertion order; for stability we explicitly sort
                # by (-count, label) and pick first.
                sorted_labels = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
                best_label = sorted_labels[0][0]
                if best_label != community[i]:
                    community[i] = best_label
                    moved += 1
        if moved == 0:
            break

    # Renumber communities to 0..K-1 in first-appearance order.
    remap: dict[int, int] = {}
    next_id = 0
    for c in community:
        if c not in remap:
            remap[c] = next_id
            next_id += 1
    return {ids[i]: remap[community[i]] for i in range(n)}


def _constellation_layout(
    ids: list[str],
    edges: list[tuple[str, str]],
    weights: dict[str, int] | None = None,
) -> dict[str, tuple[float, float]]:
    """Obsidian식 별자리/신경망 감각의 deterministic graph layout.

    v1 기준:
    - degree/weight 높은 hub는 component 중심부에 배치
    - hub의 1-hop 이웃은 hub 주변 궤도, leaf/low-degree는 바깥 ring에 배치
    - connected components는 큰 원 둘레에 분리
    - slug hash 기반 각도 jitter로 입력이 같으면 항상 같은 좌표
    - 최종 좌표는 기존 graph contract처럼 center=0, scale=±500
    """
    import math

    n = len(ids)
    if n == 0:
        return {}
    if n == 1:
        return {ids[0]: (0.0, 0.0)}

    weights = weights or {}
    idx = {s: i for i, s in enumerate(ids)}
    adj: dict[str, set[str]] = {s: set() for s in ids}
    for s, t in edges:
        if s in idx and t in idx and s != t:
            adj[s].add(t)
            adj[t].add(s)

    # connected components — 큰 component를 먼저 배치해 전체 별자리의 주 구조를 잡는다.
    remaining = set(ids)
    components: list[list[str]] = []
    while remaining:
        start = min(remaining)
        stack = [start]
        remaining.remove(start)
        comp: list[str] = []
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nb in sorted(adj[cur]):
                if nb in remaining:
                    remaining.remove(nb)
                    stack.append(nb)
        components.append(comp)

    def node_score(slug: str) -> tuple[int, int, float, str]:
        degree = len(adj[slug])
        weight = int(weights.get(slug, 0) or 0)
        # degree가 가장 중요하고, in-degree/weight가 hub tie-breaker 역할.
        return (degree * 10 + weight * 3, degree, _stable_unit(slug, "hub"), slug)

    components.sort(key=lambda c: (-len(c), -max(node_score(s)[0] for s in c), min(c)))
    comp_count = len(components)
    global_pos: dict[str, tuple[float, float]] = {}

    for comp_i, comp in enumerate(components):
        comp_size = len(comp)
        hub = max(comp, key=node_score)

        # Component 중심: 단일/최대 component는 원점, 나머지는 큰 원 둘레에 deterministic 분리.
        if comp_count == 1:
            comp_cx = comp_cy = 0.0
        else:
            outer_r = 520.0 + 170.0 * math.sqrt(comp_count)
            if comp_i == 0 and comp_size > 1:
                comp_cx = comp_cy = 0.0
            else:
                angle = (2.0 * math.pi * (comp_i - 1) / max(comp_count - 1, 1))
                angle += (_stable_unit(hub, "component") - 0.5) * 0.28
                comp_cx = math.cos(angle) * outer_r
                comp_cy = math.sin(angle) * outer_r

        if comp_size == 1:
            angle = 2.0 * math.pi * _stable_unit(hub, "isolated")
            # 완전 고립 노드는 바깥 별 ring으로 보낸다.
            r = 360.0 + 55.0 * comp_i
            global_pos[hub] = (comp_cx + math.cos(angle) * r, comp_cy + math.sin(angle) * r)
            continue

        # Hub 중심. weight가 높은 hub가 시각 중심을 잡고, 주변 node는 level ring에 배치.
        global_pos[hub] = (comp_cx, comp_cy)

        # BFS level: hub 주변 1-hop ring, 그 밖은 더 외곽 ring.
        levels: dict[str, int] = {hub: 0}
        queue = [hub]
        for cur in queue:
            for nb in sorted(adj[cur]):
                if nb in comp and nb not in levels:
                    levels[nb] = levels[cur] + 1
                    queue.append(nb)

        rings: dict[int, list[str]] = {}
        for slug in comp:
            if slug == hub:
                continue
            level = levels.get(slug, 2)
            degree = len(adj[slug])
            # leaf/low-degree는 같은 level에서도 한 단계 바깥으로 밀어 별자리 꼬리를 만든다.
            ring = level
            if degree <= 1:
                ring += 1
            rings.setdefault(ring, []).append(slug)

        base_angle = 2.0 * math.pi * _stable_unit(hub, "base-angle")
        for ring, slugs in sorted(rings.items()):
            slugs.sort(key=lambda s: (_stable_unit(s, f"ring-{ring}"), s))
            count = len(slugs)
            # 1-hop orbit은 촘촘히, leaf/outer ring은 넓게.
            radius = 145.0 + 125.0 * ring + 18.0 * math.sqrt(comp_size)
            for j, slug in enumerate(slugs):
                angle = base_angle + 2.0 * math.pi * j / max(count, 1)
                angle += (_stable_unit(slug, "angle-jitter") - 0.5) * (0.45 / max(ring, 1))
                radial_jitter = (_stable_unit(slug, "radius-jitter") - 0.5) * 36.0
                degree = len(adj[slug])
                if degree >= 3:
                    radial_jitter -= 45.0  # secondary hub는 안쪽으로
                elif degree <= 1:
                    radial_jitter += 55.0  # leaf는 바깥으로
                r = radius + radial_jitter
                global_pos[slug] = (comp_cx + math.cos(angle) * r, comp_cy + math.sin(angle) * r)

    pos_x = [global_pos.get(s, (0.0, 0.0))[0] for s in ids]
    pos_y = [global_pos.get(s, (0.0, 0.0))[1] for s in ids]
    return _normalize_layout(ids, pos_x, pos_y)


def _forceatlas_layout(
    ids: list[str],
    edges: list[tuple[str, str]],
    weights: dict[str, int] | None = None,
    iterations: int = 320,
) -> dict[str, tuple[float, float]]:
    """ForceAtlas2 / LinLog hybrid v2 — PKM 문서 그래프 가독성 우선.

    v1 (0b71e5e) 대비 개선점 (v2):
      - attraction: log1p(d)·d → d (선형) — 같은 군집이 더 강하게 뭉친다.
      - per-node mass = 1 + degree + 0.6·sqrt(weight) — hub가 너무 커지지 않게 cap.
      - repulsion: mass-스케일 + 1/r (degenerate 막기 위해 +1 jitter) — 큰 hub 주변이 비좁지 않게.
      - per-component seed offset: connected component별로 ±R 떨어뜨려서 seed에서도
        군집 간 분리가 시작되게 한다. 그 후 force로 다듬는다.
      - iterations 220 → 320 (deterministic, 출력 안정).
      - output은 기존 graph contract: center=0, scale=±500.
    결정론: random 없음. 입력과 시드가 같으면 같은 좌표.
    """
    import math

    n = len(ids)
    if n == 0:
        return {}
    if n == 1:
        return {ids[0]: (0.0, 0.0)}

    weights = weights or {}
    idx = {s: i for i, s in enumerate(ids)}
    valid_edges = [(s, t) for s, t in edges if s in idx and t in idx and s != t]

    # Seed: 기존 constellation 결과를 사용하되, 연결 컴포넌트별 중심을 멀리 떨어뜨려
    # force가 시작부터 군집을 분리할 수 있게 한다. → LinLog의 핵심.
    seed = _constellation_layout(ids, valid_edges, weights=weights)
    pos_x = [seed.get(s, (0.0, 0.0))[0] for s in ids]
    pos_y = [seed.get(s, (0.0, 0.0))[1] for s in ids]

    # Connected components — 각 컴포넌트의 centroid를 0 주변에서 ring으로 배치.
    from collections import deque
    seen = [False] * n
    components: list[list[int]] = []
    for start in range(n):
        if seen[start]:
            continue
        seen[start] = True
        comp: list[int] = [start]
        dq = deque([start])
        while dq:
            u = dq.popleft()
            for s, t in valid_edges:
                su, tu = idx[s], idx[t]
                for v in (su, tu):
                    if v == u or seen[v]:
                        continue
                    seen[v] = True
                    comp.append(v)
                    dq.append(v)
        components.append(comp)
    if len(components) > 1:
        ring_r = 180.0 + 30.0 * (len(components) - 1)
        for k, comp in enumerate(components):
            ang = (2 * math.pi * k) / max(len(components), 1)
            cx = ring_r * math.cos(ang)
            cy = ring_r * math.sin(ang)
            for v in comp:
                pos_x[v] += cx
                pos_y[v] += cy

    degree = [0] * n
    for s, t in valid_edges:
        degree[idx[s]] += 1
        degree[idx[t]] += 1
    mass = [
        1.0 + min(degree[i], 6) * 0.55 + math.sqrt(max(int(weights.get(ids[i], 0) or 0), 0)) * 0.6
        for i in range(n)
    ]

    steps = max(40, min(iterations, 500))
    repulsion = 4200.0
    attraction = 0.075
    gravity = 0.022
    max_step0 = 28.0

    edge_indices = [(idx[s], idx[t]) for s, t in valid_edges]

    for it in range(steps):
        temp = max_step0 * (1.0 - (it / max(steps - 1, 1))) + 1.0
        dx = [0.0] * n
        dy = [0.0] * n

        # Repulsion (mass-scaled). 모든 노드쌍 — 큰 vault는 O(n^2)이지만
        # 200 노드 이내에선 충분히 빠르고, 더 큰 vault는 v3에서 Barnes-Hut 검토.
        for i in range(n):
            for j in range(i + 1, n):
                vx = pos_x[i] - pos_x[j]
                vy = pos_y[i] - pos_y[j]
                d2 = vx * vx + vy * vy + 1.0
                d = math.sqrt(d2)
                f = repulsion * mass[i] * mass[j] / d2
                fx = (vx / d) * f
                fy = (vy / d) * f
                dx[i] += fx
                dy[i] += fy
                dx[j] -= fx
                dy[j] -= fy

        # Linear attraction: 거리 비례 — 짧은 edge는 강하게, 긴 edge는 약하게.
        # LinLog와 다른 선택이지만 PKM 위키처럼 군집이 응집되어 있을 때 더 예쁘게 모임.
        for i, j in edge_indices:
            vx = pos_x[i] - pos_x[j]
            vy = pos_y[i] - pos_y[j]
            d = math.sqrt(vx * vx + vy * vy) + 0.001
            f = attraction * d
            fx = (vx / d) * f
            fy = (vy / d) * f
            dx[i] -= fx
            dy[i] -= fy
            dx[j] += fx
            dy[j] += fy

        # Gravity: center 방향으로 약한 인력 — disconnected 군집이 무한히 멀리 안 가게.
        for i in range(n):
            dx[i] -= pos_x[i] * gravity
            dy[i] -= pos_y[i] * gravity

        for i in range(n):
            disp = math.sqrt(dx[i] * dx[i] + dy[i] * dy[i])
            if disp <= 0.0001:
                continue
            scale = min(disp, temp) / disp
            pos_x[i] += dx[i] * scale
            pos_y[i] += dy[i] * scale

    return _normalize_layout(ids, pos_x, pos_y)


def _spring_layout(
    ids: list[str],
    edges: list[tuple[str, str]],
    iterations: int = 500,
) -> dict[str, tuple[float, float]]:
    """Fruchterman-Reingold 스타일의 force-directed layout (v0.6.11 튜닝).

    의존성 최소화 (networkx/dagre ❌). FR 알고리즘 직접 구현:
    - 인접 노드간 인력 (attractive, ×0.3), 비인접 노드간 척력 (repulsive, ×10)
    - ideal_distance=200 으로 spacing 목표 명시 (sparse layout)
    - uniform random 초기 위치 (FR 정석; 격자 시작은 hub가 중앙 모이게 함)
    - 결정론: 시드 0 고정 → 같은 vault에서 같은 위치 재현

    Returns: {slug: (x, y)} dict.
    """
    import math
    import random as _r
    rng = _r.Random(0)  # 결정론
    idx = {s: i for i, s in enumerate(ids)}
    n = len(ids)
    if n == 0:
        return {}
    # 초기 위치 — uniform random (FR 알고리즘 정석).
    # 이전 격자 시작은 hub 노드가 중앙에 모이는 패턴을 유발했음.
    # 스케일은 ideal_distance × sqrt(n) 정도로 잡아서 초기부터 적정 간격 근처.
    spread = LAYOUT_IDEAL_DISTANCE * math.sqrt(max(n, 1))
    pos_x = [rng.uniform(-spread, spread) for _ in range(n)]
    pos_y = [rng.uniform(-spread, spread) for _ in range(n)]

    # 인접 리스트 (인덱스 기반)
    adj: list[set[int]] = [set() for _ in range(n)]
    for s, t in edges:
        si, ti = idx.get(s), idx.get(t)
        if si is not None and ti is not None and si != ti:
            adj[si].add(ti)
            adj[ti].add(si)

    # ideal_distance 를 k 로 직접 사용 (vault 크기와 무관하게 일정 spacing 목표).
    k = LAYOUT_IDEAL_DISTANCE
    k2 = k * k

    # 온도 스케줄 (v0.6.11: t0 100→50, 점진 감쇠)
    t0 = LAYOUT_T0
    t_min = 1.0

    for it in range(iterations):
        temp = t0 * ((t_min / t0) ** (it / max(iterations - 1, 1)))
        # displacement 버퍼
        dx = [0.0] * n
        dy = [0.0] * n
        # 1) 모든 쌍 척력 — O(n^2) (vault 페이지 수 ~ 수백 가정, 충분)
        for i in range(n):
            for j in range(i + 1, n):
                d_x = pos_x[i] - pos_x[j]
                d_y = pos_y[i] - pos_y[j]
                d2 = d_x * d_x + d_y * d_y
                if d2 < 0.01:
                    d2 = 0.01
                d = math.sqrt(d2)
                # FR 척력 = k^2 / d × repulsion_gain (×10)
                force = (k2 / d) * LAYOUT_REPULSION_GAIN
                # 양쪽으로 분리
                fx = (d_x / d) * force
                fy = (d_y / d) * force
                dx[i] += fx
                dy[i] += fy
                dx[j] -= fx
                dy[j] -= fy
        # 2) 인접 노드 인력 — d^2 / k × attraction_gain (×0.3)
        for i in range(n):
            for j in adj[i]:
                if j < i:
                    continue  # 쌍 한 번만
                d_x = pos_x[i] - pos_x[j]
                d_y = pos_y[i] - pos_y[j]
                d2 = d_x * d_x + d_y * d_y
                if d2 < 0.01:
                    d2 = 0.01
                d = math.sqrt(d2)
                force = ((d * d) / k) * LAYOUT_ATTRACTION_GAIN
                fx = (d_x / d) * force
                fy = (d_y / d) * force
                dx[i] -= fx
                dy[i] -= fy
                dx[j] += fx
                dy[j] += fy
        # 적용 — 변위를 온도로 클램핑 후 누적 위치
        for i in range(n):
            disp_mag = math.sqrt(dx[i] * dx[i] + dy[i] * dy[i])
            scale = min(disp_mag, temp) / max(disp_mag, 0.001)
            pos_x[i] += dx[i] * scale
            pos_y[i] += dy[i] * scale
    # 정규화 (v0.6.12 Patch 1): xyflow fitView가 viewport에 잡도록 좌표를
    # 항상 center=0, scale=±500으로 transform. 이전 min≥0 정규화는 vault마다
    # 스케일이 들쭉날쭉해서 fitView가 viewport 밖에 있는 노드를 놓쳤다.
    # - center = (min + max) / 2 → 모든 좌표의 centroid를 origin으로
    # - scale  = max(|min - center|, |max - center|) → 가장 먼 노드를 정확히 ±500
    # - x_new  = (x - center) / scale * 500  (y 동일)
    # 특수 케이스:
    #   n == 1 → (0, 0)
    #   모든 노드가 같은 좌표 (scale == 0) → (0, 0)
    return _normalize_layout(ids, pos_x, pos_y)


@app.get("/api/vaults/{name}/graph")
def vault_graph(
    name: str,
    iterations: int = Query(500, ge=1, le=2000, description="spring iterations"),
    layout: Literal["atlas", "constellation", "spring"] = Query(
        "atlas", description="layout: atlas, constellation, or spring"
    ),
    community: Literal["none", "modularity"] = Query(
        "none",
        description="community detection (v0.6.15+): 'modularity' attaches a "
        "Louvain-style community id per node so the dashboard can color by "
        "structure instead of metadata. 'none' skips the computation.",
    ),
):
    """vault 페이지 + wikilink edges + graph layout 좌표를 반환.

    v0.6.10+: nodes[i].x, nodes[i].y = 서버 계산 graph layout 좌표.
    v0.6.14+: default layout = atlas (constellation/spring은 query fallback).
    v0.6.15+: ?community=modularity attaches nodes[i].community = Louvain-style
        community id (0..K-1). 'none' (default) skips the call.

    nodes: [{id: slug, title, type, weight, x, y, community?}]
    edges: [{source: src_slug, target: tgt_slug}]

    wiki.db의 links 테이블에서 source/target 직접 매칭 (정확성 우선).
    wiki.db가 없으면 (구 vault) rglob fallback.
    """
    v = _vault_or_404(name)

    # 1) wiki.db가 있으면 DB 사용 (정확)
    wiki_db = v.root / "wiki.db"
    if wiki_db.exists():
        try:
            import sqlite3
            db = sqlite3.connect(str(wiki_db))
            db.row_factory = sqlite3.Row
            pages = db.execute("SELECT slug, title, type FROM pages").fetchall()
            # in-degree: target_slug별 들어오는 edge 수 (auto+broken 한정, missing 제외)
            in_deg_raw = db.execute(
                "SELECT target_slug, COUNT(*) AS cnt FROM links "
                "WHERE intent IN ('auto', 'broken') GROUP BY target_slug"
            ).fetchall()
            in_degree = {r["target_slug"]: r["cnt"] for r in in_deg_raw}
            nodes = [
                {
                    "id": p["slug"],
                    "title": p["title"],
                    "type": p["type"],
                    "weight": in_degree.get(p["slug"], 0),
                }
                for p in pages
            ]
            # intent='auto' or 'broken' 만 edge로 (missing은 의도적 placeholder)
            edges_raw = db.execute(
                "SELECT source_slug, target_slug FROM links WHERE intent IN ('auto', 'broken')"
            ).fetchall()
            edges = [{"source": r["source_slug"], "target": r["target_slug"]} for r in edges_raw]
            db.close()
            # Patch A1 (v0.6.10+): force-directed 좌표 부착 (서버 1회 계산, 결정론).
            ids = [n["id"] for n in nodes]
            edge_pairs = [(e["source"], e["target"]) for e in edges]
            weights = {n["id"]: int(n.get("weight", 0) or 0) for n in nodes}
            layout_coords = (
                _spring_layout(ids, edge_pairs, iterations=iterations)
                if layout == "spring"
                else _constellation_layout(ids, edge_pairs, weights=weights)
                if layout == "constellation"
                else _forceatlas_layout(ids, edge_pairs, weights=weights, iterations=iterations)
            )
            for node in nodes:
                xy = layout_coords.get(node["id"], (0.0, 0.0))
                node["x"] = xy[0]
                node["y"] = xy[1]
            if community == "modularity":
                comm_map = _louvain_communities(
                    [n["id"] for n in nodes], edge_pairs
                )
                for node in nodes:
                    node["community"] = comm_map.get(node["id"], -1)
            return {
                "ok": True,
                "vault": name,
                "nodes": nodes,
                "edges": edges,
                "stats": {"nodes": len(nodes), "edges": len(edges)},
            }
        except Exception:
            pass  # fallback to rglob

    # 2) wiki.db 없거나 실패 시 — rglob fallback (구 vault)
    nodes = []
    seen = set()
    for fp in v.content_root.rglob("*.md"):
        text = fp.read_text(errors="replace")
        meta, _ = _split_fm(text)
        slug = str(fp.relative_to(v.root))[:-3]
        if slug in seen:
            continue
        seen.add(slug)
        nodes.append({
            "id": slug,
            "title": meta.get("title", slug),
            "type": meta.get("type", "?"),
        })

    import re
    wikilink_re = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
    edges = []
    edge_set = set()
    # in-degree 카운트 — rglob fallback에서도 weight 필드 보존 (대시보드 UI 일관성)
    in_degree: dict[str, int] = {}
    for fp in v.content_root.rglob("*.md"):
        text = fp.read_text(errors="replace")
        meta, body = _split_fm(text)
        src = str(fp.relative_to(v.root))[:-3]
        for m in wikilink_re.finditer(body):
            tgt = m.group(1).strip()
            if not tgt:
                continue
            if tgt.endswith(".md"):
                tgt = tgt[:-3]
            if tgt == src:
                continue
            key = (src, tgt)
            if key in edge_set:
                continue
            edge_set.add(key)
            edges.append({"source": src, "target": tgt})
            in_degree[tgt] = in_degree.get(tgt, 0) + 1

    # nodes에 weight 부착
    for node in nodes:
        node["weight"] = in_degree.get(node["id"], 0)

    # Patch A1 (v0.6.10+): force-directed 좌표 부착 (fallback 분기).
    ids = [n["id"] for n in nodes]
    edge_pairs = [(e["source"], e["target"]) for e in edges]
    weights = {n["id"]: int(n.get("weight", 0) or 0) for n in nodes}
    layout_coords = (
        _spring_layout(ids, edge_pairs, iterations=iterations)
        if layout == "spring"
        else _constellation_layout(ids, edge_pairs, weights=weights)
        if layout == "constellation"
        else _forceatlas_layout(ids, edge_pairs, weights=weights, iterations=iterations)
    )
    for node in nodes:
        xy = layout_coords.get(node["id"], (0.0, 0.0))
        node["x"] = xy[0]
        node["y"] = xy[1]

    return {
        "ok": True,
        "vault": name,
        "nodes": nodes,
        "edges": edges,
        "stats": {"nodes": len(nodes), "edges": len(edges)},
    }


@app.get("/api/vaults/{name}/pages/{slug:path}")
def get_page(name: str, slug: str):
    v = _vault_or_404(name)
    fp = _safe_slug_or_400(slug, v).with_suffix(".md")
    if not fp.exists():
        # fuzzy fallback (옛 빌드 slug 호환): 짧은 slug로 호출 시 모든 pages 중
        # slug의 마지막 segment로 끝나는 것 찾기. 예: 'vault-structure' → 'concept/vault-structure'
        base = slug.rsplit("/", 1)[-1]  # 마지막 segment만
        candidates = []
        for fp_md in v.content_root.rglob("*.md"):
            cand_slug = str(fp_md.relative_to(v.root))[:-3]
            if cand_slug == base or cand_slug.endswith("/" + base):
                candidates.append(fp_md)
        if len(candidates) == 1:
            fp = candidates[0]
        elif len(candidates) > 1:
            # ambiguous — 가장 짧은 slug 우선 (root에 가까운 게 더 canonical)
            fp = min(candidates, key=lambda p: len(p.relative_to(v.root).parts))
        else:
            raise HTTPException(status_code=404, detail=f"page {slug!r} not found in vault {name!r}")
    text = fp.read_text()
    meta, body = _split_fm(text)
    return {
        "ok": True,
        "vault": name,
        "slug": slug,
        "frontmatter": meta,
        "content": body,
    }


# ─── vault management (v0.6.10+) ─────────────────────────────────
# stats / rename / delete — 운영자가 vault 단위로 관리할 수 있는 API.

@app.get("/api/vaults/{name}/stats")
def vault_stats(name: str):
    """Return content + index stats for a vault.

    Used by the Dashboard vault manager to show "12 pages / 5 broken
    links / 84 KB" before destructive ops (rename/delete).
    """
    v = _vault_or_404(name)
    pages = list(v.content_root.rglob("*.md")) if v.content_root.exists() else []
    size_bytes = sum(p.stat().st_size for p in pages)
    log_path = v.root / "log.md"
    log_entries = 0
    if log_path.exists():
        log_entries = sum(
            1 for line in log_path.read_text().splitlines() if line.startswith("## [")
        )
    # broken wikilink count via existing CLI recipe (single source of truth)
    broken = 0
    try:
        from raven.core import link as _link
        broken = len(_link.find_broken(v))
    except Exception:
        pass  # don't fail stats on link audit errors
    return {
        "ok": True,
        "vault": name,
        "pages": len(pages),
        "size_bytes": size_bytes,
        "log_entries": log_entries,
        "broken_links": broken,
    }


class VaultRename(BaseModel):
    name: str = Field(..., description="new vault name (lowercase kebab-case 권장)")


@app.put("/api/vaults/{name}")
def rename_vault(name: str, payload: VaultRename):
    """Rename a vault. The directory on disk is renamed too (matches CLI).

    Registry default stays valid: if the renamed vault was default, the new
    name becomes default automatically.
    """
    reg = registry()
    v = _vault_or_404(name)
    new_name = payload.name.strip()
    if not new_name or new_name == name:
        raise HTTPException(status_code=400, detail=f"invalid new name: {new_name!r}")
    if reg.get(new_name):
        raise HTTPException(status_code=409, detail=f"vault {new_name!r} already exists")

    old_root = v.root
    new_root = old_root.parent / new_name

    # 1. rename directory on disk
    try:
        old_root.rename(new_root)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"rename failed: {e}")

    # 2. update registry
    was_default = reg._data.get("default") == name
    reg.remove(name)
    from raven.core.registry import VaultMeta as _VM
    reg.add(_VM(name=new_name, path=new_root, mode=v.meta.mode, owner=v.meta.owner,
                created=v.meta.created, description=v.meta.description))
    if was_default:
        reg.set_default(new_name)

    return {"ok": True, "vault": {"old": name, "new": new_name, "path": str(new_root)}}


@app.delete("/api/vaults/{name}")
def delete_vault(name: str, force: bool = False):
    """Delete (unregister) a vault.

    Default behavior (force=False):
        - refuses if the vault contains any .md files (protects user data)
        - unregisters only — directory on disk is left intact

    force=True:
        - removes the entire directory recursively (DESTRUCTIVE)
        - use with care
    """
    import shutil
    v = _vault_or_404(name)
    pages = list(v.content_root.rglob("*.md")) if v.content_root.exists() else []
    log_path = v.root / "log.md"
    has_log = log_path.exists() and log_path.stat().st_size > 0

    if (pages or has_log) and not force:
        return {
            "ok": False,
            "vault": name,
            "reason": "vault contains content",
            "stats": {
                "pages": len(pages),
                "log_present": has_log,
            },
            "hint": "retry with ?force=true to delete the directory",
        }

    # destructive path
    if force:
        try:
            shutil.rmtree(v.root)
        except OSError as e:
            raise HTTPException(status_code=500, detail=f"rmtree failed: {e}")

    # always unregister (even non-destructive unregister)
    was_default = registry()._data.get("default") == name
    registry().remove(name)
    if was_default:
        # pick another vault as default if any
        remaining = list(registry()._data.get("vaults", {}).keys())
        if remaining:
            registry().set_default(remaining[0])

    return {"ok": True, "vault": name, "destructive": force}


@app.post("/api/vaults/{name}/pages")
def create_page(name: str, payload: PageCreate):
    """Create a new page.

    Slug handling (v0.3+):
        - Invalid slugs (.., ~, absolute, NUL, ':') rejected with HTTP 400.
        - 'foo' (no '/') is auto-prefixed to 'content/foo' (matches CLI).

    v0.6.2+:
        - Delegates to `raven.core.contracts.write_page` (shared recipe).
        - HTTPException types preserved for the FastAPI boundary.
    """
    v = _vault_or_404(name)
    result = contracts.write_page(
        v,
        payload.slug,
        f"# {payload.title}\n{payload.content}".rstrip() + "\n",
        title=payload.title,
        type=payload.type,
        tags=payload.tags,
        overwrite=False,  # create-only: 409 on exists (matches pre-v0.6.2)
    )
    if not result.ok:
        if result.error == "exists":
            raise HTTPException(status_code=409, detail=f"page {result.slug!r} already exists")
        # Slug validation error → 400
        raise HTTPException(status_code=400, detail=result.error)
    return {"ok": True, "vault": name, "slug": result.slug}


@app.put("/api/vaults/{name}/pages/{slug:path}")
def update_page(name: str, slug: str, payload: PageUpdate):
    """Update an existing page.

    Slug is validated (v0.3+). 'created' is preserved from existing frontmatter
    (v0.3+ — matches Agent and CLI behavior).

    v0.6.2+:
        - Delegates to `raven.core.contracts.write_page` (shared recipe).
    """
    v = _vault_or_404(name)
    # First validate slug via the original safe_slug helper — preserves
    # the pre-v0.6.2 400-on-bad-slug semantics at the API boundary.
    _safe_slug_or_400(slug, v)
    # Existence check for update-only 404 semantics.
    try:
        normalized = slug_module.normalize_prefix(slug)
        safe_path = slug_module.validate(normalized, vault_root=v.root)
        if not safe_path.with_suffix(".md").exists():
            raise HTTPException(status_code=404, detail=f"page {slug!r} not found")
    except slug_module.SlugError:
        # Already validated above; this means normalize/validate drift
        # — let contracts.report it.
        pass
    result = contracts.write_page(
        v,
        slug,
        payload.content.rstrip() + "\n",
        title=payload.title,
        type=payload.type,
        tags=payload.tags,
        overwrite=True,
    )
    if not result.ok:
        raise HTTPException(status_code=400, detail=result.error)
    return {
        "ok": True,
        "vault": name,
        "slug": result.slug,
        "created": result.created_date,
    }


@app.delete("/api/vaults/{name}/pages/{slug:path}")
def delete_page(name: str, slug: str):
    """Archive page (moves to _archive/<original-path>-<timestamp>.md).

    Slug validated (v0.3+). Archive path mirrors original (preserves nesting).
    """
    v = _vault_or_404(name)
    safe_path = _safe_slug_or_400(slug, v)
    fp = safe_path.with_suffix(".md")
    if not fp.exists():
        raise HTTPException(status_code=404, detail=f"page {slug!r} not found")
    import datetime as _dt
    ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_dir = v.root / "_archive"
    archive_dir.mkdir(exist_ok=True)
    rel = fp.relative_to(v.root)
    dest = archive_dir / rel.parent / f"{rel.stem}-{ts}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    fp.rename(dest)
    # v0.5.1+: log.md에 archive entry 자동 append
    try:
        log_module.append(
            v, action="archive", subject=slug,
            files=[str(dest.relative_to(v.root))], note=f"원본: {slug}",
        )
    except Exception:
        pass
    return {"ok": True, "vault": name, "slug": slug, "archived_to": str(dest)}


class VaultClone(BaseModel):
    src: str = Field(..., description="source vault name")
    name: str = Field(..., description="new vault name")
    path: str = Field(..., description="absolute path for new vault directory")
    mode: Optional[str] = Field(None, description="override mode (default: copy from src)")
    owner: Optional[str] = Field(None, description="override owner (default: copy from src)")
    copy_meta: bool = Field(True, description="copy _meta/ from src")


@app.post("/api/vaults/clone")
def clone_vault(payload: VaultClone):
    """Clone an existing vault (content + _meta) to a new vault.

    Skips _archive/ and wiki.db. The new vault is registered automatically.
    """
    src_meta = registry().get(payload.src)
    if src_meta is None:
        raise HTTPException(status_code=404, detail=f"source vault {payload.src!r} not found")
    if registry().get(payload.name) is not None:
        raise HTTPException(status_code=409, detail=f"name {payload.name!r} already registered")
    src_v = Vault.load(src_meta)
    try:
        new_v = Vault.clone(
            src=src_v,
            name=payload.name,
            path=Path(payload.path).expanduser(),
            mode=payload.mode,
            owner=payload.owner,
            copy_meta=payload.copy_meta,
        )
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "ok": True,
        "vault": {
            "name": new_v.meta.name,
            "path": str(new_v.root),
            "mode": new_v.meta.mode,
            "owner": new_v.meta.owner,
            "src": payload.src,
            "copy_meta": payload.copy_meta,
        },
    }


# ────────────────────────── archive endpoints ──────────────────────────


@app.get("/api/vaults/{name}/archive")
def list_archive(name: str, older_than: int = Query(0, description="only show entries older than N days (0=all)")):
    """List all archived files in the vault."""
    v = _vault_or_404(name)
    entries = archive_module.list_archived(v)
    if older_than > 0:
        entries = [e for e in entries if e.age_days is not None and e.age_days > older_than]
    return {
        "ok": True,
        "vault": name,
        "count": len(entries),
        "entries": [e.to_dict() for e in entries],
    }


@app.post("/api/vaults/{name}/archive/clean")
def clean_archive(
    name: str,
    older_than: int = Query(30, description="delete entries older than N days (0=all)"),
    apply: bool = Query(False, description="actually delete (default: dry-run)"),
):
    """Delete old archived files. Dry-run by default."""
    v = _vault_or_404(name)
    result = archive_module.clean_archived(v, older_than_days=older_than, apply=apply)
    return result.to_dict() | {"vault": name}


@app.post("/api/vaults/{name}/archive/restore")
def restore_archive(name: str, archive_path: str = Query(..., description="vault-relative path, e.g. _archive/content/foo-20260625-123456.md")):
    """Restore an archived file to its original slug location."""
    v = _vault_or_404(name)
    result = archive_module.restore_archived(v, archive_path)
    if not result.ok:
        raise HTTPException(status_code=400, detail=result.error)
    return {
        "ok": True,
        "vault": name,
        "original_slug": result.original_slug,
        "restored_to": result.restored_to,
    }


# ────────────────────────── query endpoints ──────────────────────────


@app.get("/api/vaults/{name}/search")
def search(name: str, q: str = Query(..., min_length=1), top_k: int = 10):
    v = _vault_or_404(name)
    # reuse agent's lightweight search via direct walk
    import re as _re
    import html as _html
    terms = [t.lower() for t in _re.findall(r"\w+", q) if t]
    if not terms:
        return {"ok": True, "vault": name, "results": []}

    def _make_snippet(body_text: str, terms: list[str], width: int = 200) -> str:
        """First matching window of width chars centered on the first term hit,
        with <mark> wrapping literal matches (XSS-safe: html-escaped first)."""
        lower = body_text.lower()
        for term in terms:
            idx = lower.find(term)
            if idx < 0:
                continue
            start = max(0, idx - width // 2)
            end = min(len(body_text), idx + width // 2)
            snippet = body_text[start:end].replace("\n", " ").strip()
            # XSS escape first, then apply <mark> to literal term occurrences
            snippet = _html.escape(snippet)
            # Re-apply <mark> around case-insensitive matches (longest first
            # so e.g. "machine" matches before "mach").
            for t in sorted(set(terms), key=len, reverse=True):
                pat = _re.compile(_re.escape(t), _re.IGNORECASE)
                snippet = pat.sub(lambda m: f"<mark>{m.group(0)}</mark>", snippet)
            if start > 0:
                snippet = "…" + snippet
            if end < len(body_text):
                snippet = snippet + "…"
            return snippet
        # No match in body (only frontmatter maybe) → first 200 chars
        snippet = _html.escape(body_text[:width].replace("\n", " ").strip())
        return (snippet + "…") if len(body_text) > width else snippet

    scores = []
    for fp in v.content_root.rglob("*.md"):
        full_text = fp.read_text(errors="replace")
        text = full_text.lower()
        meta, body = _split_fm(full_text)
        slug = str(fp.relative_to(v.root))[:-3]
        score = sum(text.count(t) for t in terms)
        if score > 0:
            snippet = _make_snippet(body, terms)
            scores.append((score, {
                "slug": slug,
                "title": meta.get("title", slug),
                "type": meta.get("type", "?"),
                "score": score,
                "snippet": snippet,
            }))
    scores.sort(key=lambda x: x[0], reverse=True)
    return {"ok": True, "vault": name, "query": q, "results": [s for _, s in scores[:top_k]]}


@app.get("/api/vaults/{name}/link-check")
def link_check(name: str, slug: Optional[str] = None):
    v = _vault_or_404(name)
    return {
        "ok": True,
        "vault": name,
        "broken": link_module.find_broken(v, slug=slug),
        "missing": link_module.find_missing(v, slug=slug),
    }


@app.post("/api/vaults/{name}/build")
def build(name: str):
    v = _vault_or_404(name)
    result = db_module.build_db(v)
    lr = lint_module.run_lint(v)
    return {
        "ok": result.get("ok", False) and lr.get("ok", False),
        "build": result,
        "lint": lr,
    }


@app.post("/api/vaults/{name}/export")
def export(name: str, out_dir: Optional[str] = None):
    v = _vault_or_404(name)
    target = Path(out_dir) if out_dir else None
    result = export_module.export_static(v, out_dir=target)
    return {"ok": result.get("ok", False), "export": result}


# ────────────────────────── log endpoints (v0.5.0+) ──────────────────────────


@app.get("/api/vaults/{name}/log")
def get_log(
    name: str,
    tail: Optional[int] = Query(None, description="최근 N개만"),
    action: Optional[str] = Query(None, description="액션 필터"),
):
    """log.md 작업 이력 조회."""
    v = _vault_or_404(name)
    entries = log_module.list_entries(v, tail=tail, action=action)
    total = log_module.count(v)
    return {
        "ok": True,
        "vault": name,
        "total": total,
        "shown": len(entries),
        "entries": entries,
    }


@app.get("/api/vaults/{name}/log/status")
def get_log_status(name: str):
    """log.md 상태 (entries 수, last entry, rotation 필요)."""
    v = _vault_or_404(name)
    path = log_module.log_path(v)
    total = log_module.count(v)
    entries = log_module.list_entries(v, tail=1)
    last = entries[0] if entries else None
    return {
        "ok": True,
        "vault": name,
        "log_path": str(path),
        "exists": path.exists(),
        "total_entries": total,
        "last_entry": last,
        "needs_rotate": total >= 500,
        "rotate_threshold": 500,
    }


@app.post("/api/vaults/{name}/log")
def post_log(name: str, payload: LogAppend):
    """log.md에 새 entry 추가 (수동)."""
    v = _vault_or_404(name)
    try:
        entry = log_module.append(
            v,
            action=payload.action,
            subject=payload.subject,
            files=payload.files or None,
            note=payload.note,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "ok": True,
        "vault": name,
        "entry": {
            "date": entry.date,
            "action": entry.action,
            "subject": entry.subject,
            "details": entry.details,
        },
    }


@app.post("/api/vaults/{name}/log/rotate")
def post_log_rotate(name: str, year: Optional[int] = None, force: bool = False):
    """log.md rotate (500 entries 초과 시)."""


# ─── /api/debug-log (v0.6.10+, 개발 단계 throw/error catch) ───────
# Dashboard 브라우저에서 fetch throw / window.onerror / unhandledrejection
# 등을 POST하면 서버가 tmp/dashboard.log에 append. mobile DevTools 못 볼 때
# 사용자가 `cat tmp/dashboard.log`로 직접 진단 가능.
class DebugLogEntry(BaseModel):
    level: str = Field("info", description="info | warn | error")
    source: str = Field("", description="dashboard | unhandledrejection | fetch | component")
    message: str = Field(..., description="에러 메시지 또는 진단 라인")
    stack: str = Field("", description="스택 트레이스 (선택)")
    url: str = Field("", description="window.location.href (선택)")
    vault: str = Field("", description="active vault (선택)")


_DEBUG_LOG_PATH = Path(__file__).resolve().parent.parent.parent / "tmp" / "dashboard.log"


@app.post("/api/debug-log")
def post_debug_log(entry: DebugLogEntry):
    """Dashboard throw / error를 tmp/dashboard.log에 append. dev only."""
    _DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {entry.level.upper():5s} {entry.source:20s} vault={entry.vault or '-':12s} url={entry.url or '-'}\n"
    line += f"  msg: {entry.message}\n"
    if entry.stack:
        for sl in entry.stack.splitlines()[:10]:
            line += f"  at:  {sl}\n"
    line += "\n"
    try:
        with _DEBUG_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line)
    except OSError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "path": str(_DEBUG_LOG_PATH)}
    """log.md rotate (500 entries 초과 시)."""
    v = _vault_or_404(name)
    total = log_module.count(v)
    if total < 500 and not force:
        return {
            "ok": False,
            "error": f"{total} entries (500 미만) — 강제 rotate는 ?force=true",
            "current": total,
        }
    target = log_module.rotate(v, year=year)
    return {
        "ok": True,
        "vault": name,
        "rotated_to": str(target),
        "preserved_entries": total,
    }


# ────────────────────────── lint endpoints (v0.5.1+) ──────────────────────────


@app.get("/api/vaults/{name}/lint")
def get_lint(
    name: str,
    check: Optional[str] = Query(None, description="특정 check id (#1-#12)"),
    severity: Optional[str] = Query(None, description="critical|warning|info"),
    write_log: bool = Query(False, description="log.md에 lint entry 자동 append"),
):
    """lint 12개 (카파시 가이드) 실행."""
    v = _vault_or_404(name)
    result = lint_module.run_all(v)
    issues = result["issues"]
    if check:
        issues = [i for i in issues if i.get("id") == check]
    if severity:
        issues = [i for i in issues if i.get("severity") == severity]
    if write_log:
        try:
            c = result["counts"]
            log_module.append(
                v,
                action="lint",
                subject=f"lint 12개 ({c['critical']}C/{c['warning']}W/{c['info']}I)",
                extra={"by_check": json.dumps(result["by_check"], ensure_ascii=False)},
            )
        except Exception:
            pass
    return {
        "ok": result["ok"],
        "vault": name,
        "counts": result["counts"],
        "by_check": result["by_check"],
        "issues": issues,
    }


@app.get("/api/vaults/{name}/lint/summary")
def get_lint_summary(name: str):
    """12개 check별 통계 (빠른 헬스체크)."""
    v = _vault_or_404(name)
    result = lint_module.run_all(v)
    return {
        "ok": result["ok"],
        "vault": name,
        "counts": result["counts"],
        "by_check": result["by_check"],
    }


# ────────────────────────── digest (v0.5.6, M5 F5) ──────────────────────────


@app.get("/api/vaults/{name}/digest")
def get_digest(name: str, days: int = Query(7, ge=1, le=30, description="this_week 윈도우 (1–30)")):
    """Dashboard digest — 사람 운영자 진입 시 '오늘 vault 상태' 한 화면 요약.

    Returns: compute_digest() payload — today / this_week / lint / log_recent / stats.
    """
    v = _vault_or_404(name)
    payload = digest_module.compute_digest(v, days=days)
    return {"ok": True, **payload}


# ────────────────────────── advisory locks (M5 F4) ──────────────────────────
#
# Read-only advisory lock view for the Dashboard. Mirrors mcp.tools.check_lock
# exactly so the Dashboard and the MCP write tools see the same state. We do
# NOT add POST endpoints here — F4 is "advisory" and claim/release flow is
# the caller's job (typically via the MCP transport). Exposing GET only keeps
# this endpoint truly read-only and safe for the Dashboard to poll.


@app.get("/api/vaults/{name}/locks")
def list_locks(name: str, slug: Optional[str] = Query(None, description="specific slug to inspect")):
    """Advisory lock state for a vault (M5 F4).

    With ``slug``: returns the lock record (or ``{"holder": None}``) for
    that slug, same shape ``mcp.tools.check_lock`` returns.

    Without ``slug``: returns all currently active lock entries. Expired
    entries are filtered out (the underlying store does its own GC on
    read).
    """
    v = _vault_or_404(name)
    # Import lazily so server.py doesn't take a hard dependency on mcp.tools
    # at import time (the API server runs in processes that may not have
    # mcp installable, e.g. slim prod containers).
    from raven.mcp.tools import check_lock, _load_locks_store, _is_expired

    if slug:
        holder = check_lock(v.root, slug)
        return {
            "ok": True,
            "vault": name,
            "slug": slug,
            "holder": holder,
        }

    store = _load_locks_store(v.root)
    active = {
        s: entry for s, entry in store.items()
        if not _is_expired(entry)
    }
    return {
        "ok": True,
        "vault": name,
        "count": len(active),
        "locks": active,
    }


# ────────────────────────── local helpers ──────────────────────────


def _split_fm(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    try:
        _, fm, body = text.split("---", 2)
    except ValueError:
        return {}, text
    meta = {}
    for line in fm.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip()
    return meta, body.strip("\n")
