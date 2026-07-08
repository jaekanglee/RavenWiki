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
import type { VaultCentroid } from "../../components/GraphCanvas";

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