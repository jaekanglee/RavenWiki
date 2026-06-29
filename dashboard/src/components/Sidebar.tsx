import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import clsx from "clsx";
import { NewPageButton } from "./NewPageButton";
import { NewFolderButton } from "./NewFolderButton";
import { nodeColor } from "./GraphCanvas";
import type { TreeNode as TNode, VaultMeta } from "../types";

interface SidebarProps {
  vaults: VaultMeta[];
  trees: Record<string, TNode | null>;
  activeVault: string;
  onSelectVault: (name: string) => void;
  onRefresh?: () => void;
  onTreeChange?: () => void;
  /** Controlled drawer state owned by Layout. Off-canvas only kicks in
   *  inside @media (max-width: 744px); no-op above the breakpoint. */
  open: boolean;
  /** Called by the X button, dim area, and Escape. */
  onClose: () => void;
}

const VAULT_OPEN_KEY = "__vault__";

function openFoldersStorageKey(vault: string): string {
  return `raven.sidebar.openFolders.${vault}`;
}

function readOpenFolders(vault: string): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.localStorage.getItem(openFoldersStorageKey(vault));
    const parsed = raw ? JSON.parse(raw) : [];
    return new Set(Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string") : []);
  } catch {
    return new Set();
  }
}

function writeOpenFolders(vault: string, folders: Set<string>) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(openFoldersStorageKey(vault), JSON.stringify([...folders].sort()));
  } catch {
    // localStorage can be unavailable in private mode; sidebar still works in-memory.
  }
}

function slugMatchesActive(nodeSlug: string, activeSlug: string | null): boolean {
  if (!activeSlug) return false;
  if (nodeSlug === activeSlug) return true;
  // Raven slug prefix tolerance: `index` and `content/index` should highlight the
  // same sidebar leaf. API/page resolution already accepts both; Explorer should
  // mirror that URL SOT behavior.
  if (nodeSlug.replace(/^content\//, "") === activeSlug) return true;
  if (`content/${activeSlug}` === nodeSlug) return true;
  return false;
}

function filterTree(tree: TNode | null, query: string): TNode | null {
  const q = query.trim().toLowerCase();
  if (!tree || !q) return tree;

  function matches(node: TNode): boolean {
    if (node.path.toLowerCase().includes(q)) return true;
    if (node.type === "page") {
      const title = (node.title ?? "").toLowerCase();
      if (title.includes(q)) return true;
      const pt = (node.pageType ?? "").toLowerCase();
      if (pt.includes(q)) return true;
    }
    return false;
  }

  function visit(node: TNode): TNode | null {
    if (matches(node)) return node;
    const children = (node.children ?? []).map(visit).filter((x): x is TNode => Boolean(x));
    if (children.length > 0) return { ...node, children };
    return null;
  }

  const children = (tree.children ?? []).map(visit).filter((x): x is TNode => Boolean(x));
  return { ...tree, children };
}

function activePageFromPath(pathname: string): { vault: string; slug: string } | null {
  const match = pathname.match(/^\/page\/([^/]+)\/(.+)$/);
  if (!match) return null;
  return {
    vault: decodeURIComponent(match[1]),
    slug: decodeURIComponent(match[2]),
  };
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
  const location = useLocation();
  const activePage = activePageFromPath(location.pathname);
  const [filter, setFilter] = useState("");

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
      <div className="sidebar-top-actions">
        <button
          type="button"
          className="sidebar-close-button"
          onClick={onClose}
          aria-label="사이드바 닫기"
          title="사이드바 닫기"
        >
          ×
        </button>
      </div>

      {vaults.length > 1 && (
        <div
          className="sidebar-label"
          style={{
            padding: "8px 0 4px",
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: "0.32px",
            textTransform: "uppercase",
            color: "var(--color-muted)",
            fontFamily: "var(--font-display)",
          }}
        >
          Vaults ({vaults.length})
        </div>
      )}

      {vaults.length === 0 && (
        <div
          style={{
            padding: 8,
            fontSize: 13,
            color: "var(--color-muted)",
            fontFamily: "var(--font-display)",
          }}
        >
          vault 없음
        </div>
      )}

      {vaults.length > 0 && (
        <label className="sidebar-filter-label">
          <span className="sr-only">Explorer filter</span>
          <input
            className="sidebar-filter-input"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Explorer filter…"
            aria-label="Explorer filter"
          />
        </label>
      )}

      {vaults.map((v) => (
        <VaultTreeGroup
          key={v.name}
          vault={v}
          tree={filterTree(trees[v.name] ?? null, filter)}
          isActive={v.name === activeVault}
          showMeta={vaults.length > 1}
          activeSlug={activePage?.vault === v.name ? activePage.slug : null}
          filterActive={filter.trim().length > 0}
          onSelect={() => onSelectVault(v.name)}
          onClose={onClose}
          onRefresh={onRefresh}
        />
      ))}
    </aside>
  );
}

// ─── display title helper ───────────────────────────────────
// v0.6.16+: TreeNode가 path/slug/title을 분리해서 들고 있으므로 폴더는 path의
// 마지막 segment, 페이지는 title을 그대로 표시.
function displayTitle(node: TNode): string {
  if (node.type === "page") {
    return node.title ?? node.path;
  }
  // dir: 마지막 segment만 표시 ("content/concept" → "concept")
  const parts = node.path.split("/");
  return parts[parts.length - 1] || node.path;
}

function VaultTreeGroup({
  vault,
  tree,
  isActive,
  showMeta,
  activeSlug,
  filterActive,
  onSelect,
  onClose,
  onRefresh,
}: {
  vault: VaultMeta;
  tree: TNode | null;
  isActive: boolean;
  showMeta: boolean;
  activeSlug: string | null;
  filterActive: boolean;
  onSelect: () => void;
  onClose: () => void;
  onRefresh?: () => void;
}) {
  const [openFolders, setOpenFolders] = useState<Set<string>>(() => readOpenFolders(vault.name));
  const open = openFolders.has(VAULT_OPEN_KEY);

  function toggleFolder(key: string) {
    setOpenFolders((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      writeOpenFolders(vault.name, next);
      return next;
    });
  }

  return (
    <div style={{ marginBottom: 8 }}>
      <button
        type="button"
        className="sidebar-vault-row"
        onClick={() => {
          toggleFolder(VAULT_OPEN_KEY);
          onSelect();
        }}
        aria-expanded={open}
      >
        <span
          aria-hidden
          className={clsx("sidebar-chevron", open && "sidebar-chevron-open")}
        >
          <svg viewBox="0 0 12 12" width="14" height="14" aria-hidden>
            <path
              d="M4 2 L8 6 L4 10"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        <span className="sidebar-vault-name">{vault.name}</span>
        <NewPageButton vault={vault.name} variant="icon" label="페이지" onOpen={onClose} />
        {showMeta && vault.default && (
          <span className="sidebar-vault-default" aria-label="default">
            ★
          </span>
        )}
        {showMeta && isActive && (
          <span className="sidebar-vault-active" aria-label="active">
            ●
          </span>
        )}
      </button>

      {open && tree && (
        <div className="sidebar-tree">
          {(tree.children ?? []).map((child) => (
            <TreeLeaf
              key={child.path}
              node={child}
              vault={vault.name}
              onClose={onClose}
              activeSlug={activeSlug}
              filterActive={filterActive}
              openFolders={openFolders}
              onToggleFolder={toggleFolder}
              onRefresh={onRefresh}
              depth={1}
            />
          ))}
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
  activeSlug,
  filterActive,
  openFolders,
  onToggleFolder,
  onRefresh,
  depth = 0,
}: {
  node: TNode;
  vault: string;
  onClose: () => void;
  activeSlug: string | null;
  filterActive: boolean;
  openFolders: Set<string>;
  onToggleFolder: (slug: string) => void;
  onRefresh?: () => void;
  depth?: number;
}) {
  const isOpen = openFolders.has(node.path) || filterActive;

  // ─── page leaf ───
  if (node.type === "page") {
    const slug = node.slug ?? node.path;
    const isActive = slugMatchesActive(slug, activeSlug);
    return (
      <Link
        to={`/page/${vault}/${slug}`}
        className={clsx("link-ink sidebar-tree-leaf", isActive && "sidebar-tree-leaf-active")}
        style={{ marginLeft: depth * 14 }}
      >
        <span
          className="sidebar-tree-leaf-dot"
          style={{ background: nodeColor(node.pageType) }}
          aria-hidden
        />
        {displayTitle(node)}
      </Link>
    );
  }

  // ─── dir row ───
  const children = node.children ?? [];
  return (
    <div>
      <div className="sidebar-tree-dir-row" style={{ marginLeft: depth * 14 }}>
        <button
          type="button"
          onClick={() => onToggleFolder(node.path)}
          className="link-ink sidebar-tree-dir"
          aria-expanded={isOpen}
        >
          <span
            aria-hidden
            className={clsx("sidebar-chevron sidebar-chevron-sm", isOpen && "sidebar-chevron-open")}
          >
            <svg viewBox="0 0 12 12" width="10" height="10" aria-hidden>
              <path
                d="M4 2 L8 6 L4 10"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          {displayTitle(node)}
        </button>
        <NewFolderButton
          vault={vault}
          parentPath={node.path}
          onCreated={() => onRefresh?.()}
          onOpen={onClose}
        />
      </div>
      {isOpen &&
        children.map((c) => (
          <TreeLeaf
            key={c.path}
            node={c}
            vault={vault}
            onClose={onClose}
            activeSlug={activeSlug}
            filterActive={filterActive}
            openFolders={openFolders}
            onToggleFolder={onToggleFolder}
            onRefresh={onRefresh}
            depth={depth + 1}
          />
        ))}
    </div>
  );
}