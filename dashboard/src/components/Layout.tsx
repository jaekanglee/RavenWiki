import { Outlet, Link, useLocation } from "react-router-dom";
import clsx from "clsx";
import { Sidebar } from "./Sidebar";
import { SearchBar } from "./SearchBar";
import { fetchVaults, fetchPages, getActiveVault, setActiveVault } from "../lib/api";
import { useEffect, useState } from "react";
import type { TreeNode, VaultMeta } from "../types";

const NAV_TABS = [
  { to: "/", label: "홈", icon: "🏠", match: (p: string) => p === "/" },
  { to: "/graph", label: "그래프", icon: "🕸", match: (p: string) => p.startsWith("/graph") },
  { to: "/search", label: "검색", icon: "🔍", match: (p: string) => p.startsWith("/search") },
  { to: "/log", label: "로그", icon: "📋", match: (p: string) => p.startsWith("/log") },
  { to: "/lint", label: "린트", icon: "🛠", match: (p: string) => p.startsWith("/lint") },
  { to: "/vault/manage", label: "관리", icon: "⚙", match: (p: string) => p.startsWith("/vault/manage") },
];

export function chooseLayoutVault(vaults: VaultMeta[], current: string, stored: string): string {
  if (current && vaults.some((v) => v.name === current)) return current;
  if (stored && vaults.some((v) => v.name === stored)) return stored;
  return vaults.find((v) => v.default)?.name || vaults[0]?.name || "";
}

export function Layout() {
  const [vault, setVault] = useState<string>(() => getActiveVault() || "");
  const [vaults, setVaults] = useState<VaultMeta[]>([]);
  const [trees, setTrees] = useState<Record<string, TreeNode | null>>({});
  const [refreshKey, setRefreshKey] = useState(0);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const location = useLocation();

  // ─── load all vaults ────────────────────────────────────────
  useEffect(() => {
    fetchVaults()
      .then((vs) => setVaults(vs))
      .catch(() => setVaults([]));
  }, []);

  // Graph/Search/Log/Lint rely on Layout outlet context. If localStorage is empty
  // (fresh browser / cleared PWA state), keep the UI on the API default vault instead
  // of passing an empty string that makes routes skip their fetches.
  useEffect(() => {
    if (vaults.length === 0) return;
    const next = chooseLayoutVault(vaults, vault, getActiveVault());
    if (!next || next === vault) return;
    setVault(next);
    setActiveVault(next);
  }, [vaults, vault]);

  // ─── build tree per vault (in parallel) ─────────────────────
  useEffect(() => {
    if (vaults.length === 0) return;
    const fetchTree = async (
      vname: string
    ): Promise<[string, TreeNode | null]> => {
      try {
        const pages = await fetchPages(vname);
        const root: TreeNode = {
          slug: "root",
          title: "root",
          type: "root",
          children: [],
        };
        for (const p of pages) {
          const parts = p.slug.split("/");
          let cur = root;
          for (let i = 0; i < parts.length - 1; i++) {
            const part = parts[i];
            let next = cur.children?.find((c) => c.slug === part);
            if (!next) {
              next = { slug: part, title: part, type: "dir", children: [] };
              cur.children = cur.children || [];
              cur.children.push(next);
            }
            cur = next;
          }
          cur.children = cur.children || [];
          cur.children.push({
            slug: p.slug,
            title: p.title || parts[parts.length - 1],
            type: p.type || "?",
          });
        }
        return [vname, root];
      } catch {
        return [vname, null];
      }
    };
    Promise.all(vaults.map((v) => fetchTree(v.name))).then((results) => {
      const map: Record<string, TreeNode | null> = {};
      for (const [name, root] of results) map[name] = root;
      setTrees(map);
    });
  }, [vaults, refreshKey]);

  // Track narrow viewport so the drawer width adapts on small screens.
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const mql = window.matchMedia("(max-width: 744px)");
    const onChange = () => setIsMobile(mql.matches);
    onChange();
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  // Close the drawer on route change.
  useEffect(() => {
    setMobileNavOpen(false);
  }, [location.pathname]);

  // Escape closes the drawer.
  useEffect(() => {
    if (!mobileNavOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileNavOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [mobileNavOpen]);

  return (
    <div className="flex h-screen" style={{ background: "var(--color-canvas)" }}>
      <Sidebar
        vaults={vaults}
        trees={trees}
        activeVault={vault}
        onSelectVault={(name) => {
          setVault(name);
          setActiveVault(name);
          setRefreshKey((k) => k + 1);
          setMobileNavOpen(false);
        }}
        onRefresh={() => setRefreshKey((k) => k + 1)}
        open={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
      />

      {/* Drawer backdrop */}
      {mobileNavOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setMobileNavOpen(false)}
          aria-hidden
        />
      )}

      <main className="flex-1 flex flex-col overflow-hidden" style={{ minWidth: 0 }}>
        <header
          className="top-nav-row flex items-center gap-4 px-8"
          style={{
            height: 80,
            borderBottom: "1px solid var(--color-hairline)",
            background: "var(--color-canvas)",
          }}
        >
          {/* Hamburger — mobile only (≤744px). */}
          <button
            type="button"
            className="header-hamburger"
            onClick={() => setMobileNavOpen((v) => !v)}
            aria-label="메뉴 열기"
            aria-expanded={isMobile && mobileNavOpen}
            aria-controls="primary-sidebar"
          >
            <span aria-hidden style={{ fontSize: 22, lineHeight: 1 }}>
              ☰
            </span>
          </button>

          {/* Wordmark — pure brand, no vault info */}
          <Link
            to="/"
            className="text-ink"
            style={{
              fontSize: 20,
              fontWeight: 700,
              letterSpacing: "-0.2px",
              color: "var(--color-ink)",
              textDecoration: "none",
              flexShrink: 0,
            }}
          >
            <span aria-hidden style={{ marginRight: 6 }}>🐦</span>Raven
          </Link>

          {/* Search bar */}
          <div className="top-nav-search flex-1 flex justify-center min-w-0">
            <div style={{ width: "100%", maxWidth: 560 }}>
              <SearchBar
                vault={vault}
                onSelect={(s) => {
                  window.location.assign(`/page/${s}`);
                }}
              />
            </div>
          </div>

          {/* Right-side product tabs */}
          <nav className="top-nav-tabs flex items-center gap-1">
            {NAV_TABS.map((t) => (
              <Link
                key={t.to}
                to={t.to}
                className={clsx("nav-link", t.match(location.pathname) && "nav-link-active")}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  whiteSpace: "nowrap",
                  flexShrink: 0,
                }}
                aria-current={t.match(location.pathname) ? "page" : undefined}
              >
                <span aria-hidden style={{ fontSize: 14 }}>
                  {t.icon}
                </span>
                {t.label}
              </Link>
            ))}
          </nav>
        </header>

        <div
          className="page-content flex-1 overflow-y-auto"
          style={{ padding: "32px 64px", background: "var(--color-canvas)" }}
        >
          <Outlet
            context={{
              vault,
              refresh: () => setRefreshKey((k) => k + 1),
            }}
          />
        </div>
      </main>
    </div>
  );
}