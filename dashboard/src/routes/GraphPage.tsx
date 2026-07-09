import { useCallback, useEffect, useMemo, useReducer, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import { GraphCanvas, typeLabel } from "../components/GraphCanvas";
import { FullscreenGraphModal } from "../components/FullscreenGraphModal";
import type { Graph, GraphNode } from "../types";
import { EmptyState } from "../components/ui/EmptyState";
import { PageHeader } from "../components/ui/PageHeader";
import { TextField } from "../components/ui/TextField";
import { SelectField } from "../components/ui/SelectField";
import { Button } from "../components/ui/Button";
import { EmptyIcon } from "../lib/emptyIcons";
import {
  deriveCommunityOptions,
  deriveGraphInsights,
  deriveNodeDetail,
  filterGraphView,
  type GraphFilterState,
  type GraphInsight,
  type GraphNodeDetail,
} from "../lib/graph/derive";

// v0.7.125+: 외부 호환을 위해 re-export. 기존 import 경로 보존하면서
// lib/graph/derive.ts가 단일 source of truth.
export {
  deriveCommunityOptions,
  deriveGraphInsights,
  deriveNodeDetail,
  filterGraphView,
} from "../lib/graph/derive";

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

type GraphScope = "all" | "current";

function nodeVault(node: GraphNode, fallbackVault: string): string {
  return node.vault || fallbackVault;
}

function nodeSlug(node: GraphNode): string {
  return node.slug ?? node.id;
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
  // v0.7.144+: graphScope 토글 제거 — current 단일 vault만 표시.
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
    // v0.7.144+: ?scope= 쿼리 제거 — current만 사용.
    fetch(`/api/vaults/${encodeURIComponent(vault)}/graph`)
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
  }, [vault]);

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

  // v0.7.144+: vaultCentroids useMemo 제거 (all-scope 모드 종료).

  // v0.7.139+: useCallback으로 안정화 — GraphCanvas의 effect deps가 매번 흔들려서
  // onNodeClick/onNodeDoubleClick 리스너가 재바인딩되는 걸 방지. 안정적이어야
  // force-graph의 클릭 디바운스(lastClick)와 mousemove 히트 판정이 깨지지 않음.
  const openGraphNode = useCallback(
    (nodeId: string) => {
      const node = graphNodeMap.get(nodeId);
      if (!node) return;
      navigate(`/page/${nodeVault(node, vault)}/${nodeSlug(node)}`);
    },
    [navigate, vault, graphNodeMap]
  );

  const handleCanvasNodeClick = useCallback(
    (nodeId: string) => {
      dispatchFilters({ type: "setSelectedNodeId", value: nodeId });
    },
    [dispatchFilters]
  );

  // v0.7.127+: current scope뿐 아니라 all-scope도 vault별로 분배 저장.
  // node.id는 current=slug, all-scope="{vault}:{slug}" 이므로 graphNodeMap의
  // node.vault/node.slug를 우선 신뢰한다. fetch 실패는 silent.
  const persistPositions = useCallback(
    (positions: Record<string, { x: number; y: number }>) => {
      if (!vault) return;
      const byVault: Record<string, Record<string, { x: number; y: number }>> = {};
      for (const [id, xy] of Object.entries(positions)) {
        const node = graphNodeMap.get(id);
        const targetVault = nodeVault(node ?? ({ id } as GraphNode), vault);
        const slug = nodeSlug(node ?? ({ id } as GraphNode));
        if (!targetVault || !slug) continue;
        byVault[targetVault] ??= {};
        byVault[targetVault][slug] = xy;
      }
      const entries = Object.entries(byVault).filter(([, pos]) => Object.keys(pos).length > 0);
      if (entries.length === 0) return;
      void Promise.allSettled(
        entries.map(([targetVault, pos]) =>
          fetch(`/api/vaults/${encodeURIComponent(targetVault)}/graph/positions`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ positions: pos }),
          })
        )
      );
    },
    [vault, graphNodeMap]
  );

  const controlsSection = (
    <div className="graph-page-control-grid">
      {/* v0.7.144+: 범위 SelectField 제거 — all-scope 모드 종료. */}
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
          contextLabel={`${vault} 보관소`}
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
            // v0.7.139+: force-graph의 onNodeClick은 node.id를 그대로 전달한다.
            // all-scope에선 id="{vault}:{slug}", current-scope에선 id=slug이므로
            // selectedNodeId는 항상 id로 통일해야 highlightNodes/edge에서 매칭됨.
            // useCallback으로 안정화해서 effect 재실행 폭발 방지 — 콜백이 매번 새 ref면
            // GraphCanvas의 effect deps가 흔들려 onNodeClick 리스너가 끊임없이 재바인딩됨.
            onNodeClick={handleCanvasNodeClick}
            onNodeDoubleClick={openGraphNode}
            // v0.7.139+: 사용자가 노드를 클릭하면 선택된 노드 + 그 인접 노드(1-hop)가
            // 캔버스에서 하이라이트되고, 나머지는 톤다운되어 포커스된다.
            // 우선순위: selectedNodeId(클릭) > hoveredInsightNodeId(인사이트 카드 hover).
            externalHighlightNodeId={selectedNodeId ?? hoveredInsightNodeId}
            externalHighlightType={hoveredInsightType}
            density="normal"
            onFullscreen={() => setShowFullGraph(true)}
            onPositionsChange={persistPositions}
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
          centerTitle={`${vault} 전체 그래프`}
          onClose={() => setShowFullGraph(false)}
        />
      )}
    </div>
  );
}
