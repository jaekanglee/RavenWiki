import { Link } from "react-router-dom";
import { useState } from "react";
import type { TreeNode as TNode } from "../types";
import { NewPageButton } from "./NewPageButton";

export function Sidebar({ tree }: { tree: TNode | null }) {
  if (!tree) {
    return (
      <aside className="w-64 border-r overflow-y-auto p-4 text-sm text-gray-500">
        Loading…
        <NewPageButton />
      </aside>
    );
  }

  return (
    <aside className="w-64 border-r overflow-y-auto p-4">
      <Link to="/" className="font-bold text-lg block mb-2">
        📚 Wiki
      </Link>
      <NewPageButton />
      <TreeNodeView node={tree} depth={0} />
    </aside>
  );
}

function TreeNodeView({ node, depth }: { node: TNode; depth: number }) {
  const [open, setOpen] = useState(true);

  if (!node.children || node.children.length === 0) {
    return (
      <Link
        to={`/page/${node.slug}`}
        className="block py-1 px-2 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-sm"
        style={{ marginLeft: depth * 12 }}
      >
        {node.title}
      </Link>
    );
  }

  return (
    <div style={{ marginLeft: depth * 12 }}>
      <button
        onClick={() => setOpen(!open)}
        className="block py-1 px-2 w-full text-left text-sm font-medium"
      >
        {open ? "📂" : "📁"} {node.title}
      </button>
      {open &&
        node.children.map((c) => (
          <TreeNodeView key={c.slug} node={c} depth={depth + 1} />
        ))}
    </div>
  );
}
