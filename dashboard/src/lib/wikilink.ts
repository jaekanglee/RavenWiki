import { visit } from "unist-util-visit";

export function wikilinkPlugin(vault: string) {
  return (tree: any) => {
    visit(tree, "text", (node: any, index: number | undefined, parent: any) => {
      if (!parent || typeof node.value !== "string" || index === undefined) return;
      const regex = /\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]/g;
      const value: string = node.value;
      if (!regex.test(value)) return;

      const parts: any[] = [];
      let lastIndex = 0;
      let m: RegExpExecArray | null;
      regex.lastIndex = 0;
      while ((m = regex.exec(value)) !== null) {
        if (m.index > lastIndex) {
          parts.push({ type: "text", value: value.slice(lastIndex, m.index) });
        }
        const slug = m[1];
        parts.push({
          type: "link",
          url: `/page/${encodeURIComponent(vault)}/${encodeURIComponent(slug)}`,
          title: slug,
          children: [{ type: "text", value: slug }],
          data: { hProperties: { className: "wikilink" } },
        });
        lastIndex = m.index + m[0].length;
      }
      if (lastIndex < value.length) {
        parts.push({ type: "text", value: value.slice(lastIndex) });
      }
      parent.children.splice(index, 1, ...parts);
      return index + parts.length;
    });
  };
}
