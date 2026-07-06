import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import clsx from "clsx";
import { NewPageButton } from "./NewPageButton";
import { NewFolderButton } from "./NewFolderButton";
import { nodeColor } from "./GraphCanvas";
import { RawTree } from "./RawTree";
import type { TreeNode as TNode, VaultMeta } from "../types";

interface SidebarProps {
  vaults: VaultMeta[];
  trees: Record<string, TNode | null>;
  // v0.7.50+: raw/ 트리 (P32 OS directory = first-class). 없으면 null.
  rawItems: Record<string, import("../lib/api").RawItem[]>;
  activeVault: string;
  onSelectVault: (name: string) => void;
  onRefresh?: () => void;
  onTreeChange?: () => void;
  /** Controlled drawer state owned by Layout. Off-canvas only kicks in
   *  inside @media (max-width: 744px); no-op above the breakpoint. */
  open: boolean;
  /** Called by the X button, dim area, and Escape. */
  onClose: () => void;
  theme?: "light" | "dark";
  onToggleTheme?: () => void;
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
  // /page/{vault}/{slug...} (페이지)
  let match = pathname.match(/^\/page\/([^/]+)\/(.+)$/);
  if (match) {
    return {
      vault: decodeURIComponent(match[1]),
      slug: decodeURIComponent(match[2]),
    };
  }
  // v0.7.50+: /raw/{vault}/{relPath...} (raw 파일). slug = 'raw/<relPath>' (트리 매칭용).
  match = pathname.match(/^\/raw\/([^/]+)\/(.+)$/);
  if (match) {
    return {
      vault: decodeURIComponent(match[1]),
      slug: `raw/${decodeURIComponent(match[2])}`,
    };
  }
  // /raw/{vault} (raw 패널 진입, 파일 미선택) — null
  return null;
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
}: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const activePage = activePageFromPath(location.pathname);
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
        padding: "24px 20px",
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

      {vaults.length > 0 && (
        <div className="sidebar-vault-selector-container">
          <div
            className="sidebar-label"
            style={{
              padding: "0 0 6px",
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.32px",
              color: "var(--color-muted)",
              fontFamily: "var(--font-display)",
            }}
          >
            보관소 선택 ({vaults.length})
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
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
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                padding: 0,
                width: 38,
                height: 38,
                fontSize: 16,
                border: "1px solid var(--color-hairline)",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "transparent",
                color: favorites.has(activeVault) ? "var(--color-primary)" : "var(--color-muted)",
                cursor: "pointer",
                transition: "color 0.15s ease",
              }}
              title={favorites.has(activeVault) ? "즐겨찾기 해제" : "즐겨찾기 추가"}
              aria-label={favorites.has(activeVault) ? "즐겨찾기 해제" : "즐겨찾기 추가"}
            >
              ★
            </button>
          </div>
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
          보관소 없음
        </div>
      )}

      {vaults.length > 0 && (
        <label className="sidebar-filter-label">
          <span className="sr-only">파일 또는 폴더 필터</span>
          <input
            className="sidebar-filter-input"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="파일 또는 폴더 필터..."
            aria-label="파일 또는 폴더 필터"
          />
        </label>
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

        {/* v0.7.50+: raw/ 섹션 (P32 OS directory = first-class) */}
        {activeVaultMeta && activeRawItems.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <div
              className="sidebar-label"
              style={{
                padding: "0 0 6px",
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
                // raw/... → /raw/{vault}/<rel> (rel = 'raw/' 이후)
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

        <div className="sidebar-theme-switch-container">
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

  // Render vertical indent lines for hierarchy visual support
  const indentGuides = [];
  for (let i = 1; i < depth; i++) {
    indentGuides.push(
      <span
        key={i}
        className="sidebar-indent-line"
        style={{ left: i * 14 - 7 }}
        aria-hidden
      />
    );
  }

  // ─── page leaf ───
  if (node.type === "page") {
    const slug = node.slug ?? node.path;
    const isActive = slugMatchesActive(slug, activeSlug);
    return (
      <div className="sidebar-tree-leaf-wrapper">
        {indentGuides}
        <Link
          to={`/page/${vault}/${slug}`}
          className={clsx("link-ink sidebar-tree-leaf", isActive && "sidebar-tree-leaf-active")}
          style={{ marginLeft: depth * 14 }}
          title={`물리 경로: ${node.path}`}
        >
          <span
            className="sidebar-tree-leaf-dot"
            style={{ background: nodeColor(node.pageType) }}
            aria-hidden
          />
          {displayTitle(node)}
        </Link>
      </div>
    );
  }

  // ─── dir row ───
  const children = node.children ?? [];
  return (
    <div className="sidebar-tree-leaf-wrapper">
      {indentGuides}
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
        {/* v0.6.22+: 폴더 hover 메뉴 — 인라인 페이지 만들기. initialSlug로 prefix 자동 주입. */}
        <NewPageButton
          vault={vault}
          variant="icon"
          label="페이지"
          initialSlug={node.path}
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

function SidebarStatsWidget({ activeVault }: { activeVault: string }) {
  const [stats, setStats] = useState<{ pages: number; broken: number; locks: number } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!activeVault) return;
    let active = true;
    setLoading(true);

    async function fetchWidgetData() {
      try {
        const [rStats, rLocks] = await Promise.all([
          fetch(`/api/vaults/${encodeURIComponent(activeVault)}/stats`),
          fetch(`/api/vaults/${encodeURIComponent(activeVault)}/locks`),
        ]);
        if (!active) return;
        const dStats = await rStats.json();
        const dLocks = await rLocks.json();
        setStats({
          pages: dStats.pages || 0,
          broken: dStats.broken_links || 0,
          locks: dLocks.locks ? Object.keys(dLocks.locks).length : 0,
        });
      } catch (e) {
        console.error("Sidebar stats fetch fail", e);
      } finally {
        if (active) setLoading(false);
      }
    }

    fetchWidgetData();
    return () => {
      active = false;
    };
  }, [activeVault]);

  if (!activeVault) return null;

  return (
    <div
      style={{
        padding: "10px 12px",
        borderRadius: "var(--radius-sm)",
        background: "var(--color-surface-soft, #f8f9fa)",
        border: "1px solid var(--color-hairline, #e9ecef)",
        marginBottom: 16,
        fontSize: 12,
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 8, color: "var(--color-ink)", display: "flex", justifyContent: "space-between" }}>
        <span>📊 보관소 건강도</span>
        {loading && <span style={{ fontSize: 10, color: "var(--color-muted)" }}>...</span>}
      </div>
      {stats ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8, textAlign: "center" }}>
          <div>
            <div style={{ fontSize: 10, color: "var(--color-muted)" }}>페이지</div>
            <div style={{ fontWeight: 700, color: "var(--color-ink)", marginTop: 2 }}>{stats.pages}</div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: "var(--color-muted)" }}>깨진 링크</div>
            <div style={{ fontWeight: 700, color: stats.broken > 0 ? "var(--color-danger-text)" : "var(--color-ink)", marginTop: 2 }}>{stats.broken}</div>
          </div>
          <div>
            <div style={{ fontSize: 10, color: "var(--color-muted)" }}>활성 락</div>
            <div style={{ fontWeight: 700, color: stats.locks > 0 ? "var(--color-primary)" : "var(--color-ink)", marginTop: 2 }}>{stats.locks}</div>
          </div>
        </div>
      ) : (
        <div style={{ color: "var(--color-muted)", fontSize: 11 }}>데이터가 없습니다</div>
      )}
    </div>
  );
}
