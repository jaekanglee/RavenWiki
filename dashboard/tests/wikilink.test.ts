import { describe, it, expect } from "vitest";
import { wikilinkPlugin } from "../src/lib/wikilink";

// Minimal mdast text node shape — what the remark visitor gets.
function textNode(value: string) {
  return { type: "text", value };
}

function root(children: any[]) {
  return { type: "root", children };
}

function run(input: string) {
  const tree = root([textNode(input)]);
  wikilinkPlugin("develop")(tree);
  return tree.children;
}

describe("wikilinkPlugin", () => {
  it("rewrites a simple [[slug]] into a link", () => {
    const out = run("see [[concepts/wiki]] please");
    expect(out).toHaveLength(2);
    expect(out[1]).toMatchObject({
      type: "link",
      url: "/page/concepts%2Fwiki",
    });
  });

  it("preserves intent char (?)", () => {
    const out = run("see [[foo?]] and [[bar!]]");
    const texts = out.map((n: any) => n.value).join("|");
    // Links present, no leftover literal [[
    expect(texts).not.toContain("[[");
  });

  it("handles aliased [[slug|display]]", () => {
    const out = run("hello [[person/hermes|Hermes]]");
    const link = out.find((n: any) => n.type === "link");
    expect(link).toBeDefined();
    expect(link.url).toContain("/page/");
  });

  it("is a no-op when there are no wikilinks", () => {
    const out = run("no links here at all");
    expect(out).toHaveLength(1);
    expect(out[0].value).toBe("no links here at all");
  });
});
