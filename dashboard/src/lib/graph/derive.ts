/**
 * dashboard/src/lib/graph/derive.ts — 그래프 데이터 derive/filter 순수 함수.
 *
 * v0.7.125+: GraphPage.tsx에 inline되어 있던 derive/filter 로직을 분리해
 * FullscreenGraphModal, FloatingGraphPanel 등 다른 그래프 뷰에서도 재사용.
 * GraphPage.tsx는 기존 호환을 위해 re-export만 유지 (외부 import 경로 보존).
 *
 * 이 모듈은 React/xyflow/DOM에 의존하지 않는 순수 함수 — 단위 테스트와
 * 다른 라우트/컴포넌트에서 안전하게 import 가능.
 */
import type { Graph, GraphNode } from "../../types";
// v0.7.144+: VaultCentroid import + deriveVaultCentroids 함수 제거
// (all-scope 모드 종료로 client-side centroid 도출 불필요).

export interface GraphInsight {
  topConnected: GraphNode[];
  topOrphans: GraphNode[];
  typeBreakdown: Array<{ type: string; count: number }>;
}

export interface GraphNodeDetail {
  node: GraphNode;
  inbound: GraphNode[];
  outbound: GraphNode[];
  neighbors: GraphNode[];
}

export interface GraphFilterState {
  hideOrphans: boolean;
  query: string;
  selectedType: string;
  selectedCommunity: number | null;
  visibleRelations?: string[];
}

export interface CommunityOption {
  value: string;
  label: string;
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

// v0.7.144+: deriveVaultCentroids 제거 (all-scope 모드 종료로 client-side
// centroid 도출 불필요). v0.7.123~v0.7.143 동안 사용.

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
  const visibleRelations = filters.visibleRelations ?? [
    "wikilink", "uses", "depends_on", "implements", "implemented_by", "related"
  ];

  // 1. 의미 관계 유형에 따라 엣지 먼저 필터링
  const filteredEdges = graph.edges.filter((edge) => {
    const type = edge.relation_type || "wikilink";
    return visibleRelations.includes(type);
  });

  // 필터링된 엣지 기준 활성 노드 ID 집합 계산 (고립 노드 판별용)
  const activeNodeIds = new Set<string>();
  for (const edge of filteredEdges) {
    activeNodeIds.add(edge.source);
    activeNodeIds.add(edge.target);
  }

  // 2. 노드 필터링
  const visibleNodes = graph.nodes.filter((node) => {
    if (filters.hideOrphans && !activeNodeIds.has(node.id)) return false;
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

  const visibleMap = new Map(visibleNodes.map((node) => [node.id, node]));
  const normalizedQuery = normalizeGraphText(filters.query);

  let nodeIds = new Set(visibleNodes.map((node) => node.id));
  if (normalizedQuery) {
    const matchedIds = new Set(
      visibleNodes
        .filter((node) => matchesGraphQuery(node, normalizedQuery))
        .map((node) => node.id)
    );

    if (matchedIds.size > 0) {
      const expandedIds = new Set(matchedIds);
      // 필터링된 엣지를 기반으로 1-hop 확장
      for (const edge of filteredEdges) {
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

  const nodes = visibleNodes.filter((node) => nodeIds.has(node.id));
  const ids = new Set(nodes.map((node) => node.id));
  const edges = filteredEdges.filter((edge) => {
    const source = edge.source;
    const target = edge.target;
    return ids.has(source) && ids.has(target);
  });

  return { nodes, edges };
}