import { useState } from "react";
import { Link } from "react-router-dom";
import clsx from "clsx";
import { NewPageButton } from "./NewPageButton";
import type { TreeNode as TNode, VaultMeta } from "../types";

interface SidebarProps {
  vaults: VaultMeta[];
  trees: Record<string, TNode | null>;
  activeVault: string;
  onSelectVault: (name: string) => void;
  onRefresh?: () => void;
  /** Reserved for future tree-mutation refresh hooks; not used in the
   *  off-canvas-drawer flow. */
  onTreeChange?: () => void;
  /** Controlled drawer state owned by Layout. On desktop the off-canvas
   *  CSS only takes effect inside @media (max-width: 744px), so this is
   *  effectively a no-op above the breakpoint. */
  open: boolean;
  /** Called by the leaf Link onClick and (in Layout) by backdrop/Escape. */
  onClose: () => void;
}

export function Sidebar({
  vaults,
  trees,
  activeVault,
  onSelectVault,
  onRefresh,
  open,
  onClose,
}: SidebarProps) {
  return (
    <aside
      id="primary-sidebar"
      className={clsx(
        "layout-sidebar",
        "sidebar-offcanvas",
        open && "sidebar-offcanvas-open"
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
          padding: "8px 0 4px",
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: "0.32px",
          textTransform: "uppercase",
          color: "var(--color-muted)",
        }}
      >
        Vaults ({vaults.length})
      </div>

      {vaults.length === 0 && (
        <div style={{ padding: 8, fontSize: 13, color: "var(--color-muted)" }}>
          vault 없음
        </div>
      )}

      {vaults.map((v) => (
        <VaultTreeGroup
          key={v.name}
          vault={v}
          tree={trees[v.name] ?? null}
          isActive={v.name === activeVault}
          onSelect={() => onSelectVault(v.name)}
          onClose={onClose}
          onRefresh={onRefresh}
        />
      ))}
    </aside>
  );
}

// ─── display title helper ────────────────────────────────────
// Vault filenames are slugs — turn "2026-06-28-pwa-cache" into "Pwa Cache",
// "index" into "Index", keep "_template" as-is. Strips leading
// date prefix and replaces separators with spaces.
function displayTitle(slug: string): string {
  const last = slug.split("/").pop() || slug;
  const base = last.replace(/\.md$/, "");
  // strip leading YYYY-MM-DD- prefix
  const dated = base.replace(/^\d{4}-\d{2}-\d{2}-/, "");
  if (dated === "") return base;
  return dated
    .replace(/[-_]+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ─── Vault tree group ────────────────────────────────────────
function VaultTreeGroup({
  vault,
  tree,
  isActive,
  onSelect,
  onClose,
  onRefresh,
}: {
  vault: VaultMeta;
  tree: TNode | null;
  isActive: boolean;
  onSelect: () => void;
  onClose: () => void;
  onRefresh?: () => void;
}) {
  // 기본 닫힘 (v0.6.10 UX 강화).
  const [open, setOpen] = useState(false);
  const [pagesOpen, setPagesOpen] = useState(false);

  return (
    <div
      style={{
        marginBottom: 4,
        background: isActive ? "var(--cds-field-01, #f4f4f4)" : "transparent",
        borderRadius: 4,
        padding: "2px 0",
      }}
    >
      <button
        onClick={() => {
          onSelect();
        }}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 4,
          width: "100%",
          padding: "4px 8px",
          background: "transparent",
          border: "none",
          textAlign: "left",
          fontSize: 14,
          fontWeight: 600,
          color: "var(--color-ink)",
          cursor: "pointer",
          fontFamily: "inherit",
          borderRadius: 4,
        }}
        aria-label={`switch to vault ${vault.name}`}
        title={`${vault.path}`}
      >
        <span
          onClick={(e) => {
            e.stopPropagation();
            setOpen(!open);
            // vault 닫을 때 children도 닫기.
            if (open) setPagesOpen(false);
          }}
          aria-hidden
          style={{
            fontSize: 10,
            opacity: 0.6,
            width: 12,
            display: "inline-block",
            cursor: "pointer",
          }}
        >
          {open ? "▾" : "▸"}
        </span>
        {vault.default && (
          <span
            style={{
              fontSize: 9,
              color: "var(--color-primary)",
              fontWeight: 700,
            }}
            aria-label="default"
          >
            ★
          </span>
        )}
        {isActive && (
          <span
            style={{
              fontSize: 9,
              color: "var(--color-success, #198038)",
              fontWeight: 700,
            }}
            aria-label="active"
          >
            ●
          </span>
        )}
        <span style={{ flex: 1 }}>{vault.name}</span>
        <span
          style={{
            fontSize: 10,
            padding: "1px 5px",
            background: "var(--cds-background, #fff)",
            border: "1px solid var(--cds-border-subtle-01, #e0e0e0)",
            borderRadius: 8,
            color: "var(--color-muted)",
          }}
        >
          {vault.mode}
        </span>
      </button>

      {open && (
        <div style={{ paddingLeft: 8, paddingTop: 2 }}>
          <button
            onClick={() => setPagesOpen(!pagesOpen)}
            className={clsx("link-ink")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 4,
              padding: "2px 8px",
              fontSize: 11,
              fontWeight: 600,
              color: "var(--color-muted)",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              width: "100%",
              textAlign: "left",
              fontFamily: "inherit",
              letterSpacing: "0.32px",
              textTransform: "uppercase",
            }}
          >
            <span aria-hidden style={{ fontSize: 9 }}>
              {pagesOpen ? "▾" : "▸"}
            </span>
            Pages
          </button>

          {pagesOpen && (
            <div>
              {tree ? (
                tree.children?.length ? (
                  tree.children.map((child) => (
                    <TreeLeaf
                      key={child.slug}
                      node={child}
                      vault={vault.name}
                      onClose={onClose}
                    />
                  ))
                ) : (
                  <div
                    style={{
                      padding: "4px 8px",
                      fontSize: 12,
                      color: "var(--color-muted)",
                    }}
                  >
                    empty
                  </div>
                )
              ) : (
                <div
                  style={{
                    padding: "4px 8px",
                    fontSize: 12,
                    color: "var(--color-muted)",
                  }}
                >
                  loading…
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Tree leaf (recursive for nested dirs) ───────────────────
function TreeLeaf({
  node,
  vault,
  onClose,
  depth = 0,
}: {
  node: TNode;
  vault: string;
  onClose: () => void;
  depth?: number;
}) {
  const [isOpen, setIsOpen] = useState(false);

  if (!node.children || node.children.length === 0) {
    // leaf page
    return (
      <Link
        to={`/page/${vault}/${node.slug}`}
        onClick={onClose}
        className="link-ink"
        style={{
          display: "block",
          padding: "3px 8px",
          fontSize: 13,
          fontWeight: 400,
          color: "var(--color-ink)",
          marginLeft: depth * 12,
          borderRadius: 3,
        }}
      >
        {displayTitle(node.title || node.slug)}
      </Link>
    );
  }

  // dir node
  return (
    <div>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={clsx("link-ink")}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 4,
          padding: "3px 8px",
          fontSize: 12,
          fontWeight: 600,
          color: "var(--color-muted)",
          background: "transparent",
          border: "none",
          cursor: "pointer",
          width: "100%",
          textAlign: "left",
          fontFamily: "inherit",
          marginLeft: depth * 12,
          borderRadius: 3,
        }}
      >
        <span aria-hidden style={{ fontSize: 9 }}>
          {isOpen ? "▾" : "▸"}
        </span>
        {displayTitle(node.title || node.slug)}
      </button>
      {isOpen &&
        node.children.map((c) => (
          <TreeLeaf
            key={c.slug}
            node={c}
            vault={vault}
            onClose={onClose}
            depth={depth + 1}
          />
        ))}
    </div>
  );
}