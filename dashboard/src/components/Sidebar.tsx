import { Link } from "react-router-dom";
import clsx from "clsx";
import { useState } from "react";
import type { TreeNode as TNode } from "../types";
import { NewPageButton } from "./NewPageButton";

export function Sidebar({
  vault,
  tree,
  open,
  onClose,
}: {
  vault: string;
  tree: TNode | null;
  /** Reserved for future tree-mutation refresh hooks; not used in the
   *  off-canvas-drawer flow. */
  onTreeChange?: () => void;
  /** Controlled drawer state owned by Layout. On desktop the off-canvas
   *  CSS only takes effect inside @media (max-width: 744px), so this is
   *  effectively a no-op above the breakpoint. */
  open: boolean;
  /** Called by the leaf Link onClick and (in Layout) by backdrop/Escape. */
  onClose: () => void;
}) {
  return (
    <aside
      id="primary-sidebar"
      className={clsx(
        "layout-sidebar",
        "sidebar-offcanvas",
        open && "sidebar-offcanvas-open",
      )}
      style={{
        borderRight: "1px solid var(--color-hairline)",
        width: 288,
        overflowY: "auto",
        padding: "24px 20px",
        background: "var(--color-canvas)",
        flexShrink: 0,
      }}
    >
      <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ flex: 1 }}>
          <NewPageButton />
        </div>
      </div>

      <div
        className="sidebar-label"
        style={{
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: "0.32px",
          textTransform: "uppercase",
          color: "var(--color-muted)",
          padding: "0 8px 8px",
        }}
      >
        Pages
      </div>

      {tree ? (
        <TreeNodeView node={tree} depth={0} vault={vault} onClose={onClose} />
      ) : (
        <div className="text-muted sidebar-text" style={{ padding: "8px", fontSize: 13 }}>
          Loading {vault}…
        </div>
      )}
    </aside>
  );
}

function TreeNodeView({
  node,
  depth,
  vault,
  onClose,
}: {
  node: TNode;
  depth: number;
  vault: string;
  onClose: () => void;
}) {
  const [isOpen, setIsOpen] = useState(true);

  if (!node.children || node.children.length === 0) {
    if (node.slug === "root") return null;
    return (
      <Link
        to={`/page/${vault}/${node.slug}`}
        onClick={onClose}
        className="link-ink"
        style={{
          display: "block",
          padding: "6px 8px",
          fontSize: 14,
          marginLeft: depth * 12,
          borderRadius: 6,
        }}
      >
        {node.title}
      </Link>
    );
  }

  return (
    <div style={{ marginLeft: depth * 12 }}>
      {node.slug !== "root" && (
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={clsx("link-ink")}
          style={{
            display: "block",
            padding: "6px 8px",
            fontSize: 14,
            fontWeight: 600,
            width: "100%",
            textAlign: "left",
            background: "transparent",
            border: "none",
            cursor: "pointer",
            borderRadius: 6,
          }}
        >
          {isOpen ? "▾" : "▸"} {node.title}
        </button>
      )}
      {isOpen &&
        node.children.map((c) => (
          <TreeNodeView key={c.slug} node={c} depth={depth + 1} vault={vault} onClose={onClose} />
        ))}
    </div>
  );
}
