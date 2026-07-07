import { Outlet, Link, useLocation, Navigate } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { fetchRawList, fetchVaults, fetchTree, getActiveVault, setActiveVault, type RawItem } from "../lib/api";
import { useEffect, useState } from "react";
import type { TreeNode, VaultMeta } from "../types";

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
  const [rawItems, setRawItems] = useState<Record<string, RawItem[]>>({});
  const [refreshKey, setRefreshKey] = useState(0);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const location = useLocation();

  // theme state
  const [theme, setTheme] = useState<"light" | "dark">(() => {
    if (typeof window === "undefined") return "light";
    try {
      const stored = window.localStorage.getItem("theme");
      if (stored === "dark" || stored === "light") return stored;
    } catch {}
    if (window.matchMedia("(prefers-color-scheme: dark)").matches) return "dark";
    return "light";
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    const root = window.document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
      root.setAttribute("data-color-mode", "dark");
    } else {
      root.classList.remove("dark");
      root.setAttribute("data-color-mode", "light");
    }
    try { window.localStorage.setItem("theme", theme); } catch {}
  }, [theme]);

  useEffect(() => {
    fetchVaults().then((vs) => { setVaults(vs); setLoaded(true); }).catch(() => { setVaults([]); setLoaded(true); });
  }, [refreshKey]);

  useEffect(() => {
    if (vaults.length === 0) return;
    const next = chooseLayoutVault(vaults, vault, getActiveVault());
    if (!next || next === vault) return;
    setVault(next);
    setActiveVault(next);
  }, [vaults, vault]);

  useEffect(() => {
    if (vaults.length === 0) return;
    Promise.all(vaults.map((v) => fetchTree(v.name)))
      .then((results) => {
        const map: Record<string, TreeNode | null> = {};
        for (let i = 0; i < vaults.length; i++) map[vaults[i].name] = results[i];
        setTrees(map);
      });
  }, [vaults, refreshKey]);

  useEffect(() => {
    if (vaults.length === 0) return;
    Promise.all(vaults.map((v) => fetchRawList(v.name)))
      .then((results) => {
        const map: Record<string, RawItem[]> = {};
        for (let i = 0; i < vaults.length; i++) map[vaults[i].name] = results[i]?.items ?? [];
        setRawItems(map);
      });
  }, [vaults, refreshKey]);

  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const mql = window.matchMedia("(max-width: 744px)");
    const onChange = () => setIsMobile(mql.matches);
    onChange();
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    if (!mobileNavOpen) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setMobileNavOpen(false); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [mobileNavOpen]);

  if (loaded && vaults.length === 0 && location.pathname !== "/vault/new") {
    return <Navigate to="/vault/new" replace />;
  }

  const toggleTheme = () => setTheme((t) => (t === "light" ? "dark" : "light"));

  return (
    <div className="flex h-screen" style={{ background: "var(--color-canvas)" }}>
      {/* v0.7.97.2+: 사이드바가 메인 nav. 헤더는 브랜드만.
          desktop: 상시 노출. mobile: drawer (mobileNavOpen). */}
      <Sidebar
        vaults={vaults}
        trees={trees}
        rawItems={rawItems}
        activeVault={vault}
        onSelectVault={(name) => { setVault(name); setActiveVault(name); setRefreshKey((k) => k + 1); }}
        onRefresh={() => setRefreshKey((k) => k + 1)}
        open={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
        theme={theme}
        onToggleTheme={toggleTheme}
        currentPath={location.pathname}
      />

      {mobileNavOpen && <div className="sidebar-backdrop" onClick={() => setMobileNavOpen(false)} aria-hidden />}

      <main className="flex-1 flex flex-col overflow-hidden" style={{ minWidth: 0 }}>
        {/* v0.7.97.2+: 헤더 — sticky 56px, 브랜드만. nav는 사이드바로.
            노션/옵시디안 스타일. 헤더는 가볍고, 페이지가 메인. */}
        <header
          className="app-header"
          style={{
            height: 56,
            borderBottom: "1px solid var(--color-hairline)",
            background: "var(--color-canvas)",
            boxShadow: "0 1px 0 var(--shadow-base)",
            flexShrink: 0,
            position: "sticky",
            top: 0,
            zIndex: 50,
          }}
        >
          <div
            className="app-header-inner"
            style={{
              height: "100%",
              maxWidth: 1440,
              margin: "0 auto",
              padding: "0 20px",
              display: "flex",
              alignItems: "center",
              gap: 12,
            }}
          >
            <button
              type="button"
              className="header-hamburger"
              onClick={() => setMobileNavOpen((v) => !v)}
              aria-label="메뉴 열기"
              aria-expanded={isMobile && mobileNavOpen}
              aria-controls="primary-sidebar"
            >
              <span aria-hidden style={{ fontSize: 18, lineHeight: 1 }}>☰</span>
            </button>
            <Link
              to="/"
              className="app-header-brand"
              style={{
                fontSize: 17,
                fontWeight: 700,
                letterSpacing: "-0.2px",
                color: "var(--color-ink)",
                textDecoration: "none",
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <span aria-hidden style={{ fontSize: 18 }}>🐦</span>
              <span>Raven</span>
            </Link>
          </div>
        </header>

        <div
          className="page-content flex-1 overflow-y-auto"
          style={{
            width: "100%",
            maxWidth: 1440,
            margin: "0 auto",
            padding: "32px 40px",
            background: "var(--color-canvas)",
          }}
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