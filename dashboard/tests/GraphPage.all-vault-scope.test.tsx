import { describe, expect, it } from "vitest";
import GraphPageSrc from "../src/routes/GraphPage.tsx?raw";
import GraphCanvasSrc from "../src/components/GraphCanvas.tsx?raw";

/**
 * Contract tests for the all-vault GraphPage scope toggle.
 * Use ?raw so the test stays focused on API/UI contract strings and does not
 * mount ReactFlow/jsdom-heavy graph components.
 */
describe("GraphPage all-vault scope contract", () => {
  it("offers an explicit 전체 vault / 현재 vault scope toggle", () => {
    expect(GraphPageSrc).toContain('전체 vault');
    expect(GraphPageSrc).toContain('현재 vault');
    expect(GraphPageSrc).toContain('graphScope');
    expect(GraphPageSrc).toContain('setGraphScope');
  });

  it("requests the graph API with scope=all only for the all-vault universe map", () => {
    expect(GraphPageSrc).toContain('scope=all');
    expect(GraphPageSrc).toContain('scope=current');
  });

  it("renders vault chips in node detail and related-document rows", () => {
    expect(GraphPageSrc).toContain('graph-vault-chip');
    expect(GraphPageSrc).toContain('node.vault');
    expect(GraphPageSrc).toContain('selectedNodeDetail.node.vault');
  });

  it("wires all-vault scope to dense graph rendering", () => {
    expect(GraphPageSrc).toContain('density={graphScope === "all" ? "dense" : "normal"}');
    expect(GraphCanvasSrc).toContain('density?: "normal" | "dense"');
    expect(GraphCanvasSrc).toContain('const isDense = density === "dense"');
    expect(GraphCanvasSrc).toContain('const showLabel = !isDense || highlighted || persistent');
    expect(GraphCanvasSrc).toContain('const opacity = isDense ? (isCrossVault ? 0.08 : 0.18) : 0.6;');
  });

  it("renders vault halos and centroid labels only in all-vault scope", () => {
    expect(GraphPageSrc).toContain('vaultCentroids={graphScope === "all" ? vaultCentroids : undefined}');
    expect(GraphPageSrc).toContain('deriveVaultCentroids');
    expect(GraphCanvasSrc).toContain('vaultCentroids?: VaultCentroid[]');
    expect(GraphCanvasSrc).toContain('isDense && vaultScreenPositions');
    expect(GraphCanvasSrc).toContain('graph-vault-halo');
    expect(GraphCanvasSrc).toContain('graph-vault-label');
  });

  it("reprojects vault centroids to screen space on every viewport change", () => {
    // v0.7.123+: halo/label은 ReactFlow 바깥 형제라 viewport transform을 자동으로
    // 안 받는다. flowToScreenPosition + onMove로 매 pan/zoom마다 갱신해야 한다.
    // v0.7.124+: 좌표 변환 로직은 vaultScreenFromCentroids 헬퍼로 추출되어
    // mount useEffect와 handleMove가 공유한다. 헬퍼 안에 zoom 비례 radius 로직
    // (`vc.radius * zoom`)이 그대로 남아 있어야 contract가 유지된다.
    expect(GraphCanvasSrc).toContain('vaultScreenPositions');
    expect(GraphCanvasSrc).toContain('flowToScreenPosition({ x: vc.x, y: vc.y })');
    expect(GraphCanvasSrc).toMatch(/vaultScreenFromCentroids[\s\S]*?vc\.radius \* zoom/);
    // onMove 핸들러 안에서 재계산 트리거
    const handleMoveMatch = GraphCanvasSrc.match(
      /const handleMove = useCallback\(\(\) => \{[\s\S]*?setVaultScreenPositions/
    );
    expect(handleMoveMatch, "handleMove 안에서 setVaultScreenPositions 호출 안 됨").toBeTruthy();
  });

  it("lets vault halos pass through pan/zoom/click to the xyflow pane", () => {
    // halo div는 명시적 pointerEvents:none을 가져야 pane 가로채기를 막는다.
    // 부모 layer가 none이라도 자식 상속 ❌ → 명시 필수.
    const haloMatch = GraphCanvasSrc.match(
      /className="graph-vault-halo"[\s\S]*?pointerEvents: "none"/
    );
    expect(haloMatch, "graph-vault-halo div가 pointerEvents:none을 명시하지 않음").toBeTruthy();
  });

  it("does not register a dead nebula node type", () => {
    // v0.7.123+: scaleMode=PLANET 단일. NebulaNode는 v0.6.15 multiscale 잔재.
    expect(GraphCanvasSrc).not.toContain("function NebulaNode");
    expect(GraphCanvasSrc).not.toMatch(/const nodeTypes = \{[\s\S]*?nebula:/);
  });

  it("dims cross-vault edges in dense mode", () => {
    // v0.7.123+: all-vault dense 모드에서 cross-vault edge는 0.08로 강하게 dim.
    // intra-vault edge는 dense base(0.18) 유지.
    expect(GraphCanvasSrc).toContain('crossVaultEdgeIds');
    expect(GraphCanvasSrc).toMatch(/srcVault\s*!==\s*tgtVault/);
    expect(GraphCanvasSrc).toContain('const opacity = isDense ? (isCrossVault ? 0.08 : 0.18) : 0.6;');
    expect(GraphCanvasSrc).toContain('if (!focus.active) return baseDisplayEdges;');
  });

  it("culls offscreen edges only for dense large graphs", () => {
    expect(GraphCanvasSrc).toContain('const shouldCullEdges = isDense && flowEdges.length >= 400;');
    expect(GraphCanvasSrc).toContain('const [visibleNodeIds, setVisibleNodeIds] = useState<Set<string>>(new Set())');
    expect(GraphCanvasSrc).toContain('const [screenNodeCenters, setScreenNodeCenters] = useState<Map<string, { x: number; y: number }>>');
    expect(GraphCanvasSrc).toContain('recomputeVisibleNodeIds');
    expect(GraphCanvasSrc).toContain('recomputeVisibleNodeIdsNow');
    expect(GraphCanvasSrc).toContain('window.requestAnimationFrame(() => {');
    expect(GraphCanvasSrc).toContain('if (visibleNodeIdsRafRef.current != null) return;');
    expect(GraphCanvasSrc).toContain('segmentIntersectsExpandedRect');
    expect(GraphCanvasSrc).toContain('edgeTouchesViewport');
    expect(GraphCanvasSrc).toContain('pointInsideExpandedRect');
    expect(GraphCanvasSrc).toContain('const overscan = 120;');
  });

  it("fans out drag persist per vault in all-scope mode", () => {
    expect(GraphPageSrc).toContain('Promise.allSettled');
    expect(GraphPageSrc).toContain('entries.map(([targetVault, pos]) =>');
    expect(GraphPageSrc).toContain('/graph/positions');
    expect(GraphPageSrc).toContain('nodeVault(node ?? ({ id } as GraphNode), vault)');
    expect(GraphPageSrc).toContain('nodeSlug(node ?? ({ id } as GraphNode))');
  });
});
