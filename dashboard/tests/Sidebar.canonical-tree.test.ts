/* v0.7.111 — Dashboard Sidebar canonical tree view.
 *
 * Vault filesystem stays free-form, but Dashboard sidebar renders a stable
 * SCHEMA-type grouping across flat / singular / plural / custom folders.
 * Auto-generated catalog pages (_index, content/index) stay hidden from the
 * human navigation tree.
 */
import { describe, expect, it } from "vitest";
import { normalizeSidebarTree } from "../src/components/Sidebar";
import type { TreeNode } from "../src/types";

const MIXED_TREE: TreeNode = {
  type: "dir",
  path: "content",
  children: [
    { type: "page", path: "content/concept-flat", slug: "content/concept-flat", title: "Flat Concept", pageType: "concept" },
    { type: "page", path: "content/index", slug: "content/index", title: "Index", pageType: "concept" },
    {
      type: "dir",
      path: "content/_index",
      children: [
        { type: "page", path: "content/_index/concept", slug: "content/_index/concept", title: "Concept Index", pageType: "concept" },
      ],
    },
    {
      type: "dir",
      path: "content/concepts",
      children: [
        { type: "page", path: "content/concepts/architecture", slug: "content/concepts/architecture", title: "Architecture", pageType: "concept" },
      ],
    },
    {
      type: "dir",
      path: "content/default",
      children: [
        { type: "page", path: "content/default/runtime-map", slug: "content/default/runtime-map", title: "Runtime Map", pageType: "rule" },
      ],
    },
  ],
};

describe("Sidebar canonical tree view", () => {
  it("groups pages by SCHEMA type and hides generated catalog pages", () => {
    const normalized = normalizeSidebarTree(MIXED_TREE);
    expect(normalized?.children?.map((n) => n.path)).toEqual([
      "__canonical/concept",
      "__canonical/rule",
    ]);

    const concept = normalized?.children?.[0];
    expect(concept?.children?.map((n) => n.path)).toEqual([
      "content/concepts/architecture",
      "content/concept-flat",
    ]);

    const allPaths = JSON.stringify(normalized);
    expect(allPaths).not.toContain("content/index");
    expect(allPaths).not.toContain("content/_index");
  });
});
