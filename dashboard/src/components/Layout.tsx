import { Outlet, Link, useLocation } from "react-router-dom";
import clsx from "clsx";
import { Sidebar } from "./Sidebar";
import { SearchBar } from "./SearchBar";
import { VaultPicker } from "./VaultPicker";
import { useEffect, useState } from "react";
import { fetchPages, getActiveVault, setActiveVault } from "../lib/api";
import type { TreeNode } from "../types";

const NAV_TABS = [
  { to: "/", label: "Home", icon: "🏠", match: (p: string) => p === "/" },
  { to: "/graph", label: "Graph", icon: "🕸", match: (p: string) => p.startsWith("/graph") },
  { to: "/search", label: "Search", icon: "🔎", match: (p: string) => p.startsWith("/search") },
  { to: "/log", label: "Log", icon: "📜", match: (p: string) => p.startsWith("/log") },
  { to: "/lint", label: "Lint", icon: "🔧", match: (p: string) => p.startsWith("/lint") },
];

export function Layout() {
  const [vault, setVault] = useState<string>(() => getActiveVault() || "default");
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    if (!vault) return;
    fetchPages(vault)
      .then((pages) => {
        const root: TreeNode = { slug: "root", title: "root", type: "root", children: [] };
        for (const p of pages) {
          const parts = p.slug.split("/");
          let cur = root;
          for (let i = 0; i < parts.length; i++) {
            const part = parts[i];
            const fullSlug = parts.slice(0, i + 1).join("/");
            let child = (cur.children || []).find((c) => c.slug === fullSlug);
            if (!child) {
              child = {
                slug: fullSlug,
                title: i === parts.length - 1 ? p.title : part,
                type: p.type,
                children: [],
              };
              cur.children = cur.children || [];
              cur.children.push(child);
            }
            cur = child;
          }
        }
        setTree(root);
      })
      .catch(() => setTree(null));
  }, [vault, refreshKey]);

  // Track narrow viewport so the drawer state is only meaningful on mobile.
  // Above 744px the drawer/backdrop/hamburger are inert and the sidebar
  // returns to its in-flow 288px layout.
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const mql = window.matchMedia("(max-width: 744px)");
    const onChange = () => {
      const next = mql.matches;
      setIsMobile(next);
      if (!next) setMobileNavOpen(false);
    };
    onChange();
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  // Close the drawer on route change so tapping a leaf link cleanly reveals
  // the destination without leaving the drawer on top of the new view.
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
        vault={vault}
        tree={tree}
        onTreeChange={() => setRefreshKey((k) => k + 1)}
        open={isMobile && mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
      />

      {/* Drawer backdrop — only on mobile when the drawer is open. Tap to close. */}
      {isMobile && mobileNavOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setMobileNavOpen(false)}
          aria-hidden
        />
      )}

      <main className="flex-1 flex flex-col overflow-hidden" style={{ minWidth: 0 }}>
        {/* Top nav — 80px white, 1px bottom hairline.
            Wraps to 2 rows below 1280px (handled by .top-nav-row media query). */}
        <header
          className="top-nav-row flex items-center gap-4 px-8"
          style={{
            height: 80,
            borderBottom: "1px solid var(--color-hairline)",
            background: "var(--color-canvas)",
          }}
        >
          {/* Hamburger — mobile only (≤744px). 44×44 tap target, Apple HIG. */}
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

          {/* Wordmark */}
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
            📚 Wiki
          </Link>

          {/* Vault picker */}
          <div style={{ flexShrink: 0 }}>
            <VaultPicker
              active={vault}
              onChange={(name) => {
                setVault(name);
                setActiveVault(name);
                setRefreshKey((k) => k + 1);
              }}
            />
          </div>

          {/* Search bar — pill, expands. Wraps below the nav row on narrow screens. */}
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

          {/* Right-side product tabs — horizontally scrollable when narrow. */}
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
              >
                <span aria-hidden>{t.icon}</span>
                <span>{t.label}</span>
              </Link>
            ))}
          </nav>
        </header>

        <div
          className="page-content flex-1 overflow-y-auto"
          style={{ padding: "32px 64px", background: "var(--color-canvas)" }}
        >
          <Outlet context={{ vault, refresh: () => setRefreshKey((k) => k + 1) }} />
        </div>
      </main>
    </div>
  );
}
