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

  it("vault halo 박스 제거, vault 색 ring이 노드 외곽선에 추가됨 (v0.7.139+)", () => {
      // v0.7.139+: 이전엔 centroid 박스(📁 Vault이름)와 radial gradient halo를 그렸는데
      // 잡음이 강해서 제거. 대신 노드 외곽선에 vault 색 1.2px ring을 그려서 같은 vault 그룹을
      // 묶어 시각화. current scope에서는 모든 노드가 같은 vault이라 ring 스킵.
      expect(GraphCanvasSrc).not.toContain("graph.onRenderFramePre");
      expect(GraphCanvasSrc).not.toContain("const text = `📁 ${vc.vault}`");
      // rounded-rect 헬퍼는 정의/호출 모두 제거됨 (코멘트에 이름만 남음).
      expect(GraphCanvasSrc).not.toMatch(/^\s*function\s+rounded/);
      expect(GraphCanvasSrc).not.toMatch(/\brounded\(/);
      // vault 색 ring은 nodeCanvasObject 안에서 그린다 — showVaultRing은 isDense에서만 true.
      expect(GraphCanvasSrc).toContain("showVaultRing = isDense");
      expect(GraphCanvasSrc).toContain("resolveVaultColor(node.vault)");
    });

  it("노드 드래그 완전 비활성화, pan/zoom은 force-graph native (v0.7.139+)", () => {
    // v0.7.139+: enableNodeDrag(false) — 모바일/터치패드에서 살짝만 손가락이 움직여도
    // force-graph이 drag로 인식해서 click이 무시되는 버그 방지. 이전엔 isDense에서만 off였는데
    // current scope에서도 사용자 신고로 인해 완전 비활성화. '배치 초기화' 버튼이 위치 재조정 책임.
    expect(GraphCanvasSrc).toContain("graph.enableNodeDrag(false)");
    expect(GraphCanvasSrc).not.toContain("graph.enableNodeDrag(!isDense)");
    expect(GraphCanvasSrc).toContain("enablePanInteraction(true)");
    expect(GraphCanvasSrc).toContain("enableZoomInteraction(true)");
  });

  it("bypasses force-graph click cache with direct mouseup/touchend hit detection", () => {
    expect(GraphCanvasSrc).toContain("findClosestNodeHit");
    expect(GraphCanvasSrc).toContain('addEventListener("mouseup", handleMouseUp');
    expect(GraphCanvasSrc).toContain('addEventListener("touchend", handleTouchEnd');
    expect(GraphCanvasSrc).toContain("graph.screen2GraphCoords(screenX, screenY)");
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
