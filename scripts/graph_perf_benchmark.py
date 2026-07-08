#!/usr/bin/env python3
"""Synthetic graph layout benchmark for Raven graph perf work.

Usage:
  python scripts/graph_perf_benchmark.py
  python scripts/graph_perf_benchmark.py --nodes 120,180,260 --iterations 80

Measures `raven.core.graph.forceatlas_layout()` on sparse chain-ish and denser
small-world-ish synthetic graphs. This is not a product-facing command; it is a
regression/profiling helper for graph optimization work.
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from raven.core.graph import forceatlas_layout


@dataclass
class Case:
    name: str
    nodes: int
    edges: list[tuple[str, str]]


def build_sparse(n: int) -> Case:
    ids = [f"n{i}" for i in range(n)]
    edges: list[tuple[str, str]] = []
    for i in range(n):
        if i + 1 < n:
            edges.append((ids[i], ids[i + 1]))
        if i + 7 < n:
            edges.append((ids[i], ids[i + 7]))
    return Case(name=f"sparse-{n}", nodes=n, edges=edges)


def build_dense(n: int) -> Case:
    ids = [f"n{i}" for i in range(n)]
    edges: list[tuple[str, str]] = []
    for i in range(n):
        for step in (1, 2, 3, 5, 8):
            j = i + step
            if j < n:
                edges.append((ids[i], ids[j]))
    return Case(name=f"dense-{n}", nodes=n, edges=edges)


def run_case(case: Case, iterations: int, repeats: int) -> dict[str, float]:
    ids = [f"n{i}" for i in range(case.nodes)]
    samples: list[float] = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        out = forceatlas_layout(ids, case.edges, iterations=iterations)
        dt = time.perf_counter() - t0
        assert len(out) == case.nodes
        samples.append(dt)
    return {
        "min": min(samples),
        "median": statistics.median(samples),
        "mean": statistics.fmean(samples),
        "max": max(samples),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nodes", default="120,180,260,360")
    ap.add_argument("--iterations", type=int, default=80)
    ap.add_argument("--repeats", type=int, default=4)
    args = ap.parse_args()

    node_sizes = [int(x.strip()) for x in args.nodes.split(",") if x.strip()]
    cases: list[Case] = []
    for n in node_sizes:
        cases.append(build_sparse(n))
        cases.append(build_dense(n))

    print(f"iterations={args.iterations} repeats={args.repeats}")
    print("case,nodes,edges,min_s,median_s,mean_s,max_s")
    for case in cases:
        stats = run_case(case, iterations=args.iterations, repeats=args.repeats)
        print(
            f"{case.name},{case.nodes},{len(case.edges)},"
            f"{stats['min']:.4f},{stats['median']:.4f},{stats['mean']:.4f},{stats['max']:.4f}"
        )


if __name__ == "__main__":
    main()
