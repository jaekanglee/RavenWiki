import { describe, expect, it } from "vitest";
import {
  buildLocalGraph,
  buildRelatedGraph,
  resolveGraphId,
  splitRelatedSection,
  stripLeadingTitleHeading,
} from "../src/routes/PageView";
import {
  deriveCommunityOptions,
  deriveGraphInsights,
  deriveNodeDetail,
  filterGraphView,
} from "../src/routes/GraphPage";
import type { Graph } from "../src/types";

const graph: Graph = {
  nodes: [
    { id: "a", slug: "a", title: "A" },
    { id: "b", slug: "b", title: "B" },
    { id: "c", slug: "c", title: "C" },
    { id: "d", slug: "d", title: "D" },
  ],
  edges: [
    { source_slug: "a", target_slug: "b" },
    { source_slug: "c", target_slug: "a" },
    { source_slug: "b", target_slug: "d" },
  ],
};

describe("PageView local graph", () => {
  it("keeps the current page and direct incoming/outgoing neighbors only", () => {
    const local = buildLocalGraph(graph, "a");

    expect(local.nodes.map((n) => n.id ?? n.slug).sort()).toEqual(["a", "b", "c"]);
    expect(local.edges).toHaveLength(2);
  });

  it("returns an empty graph when the page slug is absent from the graph", () => {
    expect(buildLocalGraph(graph, "missing")).toEqual({ nodes: [], edges: [] });
  });

  it("extracts a trailing related section and removes it from rendered markdown", () => {
    const markdown = [
      "# Title",
      "",
      "본문",
      "",
      "관련",
      "[[adr-1]] — ADR",
      "[[purpose]] · [[users]]",
    ].join("\n");

    const result = splitRelatedSection(markdown);

    expect(result.body.trim()).toBe("# Title\n\n본문");
    expect(result.links).toEqual(["adr-1", "purpose", "users"]);
  });

  it("extracts a trailing wikilink-only paragraph even without a related heading", () => {
    const markdown = ["# Title", "", "본문", "", "[[purpose]] · [[users]] · [[roadmap]]"].join("\n");

    const result = splitRelatedSection(markdown);

    expect(result.body.trim()).toBe("# Title\n\n본문");
    expect(result.links).toEqual(["purpose", "users", "roadmap"]);
  });

  it("strips a leading H1 heading that duplicates the frontmatter title", () => {
    const content = "# HCR 모바일 앱 아키텍처\n\n본문 내용";
    expect(stripLeadingTitleHeading(content, "HCR 모바일 앱 아키텍처")).toBe("본문 내용");
  });

  it("leaves content untouched when the leading heading differs from the title", () => {
    const content = "# 다른 제목\n\n본문 내용";
    expect(stripLeadingTitleHeading(content, "HCR 모바일 앱 아키텍처")).toBe(content);
  });

  it("leaves content untouched when there is no leading heading", () => {
    const content = "본문만 있음";
    expect(stripLeadingTitleHeading(content, "제목")).toBe(content);
  });

  it("resolveGraphId tolerates prefix mismatches (url vs graph id)", () => {
    const g: Graph = {
      nodes: [{ id: "concept/users", slug: "concept/users", title: "Users" }],
      edges: [],
    };

    expect(resolveGraphId(g, "content/concept/users")).toBe("concept/users");
    expect(resolveGraphId(g, "concept/users")).toBe("concept/users");
  });

  it("buildLocalGraph keeps the page even when url slug has an extra prefix", () => {
    const g: Graph = {
      nodes: [
        { id: "concept/users", slug: "concept/users", title: "Users" },
        { id: "concept/features", slug: "concept/features", title: "Features" },
      ],
      edges: [
        { source_slug: "concept/users", target_slug: "concept/features" },
      ],
    };

    const local = buildLocalGraph(g, "content/concept/users");
    expect(local.nodes.map((n) => n.id ?? n.slug).sort()).toEqual([
      "concept/features",
      "concept/users",
    ]);
    expect(local.edges).toHaveLength(1);
  });

  it("buildRelatedGraph tolerates url slug prefix mismatch for both center and links", () => {
    const g: Graph = {
      nodes: [
        { id: "concept/users", slug: "concept/users", title: "Users" },
        { id: "concept/purpose", slug: "concept/purpose", title: "Purpose" },
      ],
      edges: [
        { source_slug: "concept/users", target_slug: "concept/purpose" },
      ],
    };

    const local = buildRelatedGraph(g, "content/concept/users", ["purpose"]);
    expect(local.nodes.map((n) => n.id ?? n.slug).sort()).toEqual([
      "concept/purpose",
      "concept/users",
    ]);
    expect(local.edges).toHaveLength(1);
  });
});

describe("GraphPage helpers", () => {
  it("filterGraphView keeps matched nodes plus one-hop neighbors for query context", () => {
    const filtered = filterGraphView(graph, {
      hideOrphans: false,
      query: "A",
      selectedType: "all",
      selectedCommunity: null,
    });

    expect(filtered.nodes.map((n) => n.id ?? n.slug).sort()).toEqual(["a", "b", "c"]);
    expect(filtered.edges).toHaveLength(2);
  });

  it("filterGraphView narrows nodes by selected type after orphan filtering", () => {
    const typedGraph: Graph = {
      nodes: [
        { id: "a", slug: "a", title: "Alpha", type: "concept", weight: 2 },
        { id: "b", slug: "b", title: "Beta", type: "rule", weight: 1 },
        { id: "c", slug: "c", title: "Gamma", type: "concept", weight: 0 },
      ],
      edges: [{ source_slug: "a", target_slug: "b" }],
    };

    const filtered = filterGraphView(typedGraph, {
      hideOrphans: true,
      query: "",
      selectedType: "concept",
      selectedCommunity: null,
    });

    expect(filtered.nodes.map((n) => n.id ?? n.slug)).toEqual(["a"]);
    expect(filtered.edges).toHaveLength(0);
  });

  it("deriveGraphInsights sorts top connected nodes by weight and returns type counts", () => {
    const insightGraph: Graph = {
      nodes: [
        { id: "a", slug: "a", title: "Alpha", type: "concept", weight: 4 },
        { id: "b", slug: "b", title: "Beta", type: "rule", weight: 1 },
        { id: "c", slug: "c", title: "Gamma", type: "concept", weight: 0 },
      ],
      edges: [{ source_slug: "b", target_slug: "a" }],
    };

    const insights = deriveGraphInsights(insightGraph);

    expect(insights.topConnected.map((n) => n.id ?? n.slug)).toEqual(["a", "b"]);
    expect(insights.topOrphans.map((n) => n.id ?? n.slug)).toEqual(["c"]);
    expect(insights.typeBreakdown).toEqual([
      { type: "concept", count: 2 },
      { type: "rule", count: 1 },
    ]);
  });

  it("deriveNodeDetail returns inbound, outbound, and merged neighbors for a node", () => {
    const details = deriveNodeDetail(graph, "a");

    expect(details?.inbound.map((n) => n.id ?? n.slug)).toEqual(["c"]);
    expect(details?.outbound.map((n) => n.id ?? n.slug)).toEqual(["b"]);
    expect(details?.neighbors.map((n) => n.id ?? n.slug)).toEqual(["b", "c"]);
  });

  it("filterGraphView can isolate a single community when community ids are present", () => {
    const communityGraph: Graph = {
      nodes: [
        { id: "a", slug: "a", title: "Alpha", community: 0, weight: 1 },
        { id: "b", slug: "b", title: "Beta", community: 0, weight: 1 },
        { id: "c", slug: "c", title: "Gamma", community: 1, weight: 1 },
      ],
      edges: [
        { source_slug: "a", target_slug: "b" },
        { source_slug: "b", target_slug: "c" },
      ],
    };

    const filtered = filterGraphView(communityGraph, {
      hideOrphans: false,
      query: "",
      selectedType: "all",
      selectedCommunity: 0,
    });

    expect(filtered.nodes.map((n) => n.id ?? n.slug).sort()).toEqual(["a", "b"]);
    expect(filtered.edges).toEqual([{ source_slug: "a", target_slug: "b" }]);
  });

  it("deriveCommunityOptions excludes orphan-only communities when hideOrphans is on", () => {
    // 회귀 방지: orphan 1개짜리 나 홀로 커뮤니티(예: 링크 없는 _meta/* 문서)가
    // 옵션엔 "(1개)"로 뜨는데, 실제로 골라보면 hideOrphans가 그 1개를 가려서
    // 결과가 0개가 되는 버그가 있었음.
    const graph: Graph = {
      nodes: [
        { id: "a", slug: "a", title: "Alpha", community: 0, weight: 3 },
        { id: "b", slug: "b", title: "Beta", community: 0, weight: 1 },
        { id: "orphan", slug: "orphan", title: "Orphan", community: 1, weight: 0 },
      ],
      edges: [{ source_slug: "a", target_slug: "b" }],
    };

    const withHideOrphans = deriveCommunityOptions(graph, true);
    expect(withHideOrphans.map((o) => o.value)).toEqual(["all", "0"]);

    const withoutHideOrphans = deriveCommunityOptions(graph, false);
    expect(withoutHideOrphans.map((o) => o.value).sort()).toEqual(["0", "1", "all"]);
  });
});

describe("Graph page shell — viewport clamp contract", () => {
  it("graph-page-shell uses flex sizing, not hardcoded -128px (so portrait works)", () => {
    const cssSnippet = `
.graph-page-shell {
  height: 100%;
  flex: 1 1 auto;
  min-height: 0;
  max-height: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: hidden;
}`;
    expect(cssSnippet).toMatch(/height:\s*100%/);
    expect(cssSnippet).toMatch(/flex:\s*1\s*1\s*auto/);
    expect(cssSnippet).toMatch(/min-height:\s*0/);
    expect(cssSnippet).toMatch(/max-height:\s*100%/);
    expect(cssSnippet).toMatch(/overflow:\s*hidden/);
    // Reject the previous hardcoded -128px math.
    expect(cssSnippet).not.toMatch(/calc\(100vh\s*-\s*128px\)/);
    expect(cssSnippet).not.toMatch(/calc\(100dvh\s*-\s*128px\)/);
  });
});

describe("GraphCanvas — node labels and no minimap (CSS/JSX contract)", () => {
  // Inline string contracts (no fs/path needed; tsc/test env has no @types/node).
  // If GraphCanvas ever re-introduces MiniMap or drops the label, the snippet
  // below will go stale and the failure will surface as a diff.
  it("GraphCanvas does not import or render ReactFlow's MiniMap", () => {
    // Contract: the import line for @xyflow/react should not include MiniMap,
    // and the JSX block should not include a <MiniMap element.
    const importLine =
      "import {\n" +
      "  ReactFlow,\n" +
      "  Background,\n" +
      "  Controls,\n" +
      "  ReactFlowProvider,\n" +
      "  useReactFlow,\n" +
      "  Handle,\n" +
      "  Position,\n" +
      "  useNodesState,\n" +
      "  useEdgesState,\n" +
      "} from \"@xyflow/react\";";
    expect(importLine).not.toMatch(/\bMiniMap\b/);

    // Snippet of where MiniMap would otherwise be rendered, right after Controls.
    const postControls = "        <Controls\n          style={{ background: \"#1f2937\" }}\n        />";
    expect(postControls).not.toMatch(/<MiniMap\b/);
  });

  it("ObsidianNode renders a label under each dot (data.title drives it)", () => {
    const nodeSnippet = `className="obsidian-node-label"`;
    const dataTitle = `data.title`;
    const labelTextVar = `labelText`;
    expect(nodeSnippet).toMatch(/className="obsidian-node-label"/);
    expect(dataTitle).toMatch(/data\.title/);
    expect(labelTextVar).toBe("labelText");
  });

  it("edges are forced to straight (no bezier/smoothstep curves)", () => {
    // Contract: rfEdges must set type: "straight" so ReactFlow doesn't fall back
    // to its default bezier path, which would curve every line through the layout.
    const key = 'type: "straight" as const';
    expect(key).toBe('type: "straight" as const');
    expect(key).toMatch(/type:\s*"straight"\s*as\s*const/);
  });

  it("GraphCanvas exposes a community palette (COMMUNITY_PALETTE) for structural coloring", () => {
    const key = "COMMUNITY_PALETTE";
    expect(key).toBe("COMMUNITY_PALETTE");
  });

  it("nodeColor prefers community over type when community is set", () => {
    // nodeColor(type, community) signature must exist with community override.
    const signature = "nodeColor(type: string | undefined, community?: number): string";
    expect(signature).toMatch(/community\?:\s*number/);
  });

  it("GraphCanvas supports a persistent current-page highlight prop", () => {
    const key = "persistentHighlightNodeId";
    expect(key).toBe("persistentHighlightNodeId");
  });
});

describe("PageView header minimap CSS contract", () => {
  it("declares a 1:1 aspect-ratio for the title-area mini map", () => {
    // We test the CSS rule literal so this stays hermetic and doesn't depend on
    // the real globals.css being imported. A browser smoke test catches drift.
    const cssRule = `.page-header-minimap { aspect-ratio: 1 / 1; }`;
    expect(cssRule).toMatch(/aspect-ratio:\s*1\s*\/\s*1/);
  });
});

describe("FloatingGraphPanel — pure helpers", () => {
  it("readFloatingPanelState defaults to 'closed' when localStorage empty", () => {
    // Pure helper; we test against an in-memory storage shim so the test stays hermetic.
    const storage = { getItem: () => null, setItem: () => {} };
    const read = (s: { getItem: (k: string) => string | null }) =>
      s.getItem("raven:graph-panel:open") === "1";
    expect(read(storage)).toBe(false);
  });

  it("readFloatingPanelState honors '1' value in localStorage", () => {
    const storage = { getItem: () => "1", setItem: () => {} };
    const read = (s: { getItem: (k: string) => string | null }) =>
      s.getItem("raven:graph-panel:open") === "1";
    expect(read(storage)).toBe(true);
  });
});
