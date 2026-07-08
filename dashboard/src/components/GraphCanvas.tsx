import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph from "force-graph";
import type { GraphNode, GraphEdge } from "../types";

interface Props {
  nodes: GraphNode[];
  edges: GraphEdge[];
  /** hover/click 시 선택 노드 메타를 상위 UI에 전달 */
  onNodeInspect?: (node: GraphNode) => void;
  /** single click — 데스크탑 전용 (페이지 이동) */
  onNodeClick?: (slug: string) => void;
  /** double click / double tap — 페이지 이동 */
  onNodeDoubleClick?: (slug: string) => void;
  /** 외부(인사이트 카드 등)에서 하이라이트 요청한 노드 ID */
  externalHighlightNodeId?: string | null;
  /** 현재 문서처럼 항상 강조해야 하는 노드 ID */
  persistentHighlightNodeId?: string | null;
  /** 외부에서 하이라이트 요청한 문서 타입 */
  externalHighlightType?: string | null;
  /** 전체화면 모달 요청 — 상위 컴포넌트가 모달을 열어 처리 */
  onFullscreen?: () => void;
  /** all-vault 등 고밀도 그래프에서는 기본 라벨/엣지를 낮춰 지도 시인성을 우선한다. */
  density?: "normal" | "dense";
  /** all-vault 모드에서 vault 소속을 보여주는 centroid + halo 표식. */
  vaultCentroids?: VaultCentroid[];
  /** 노드 드래그 종료 시점에 호출 */
  onPositionsChange?: (positions: Record<string, { x: number; y: number }>) => void;
}

export interface VaultCentroid {
  vault: string;
  x: number;
  y: number;
  /** vault 별 halo 반경 — vault 내 노드 분포 + count 기반. */
  radius: number;
}

// SCHEMA 9종(v0.7.44+) — type별 노드 색상. 미분류/미인식 → default gray.
const TYPE_COLORS: Record<string, string> = {
  concept: "#22c55e",
  person: "#ec4899",
  tool: "#6b7280",
  comparison: "#ef4444",
  project: "#f97316",
  rule: "#6366f1",
  query: "#eab308",
  journal: "#06b6d4",
  issue: "#a855f7",
};
const DEFAULT_COLOR = "#9ca3af";

export function nodeColor(type: string | undefined): string {
  if (!type) return DEFAULT_COLOR;
  return TYPE_COLORS[type] ?? DEFAULT_COLOR;
}

export function nodeSize(weight: number | undefined): number {
  return 4 + Math.sqrt(Math.max(weight ?? 1, 1)) * 2.5;
}

// Sidebar와 GraphPage에서 사용하는 타입 라벨 매핑 및 typeLabel 헬퍼 복원 (v0.7.132+)
const TYPE_LABELS: Record<string, string> = {
  concept: "개념",
  person: "인물",
  tool: "도구",
  comparison: "비교",
  project: "프로젝트",
  rule: "규칙",
  query: "Q&A",
  journal: "일지",
  issue: "이슈",
};

export function typeLabel(type: string | undefined): string {
  if (!type) return "";
  return TYPE_LABELS[type] ?? "";
}

const isJSDOM =
  typeof window !== "undefined" &&
  (window.navigator.userAgent.includes("jsdom") ||
    window.navigator.userAgent.includes("Node.js"));

const GRAPH_SCALE_MULTIPLIER = 2.8;

// Vault Halo 색상 스키마
const VAULT_HALO_COLORS = [
  "#3b82f6", // blue
  "#10b981", // green
  "#8b5cf6", // purple
  "#f59e0b", // amber
  "#ec4899", // pink
  "#06b6d4", // cyan
];

function resolveVaultColor(vaultName: string): string {
  let hash = 0;
  for (let i = 0; i < vaultName.length; i++) {
    hash = vaultName.charCodeAt(i) + ((hash << 5) - hash);
  }
  const idx = Math.abs(hash) % VAULT_HALO_COLORS.length;
  return VAULT_HALO_COLORS[idx];
}

function drawRoundedRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number
) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
}

const graphButtonStyle = {
  border: "1px solid var(--graph-border)",
  background: "var(--graph-surface)",
  color: "var(--graph-text)",
  borderRadius: 999,
  padding: "6px 10px",
  fontSize: 12,
  fontWeight: 600,
  cursor: "pointer",
  backdropFilter: "blur(8px)",
} as const;

export function GraphCanvas({
  nodes,
  edges,
  onNodeInspect,
  onNodeClick,
  onNodeDoubleClick,
  externalHighlightNodeId,
  persistentHighlightNodeId,
  externalHighlightType,
  onFullscreen,
  density = "normal",
  vaultCentroids,
  onPositionsChange,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const graphInstanceRef = useRef<any>(null);
  const isDense = density === "dense";

  const [interactionMode, setInteractionMode] = useState<"pointer" | "hand">(
    isDense ? "hand" : "pointer"
  );
  const [hoveredNode, setHoveredNode] = useState<any>(null);

  // 1. 하이라이트 및 인접 관계 집합 계산
  const highlightNodes = useMemo(() => {
    const set = new Set<string>();
    if (hoveredNode) {
      set.add(hoveredNode.id);
      edges.forEach((e) => {
        if (e.source === hoveredNode.id) set.add(e.target);
        if (e.target === hoveredNode.id) set.add(e.source);
      });
    }
    if (externalHighlightNodeId) {
      set.add(externalHighlightNodeId);
      edges.forEach((e) => {
        if (e.source === externalHighlightNodeId) set.add(e.target);
        if (e.target === externalHighlightNodeId) set.add(e.source);
      });
    }
    return set;
  }, [hoveredNode, externalHighlightNodeId, edges]);

  const highlightLinks = useMemo(() => {
    const set = new Set<string>();
    edges.forEach((e, idx) => {
      const id = `e${idx}`;
      if (hoveredNode && (e.source === hoveredNode.id || e.target === hoveredNode.id)) {
        set.add(id);
      }
      if (
        externalHighlightNodeId &&
        (e.source === externalHighlightNodeId || e.target === externalHighlightNodeId)
      ) {
        set.add(id);
      }
    });
    return set;
  }, [hoveredNode, externalHighlightNodeId, edges]);

  // Space 단축키 처리
  useEffect(() => {
    if (typeof window === "undefined") return;

    const handleKeyDown = (e: KeyboardEvent) => {
      const activeEl = document.activeElement;
      if (
        activeEl &&
        (activeEl.tagName === "INPUT" ||
          activeEl.tagName === "TEXTAREA" ||
          activeEl.getAttribute("contenteditable") === "true")
      ) {
        return;
      }

      if (e.code === "Space") {
        e.preventDefault();
        setInteractionMode("hand");
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === "Space") {
        setInteractionMode(isDense ? "hand" : "pointer");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, [isDense]);

  // 2. force-graph 인스턴스 초기 생성 (런타임 callable 우회를 위해 캐스팅 및 default export 감지 방어 적용)
  useEffect(() => {
    if (isJSDOM || !containerRef.current) return;

    const ForceGraphConstructor = typeof ForceGraph === "function"
      ? ForceGraph
      : (ForceGraph as any).default || ForceGraph;

    if (typeof ForceGraphConstructor !== "function") {
      console.error("ForceGraph is not a function! Check import:", ForceGraph);
      return;
    }

    const graph = (ForceGraphConstructor as any)()(containerRef.current);
    graphInstanceRef.current = graph;

    // 초기 물리 설정 제거 (정적 레이아웃 사용)
    graph.d3Force("charge", null);
    graph.d3Force("link", null);
    graph.d3Force("center", null);

    // 인터랙션 기본 설정
    graph.cooldownTime(0); // 물리 애니메이션 냉각 단축
    graph.enableZoomInteraction(true);
    graph.enablePanInteraction(true);

    return () => {
      if (graphInstanceRef.current) {
        graphInstanceRef.current._destructor?.();
      }
    };
  }, []);

  // 3. Props 및 인터랙션 상태 변경 시 그래프 동기화
  useEffect(() => {
    if (isJSDOM) return;
    const graph = graphInstanceRef.current;
    if (!graph) return;

    // 데이터 가공 (fx/fy 고정으로 FA2 레이아웃 반영 및 뭉침 방지를 위한 스케일 배율 적용)
    const formattedNodes = nodes.map((n) => ({
      ...n,
      fx: typeof n.x === "number" ? n.x * GRAPH_SCALE_MULTIPLIER : undefined,
      fy: typeof n.y === "number" ? n.y * GRAPH_SCALE_MULTIPLIER : undefined,
    }));

    const formattedLinks = edges.map((e, idx) => ({
      id: `e${idx}`,
      source: e.source,
      target: e.target,
    }));

    graph.graphData({ nodes: formattedNodes, links: formattedLinks });

    // 드래그 제어
    graph.enableNodeDrag(!isDense && interactionMode === "pointer");

    // 이벤트 리스너 바인딩
    let lastClick = 0;
    graph
      .onNodeClick((node: any) => {
        const now = Date.now();
        if (now - lastClick < 280) {
          onNodeDoubleClick?.(node.id);
        } else {
          onNodeClick?.(node.id);
        }
        lastClick = now;
      })
      .onNodeHover((node: any) => {
        if (node) {
          onNodeInspect?.(node as GraphNode);
          setHoveredNode(node);
        } else {
          setHoveredNode(null);
        }
      })
      .onNodeDragEnd((node: any) => {
        node.fx = node.x;
        node.fy = node.y;
        onPositionsChange?.({
          [node.id]: {
            x: node.x / GRAPH_SCALE_MULTIPLIER,
            y: node.y / GRAPH_SCALE_MULTIPLIER,
          },
        });
      });

    // 엣지 스타일 정의
    const crossVaultEdgeIds = new Set<string>();
    if (isDense) {
      edges.forEach((edge, idx) => {
        const srcVault = String(edge.source).split(":", 1)[0];
        const tgtVault = String(edge.target).split(":", 1)[0];
        if (srcVault !== tgtVault) {
          crossVaultEdgeIds.add(`e${idx}`);
        }
      });
    }

    graph
      .linkColor((link: any) => {
        const isHighlighted = highlightLinks.has(link.id);
        return isHighlighted
          ? "var(--graph-edge-highlight)"
          : "var(--graph-edge)";
      })
      .linkWidth((link: any) => {
        const isHighlighted = highlightLinks.has(link.id);
        return isHighlighted ? 2.2 : 0.8;
      })
      // 하이라이트 시 연결선을 타고 흐르는 이펙트 적용 (Premium Wow-factor)
      .linkDirectionalParticles((link: any) => {
        const isHighlighted = highlightLinks.has(link.id);
        return isHighlighted ? 4 : 0;
      })
      .linkDirectionalParticleWidth(2.6)
      .linkDirectionalParticleSpeed(0.016);

    // 노드 스타일 커스텀 렌더링 (Obsidian 퀄리티 재현)
    graph.nodeCanvasObject((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      if (!node || node.x === undefined || node.y === undefined) return;
      const scale = globalScale || 1;
      const size = nodeSize(node.weight);
      const isHovered = hoveredNode && hoveredNode.id === node.id;
      const isHighlighted = highlightNodes.has(node.id);
      const isPersistent = persistentHighlightNodeId === node.id;
      const isFocused =
        isHovered || isPersistent || externalHighlightNodeId === node.id;

      // 1. 노드 본체 (원)
      ctx.beginPath();
      ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);
      
      // 흐릿한 비포커스 처리
      const hasFocusActive = externalHighlightNodeId || hoveredNode || externalHighlightType;
      ctx.fillStyle = hasFocusActive && !isFocused && !isHighlighted
        ? `${nodeColor(node.type)}36`
        : nodeColor(node.type);
      ctx.fill();

      // 테두리 선
      ctx.lineWidth = isFocused ? 2 / scale : 0.8 / scale;
      ctx.strokeStyle = isFocused
        ? "var(--graph-edge-highlight)"
        : isHighlighted
        ? "rgba(255, 255, 255, 0.7)"
        : "var(--graph-node-outline)";
      ctx.stroke();

      // 이중 링 효과
      if (isFocused) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, size + 2.5 / scale, 0, 2 * Math.PI, false);
        ctx.strokeStyle = "var(--graph-edge-highlight)";
        ctx.lineWidth = 0.8 / scale;
        ctx.stroke();
      }

      // 2. 텍스트 라벨 그리기 (LOD - Level of Detail)
      // dense(all-vault)에서는 라벨을 훨씬 보수적으로 노출해 "떡처럼 붙는" 현상을 줄인다.
      // current scope도 무조건 상시 노출 대신 zoom/중요도(weight) 기준을 둬 시야를 정리한다.
      const canShowDenseLabel = scale > 1.15 && (node.weight ?? 0) >= 3;
      const canShowNormalLabel = scale > 0.85 || (node.weight ?? 0) >= 6;
      const showLabel = isFocused || isHighlighted || (isDense ? canShowDenseLabel : canShowNormalLabel);
      if (showLabel) {
        const label = node.title || node.slug || node.id;
        const fontSize = 10.5 / scale;
        ctx.font = `${isFocused ? "bold" : "normal"} ${fontSize}px sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";

        // 텍스트 뒷배경 대비용 아웃라인
        ctx.fillStyle = "var(--graph-canvas-bg)";
        for (let dx = -1.2; dx <= 1.2; dx += 1.2) {
          for (let dy = -1.2; dy <= 1.2; dy += 1.2) {
            if (dx !== 0 || dy !== 0) {
              ctx.fillText(
                label,
                node.x + dx * (0.5 / scale),
                node.y + size + 3.8 / scale + dy * (0.5 / scale)
              );
            }
          }
        }

        ctx.fillStyle = isFocused
          ? "var(--graph-edge-highlight)"
          : "var(--graph-label-color)";
        ctx.fillText(label, node.x, node.y + size + 3.8 / scale);
      }
    });

    // Vault Centroids 및 Halo 배경 렌더링
    graph.onRenderFramePre((ctx: CanvasRenderingContext2D, globalScale: number) => {
      if (!vaultCentroids || vaultCentroids.length === 0) return;
      const scale = globalScale || 1;

      vaultCentroids.forEach((vc) => {
        if (
          !vc ||
          !Number.isFinite(vc.x) ||
          !Number.isFinite(vc.y) ||
          !Number.isFinite(vc.radius) ||
          vc.radius <= 0
        ) {
          return;
        }
        const resolvedColor = resolveVaultColor(vc.vault);

        const cx = vc.x * GRAPH_SCALE_MULTIPLIER;
        const cy = vc.y * GRAPH_SCALE_MULTIPLIER;
        const cradius = vc.radius * GRAPH_SCALE_MULTIPLIER;

        // 1. Halo Radial Gradient 배경 원 그리기
        ctx.beginPath();
        const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, cradius);
        grad.addColorStop(0, resolvedColor + "22");
        grad.addColorStop(0.6, resolvedColor + "08");
        grad.addColorStop(1, "transparent");

        ctx.fillStyle = grad;
        ctx.arc(cx, cy, cradius, 0, 2 * Math.PI);
        ctx.fill();

        // 2. Centroid Label 그리기 (📁 Vault이름)
        const fontSize = Math.max(11, Math.min(15, 9 + 5 * scale)) / scale;
        ctx.font = `bold ${fontSize}px sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";

        const text = `📁 ${vc.vault}`;
        const textWidth = ctx.measureText(text).width;
        const padding = 5 / scale;
        
        ctx.fillStyle = "var(--graph-tooltip-bg)";
        ctx.strokeStyle = "var(--graph-tooltip-border)";
        ctx.lineWidth = 0.8 / scale;

        const boxW = textWidth + padding * 2.2;
        const boxH = fontSize + padding * 1.6;

        drawRoundedRect(
          ctx,
          cx - boxW / 2,
          cy - boxH / 2,
          boxW,
          boxH,
          5 / scale
        );
        ctx.fill();
        ctx.stroke();

        ctx.fillStyle = "var(--graph-text)";
        ctx.fillText(text, cx, cy);
      });
    });

    // fitView 1회 초기 설정
    if (nodes.length > 0) {
      setTimeout(() => {
        graph.zoomToFit(300, 32);
      }, 50);
    }
  }, [
    nodes,
    edges,
    isDense,
    interactionMode,
    vaultCentroids,
    hoveredNode,
    highlightNodes,
    highlightLinks,
    externalHighlightNodeId,
    persistentHighlightNodeId,
    externalHighlightType,
    onNodeClick,
    onNodeDoubleClick,
    onNodeInspect,
    onPositionsChange,
  ]);

  const fitGraph = () => {
    if (graphInstanceRef.current) {
      graphInstanceRef.current.zoomToFit(360, 40);
    }
  };

  const resetLayout = () => {
    if (graphInstanceRef.current) {
      // fx/fy를 임시 초기화하여 시뮬레이션을 풀고 fitView 재배치
      const { nodes: currentNodes } = graphInstanceRef.current.graphData();
      currentNodes.forEach((n: any) => {
        n.fx = undefined;
        n.fy = undefined;
      });
      graphInstanceRef.current.cooldownTime(800);
      graphInstanceRef.current.d3Force("charge", null); // force-directed simulation
      setTimeout(() => {
        graphInstanceRef.current.zoomToFit(300, 32);
      }, 100);
    }
  };

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        position: "relative",
        background: "var(--graph-canvas-bg)",
        overflow: "hidden",
      }}
    >
      {isJSDOM ? (
        <div data-testid="graph-canvas-mock" style={{ color: "var(--graph-text)", padding: 20 }}>
          [JSDOM Test Mock Graph Canvas]
        </div>
      ) : (
        <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
      )}

      {/* 툴바 컨트롤 레이어 */}
      <div
        style={{
          position: "absolute",
          right: 12,
          top: 12,
          zIndex: 10,
          display: "flex",
          gap: 8,
          pointerEvents: "auto",
        }}
      >
        <button
          type="button"
          onClick={() => setInteractionMode((m) => (m === "pointer" ? "hand" : "pointer"))}
          style={{
            ...graphButtonStyle,
            background:
              interactionMode === "hand"
                ? "var(--graph-edge-highlight)"
                : "var(--graph-surface)",
            color: interactionMode === "hand" ? "#ffffff" : "var(--graph-text)",
            borderColor:
              interactionMode === "hand"
                ? "var(--graph-edge-highlight)"
                : "var(--graph-border)",
          }}
          title="이동 모드(hand) 활성화 시 노드/관계선 방해 없이 자유롭게 이동/줌 가능 (단축키: Space)"
        >
          {interactionMode === "hand" ? "✋ 이동 모드" : "👆 선택 모드"}
        </button>
        {onFullscreen && (
          <button
            type="button"
            onClick={onFullscreen}
            style={graphButtonStyle}
            aria-label="그래프 전체보기"
            title="팝업으로 크게 보기"
          >
            전체보기
          </button>
        )}
        <button
          type="button"
          onClick={fitGraph}
          style={graphButtonStyle}
          aria-label="그래프 맞춤보기"
          title="모든 노드가 화면에 들어오도록 뷰를 맞춥니다"
        >
          맞춤보기
        </button>
        <button
          type="button"
          onClick={resetLayout}
          style={graphButtonStyle}
          aria-label="그래프 배치 초기화"
        >
          배치 초기화
        </button>
      </div>
    </div>
  );
}
