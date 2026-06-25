import { Link } from "react-router-dom";
import clsx from "clsx";
import { useEffect, useState } from "react";
import type { TreeNode as TNode } from "../types";
import { NewPageButton } from "./NewPageButton";

export function Sidebar({
  vault,
  tree,
  onTreeChange,
}: {
  vault: string;
  tree: TNode | null;
  onTreeChange?: () => void;
}) {
  // Auto-collapse sidebar on narrow screens.
  const [collapsed, setCollapsed] = useState(false);
  useEffect(() => {
    const mql = window.matchMedia("(max-width: 744px)");
    const onChange = () => setCollapsed(mql.matches);
    onChange();
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  return (
    <aside
      className={clsx(collapsed && "sidebar-collapsed-mobile")}
      style={{
        width: 288,
        borderRight: "1px solid var(--color-hairline)",
        overflowY: "auto",
        padding: "24px 20px",
        background: "var(--color-canvas)",
        flexShrink: 0,
        transition: "width 0.16s ease, padding 0.16s ease",
      }}
    >
      <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
        {/* Mobile-only toggle to expand the collapsed rail */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          aria-label="사이드바 토글"
          className="sidebar-mobile-toggle"
          style={{
            background: "transparent",
            border: "none",
            cursor: "pointer",
            color: "var(--color-muted)",
            fontSize: 18,
            padding: 4,
          }}
        >
          ☰
        </button>
        {!collapsed && (
          <div style={{ flex: 1 }}>
            <NewPageButton />
          </div>
        )}
      </div>

      {!collapsed && (
        <>
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
            <TreeNodeView node={tree} depth={0} />
          ) : (
            <div className="text-muted sidebar-text" style={{ padding: "8px", fontSize: 13 }}>
              Loading {vault}…
            </div>
          )}
        </>
      )}
    </aside>
  );
}

function TreeNodeView({ node, depth }: { node: TNode; depth: number }) {
  const [open, setOpen] = useState(true);

  if (!node.children || node.children.length === 0) {
    if (node.slug === "root") return null;
    return (
      <Link
        to={`/page/${node.slug}`}
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
          onClick={() => setOpen(!open)}
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
          {open ? "▾" : "▸"} {node.title}
        </button>
      )}
      {open &&
        node.children.map((c) => <TreeNodeView key={c.slug} node={c} depth={depth + 1} />)}
    </div>
  );
}