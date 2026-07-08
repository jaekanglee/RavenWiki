import { describe, expect, it } from "vitest";
import GraphPageSrc from "../src/routes/GraphPage.tsx?raw";
import GraphCanvasSrc from "../src/components/GraphCanvas.tsx?raw";

/**
 * Contract tests for the all-vault GraphPage scope toggle & ForceGraph migration.
 * Use ?raw so the test stays focused on API/UI contract strings and does not
 * mount heavy Canvas/force-graph components in JSDOM.
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
  });

  it("utilizes high-performance HTML Canvas force-graph library", () => {
    expect(GraphCanvasSrc).toContain("import ForceGraph from \"force-graph\";");
    expect(GraphCanvasSrc).toContain("const graph = (ForceGraphConstructor as any)()(containerRef.current);");
  });

  it("implements Obsidian-style custom node canvas rendering and LOD", () => {
    expect(GraphCanvasSrc).toContain("graph.nodeCanvasObject");
    expect(GraphCanvasSrc).toContain("const canShowDenseLabel = scale > 1.15 && (node.weight ?? 0) >= 3;");
    expect(GraphCanvasSrc).toContain("const canShowNormalLabel = scale > 0.85 || (node.weight ?? 0) >= 6;");
    expect(GraphCanvasSrc).toContain("const showLabel = isFocused || isHighlighted || (isDense ? canShowDenseLabel : canShowNormalLabel);");
    expect(GraphCanvasSrc).toContain("ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);");
  });

  it("renders vault halos & centroid labels on pre-render frame hook", () => {
    expect(GraphPageSrc).toContain('vaultCentroids={graphScope === "all" ? vaultCentroids : undefined}');
    expect(GraphPageSrc).toContain('deriveVaultCentroids');
    expect(GraphCanvasSrc).toContain('vaultCentroids?: VaultCentroid[]');
    expect(GraphCanvasSrc).toContain('graph.onRenderFramePre');
    expect(GraphCanvasSrc).toContain('const text = `📁 ${vc.vault}`;');
  });

  it("contains keyboard shortcuts & hand-mode toggle for seamless panning/zooming", () => {
    expect(GraphCanvasSrc).toContain("interactionMode");
    expect(GraphCanvasSrc).toContain("setInteractionMode");
    expect(GraphCanvasSrc).toContain("e.code === \"Space\"");
    expect(GraphCanvasSrc).toContain("graph.enableNodeDrag(!isDense && interactionMode === \"pointer\")");
  });

  it("dims cross-vault edges in dense mode with customized properties", () => {
    expect(GraphCanvasSrc).toContain('crossVaultEdgeIds');
    expect(GraphCanvasSrc).toMatch(/srcVault\s*!==\s*tgtVault/);
    expect(GraphCanvasSrc).toContain('linkColor');
    expect(GraphCanvasSrc).toContain('linkWidth');
    expect(GraphCanvasSrc).toContain('linkDirectionalParticles');
  });

  it("fans out drag persist per vault in all-scope mode", () => {
    expect(GraphPageSrc).toContain('Promise.allSettled');
    expect(GraphPageSrc).toContain('entries.map(([targetVault, pos]) =>');
    expect(GraphPageSrc).toContain('/graph/positions');
    expect(GraphPageSrc).toContain('nodeVault(node ?? ({ id } as GraphNode), vault)');
    expect(GraphPageSrc).toContain('nodeSlug(node ?? ({ id } as GraphNode))');
  });
});
