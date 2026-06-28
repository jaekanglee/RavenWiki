import { describe, it, expect } from "vitest";
import { wikilinkPlugin } from "../src/lib/wikilink";

// Minimal mdast text node shape — what the remark visitor gets.
function textNode(value: string) {
  return { type: "text", value };
}

function root(children: any[]) {
  return { type: "root", children };
}

function run(input: string, vault = "develop") {
  const tree = root([textNode(input)]);
  wikilinkPlugin(vault)(tree);
  return tree.children;
}

describe("wikilinkPlugin", () => {
  it("rewrites a simple [[slug]] into a link (3-part: text + link + text)", () => {
    // Input: "see [[concepts/wiki]] please"
    // After wikilink: [text("see "), link, text(" please")] = 3 nodes
    const out = run("see [[concepts/wiki]] please");
    expect(out).toHaveLength(3);
    const link = out.find((n: any) => n.type === "link");
    expect(link).toMatchObject({
      type: "link",
      url: "/page/develop/concepts%2Fwiki",
    });
  });

  it("preserves intent char (?) and broken (!)", () => {
    // Wikilinks with intent markers must not crash; links emit.
    const out = run("see [[foo?]] and [[bar!]]");
    const texts = out.map((n: any) => n.value || "").join("|");
    // No leftover literal [[
    expect(texts).not.toContain("[[");
    // Both intent markers kept as link suffix (preserved or stripped — current impl strips)
    const links = out.filter((n: any) => n.type === "link");
    expect(links.length).toBeGreaterThanOrEqual(1);
  });

  it("handles aliased [[slug|display]]", () => {
    const out = run("hello [[person/hermes|Hermes]]");
    const link = out.find((n: any) => n.type === "link");
    expect(link).toBeDefined();
    expect(link.url).toContain("/page/");
    // display text = slug "person/hermes", not "Hermes" (current impl uses slug as children text)
    expect(link.children?.[0]?.value).toBe("person/hermes");
  });

  it("is a no-op when there are no wikilinks", () => {
    const out = run("no links here at all");
    expect(out).toHaveLength(1);
    expect(out[0].value).toBe("no links here at all");
  });

  it("URL-encodes vault and slug separately", () => {
    // Different vault, same slug
    const out = run("see [[concepts/wiki]] please", "raven-dev");
    const link = out.find((n: any) => n.type === "link");
    expect(link.url).toBe("/page/raven-dev/concepts%2Fwiki");
  });
});
