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
