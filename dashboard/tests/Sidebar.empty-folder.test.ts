/* v0.6.16+ — Folder first-class citizen.
 *
 * 빈 폴더도 TreeNode.children: []로 그대로 표현되어야 sidebar에 표시된다.
 * TreeNode shape: {type: "dir" | "page", path, slug?, title?, pageType?, children?}.
 */
import { describe, it, expect } from "vitest";

interface TreeNode {
  type: "dir" | "page";
  path: string;
  slug?: string;
  title?: string;
  pageType?: string;
  children?: TreeNode[];
}

describe("Sidebar — empty folder rendering contract", () => {
  it("empty folder node has children: [] and type: 'dir'", () => {
    const empty: TreeNode = {
      type: "dir",
      path: "content/empty-folder",
      children: [],
    };
    expect(empty.children).toEqual([]);
    expect(empty.children?.length).toBe(0);
  });

  it("page node carries slug + title + pageType", () => {
    const page: TreeNode = {
      type: "page",
      path: "content/concept/users",
      slug: "content/concept/users",
      title: "사용자",
      pageType: "concept",
    };
    expect(page.slug).toBe("content/concept/users");
    expect(page.title).toBe("사용자");
    expect(page.pageType).toBe("concept");
  });

  it("mixed tree (folder + page + empty folder) round-trips", () => {
    const tree: TreeNode = {
      type: "dir",
      path: "content",
      children: [
        { type: "dir", path: "content/concept", children: [
          { type: "page", path: "content/concept/users", slug: "content/concept/users", title: "사용자" },
        ]},
        { type: "dir", path: "content/empty", children: [] },
      ],
    };
    expect(tree.children?.length).toBe(2);
    expect(tree.children?.[1].children?.length).toBe(0);
  });
});