import { useEffect, useMemo, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { COMMUNITY_PALETTE, GraphCanvas } from "../components/GraphCanvas";
import type { Graph, GraphNode } from "../types";

/**
 * GraphPage — dark xyflow canvas + orphan hide toggle + community color toggle.
 * v0.6.10+: 백엔드가 nodes[i].x/y force-directed 좌표 제공.
 * v0.6.14+: default layout = atlas.
 * v0.6.15+: ?community=modularity 옵션. 켜면 노드 색상이 type 대신 Louvain
 *   community id별로 결정 (구조 기반 색). hover 시 같은 community 노드도 highlight.
 */
export function GraphPage() {
  const [graph, setGraph] = useState<Graph>({ nodes: [], edges: [] });
  const [hideOrphans, setHideOrphans] = useState(true);
  const [useCommunity, setUseCommunity] = useState(false);
  const navigate = useNavigate();
  const { vault } = useOutletContext<{ vault: string }>();

  useEffect(() => {
    if (!vault) return;
    const url = `/api/vaults/${encodeURIComponent(vault)}/graph?layout=atlas&community=${
      useCommunity ? "modularity" : "none"
    }`;
    fetch(url)
      .then((r) => (r.ok ? r.json() : { nodes: [], edges: [] }))
      .then((d) => setGraph({ nodes: d.nodes ?? [], edges: d.edges ?? [] }))
      .catch(() => setGraph({ nodes: [], edges: [] }));
  }, [vault, useCommunity]);

  // 표시할 노드 (orphan 가시성 토글 + 연결된 엣지만 필터링)
  const visibleNodes = useMemo<GraphNode[]>(() => {
    if (!hideOrphans) return graph.nodes;
    return graph.nodes.filter((n) => (n.weight ?? 0) > 0);
  }, [graph.nodes, hideOrphans]);

  const visibleEdges = useMemo(() => {
    const visibleIds = new Set(visibleNodes.map((n) => n.id ?? n.slug));
    return graph.edges.filter((e) => {
      const s = (e as any).source ?? e.source_slug;
      const t = (e as any).target ?? e.target_slug;
      return visibleIds.has(s) && visibleIds.has(t);
    });
  }, [graph.edges, visibleNodes]);

  const orphanCount = useMemo(
    () => graph.nodes.filter((n) => (n.weight ?? 0) === 0).length,
    [graph.nodes]
  );

  const communityCount = useMemo(
    () => new Set(visibleNodes.map((n) => n.community).filter((c): c is number => typeof c === "number" && c >= 0)).size,
    [visibleNodes]
  );

  return (
    <div className="graph-page-shell">
      <div className="graph-page-toolbar">
        <h1>Graph</h1>
        <div className="graph-page-meta" aria-label="그래프 상태">
          <strong>{vault}</strong>
          <span>{visibleNodes.length}/{graph.nodes.length} nodes</span>
          <span>{visibleEdges.length} edges</span>
          {useCommunity && communityCount > 0 && (
            <span>{communityCount} communities</span>
          )}
          {orphanCount > 0 && hideOrphans && <span>{orphanCount} orphan 숨김</span>}
        </div>
        <label className="graph-page-toggle">
          <input
            type="checkbox"
            checked={hideOrphans}
            onChange={(e) => setHideOrphans(e.target.checked)}
          />
          고아 숨김
        </label>
        <label
          className={`graph-page-toggle graph-page-toggle-community${
            useCommunity ? "" : " graph-page-toggle-community-off"
          }`}
          title="켜면 노드 색상이 Louvain 커뮤니티별로 결정됩니다 (구조 기반 색상)."
        >
          <input
            type="checkbox"
            checked={useCommunity}
            onChange={(e) => setUseCommunity(e.target.checked)}
          />
          커뮤니티별 색상
          <span className="graph-page-toggle-palette" aria-hidden>
            {COMMUNITY_PALETTE.map((c, i) => (
              <span
                key={i}
                className="graph-page-toggle-dot"
                style={{ background: c }}
              />
            ))}
          </span>
        </label>
      </div>
      <div className="graph-canvas-frame">
        <GraphCanvas
          nodes={visibleNodes}
          edges={visibleEdges}
          // 데스크탑: 1회 click → navigate
          onNodeClick={(slug) => navigate(`/page/${vault}/${slug}`)}
          // 모바일/데스크탑 공통: 더블 click/tap → navigate
          // (GraphCanvas 내부에서 coarse pointer 검출 + 320ms tap 디바운스로 처리)
          onNodeDoubleClick={(slug) => navigate(`/page/${vault}/${slug}`)}
        />
      </div>
    </div>
  );
}
