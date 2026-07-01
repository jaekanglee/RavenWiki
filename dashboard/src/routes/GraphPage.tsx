import { useEffect, useMemo, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { COMMUNITY_PALETTE, GraphCanvas } from "../components/GraphCanvas";
import type { Graph, GraphNode } from "../types";
import { EmptyState } from "../components/ui/EmptyState";
import { PageHeader } from "../components/ui/PageHeader";
import { TextField } from "../components/ui/TextField";
import { SelectField } from "../components/ui/SelectField";
import { Button } from "../components/ui/Button";

type GraphLayout = "atlas" | "constellation" | "spring";

interface GraphFilterState {
  hideOrphans: boolean;
  query: string;
  selectedType: string;
  selectedCommunity: number | null;
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

function normalizeGraphText(value: string | undefined): string {
  return (value ?? "").trim().toLowerCase();
}

function matchesGraphQuery(node: GraphNode, query: string): boolean {
  const normalized = normalizeGraphText(query);
  if (!normalized) return true;
  return [node.title, node.slug, node.type]
    .map(normalizeGraphText)
    .some((token) => token.includes(normalized));
}

export function deriveGraphInsights(graph: Graph): GraphInsight {
  const sortedNodes = [...graph.nodes].sort((a, b) => {
    const weightDiff = (b.weight ?? 0) - (a.weight ?? 0);
    if (weightDiff !== 0) return weightDiff;
    return (a.title ?? a.slug).localeCompare(b.title ?? b.slug, "ko");
  });

  const topConnected = sortedNodes.filter((node) => (node.weight ?? 0) > 0).slice(0, 5);
  const topOrphans = [...graph.nodes]
    .filter((node) => (node.weight ?? 0) === 0)
    .sort((a, b) => (a.title ?? a.slug).localeCompare(b.title ?? b.slug, "ko"))
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
  const node = graph.nodes.find((item) => (item.id ?? item.slug) === nodeId);
  if (!node) return null;

  const nodeMap = new Map(graph.nodes.map((item) => [item.id ?? item.slug, item]));
  const inboundIds = new Set<string>();
  const outboundIds = new Set<string>();

  for (const edge of graph.edges) {
    const source = (edge as any).source ?? edge.source_slug;
    const target = (edge as any).target ?? edge.target_slug;
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

  const visibleMap = new Map(visibleByType.map((node) => [node.id ?? node.slug, node]));
  const normalizedQuery = normalizeGraphText(filters.query);

  let nodeIds = new Set(visibleByType.map((node) => node.id ?? node.slug));
  if (normalizedQuery) {
    const matchedIds = new Set(
      visibleByType
        .filter((node) => matchesGraphQuery(node, normalizedQuery))
        .map((node) => node.id ?? node.slug)
    );

    if (matchedIds.size > 0) {
      const expandedIds = new Set(matchedIds);
      for (const edge of graph.edges) {
        const source = (edge as any).source ?? edge.source_slug;
        const target = (edge as any).target ?? edge.target_slug;
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

  const nodes = visibleByType.filter((node) => nodeIds.has(node.id ?? node.slug));
  const ids = new Set(nodes.map((node) => node.id ?? node.slug));
  const edges = graph.edges.filter((edge) => {
    const source = (edge as any).source ?? edge.source_slug;
    const target = (edge as any).target ?? edge.target_slug;
    return ids.has(source) && ids.has(target);
  });

  return { nodes, edges };
}

/**
 * GraphPage — dark xyflow canvas + orphan hide toggle + community color toggle.
 * v0.6.10+: 백엔드가 nodes[i].x/y force-directed 좌표 제공.
 * v0.6.14+: default layout = atlas.
 * v0.6.15+: ?community=modularity 옵션. 켜면 노드 색상이 type 대신 Louvain
 *   community id별로 결정 (구조 기반 색). hover 시 같은 community 노드도 highlight.
 * v0.7.35+: search/type/layout controls + insight cards for graph exploration.
 */
export function GraphPage() {
  const [graph, setGraph] = useState<Graph>({ nodes: [], edges: [] });
  const [hideOrphans, setHideOrphans] = useState(true);
  const [useCommunity, setUseCommunity] = useState(false);
  const [layout, setLayout] = useState<GraphLayout>("atlas");
  const [query, setQuery] = useState("");
  const [selectedType, setSelectedType] = useState("all");
  const [selectedCommunity, setSelectedCommunity] = useState<number | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [hoveredInsightNodeId, setHoveredInsightNodeId] = useState<string | null>(null);
  const [hoveredInsightType, setHoveredInsightType] = useState<string | null>(null);
  const navigate = useNavigate();
  const { vault } = useOutletContext<{ vault: string }>();

  const resetGraphFilters = () => {
    setQuery("");
    setSelectedType("all");
    setSelectedCommunity(null);
    setLayout("atlas");
    setHideOrphans(true);
    setUseCommunity(false);
    setSelectedNodeId(null);
    setHoveredInsightNodeId(null);
    setHoveredInsightType(null);
  };

  const loadGraph = () => {
    if (!vault) return;
    setLoading(true);
    setLoadError(false);
    const url = `/api/vaults/${encodeURIComponent(vault)}/graph?layout=${layout}&community=${
      useCommunity ? "modularity" : "none"
    }`;
    fetch(url)
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
  }, [vault, useCommunity, layout]);

  const filteredGraph = useMemo(
    () =>
      filterGraphView(graph, {
        hideOrphans,
        query,
        selectedType,
        selectedCommunity,
      }),
    [graph, hideOrphans, query, selectedType, selectedCommunity]
  );

  const visibleNodes = filteredGraph.nodes;
  const visibleEdges = filteredGraph.edges;

  const orphanCount = useMemo(
    () => graph.nodes.filter((n) => (n.weight ?? 0) === 0).length,
    [graph.nodes]
  );

  const communityCount = useMemo(
    () =>
      new Set(
        visibleNodes
          .map((n) => n.community)
          .filter((c): c is number => typeof c === "number" && c >= 0)
      ).size,
    [visibleNodes]
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
        label: `${type} (${count})`,
      })),
    ],
    [graphInsights.typeBreakdown]
  );

  const hasAnyNodes = graph.nodes.length > 0;
  const hasVisibleNodes = visibleNodes.length > 0;
  const hasActiveFilter =
    query.trim().length > 0 ||
    selectedType !== "all" ||
    selectedCommunity !== null ||
    layout !== "atlas" ||
    !hideOrphans ||
    useCommunity;

  const controlsSection = (
    <div className="graph-page-control-grid">
      <TextField
        label="문서 검색"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="제목, slug, type으로 필터"
        helper="검색 시 일치 문서와 1-hop 이웃만 남겨 맥락을 유지합니다."
      />
      <SelectField
        label="레이아웃"
        value={layout}
        onChange={(e) => setLayout(e.target.value as GraphLayout)}
        options={[
          { value: "atlas", label: "Atlas" },
          { value: "constellation", label: "Constellation" },
          { value: "spring", label: "Spring" },
        ]}
        helper="API가 지원하는 서버 계산 레이아웃을 즉시 전환합니다."
      />
      <SelectField
        label="타입 필터"
        value={selectedType}
        onChange={(e) => setSelectedType(e.target.value)}
        options={typeOptions}
        helper="특정 문서 타입만 남겨 구조를 집중 탐색합니다."
      />
      <div className="graph-page-actions">
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
          그래프 다시 계산
        </Button>
      </div>
    </div>
  );

  const insightsSection = hasAnyNodes ? (
    <div className="graph-page-insights">
      <section className="graph-insight-card">
        <div className="graph-insight-card-header">
          <strong>핵심 허브</strong>
          <span>가장 많이 참조되는 문서</span>
        </div>
        {graphInsights.topConnected.length > 0 ? (
          <ul className="graph-insight-list">
            {graphInsights.topConnected.map((node) => (
              <li key={node.id ?? node.slug}>
                <button
                  type="button"
                  className="graph-insight-link"
                  onClick={() => navigate(`/page/${vault}/${node.slug}`)}
                  onMouseEnter={() => setHoveredInsightNodeId(node.id ?? node.slug)}
                  onMouseLeave={() => setHoveredInsightNodeId(null)}
                >
                  <span>{node.title}</span>
                  <span>{node.weight ?? 0} links</span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="graph-insight-empty">아직 참조 허브가 없습니다.</p>
        )}
      </section>

      <section className="graph-insight-card">
        <div className="graph-insight-card-header">
          <strong>고립 문서</strong>
          <span>연결되지 않은 문서 후보</span>
        </div>
        {graphInsights.topOrphans.length > 0 ? (
          <ul className="graph-insight-list">
            {graphInsights.topOrphans.map((node) => (
              <li key={node.id ?? node.slug}>
                <button
                  type="button"
                  className="graph-insight-link"
                  onClick={() => navigate(`/page/${vault}/${node.slug}`)}
                  onMouseEnter={() => setHoveredInsightNodeId(node.id ?? node.slug)}
                  onMouseLeave={() => setHoveredInsightNodeId(null)}
                >
                  <span>{node.title}</span>
                  <span>{node.type ?? "미분류"}</span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="graph-insight-empty">모든 문서가 최소 한 번은 연결돼 있습니다.</p>
        )}
      </section>

      <section className="graph-insight-card">
        <div className="graph-insight-card-header">
          <strong>타입 분포</strong>
          <span>지금 보관소의 문서 성격</span>
        </div>
        {graphInsights.typeBreakdown.length > 0 ? (
          <ul className="graph-insight-list">
            {graphInsights.typeBreakdown.slice(0, 5).map(({ type, count }) => (
              <li key={type}>
                <button
                  type="button"
                  className={`graph-insight-link${selectedType === type ? " graph-insight-link-active" : ""}`}
                  onClick={() => {
                    setSelectedType(type);
                    setSelectedCommunity(null);
                  }}
                  onMouseEnter={() => setHoveredInsightType(type)}
                  onMouseLeave={() => setHoveredInsightType(null)}
                >
                  <span>{type}</span>
                  <span>{count} docs</span>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="graph-insight-empty">타입 통계가 아직 없습니다.</p>
        )}
      </section>
    </div>
  ) : null;

  useEffect(() => {
    if (!selectedNodeId) return;
    const stillVisible = visibleNodes.some((node) => (node.id ?? node.slug) === selectedNodeId);
    if (!stillVisible) setSelectedNodeId(null);
  }, [selectedNodeId, visibleNodes]);

  return (
    <div className="graph-page-shell">
      <div className="graph-page-toolbar">
        <PageHeader
          title="그래프"
          contextLabel={`${vault} 보관소`}
          subtitle="문서 연결 구조를 탐색하고, 연결이 약한 영역과 집중 허브를 빠르게 파악합니다."
          titleSize={22}
          bottomSpacing={0}
        />
        <div className="graph-page-meta" aria-label="그래프 상태">
          <span>{loading ? "그래프 계산 중…" : `문서 ${visibleNodes.length}/${graph.nodes.length}`}</span>
          <span>{loading ? "잠시만 기다려 주세요" : `연결 ${visibleEdges.length}`}</span>
          <span>레이아웃 {layout}</span>
          {useCommunity && communityCount > 0 && <span>커뮤니티 {communityCount}</span>}
          {orphanCount > 0 && hideOrphans && <span>고아 {orphanCount}개 숨김</span>}
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

      <div className="graph-desktop-only">
        {controlsSection}
        {insightsSection}
      </div>

      <div className="graph-page-workspace">
      <div className="graph-canvas-frame">
        {loading ? (
          <EmptyState
            icon="🕸"
            title="그래프를 불러오는 중입니다"
            description="문서 연결과 커뮤니티 구조를 계산하고 있습니다."
          />
        ) : loadError ? (
          <EmptyState
            icon="⚠️"
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
            icon="🗂"
            title="아직 시각화할 문서가 없습니다"
            description="현재 보관소에 문서를 추가하면 연결 그래프가 여기에 표시됩니다."
          />
        ) : !hasVisibleNodes && hideOrphans && orphanCount === graph.nodes.length ? (
          <EmptyState
            icon="🌫"
            title="지금은 모두 고아 문서입니다"
            description="`고아 숨김`을 끄면 문서는 보이지만 아직 서로 연결되지 않았다는 뜻입니다."
            action={(
              <button
                type="button"
                className="btn-secondary"
                style={{ height: 36, padding: "8px 14px", fontSize: 13 }}
                onClick={() => setHideOrphans(false)}
              >
                고아 문서 보기
              </button>
            )}
          />
        ) : !hasVisibleNodes ? (
          <EmptyState
            icon="🔎"
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
            onNodeInspect={(node) => setSelectedNodeId(node.id ?? node.slug)}
            onNodeClick={(slug) => navigate(`/page/${vault}/${slug}`)}
            onNodeDoubleClick={(slug) => navigate(`/page/${vault}/${slug}`)}
            externalHighlightNodeId={hoveredInsightNodeId}
            externalHighlightType={hoveredInsightType}
          />
        )}
      </div>
      <aside className="graph-detail-panel" aria-label="선택 문서 상세">
        {selectedNodeDetail ? (
          <>
            <div className="graph-detail-header">
              <div>
                <strong>{selectedNodeDetail.node.title}</strong>
                <p>{selectedNodeDetail.node.slug}</p>
              </div>
              <span className="graph-detail-chip">
                {selectedNodeDetail.node.type ?? "미분류"}
              </span>
            </div>
            <div className="graph-detail-stats">
              <div>
                <span>인바운드</span>
                <strong>{selectedNodeDetail.inbound.length}</strong>
              </div>
              <div>
                <span>아웃바운드</span>
                <strong>{selectedNodeDetail.outbound.length}</strong>
              </div>
              <div>
                <span>이웃</span>
                <strong>{selectedNodeDetail.neighbors.length}</strong>
              </div>
            </div>
            {typeof selectedNodeDetail.node.community === "number" && selectedNodeDetail.node.community >= 0 && (
              <button
                type="button"
                className={`graph-detail-community-chip${
                  selectedCommunity === selectedNodeDetail.node.community ? " graph-detail-community-chip-active" : ""
                }`}
                onClick={() =>
                  setSelectedCommunity((prev) =>
                    prev === selectedNodeDetail.node.community ? null : selectedNodeDetail.node.community ?? null
                  )
                }
              >
                커뮤니티 #{selectedNodeDetail.node.community}
              </button>
            )}
            <div className="graph-detail-actions">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => {
                  setQuery(selectedNodeDetail.node.title);
                  setSelectedType("all");
                  setSelectedCommunity(null);
                }}
              >
                이 문서로 포커스
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => navigate(`/page/${vault}/${selectedNodeDetail.node.slug}`)}
              >
                문서 열기
              </Button>
            </div>
            <div className="graph-detail-section">
              <h3>들어오는 연결</h3>
              {selectedNodeDetail.inbound.length > 0 ? (
                <ul className="graph-detail-list">
                  {selectedNodeDetail.inbound.slice(0, 8).map((node) => (
                    <li key={node.id ?? node.slug}>
                      <button
                        type="button"
                        className="graph-detail-link"
                        onClick={() => setSelectedNodeId(node.id ?? node.slug)}
                        onMouseEnter={() => setHoveredInsightNodeId(node.id ?? node.slug)}
                        onMouseLeave={() => setHoveredInsightNodeId(null)}
                      >
                        <span>{node.title}</span>
                        <span>{node.type ?? "미분류"}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="graph-insight-empty">이 문서를 참조하는 문서가 아직 없습니다.</p>
              )}
            </div>
            <div className="graph-detail-section">
              <h3>나가는 연결</h3>
              {selectedNodeDetail.outbound.length > 0 ? (
                <ul className="graph-detail-list">
                  {selectedNodeDetail.outbound.slice(0, 8).map((node) => (
                    <li key={node.id ?? node.slug}>
                      <button
                        type="button"
                        className="graph-detail-link"
                        onClick={() => setSelectedNodeId(node.id ?? node.slug)}
                        onMouseEnter={() => setHoveredInsightNodeId(node.id ?? node.slug)}
                        onMouseLeave={() => setHoveredInsightNodeId(null)}
                      >
                        <span>{node.title}</span>
                        <span>{node.type ?? "미분류"}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="graph-insight-empty">이 문서가 참조하는 문서가 아직 없습니다.</p>
              )}
            </div>
            <div className="graph-detail-section">
              <h3>전체 이웃</h3>
              {selectedNodeDetail.neighbors.length > 0 ? (
                <ul className="graph-detail-list">
                  {selectedNodeDetail.neighbors.slice(0, 8).map((node) => (
                    <li key={node.id ?? node.slug}>
                      <button
                        type="button"
                        className="graph-detail-link"
                        onClick={() => setSelectedNodeId(node.id ?? node.slug)}
                        onMouseEnter={() => setHoveredInsightNodeId(node.id ?? node.slug)}
                        onMouseLeave={() => setHoveredInsightNodeId(null)}
                      >
                        <span>{node.title}</span>
                        <span>{node.type ?? "미분류"}</span>
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
            <p>그래프 위 문서를 hover하거나 탭하면 연결 구조와 이동 액션을 여기서 바로 확인할 수 있습니다.</p>
          </div>
        )}
      </aside>
      </div>

      <details className="graph-mobile-panel graph-mobile-only">
        <summary>모바일 세부 옵션</summary>
        <div className="graph-mobile-panel-body">
          {controlsSection}
          {insightsSection}
        </div>
      </details>
    </div>
  );
}
