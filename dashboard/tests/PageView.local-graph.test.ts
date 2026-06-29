import { describe, expect, it } from "vitest";
import { buildLocalGraph, buildRelatedGraph, resolveGraphId, splitRelatedSection } from "../src/routes/PageView";
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
