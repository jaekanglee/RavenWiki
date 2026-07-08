import { useEffect, useMemo, useReducer, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { GraphCanvas, typeLabel, type VaultCentroid } from "../components/GraphCanvas";
import { FullscreenGraphModal } from "../components/FullscreenGraphModal";
import type { Graph, GraphNode } from "../types";
import { EmptyState } from "../components/ui/EmptyState";
import { PageHeader } from "../components/ui/PageHeader";
import { TextField } from "../components/ui/TextField";
import { SelectField } from "../components/ui/SelectField";
import { Button } from "../components/ui/Button";
import { EmptyIcon } from "../lib/emptyIcons";

interface GraphFilterState {
  hideOrphans: boolean;
  query: string;
  selectedType: string;
  selectedCommunity: number | null;
}

/**
 * v0.7.123+: GraphPage의 사용자 입력 필터 상태 (GraphFilterState와 1:1 매핑이지만
 * selectedCommunity는 현재 UX에서 노출하지 않으므로 항상 null). useReducer
 * 상태로 묶어 resetGraphFilters 등 다중 setState를 한 번의 dispatch로 통합.
 */
type GraphPageFilters = {
  query: string;
  selectedType: string;
  hideOrphans: boolean;
  selectedNodeId: string | null;
};

type GraphPageFilterAction =
  | { type: "setQuery"; value: string }
  | { type: "setSelectedType"; value: string }
  | { type: "setHideOrphans"; value: boolean }
  | { type: "setSelectedNodeId"; value: string | null }
  | { type: "reset" };

const initialFilters: GraphPageFilters = {
  query: "",
  selectedType: "all",
  hideOrphans: true,
  selectedNodeId: null,
};

function filterReducer(
  state: GraphPageFilters,
  action: GraphPageFilterAction
): GraphPageFilters {
  switch (action.type) {
    case "setQuery":
      return { ...state, query: action.value };
    case "setSelectedType":
      return { ...state, selectedType: action.value };
    case "setHideOrphans":
      return { ...state, hideOrphans: action.value };
    case "setSelectedNodeId":
      return { ...state, selectedNodeId: action.value };
    case "reset":
      return initialFilters;
    default:
      return state;
  }
}

interface GraphInsight {
  topConnected: GraphNode[];
  topOrphans: GraphNode[];
  typeBreakdown: Array<{ type: string; count: number }>;
}

interface GraphNodeDetail {
  node: GraphNode;
  inbound: GraphNode[];
  outbound: GraphNode[];
  neighbors: GraphNode[];
}

type GraphScope = "all" | "current";

function nodeVault(node: GraphNode, fallbackVault: string): string {
  return node.vault || fallbackVault;
}

function nodeSlug(node: GraphNode): string {
  return node.slug ?? node.id;
}

function normalizeGraphText(value: string | undefined): string {
  return (value ?? "").trim().toLowerCase();
}

function matchesGraphQuery(node: GraphNode, query: string): boolean {
  const normalized = normalizeGraphText(query);
  if (!normalized) return true;
  return [node.title, node.slug ?? node.id, node.type]
    .map(normalizeGraphText)
    .some((token) => token.includes(normalized));
}

/**
 * v0.7.123+ all-vault 모드에서 vault별 centroid + halo 반경을 클라이언트에서 계산.
 *   - 백엔드가 모든 vault의 노드 좌표를 같은 ±500 좌표계에 두고 vault centroid
 *     ring (반경 380) 에 배치해두었으므로, 그 centroid를 그대로 사용.
 *   - 반경은 vault 안 노드 수 + 분포로 산정 (작은 vault 100, 큰 vault 220).
 * surgical A'의 일관: API contract 변경 없이 client-only 추가.
 */
export function deriveVaultCentroids(graph: Graph): VaultCentroid[] {
  const groups = new Map<string, GraphNode[]>();
  for (const n of graph.nodes) {
    if (!n.vault) continue;
    const list = groups.get(n.vault);
    if (list) list.push(n);
    else groups.set(n.vault, [n]);
  }
  if (groups.size === 0) return [];
  const out: VaultCentroid[] = [];
  for (const [vault, nodes] of groups) {
    if (nodes.length === 0) continue;
    const avgX = nodes.reduce((s, n) => s + (n.x ?? 0), 0) / nodes.length;
    const avgY = nodes.reduce((s, n) => s + (n.y ?? 0), 0) / nodes.length;
    // 분산 기반 반경 + 노드 수 보정
    const avgDist =
      nodes.reduce((s, n) => s + Math.hypot((n.x ?? 0) - avgX, (n.y ?? 0) - avgY), 0) /
      nodes.length;
    const baseRadius = Math.min(220, Math.max(110, avgDist * 1.6 + Math.sqrt(nodes.length) * 8));
    out.push({ vault, x: avgX, y: avgY, radius: baseRadius });
  }
  return out;
}

export function deriveGraphInsights(graph: Graph): GraphInsight {
  const sortedNodes = [...graph.nodes].sort((a, b) => {
    const weightDiff = (b.weight ?? 0) - (a.weight ?? 0);
    if (weightDiff !== 0) return weightDiff;
    return (a.title ?? a.slug ?? a.id).localeCompare(b.title ?? b.slug ?? b.id, "ko");
  });

  const topConnected = sortedNodes.filter((node) => (node.weight ?? 0) > 0).slice(0, 5);
  const topOrphans = [...graph.nodes]
    .filter((node) => (node.weight ?? 0) === 0)
    .sort((a, b) => (a.title ?? a.slug ?? a.id).localeCompare(b.title ?? b.slug ?? b.id, "ko"))
    .slice(0, 5);

  const typeCounts = new Map<string, number>();
  for (const node of graph.nodes) {
    const type = node.type || "미분류";
    typeCounts.set(type, (typeCounts.get(type) ?? 0) + 1);
  }

  const typeBreakdown = [...typeCounts.entries()]
    .map(([type, count]) => ({ type, count }))
    .sort((a, b) => {
      if (b.count !== a.count) return b.count - a.count;
      return a.type.localeCompare(b.type, "ko");
    });

  return { topConnected, topOrphans, typeBreakdown };
}

export function deriveNodeDetail(graph: Graph, nodeId: string): GraphNodeDetail | null {
  const node = graph.nodes.find((item) => (item.id) === nodeId);
  if (!node) return null;

  const nodeMap = new Map(graph.nodes.map((item) => [item.id, item]));
  const inboundIds = new Set<string>();
  const outboundIds = new Set<string>();

  for (const edge of graph.edges) {
    const source = edge.source;
    const target = edge.target;
    if (target === nodeId && nodeMap.has(source)) inboundIds.add(source);
    if (source === nodeId && nodeMap.has(target)) outboundIds.add(target);
  }

  const sortNodes = (ids: Set<string>) =>
    [...ids]
      .map((id) => nodeMap.get(id))
      .filter((item): item is GraphNode => Boolean(item))
      .sort((a, b) => (a.title ?? a.slug).localeCompare(b.title ?? b.slug, "ko"));

  const inbound = sortNodes(inboundIds);
  const outbound = sortNodes(outboundIds);
  const neighbors = sortNodes(new Set([...inboundIds, ...outboundIds]));

  return { node, inbound, outbound, neighbors };
}

interface CommunityOption {
  value: string;
  label: string;
}

/**
 * Internal helper for optional relation-group filtering. The primary GraphPage UX
 * no longer exposes community/cluster controls, but tests keep this helper as a
 * regression guard for future advanced filters.
 */
export function deriveCommunityOptions(graph: Graph, hideOrphans: boolean): CommunityOption[] {
  const commHubs: Record<number, { title: string; maxWeight: number; count: number }> = {};
  for (const n of graph.nodes) {
    const c = n.community;
    const w = n.weight ?? 0;
    if (hideOrphans && w === 0) continue;
    if (typeof c === "number" && c >= 0) {
      if (!commHubs[c]) {
        commHubs[c] = { title: n.title ?? n.slug, maxWeight: w, count: 0 };
      }
      commHubs[c].count += 1;
      if (w > commHubs[c].maxWeight) {
        commHubs[c].title = n.title ?? n.slug;
        commHubs[c].maxWeight = w;
      }
    }
  }

  return [
    { value: "all", label: "전체 관계 묶음" },
    ...Object.entries(commHubs).map(([commIdStr, data]) => ({
      value: commIdStr,
      label: `${data.title} (#${commIdStr}, ${data.count}개)`,
    })),
  ];
}

export function filterGraphView(graph: Graph, filters: GraphFilterState): Graph {
  const visibleByType = graph.nodes.filter((node) => {
    if (filters.hideOrphans && (node.weight ?? 0) === 0) return false;
    if (filters.selectedType !== "all" && (node.type ?? "미분류") !== filters.selectedType) {
      return false;
    }
    if (
      filters.selectedCommunity !== null &&
      (typeof node.community !== "number" || node.community !== filters.selectedCommunity)
    ) {
      return false;
    }
    return true;
  });

  const visibleMap = new Map(visibleByType.map((node) => [node.id, node]));
  const normalizedQuery = normalizeGraphText(filters.query);

  let nodeIds = new Set(visibleByType.map((node) => node.id));
  if (normalizedQuery) {
    const matchedIds = new Set(
      visibleByType
        .filter((node) => matchesGraphQuery(node, normalizedQuery))
        .map((node) => node.id)
    );

    if (matchedIds.size > 0) {
      const expandedIds = new Set(matchedIds);
      for (const edge of graph.edges) {
        const source = edge.source;
        const target = edge.target;
        if (!visibleMap.has(source) || !visibleMap.has(target)) continue;
        if (matchedIds.has(source) || matchedIds.has(target)) {
          expandedIds.add(source);
          expandedIds.add(target);
        }
      }
      nodeIds = expandedIds;
    } else {
      nodeIds = new Set();
    }
  }

  const nodes = visibleByType.filter((node) => nodeIds.has(node.id));
  const ids = new Set(nodes.map((node) => node.id));
  const edges = graph.edges.filter((edge) => {
    const source = edge.source;
    const target = edge.target;
    return ids.has(source) && ids.has(target);
  });

  return { nodes, edges };
}

/**
 * GraphPage — dark xyflow canvas + connected-document exploration.
 * v0.6.10+: 백엔드가 nodes[i].x/y force-directed 좌표 제공.
 * v0.7.35+: search/type controls + insight cards for graph exploration.
 * v0.7.6x+: layout은 atlas(ForceAtlas2/LinLog hybrid) 고정 — 선택 UI 제거.
 * v0.7.122+: community/cluster controls are hidden from the primary UX;
 *   graph colors are user-facing document type colors.
 */
export function GraphPage() {
  const [graph, setGraph] = useState<Graph>({ nodes: [], edges: [] });
  const [graphScope, setGraphScope] = useState<GraphScope>("current");
  // v0.7.123+: 그래프 페이지 필터 상태(query/selectedType/hideOrphans/selectedNodeId)를
  // useReducer로 묶어 resetGraphFilters 등 다중 setState 시 동기화 + 의도 명시.
  // 인사이트 hover 2종 + 로딩/에러/showFullGraph는 데이터 라이프사이클/UI 토글로
  // 빈도가 낮아 그대로 useState 유지.
  const [filters, dispatchFilters] = useReducer(filterReducer, initialFilters);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [hoveredInsightNodeId, setHoveredInsightNodeId] = useState<string | null>(null);
  const [hoveredInsightType, setHoveredInsightType] = useState<string | null>(null);
  const [showFullGraph, setShowFullGraph] = useState(false);
  const navigate = useNavigate();
  const { vault } = useOutletContext<{ vault: string }>();

  const { query, selectedType, hideOrphans, selectedNodeId } = filters;

  const resetGraphFilters = () => dispatchFilters({ type: "reset" });

  const loadGraph = () => {
    if (!vault) return;
    setLoading(true);
    setLoadError(false);
    const graphScopeQuery = graphScope === "all" ? "scope=all" : "scope=current";
    fetch(`/api/vaults/${encodeURIComponent(vault)}/graph?${graphScopeQuery}`)
      .then((r) => (r.ok ? r.json() : { nodes: [], edges: [] }))
      .then((d) => setGraph({ nodes: d.nodes ?? [], edges: d.edges ?? [] }))
      .catch(() => {
        setGraph({ nodes: [], edges: [] });
        setLoadError(true);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadGraph();
  }, [vault, graphScope]);

  const filteredGraph = useMemo(
    () =>
      filterGraphView(graph, {
        hideOrphans,
        query,
        selectedType,
        selectedCommunity: null,
      }),
    [graph, hideOrphans, query, selectedType]
  );

  const visibleNodes = filteredGraph.nodes;
  const visibleEdges = filteredGraph.edges;

  const orphanCount = useMemo(
    () => graph.nodes.filter((n) => (n.weight ?? 0) === 0).length,
    [graph.nodes]
  );

  const graphInsights = useMemo(() => deriveGraphInsights(graph), [graph]);
  const selectedNodeDetail = useMemo(
    () => (selectedNodeId ? deriveNodeDetail(graph, selectedNodeId) : null),
    [graph, selectedNodeId]
  );

  const typeOptions = useMemo(
    () => [
      { value: "all", label: "전체 타입" },
      ...graphInsights.typeBreakdown.map(({ type, count }) => ({
        value: type,
        label: `${typeLabel(type) || type} (${count})`,
      })),
    ],
    [graphInsights.typeBreakdown]
  );

  const hasAnyNodes = graph.nodes.length > 0;
  const hasVisibleNodes = visibleNodes.length > 0;
  const hasActiveFilter =
    query.trim().length > 0 ||
    selectedType !== "all" ||
    !hideOrphans;

  const graphNodeMap = useMemo(
    () => new Map(graph.nodes.map((node) => [node.id, node])),
    [graph.nodes]
  );

  // v0.7.123+ all-vault 모드에서만 vault halo/labal 데이터를 만든다.
  // current scope에서는 GraphCanvas에 prop 자체를 안 넘겨서 halo/labal 비활성.
  const vaultCentroids = useMemo(
    () => (graphScope === "all" ? deriveVaultCentroids(graph) : []),
    [graph, graphScope]
  );

  const openGraphNode = (nodeId: string) => {
    const node = graphNodeMap.get(nodeId);
    if (!node) return;
    navigate(`/page/${nodeVault(node, vault)}/${nodeSlug(node)}`);
  };

  const controlsSection = (
    <div className="graph-page-control-grid">
      <SelectField
        label="범위"
        value={graphScope}
        onChange={(e) => {
          const next = e.target.value as GraphScope;
          setGraphScope(next);
          dispatchFilters({ type: "setSelectedNodeId", value: null });
        }}
        options={[
          { value: "all", label: "전체 vault" },
          { value: "current", label: "현재 vault" },
        ]}
        helper="전체 vault 우주 지도 또는 현재 보관소만 봅니다."
      />
      <TextField
        label="문서 검색"
        value={query}
        onChange={(e) => dispatchFilters({ type: "setQuery", value: e.target.value })}
        placeholder="제목, slug, type으로 필터"
        helper="검색 시 일치 문서와 1-hop 이웃만 남겨 맥락을 유지합니다."
      />
      <SelectField
        label="타입 필터"
        value={selectedType}
        onChange={(e) => dispatchFilters({ type: "setSelectedType", value: e.target.value })}
        options={typeOptions}
        helper="특정 문서 타입만 남겨 구조를 집중 탐색합니다."
      />
      <div className="graph-page-actions" style={{ display: "flex", gap: 8, alignItems: "flex-end", paddingBottom: 6 }}>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={resetGraphFilters}
          disabled={!hasActiveFilter}
        >
          필터 초기화
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={loadGraph}>
          새로고침
        </Button>
      </div>
    </div>
  );

  useEffect(() => {
    if (!selectedNodeId) return;
    const stillVisible = visibleNodes.some((node) => (node.id) === selectedNodeId);
    if (!stillVisible) dispatchFilters({ type: "setSelectedNodeId", value: null });
  }, [selectedNodeId, visibleNodes]);

  return (
    <div className="graph-page-shell">
      <div className="graph-page-toolbar">
        <PageHeader
          title="그래프"
          contextLabel={graphScope === "all" ? "전체 vault 우주 지도" : `${vault} 보관소`}
          titleSize={22}
          bottomSpacing={0}
        />
        <div className="graph-page-meta" aria-label="그래프 상태">
          <span>{loading ? "그래프 계산 중…" : `문서 ${visibleNodes.length}/${graph.nodes.length}`}</span>
          <span>{loading ? "잠시만 기다려 주세요" : `연결 ${visibleEdges.length}`}</span>
          {orphanCount > 0 && hideOrphans && <span>연결 없는 문서 {orphanCount}개 숨김</span>}
        </div>
        <label className="graph-page-toggle">
          <input
            type="checkbox"
            checked={hideOrphans}
            onChange={(e) => dispatchFilters({ type: "setHideOrphans", value: e.target.checked })}
          />
          연결 없는 문서 숨김
        </label>
      </div>

      <div className="graph-desktop-only">
        {controlsSection}
      </div>

      <div className="graph-page-workspace">
      <div className="graph-canvas-frame">
        {loading ? (
          <EmptyState
            icon={<EmptyIcon.Spinner />}
            title="그래프를 불러오는 중입니다"
            description="문서 연결 구조를 계산하고 있습니다."
          />
        ) : loadError ? (
          <EmptyState
            icon={<EmptyIcon.AlertTriangle />}
            title="그래프를 불러오지 못했습니다"
            description="API 응답 또는 로컬 상태를 다시 확인해 보세요."
            action={(
              <button
                type="button"
                className="btn-secondary"
                style={{ height: 36, padding: "8px 14px", fontSize: 13 }}
                onClick={loadGraph}
              >
                다시 시도
              </button>
            )}
          />
        ) : !hasAnyNodes ? (
          <EmptyState
            icon={<EmptyIcon.Database />}
            title="아직 시각화할 문서가 없습니다"
            description="현재 보관소에 문서를 추가하면 연결 그래프가 여기에 표시됩니다."
          />
        ) : !hasVisibleNodes && hideOrphans && orphanCount === graph.nodes.length ? (
          <EmptyState
            icon={<EmptyIcon.Fog />}
            title="지금은 모두 연결 없는 문서입니다"
            description="연결 없는 문서 숨김을 끄면 문서는 보이지만 아직 서로 연결되지 않았다는 뜻입니다."
            action={(
              <button
                type="button"
                className="btn-secondary"
                style={{ height: 36, padding: "8px 14px", fontSize: 13 }}
                onClick={() => dispatchFilters({ type: "setHideOrphans", value: false })}
              >
                연결 없는 문서 보기
              </button>
            )}
          />
        ) : !hasVisibleNodes ? (
          <EmptyState
            icon={<EmptyIcon.Search />}
            title="필터와 일치하는 문서가 없습니다"
            description="검색어를 지우거나 타입 필터를 바꿔서 다시 확인해 보세요."
            action={(
              <button
                type="button"
                className="btn-secondary"
                style={{ height: 36, padding: "8px 14px", fontSize: 13 }}
                onClick={resetGraphFilters}
              >
                필터 초기화
              </button>
            )}
          />
        ) : (
          <GraphCanvas
            nodes={visibleNodes}
            edges={visibleEdges}
            onNodeClick={(slug) => dispatchFilters({ type: "setSelectedNodeId", value: slug })}
            onNodeDoubleClick={openGraphNode}
            externalHighlightNodeId={hoveredInsightNodeId}
            externalHighlightType={hoveredInsightType}
            density={graphScope === "all" ? "dense" : "normal"}
            vaultCentroids={graphScope === "all" ? vaultCentroids : undefined}
            onFullscreen={() => setShowFullGraph(true)}
          />
        )}
      </div>
      <aside className="graph-detail-panel" aria-label="선택 문서 상세">
        {selectedNodeDetail ? (
          <>
            <div className="graph-detail-header">
              <div>
                <strong>{selectedNodeDetail.node.title}</strong>
                <p>{nodeSlug(selectedNodeDetail.node)}</p>
                {selectedNodeDetail.node.vault && (
                  <span className="graph-vault-chip">{selectedNodeDetail.node.vault}</span>
                )}
              </div>
              <span className="graph-detail-chip">
                {selectedNodeDetail.node.type ?? "미분류"}
              </span>
            </div>
            <div className="graph-detail-stats">
              <div>
                <span>참조됨</span>
                <strong>{selectedNodeDetail.inbound.length}</strong>
              </div>
              <div>
                <span>참조함</span>
                <strong>{selectedNodeDetail.outbound.length}</strong>
              </div>
              <div>
                <span>관련</span>
                <strong>{selectedNodeDetail.neighbors.length}</strong>
              </div>
            </div>
            <div className="graph-detail-actions">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => {
                  dispatchFilters({ type: "setQuery", value: selectedNodeDetail.node.title });
                  dispatchFilters({ type: "setSelectedType", value: "all" });
                }}
              >
                이 문서로 포커스
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => openGraphNode(selectedNodeDetail.node.id)}
              >
                문서 열기
              </Button>
            </div>
            <div className="graph-detail-section">
              <h3>나를 참조한 문서</h3>
              {selectedNodeDetail.inbound.length > 0 ? (
                <ul className="graph-detail-list">
                  {selectedNodeDetail.inbound.slice(0, 8).map((node) => (
                    <li key={node.id}>
                      <button
                        type="button"
                        className="graph-detail-link"
                        onClick={() => dispatchFilters({ type: "setSelectedNodeId", value: node.id })}
                        onMouseEnter={() => setHoveredInsightNodeId(node.id)}
                        onMouseLeave={() => setHoveredInsightNodeId(null)}
                      >
                        <span>{node.title}</span>
                        <span>
                          {node.vault && <span className="graph-vault-chip">{node.vault}</span>}
                          {node.type ?? "미분류"}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="graph-insight-empty">이 문서를 참조하는 문서가 아직 없습니다.</p>
              )}
            </div>
            <div className="graph-detail-section">
              <h3>내가 참조한 문서</h3>
              {selectedNodeDetail.outbound.length > 0 ? (
                <ul className="graph-detail-list">
                  {selectedNodeDetail.outbound.slice(0, 8).map((node) => (
                    <li key={node.id}>
                      <button
                        type="button"
                        className="graph-detail-link"
                        onClick={() => dispatchFilters({ type: "setSelectedNodeId", value: node.id })}
                        onMouseEnter={() => setHoveredInsightNodeId(node.id)}
                        onMouseLeave={() => setHoveredInsightNodeId(null)}
                      >
                        <span>{node.title}</span>
                        <span>
                          {node.vault && <span className="graph-vault-chip">{node.vault}</span>}
                          {node.type ?? "미분류"}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="graph-insight-empty">이 문서가 참조하는 문서가 아직 없습니다.</p>
              )}
            </div>
            <div className="graph-detail-section">
              <h3>관련 문서</h3>
              {selectedNodeDetail.neighbors.length > 0 ? (
                <ul className="graph-detail-list">
                  {selectedNodeDetail.neighbors.slice(0, 8).map((node) => (
                    <li key={node.id}>
                      <button
                        type="button"
                        className="graph-detail-link"
                        onClick={() => dispatchFilters({ type: "setSelectedNodeId", value: node.id })}
                        onMouseEnter={() => setHoveredInsightNodeId(node.id)}
                        onMouseLeave={() => setHoveredInsightNodeId(null)}
                      >
                        <span>{node.title}</span>
                        <span>
                          {node.vault && <span className="graph-vault-chip">{node.vault}</span>}
                          {node.type ?? "미분류"}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="graph-insight-empty">아직 연결된 문서가 없습니다.</p>
              )}
            </div>
          </>
        ) : (
          <div className="graph-detail-empty">
            <strong>노드를 선택해 주세요</strong>
            <p>그래프 위 문서를 클릭하면 관련 문서와 이동 액션을 여기서 바로 확인할 수 있습니다.</p>
          </div>
        )}
      </aside>
      </div>

      <details className="graph-mobile-panel graph-mobile-only">
        <summary>모바일 세부 옵션</summary>
        <div className="graph-mobile-panel-body">
          {controlsSection}
        </div>
      </details>

      {showFullGraph && graph.nodes.length > 0 && (
        <FullscreenGraphModal
          vault={vault}
          nodes={graph.nodes}
          edges={graph.edges}
          centerTitle={graphScope === "all" ? "전체 vault 우주 지도" : `${vault} 전체 그래프`}
          onClose={() => setShowFullGraph(false)}
        />
      )}
    </div>
  );
}
