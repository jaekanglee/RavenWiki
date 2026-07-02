import { Outlet, Link, useLocation, Navigate } from "react-router-dom";
import clsx from "clsx";
import { Sidebar } from "./Sidebar";
import { SearchBar } from "./SearchBar";
import { fetchRawList, fetchVaults, fetchTree, getActiveVault, setActiveVault, type RawItem } from "../lib/api";
import { useEffect, useState } from "react";
import { VaultPicker } from "./VaultPicker";
import type { TreeNode, VaultMeta } from "../types";

const NAV_TABS = [
  { to: "/", label: "홈", icon: "🏠", match: (p: string) => p === "/" },
  { to: "/graph", label: "그래프", icon: "🕸", match: (p: string) => p.startsWith("/graph") },
  { to: "/search", label: "검색", icon: "🔍", match: (p: string) => p.startsWith("/search") },
  { to: "/log", label: "로그", icon: "📋", match: (p: string) => p.startsWith("/log") },
  { to: "/lint", label: "린트", icon: "🛠", match: (p: string) => p.startsWith("/lint") },
  { to: "/garden", label: "정원", icon: "🌱", match: (p: string) => p.startsWith("/garden") },
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
  const [loaded, setLoaded] = useState(false);
  const [trees, setTrees] = useState<Record<string, TreeNode | null>>({});
  // v0.7.50+: raw/ 폴더 트리 (P32 OS directory = first-class).
  const [rawItems, setRawItems] = useState<Record<string, RawItem[]>>({});
  const [refreshKey, setRefreshKey] = useState(0);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const location = useLocation();

  // ─── load theme ─────────────────────────────────────────────
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof window !== "undefined") {
      const stored = window.localStorage.getItem("theme");
      if (stored === "dark" || stored === "light") return stored;
      return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    return "light";
  });

  useEffect(() => {
    const root = window.document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    window.localStorage.setItem("theme", theme);
  }, [theme]);

  // ─── load all vaults ────────────────────────────────────────
  useEffect(() => {
    fetchVaults()
      .then((vs) => {
        setVaults(vs);
        setLoaded(true);
      })
      .catch(() => {
        setVaults([]);
        setLoaded(true);
      });
  }, [refreshKey]);

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
  // v0.6.16+: 폴더는 1차 시민. fetchTree가 OS 디렉토리 + .md 파일을 모두 반환.
  // 빈 폴더도 children: []으로 포함. Sidebar가 그대로 렌더.
  useEffect(() => {
    if (vaults.length === 0) return;
    Promise.all(vaults.map((v) => fetchTree(v.name)))
      .then((results) => {
        const map: Record<string, TreeNode | null> = {};
        for (let i = 0; i < vaults.length; i++) map[vaults[i].name] = results[i];
        setTrees(map);
      });
  }, [vaults, refreshKey]);

  // v0.7.50+: fetch raw/ 트리 (각 vault마다). 404면 빈 배열 (raw/ 없는 vault).
  useEffect(() => {
    if (vaults.length === 0) return;
    Promise.all(vaults.map((v) => fetchRawList(v.name)))
      .then((results) => {
        const map: Record<string, RawItem[]> = {};
        for (let i = 0; i < vaults.length; i++) map[vaults[i].name] = results[i]?.items ?? [];
        setRawItems(map);
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

  // Drawer stays open across route changes. Users close it explicitly via dim area,
  // Escape, or the sidebar close button. This keeps desktop explorer navigation stable.

  // Escape closes the drawer.
  useEffect(() => {
    if (!mobileNavOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileNavOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [mobileNavOpen]);

  if (loaded && vaults.length === 0 && location.pathname !== "/vault/new") {
    return <Navigate to="/vault/new" replace />;
  }

  return (
    <div className="flex h-screen" style={{ background: "var(--color-canvas)" }}>
      <Sidebar
        vaults={vaults}
        trees={trees}
        rawItems={rawItems}
        activeVault={vault}
        onSelectVault={(name) => {
          setVault(name);
          setActiveVault(name);
          setRefreshKey((k) => k + 1);
        }}
        onRefresh={() => setRefreshKey((k) => k + 1)}
        open={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
        theme={theme}
        onToggleTheme={() => setTheme((t) => (t === "light" ? "dark" : "light"))}
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

          {/* Active Vault Indicator */}
          {vault && (
            <div className="flex items-center" style={{ flexShrink: 0, gap: 12 }}>
              <div
                style={{
                  height: 16,
                  width: 1,
                  background: "var(--color-hairline-strong)",
                }}
              />
              <VaultPicker
                active={vault}
                onChange={(name) => {
                  setVault(name);
                  setActiveVault(name);
                  setRefreshKey((k) => k + 1);
                }}
              />
            </div>
          )}

          {/* Search bar */}
          <div className="top-nav-search flex-1 flex justify-center min-w-0">
            <div style={{ width: "100%", maxWidth: 560 }}>
              <SearchBar
                vault={vault}
                onSelect={(s) => {
                  window.location.assign(`/page/${vault}/${s}`);
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