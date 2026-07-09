"""raven.core.analytics — 순수 파이썬 기반의 그래프 분석 알고리즘 (PageRank, Betweenness Centrality, Louvain Communities).

이 모듈은 외부 라이브러리(NetworkX 등) 의존성 없이 지식 네트워크의 중요도와 중앙성,
그리고 커뮤니티 그룹을 동적으로 산출하고 wiki.db에 업데이트하는 기능을 제공합니다.
"""
from __future__ import annotations

import sqlite3
from collections import defaultdict, deque
import math
from typing import Any


def calculate_pagerank(
    nodes: list[str],
    edges: list[tuple[str, str]],
    d: float = 0.85,
    max_iter: int = 100,
    tol: float = 1.0e-6,
) -> dict[str, float]:
    """방향성 그래프 상에서 PageRank 알고리즘을 수행하여 각 노드의 중요도(importance)를 계산합니다.

    - Dangling nodes (out-degree가 0인 노드)의 값은 모든 노드에 균등 분배됩니다.
    - 수렴 한계치(tol) 내에 도달하거나 max_iter에 도달하면 계산을 종료합니다.
    """
    n = len(nodes)
    if n == 0:
        return {}
    if n == 1:
        return {nodes[0]: 1.0}

    # 각 노드별 PageRank 초기화
    pr = {node: 1.0 / n for node in nodes}

    # out-degree와 in-edges 맵 빌드
    out_edges = {node: [] for node in nodes}
    in_edges = {node: [] for node in nodes}

    for u, v in edges:
        if u in out_edges and v in out_edges:
            out_edges[u].append(v)
            in_edges[v].append(u)

    # Power Iteration
    for _ in range(max_iter):
        next_pr = {}
        # Dangling node 처리: 나가는 링크가 없는 노드들의 rank 합산 후 균등 분배
        dangling_sum = sum(pr[node] for node in nodes if not out_edges[node])
        dangling_share = dangling_sum / n

        for node in nodes:
            # incoming links로부터의 유입 기여도 합산
            in_sum = sum(pr[source] / len(out_edges[source]) for source in in_edges[node])
            next_pr[node] = (1.0 - d) / n + d * (in_sum + dangling_share)

        # 수렴 여부 확인 (L1 norm 차이 계산)
        err = sum(abs(next_pr[node] - pr[node]) for node in nodes)
        pr = next_pr
        if err < tol:
            break

    return pr


def calculate_betweenness_centrality(
    nodes: list[str],
    edges: list[tuple[str, str]],
) -> dict[str, float]:
    """무방향 그래프 상에서 Brandes 알고리즘을 수행하여 각 노드의 매개 중앙성(centrality)을 계산합니다.

    - 최단 경로 계산 시 가중치가 없으므로 BFS를 활용하여 O(V*E) 복잡도로 수행합니다.
    - 최종 값은 (n-1)*(n-2) (n > 2)로 나누어 [0, 1] 범위로 정규화합니다.
    """
    cb = {node: 0.0 for node in nodes}

    # 무방향 Adjacency list 구축
    adj = {node: [] for node in nodes}
    for u, v in edges:
        if u in adj and v in adj:
            if v not in adj[u]:
                adj[u].append(v)
            if u not in adj[v]:
                adj[v].append(u)

    for s in nodes:
        # 단일 출발점 최단 경로 탐색 (BFS)
        stack = []
        pred = {w: [] for w in nodes}
        sigma = {w: 0.0 for w in nodes}
        sigma[s] = 1.0
        dist = {w: -1 for w in nodes}
        dist[s] = 0

        queue = deque([s])

        while queue:
            v = queue.popleft()
            stack.append(v)
            for w in adj[v]:
                # 최단 경로 탐색
                if dist[w] < 0:
                    dist[w] = dist[v] + 1
                    queue.append(w)
                # 경로 개수 누적
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)

        # 의존성 전파 (Backpropagation)
        delta = {w: 0.0 for w in nodes}
        while stack:
            w = stack.pop()
            for v in pred[w]:
                delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != s:
                cb[w] += delta[w]

    # 정규화
    n = len(nodes)
    if n > 2:
        scale = 1.0 / ((n - 1) * (n - 2))
        for v in cb:
            cb[v] *= scale

    return cb


def louvain_communities(
    ids: list[str],
    edges: list[tuple[str, str]],
    weights: list[float] | None = None,
) -> dict[str, int]:
    """Louvain-style community detection.

    이 로직은 원래 raven.core.graph에 정의되어 있던 코드를 순환 참조를 피하기 위해
    이곳으로 이전하고, graph.py가 이를 import하여 재사용하도록 합니다.
    """
    n = len(ids)
    if n == 0:
        return {}
    if n == 1:
        return {ids[0]: 0}
    idx = {s: i for i, s in enumerate(ids)}

    # Build undirected adjacency.
    adj = defaultdict(list)
    for i, e in enumerate(edges):
        s, t = e[0], e[1]
        w = weights[i] if weights is not None and i < len(weights) else 1.0
        if s in idx and t in idx and s != t:
            adj[idx[s]].append((idx[t], w))
            adj[idx[t]].append((idx[s], w))

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
            for nb, _w in adj[u]:
                if not seen[nb]:
                    seen[nb] = True
                    stack.append(nb)

    # Step 2: label propagation.
    for _iteration in range(8):
        moved = 0
        for i in range(n):
            if not adj[i]:
                continue

            label_weights = defaultdict(float)
            for nb, w in adj[i]:
                label_weights[community[nb]] += w

            if not label_weights:
                continue

            sorted_labels = sorted(label_weights.items(), key=lambda x: (-x[1], x[0]))
            best_label = sorted_labels[0][0]

            if best_label != community[i]:
                community[i] = best_label
                moved += 1
        if moved == 0:
            break

    # Renumber communities to 0..K-1 in first-appearance order.
    remap = {}
    next_id = 0
    for c in community:
        if c not in remap:
            remap[c] = next_id
            next_id += 1
    return {ids[i]: remap[community[i]] for i in range(n)}


def update_analytics_properties(conn: sqlite3.Connection) -> None:
    """wiki.db에 구축된 페이지와 관계 데이터를 토대로 PageRank, Centrality, Community를

    계산하고, 각 페이지 레코드에 업데이트합니다.
    relations 테이블이 비어있을 경우, links (일반 위키링크) 테이블을 fallback으로 삼아 그래프를 분석합니다.
    """
    # 1. 모든 노드 목록 가져오기
    rows = conn.execute("SELECT slug FROM pages").fetchall()
    nodes = [r[0] for r in rows]
    if not nodes:
        return

    # 2. relations 테이블의 엣지 정보 가져오기
    rel_rows = conn.execute("SELECT source_slug, target_slug FROM relations").fetchall()
    edges = [(r[0], r[1]) for r in rel_rows if r[0] in nodes and r[1] in nodes]

    # relations 정보가 없을 때 links 테이블로 fallback
    is_fallback = False
    if not edges:
        link_rows = conn.execute("SELECT source_slug, target_slug FROM links").fetchall()
        edges = [(r[0], r[1]) for r in link_rows if r[0] in nodes and r[1] in nodes]
        is_fallback = True

    # 3. 중요도 (PageRank) 계산
    importance_map = calculate_pagerank(nodes, edges)

    # 4. 중앙성 (Betweenness Centrality) 계산
    # Betweenness Centrality는 무방향 그래프 기반으로 계산합니다.
    centrality_map = calculate_betweenness_centrality(nodes, edges)

    # 5. 커뮤니티 계산 (Louvain)
    community_map = louvain_communities(nodes, edges)

    # 6. DB에 분석 정보 일괄 업데이트
    update_data = [
        (
            importance_map.get(node, 0.0),
            centrality_map.get(node, 0.0),
            community_map.get(node, 0),
            node,
        )
        for node in nodes
    ]

    conn.executemany(
        "UPDATE pages SET importance = ?, centrality = ?, community = ? WHERE slug = ?",
        update_data,
    )
