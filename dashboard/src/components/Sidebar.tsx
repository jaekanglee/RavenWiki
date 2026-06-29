import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import clsx from "clsx";
import { NewPageButton } from "./NewPageButton";
import { nodeColor } from "./GraphCanvas";
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

/**
 * contentRoot (v0.6.15 sidebar cleanup)
 * ─────────────────────────────────────────────────
 * 모든 vault에 공통으로 있는 `content/` 같은 single-child 디렉토리는
 * 사용자에게 노이즈다. TreeNode에서 이걸 자동 감지해서 그 자식들만 노출한다.
 *
 * 예: vault tree = {content/ → [concept/, decision/]}
 *     → sidebar에 "content/" 자체를 숨기고 concept/, decision/가 root로 표시
 *
 * v1 heuristic: root.children 중 단일 child만 있고, 그 child의 slug가
 * `content` (case-insensitive)이면 그 child의 children을 root로 올림.
 * 다른 디렉토리(`notes/`, `wiki/`)는 vault에 따라 다르므로 압축 안 함.
 */
function flattenCommonRoot(tree: TNode | null): TNode | null {
  if (!tree || !tree.children || tree.children.length === 0) return tree;
  const SINGLE_CHILD_NAMES = new Set(["content"]);
  if (
    tree.children.length === 1 &&
    SINGLE_CHILD_NAMES.has(tree.children[0].slug.toLowerCase())
  ) {
    const inner = tree.children[0];
    return { ...inner, children: inner.children ?? [] };
  }
  return tree;
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

function folderCreatePrefix(slug: string): string {
  const clean = slug.replace(/\/$/, "");
  const prefixed = clean.startsWith("content/") ? clean : `content/${clean}`;
  return `${prefixed}/`;
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
    return (
      node.slug.toLowerCase().includes(q) ||
      displayTitle(node.slug, node.title).toLowerCase().includes(q) ||
      (node.type ?? "").toLowerCase().includes(q)
    );
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

      {/*
        "Vaults (N)" label: 1개일 땐 의미 없어서 숨김. 2개+일 때만 카운트 표시.
        각 vault는 자체 row에서 vault name + mode badge로 충분히 식별 가능.
      */}
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
          tree={filterTree(flattenCommonRoot(trees[v.name] ?? null), filter)}
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
// Vault filenames are slugs — turn "2026-06-28-pwa-cache" into "Pwa Cache",
// "index" into "Index" (with 📑 prefix per Obsidian/Notion/Craft 컨벤션),
// keep "_template" as-is. Strips leading date prefix and replaces separators
// with spaces.
//
// v0.6.15: Index 페이지는 frontmatter title과 무관하게 항상 "📑 Index"로
// 표기 (Obsidian/Notion/Craft 컨벤션 + 자료조사 결과). 파일명 변경 ❌
// — [[wiki-link]] 호환성 유지.
function displayTitle(slug: string, explicitTitle?: string): string {
  const last = slug.split("/").pop() || slug;
  const base = last.replace(/\.md$/, "");
  // Index page: 파일명/경로가 'index'로 끝나면 frontmatter title과 무관하게
  // "📑 Index"로 고정. wiki-link는 파일명 기반이라 링크 깨지지 않음.
  if (/^index(\.|$)/i.test(base)) {
    return "📑 Index";
  }
  if (explicitTitle?.trim()) return explicitTitle.trim();
  // strip leading YYYY-MM-DD- prefix (e.g. for dated ADRs)
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
  const open = openFolders.has(VAULT_OPEN_KEY) || filterActive;

  function toggleFolder(key: string) {
    setOpenFolders((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      writeOpenFolders(vault.name, next);
      return next;
    });
  }

  // 묶음 A (Plan v1, Tasks 2-3): title 영역 클릭 = toggle, arrow 클릭 = toggle.
  // 둘 다 동일한 toggle 동작. 단, vault 선택(setActive)은 별도 액션.
  // 모바일(<744px) 터치 영역 32px 유지를 위해 min-height 적용.
  const toggleVault = () => toggleFolder(VAULT_OPEN_KEY);

  return (
    <div
      style={{
        marginBottom: 2,
        background: isActive ? "var(--cds-field-01, #f4f4f4)" : "transparent",
        borderRadius: 4,
        padding: "2px 0",
      }}
    >
      <button
        onClick={onSelect}
        className="sidebar-vault-row"
        aria-label={`switch to vault ${vault.name}`}
        title={`${vault.path}`}
      >
        {/* arrow: 16px 컨테이너 + 12px chevron + 90° rotation transition. */}
        <span
          role="button"
          tabIndex={-1}
          onClick={(e) => {
            e.stopPropagation();
            toggleVault();
          }}
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
        <span className="sidebar-vault-name">{vault.name}</span>
        <NewPageButton vault={vault.name} variant="icon" label="페이지" />
        {showMeta && <span className="sidebar-vault-mode">{vault.mode}</span>}
      </button>

      {open && (
        <div style={{ paddingLeft: 8, paddingTop: 2 }}>
          {tree ? (
            tree.children?.length ? (
              tree.children.map((child) => (
                <TreeLeaf
                  key={child.slug}
                  node={child}
                  vault={vault.name}
                  onClose={onClose}
                  activeSlug={activeSlug}
                  filterActive={filterActive}
                  openFolders={openFolders}
                  onToggleFolder={toggleFolder}
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
  depth = 0,
}: {
  node: TNode;
  vault: string;
  onClose: () => void;
  activeSlug: string | null;
  filterActive: boolean;
  openFolders: Set<string>;
  onToggleFolder: (slug: string) => void;
  depth?: number;
}) {
  const nodeSlug = decodeURIComponent(node.slug);
  const isActive = slugMatchesActive(nodeSlug, activeSlug);
  const isOpen = openFolders.has(node.slug) || filterActive;

  if (!node.children || node.children.length === 0) {
    // leaf page
    return (
      <Link
        to={`/page/${vault}/${node.slug}`}
        className={clsx("link-ink sidebar-tree-leaf", isActive && "sidebar-tree-leaf-active")}
        style={{ marginLeft: depth * 14 }}
      >
        <span
          className="sidebar-tree-leaf-dot"
          style={{ background: nodeColor(node.type) }}
          aria-hidden
        />
        {displayTitle(node.slug, node.title)}
      </Link>
    );
  }

  // dir node — chevron + transition + IBM Plex Sans.
  return (
    <div>
      <div className="sidebar-tree-dir-row" style={{ marginLeft: depth * 14 }}>
        <button
          onClick={() => onToggleFolder(node.slug)}
          className="link-ink sidebar-tree-dir"
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
          {displayTitle(node.slug, node.title)}
        </button>
        <NewPageButton
          vault={vault}
          variant="icon"
          label="페이지"
          initialSlug={folderCreatePrefix(node.slug)}
        />
      </div>
      {isOpen &&
        node.children.map((c) => (
          <TreeLeaf
            key={c.slug}
            node={c}
            vault={vault}
            onClose={onClose}
            activeSlug={activeSlug}
            filterActive={filterActive}
            openFolders={openFolders}
            onToggleFolder={onToggleFolder}
            depth={depth + 1}
          />
        ))}
    </div>
  );
}