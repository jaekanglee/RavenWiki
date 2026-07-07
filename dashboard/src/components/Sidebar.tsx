import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import clsx from "clsx";
import { NewPageButton } from "./NewPageButton";
import { NewFolderButton } from "./NewFolderButton";
import { nodeColor } from "./GraphCanvas";
import { RawTree } from "./RawTree";
import { SearchBar } from "./SearchBar";
import type { TreeNode as TNode, VaultMeta } from "../types";

interface SidebarProps {
  vaults: VaultMeta[];
  trees: Record<string, TNode | null>;
  rawItems: Record<string, import("../lib/api").RawItem[]>;
  activeVault: string;
  onSelectVault: (name: string) => void;
  onRefresh?: () => void;
  onTreeChange?: () => void;
  /** Controlled drawer state owned by Layout. Off-canvas only kicks in
   *  inside @media (max-width: 744px); no-op above the breakpoint. */
  open: boolean;
  onClose: () => void;
  theme?: "light" | "dark";
  onToggleTheme?: () => void;
  /** v0.7.97.2+: 현재 라우트 pathname — nav 활성 표시용 */
  currentPath: string;
}

const VAULT_OPEN_KEY = "__vault__";

// v0.7.97.2+: 사이드바 nav. 헤더에서 이관됨. 모바일 drawer에서도 표시.
const SIDEBAR_NAV = [
  { to: "/", label: "홈", icon: "🏠", match: (p: string) => p === "/" },
  { to: "/graph", label: "그래프", icon: "🕸", match: (p: string) => p.startsWith("/graph") },
  { to: "/search", label: "검색", icon: "🔍", match: (p: string) => p.startsWith("/search") },
  { to: "/log", label: "로그", icon: "📋", match: (p: string) => p.startsWith("/log") },
  { to: "/lint", label: "린트", icon: "🛠", match: (p: string) => p.startsWith("/lint") },
  { to: "/garden", label: "정원", icon: "🌱", match: (p: string) => p.startsWith("/garden") },
  { to: "/workspace", label: "워크스페이스", icon: "💻", match: (p: string) => p.startsWith("/workspace") },
  { to: "/vault/manage", label: "관리", icon: "⚙", match: (p: string) => p.startsWith("/vault/manage") },
];

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
  } catch {}
}

function readFavoriteVaults(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.localStorage.getItem("raven.dashboard.favoriteVaults");
    const parsed = raw ? JSON.parse(raw) : [];
    return new Set(Array.isArray(parsed) ? parsed : []);
  } catch {
    return new Set();
  }
}

function writeFavoriteVaults(favs: Set<string>) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem("raven.dashboard.favoriteVaults", JSON.stringify([...favs]));
  } catch {}
}

function slugMatchesActive(nodeSlug: string, activeSlug: string | null): boolean {
  if (!activeSlug) return false;
  if (nodeSlug === activeSlug) return true;
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

export function Sidebar({
  vaults,
  trees,
  rawItems,
  activeVault,
  onSelectVault,
  onRefresh,
  open,
  onClose,
  theme = "light",
  onToggleTheme = () => {},
  currentPath,
}: SidebarProps) {
  const navigate = useNavigate();
  const activePage = activePageFromPath(currentPath);
  const [filter, setFilter] = useState("");
  const [favorites, setFavorites] = useState<Set<string>>(() => readFavoriteVaults());

  function toggleFavorite(name: string) {
    setFavorites((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      writeFavoriteVaults(next);
      return next;
    });
  }

  const activeVaultMeta = vaults.find((v) => v.name === activeVault);
  const activeTree = trees[activeVault] ?? null;
  const activeRawItems = rawItems[activeVault] ?? [];

  return (
    <aside
      id="primary-sidebar"
      className={clsx(
        "layout-sidebar",
        "sidebar-offcanvas",
        open && "sidebar-offcanvas-open",
        "flex flex-col"
      )}
      style={{
        borderRight: "1px solid var(--color-hairline)",
        width: 288,
        padding: "20px 16px",
        background: "var(--color-canvas)",
        flexShrink: 0,
        display: "flex",
        flexDirection: "column",
        height: "100%",
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

      {/* v0.7.97.2+: nav tabs (헤더에서 이관) — 사이드바 최상단 primary nav */}
      <nav
        className="sidebar-nav"
        aria-label="주요 탐색"
        style={{ display: "flex", flexDirection: "column", gap: 2, marginBottom: 16 }}
      >
        {SIDEBAR_NAV.map((t) => {
          const isActive = t.match(currentPath);
          return (
            <Link
              key={t.to}
              to={t.to}
              className={clsx("sidebar-nav-item", isActive && "sidebar-nav-item-active")}
              onClick={onClose}
              aria-current={isActive ? "page" : undefined}
            >
              <span aria-hidden className="sidebar-nav-icon">{t.icon}</span>
              <span className="sidebar-nav-label">{t.label}</span>
            </Link>
          );
        })}
      </nav>

      <div
        style={{ height: 1, background: "var(--color-hairline)", margin: "4px 0 16px" }}
        aria-hidden
      />

      {/* Vault selector */}
      {vaults.length > 0 && (
        <div className="sidebar-vault-selector-container">
          <div
            className="sidebar-label"
            style={{
              padding: "0 4px 6px",
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.32px",
              color: "var(--color-muted)",
              fontFamily: "var(--font-display)",
            }}
          >
            보관소 ({vaults.length})
          </div>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <select
              className="input-base"
              value={activeVault}
              onChange={(e) => onSelectVault(e.target.value)}
              aria-label="보관소 선택"
              style={{ flex: 1, margin: 0 }}
            >
              {[...vaults]
                .sort((a, b) => {
                  const aFav = favorites.has(a.name);
                  const bFav = favorites.has(b.name);
                  if (aFav && !bFav) return -1;
                  if (!aFav && bFav) return 1;
                  if (a.default && !b.default) return -1;
                  if (!a.default && b.default) return 1;
                  return a.name.localeCompare(b.name);
                })
                .map((v) => {
                  const isFav = favorites.has(v.name);
                  return (
                    <option key={v.name} value={v.name}>
                      📁 {isFav ? "⭐ " : ""}{v.name} {v.default ? "★" : ""}
                    </option>
                  );
                })}
            </select>
            <button
              type="button"
              onClick={() => toggleFavorite(activeVault)}
              className={clsx(
                "sidebar-favorite-btn",
                favorites.has(activeVault) && "sidebar-favorite-btn-active"
              )}
              title={favorites.has(activeVault) ? "즐겨찾기 해제" : "즐겨찾기 추가"}
              aria-label={favorites.has(activeVault) ? "즐겨찾기 해제" : "즐겨찾기 추가"}
            >
              ★
            </button>
          </div>
        </div>
      )}

      {vaults.length === 0 && (
        <div style={{ padding: 8, fontSize: 13, color: "var(--color-muted)", fontFamily: "var(--font-display)" }}>
          보관소 없음
        </div>
      )}

      {/* v0.7.97+: 헤더에서 이관된 전역 검색. 필터와 역할 분리. */}
      {vaults.length > 0 && (
        <>
          <div style={{ marginTop: 12 }}>
            <SearchBar
              vault={activeVault}
              variant="sidebar"
              onSelect={(slug) => {
                navigate(`/page/${activeVault}/${slug}`);
                onClose();
              }}
            />
          </div>
          <label className="sidebar-filter-label" style={{ marginTop: 10 }}>
            <span className="sr-only">파일 또는 폴더 필터</span>
            <input
              className="sidebar-filter-input"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="파일 또는 폴더 필터..."
              aria-label="파일 또는 폴더 필터"
            />
          </label>
        </>
      )}

      <div style={{ flex: 1, overflowY: "auto", marginTop: 12 }}>
        {activeVaultMeta ? (
          <VaultTreeGroup
            vault={activeVaultMeta}
            tree={filterTree(activeTree, filter)}
            isActive={true}
            showMeta={false}
            activeSlug={activePage?.vault === activeVault ? activePage.slug : null}
            filterActive={filter.trim().length > 0}
            onSelect={() => {}}
            onClose={onClose}
            onRefresh={onRefresh}
          />
        ) : (
          vaults.length > 0 && (
            <div style={{ padding: 8, fontSize: 13, color: "var(--color-muted)" }}>
              보관소가 선택되지 않았습니다.
            </div>
          )
        )}

        {/* raw/ 섹션 */}
        {activeVaultMeta && activeRawItems.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <div
              className="sidebar-label"
              style={{
                padding: "0 4px 6px",
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: "0.32px",
                color: "var(--color-muted)",
                fontFamily: "var(--font-display)",
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <span>📂</span>
              <span>raw</span>
              <span style={{ marginLeft: "auto", fontWeight: 500, fontSize: 10 }}>
                {activeRawItems.length}
              </span>
            </div>
            <RawTree
              items={activeRawItems}
              selectedPath={activePage?.vault === activeVault ? activePage.slug : null}
              onSelect={(path) => {
                const rel = path.replace(/^raw\//, "");
                navigate(`/raw/${activeVault}/${rel}`);
                onClose();
              }}
              compact
            />
          </div>
        )}
      </div>

      <div style={{ marginTop: "auto", paddingTop: 16, borderTop: "1px solid var(--color-hairline)" }}>
        {/* Mini Stats Widget */}
        <SidebarStatsWidget activeVault={activeVault} />

        <div className="sidebar-theme-switch-container" style={{ marginTop: 12 }}>
          <button
            type="button"
            className={clsx("sidebar-theme-btn", theme === "light" && "sidebar-theme-btn-active")}
            onClick={() => { if (theme !== "light") onToggleTheme(); }}
          >
            ☀️ 라이트
          </button>
          <button
            type="button"
            className={clsx("sidebar-theme-btn", theme === "dark" && "sidebar-theme-btn-active")}
            onClick={() => { if (theme !== "dark") onToggleTheme(); }}
          >
            🌙 다크
          </button>
        </div>
      </div>
    </aside>
  );
}

// ─── helpers ────────────────────────────────────────────────
function activePageFromPath(pathname: string): { vault: string; slug: string } | null {
  let match = pathname.match(/^\/page\/([^/]+)\/(.+)$/);
  if (match) {
    return { vault: decodeURIComponent(match[1]), slug: decodeURIComponent(match[2]) };
  }
  match = pathname.match(/^\/raw\/([^/]+)\/(.+)$/);
  if (match) {
    return { vault: decodeURIComponent(match[1]), slug: `raw/${decodeURIComponent(match[2])}` };
  }
  return null;
}

function displayTitle(node: TNode): string {
  if (node.type === "page") return node.title ?? node.path;
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
      {/* v0.7.97.2+: vault row를 div + role=button 으로 변경 (중첩 <button> 회귀 해결).
          NewPageButton 안의 button이 유효한 HTML 구조 안에 들어가도록. */}
      <div
        role="button"
        tabIndex={0}
        className="sidebar-vault-row"
        onClick={() => {
          toggleFolder(VAULT_OPEN_KEY);
          onSelect();
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            toggleFolder(VAULT_OPEN_KEY);
            onSelect();
          }
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
          <span className="sidebar-vault-default" aria-label="default">★</span>
        )}
        {showMeta && isActive && (
          <span className="sidebar-vault-active" aria-label="active">●</span>
        )}
      </div>

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

// TreeLeaf + SidebarStatsWidget 동일 로직 보존 (v0.6.16+ 표준)
function TreeLeaf({
  node,
  vault,
  onClose,
  activeSlug,
  filterActive,
  openFolders,
  onToggleFolder,
  onRefresh,
  depth,
}: {
  node: TNode;
  vault: string;
  onClose: () => void;
  activeSlug: string | null;
  filterActive: boolean;
  openFolders: Set<string>;
  onToggleFolder: (k: string) => void;
  onRefresh?: () => void;
  depth: number;
}) {
  const navigate = useNavigate();
  const isOpen = openFolders.has(node.path);

  if (node.type === "dir") {
    return (
      <div>
        <button
          type="button"
          className="sidebar-tree-dir-row"
          onClick={() => onToggleFolder(node.path)}
          aria-expanded={isOpen}
          style={{ paddingLeft: 8 + depth * 12 }}
        >
          <span aria-hidden className={clsx("sidebar-chevron", isOpen && "sidebar-chevron-open")}>
            <svg viewBox="0 0 12 12" width="12" height="12" aria-hidden>
              <path d="M4 2 L8 6 L4 10" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </span>
          <span aria-hidden style={{ fontSize: 13 }}>📁</span>
          <span className="sidebar-tree-dir-label">{displayTitle(node)}</span>
        </button>
        {isOpen && (node.children ?? []).length > 0 && (
          <div className="sidebar-tree">
            {(node.children ?? []).map((child) => (
              <TreeLeaf
                key={child.path}
                node={child}
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
        )}
      </div>
    );
  }

  // page
  const isActive = slugMatchesActive(node.path, activeSlug);
  return (
    <button
      type="button"
      className={clsx("sidebar-tree-page-row", isActive && "sidebar-tree-page-row-active")}
      onClick={() => {
        navigate(`/page/${vault}/${node.path.replace(/^content\//, "")}`);
        onClose();
      }}
      style={{ paddingLeft: 8 + depth * 12 }}
      title={node.title ?? node.path}
    >
      <span aria-hidden className="sidebar-tree-page-dot" style={{ background: nodeColor(node.pageType) }} />
      <span className="sidebar-tree-page-label">{displayTitle(node)}</span>
    </button>
  );
}

function SidebarStatsWidget({ activeVault }: { activeVault: string }) {
  return (
    <div
      style={{
        padding: "10px 12px",
        background: "var(--color-surface-soft)",
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-md)",
        fontSize: 12,
        color: "var(--color-muted)",
      }}
    >
      <div style={{ fontWeight: 600, color: "var(--color-ink)", fontSize: 13, marginBottom: 2 }}>
        {activeVault || "—"}
      </div>
      <div style={{ fontFamily: "var(--font-display)" }}>현재 보관소</div>
    </div>
  );
}