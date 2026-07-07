import { Outlet, Link, useLocation, Navigate } from "react-router-dom";
import clsx from "clsx";
import { Sidebar } from "./Sidebar";
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
  { to: "/workspace", label: "워크스페이스", icon: "💻", match: (p: string) => p.startsWith("/workspace") },
  { to: "/vault/manage", label: "관리", icon: "⚙", match: (p: string) => p.startsWith("/vault/manage") },
];

export function chooseLayoutVault(vaults: VaultMeta[], current: string, stored: string): string {
  if (current && vaults.some((v) => v.name === current)) return current;
  if (stored && vaults.some((v) => v.name === stored)) return stored;
  return vaults.find((v) => v.default)?.name || vaults[0]?.name || "";
}

// v0.7.97+: 헤더 중앙에 표시되는 경로 crumb. 라우트에서 페이지 컨텍스트 추출.
// /page/{vault}/{slug...} → "홈 / {slug last segment}"
// /raw/{vault}/{rel} → "raw / {file}"
// /graph /search 등 → 라벨 그대로
function HeaderBreadcrumb({ vault, pathname }: { vault: string; pathname: string }) {
  let crumb: string | null = null;
  let m = pathname.match(/^\/page\/[^/]+\/(.+)$/);
  if (m) {
    const slug = decodeURIComponent(m[1]);
    const segs = slug.split("/").filter(Boolean);
    crumb = segs[segs.length - 1] || slug;
  } else {
    m = pathname.match(/^\/raw\/[^/]+\/(.+)$/);
    if (m) crumb = `raw / ${decodeURIComponent(m[1]).split("/").pop()}`;
    else {
      const tab = NAV_TABS.find((t) => t.match(pathname) && t.to !== "/");
      if (tab) crumb = tab.label;
    }
  }
  if (!crumb) return null;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis" }}>
      <span aria-hidden style={{ color: "var(--color-hairline-strong)" }}>/</span>
      <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{crumb}</span>
    </span>
  );
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

  // theme state — 헤더에서 토글
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
      <Sidebar
        vaults={vaults}
        trees={trees}
        rawItems={rawItems}
        activeVault={vault}
        onSelectVault={(name) => { setVault(name); setActiveVault(name); setRefreshKey((k) => k + 1); }}
        onRefresh={() => setRefreshKey((k) => k + 1)}
        open={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
      />

      {mobileNavOpen && <div className="sidebar-backdrop" onClick={() => setMobileNavOpen(false)} aria-hidden />}

      <main className="flex-1 flex flex-col overflow-hidden" style={{ minWidth: 0 }}>
        {/* v0.7.97+: 헤더 — sticky 56px 풀폭. 좌(brand) / 중앙(현재 컨텍스트) / 우(nav + theme).
            노션/옵시디안/Linear 스타일. 헤더는 가볍고, 페이지가 메인. */}
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
              display: "grid",
              gridTemplateColumns: "auto 1fr auto",
              alignItems: "center",
              gap: 16,
            }}
          >
            {/* Left — hamburger + brand */}
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
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
              {/* v0.7.97+: VaultPicker도 헤더 좌측에 inline. compact pill. */}
              {vault && (
                <>
                  <span aria-hidden style={{ color: "var(--color-hairline-strong)", margin: "0 4px" }}>·</span>
                  <VaultPicker
                    active={vault}
                    onChange={(name) => { setVault(name); setActiveVault(name); setRefreshKey((k) => k + 1); }}
                  />
                </>
              )}
            </div>

            {/* Center — 현재 컨텍스트 crumb */}
            <div
              className="app-header-center"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                justifyContent: "center",
                minWidth: 0,
                color: "var(--color-muted)",
                fontSize: 13,
                fontFamily: "var(--font-display)",
                overflow: "hidden",
                whiteSpace: "nowrap",
              }}
            >
              {vault && <HeaderBreadcrumb vault={vault} pathname={location.pathname} />}
            </div>

            {/* Right — nav tabs + theme */}
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <nav className="app-header-nav" style={{ display: "flex", alignItems: "center", gap: 2 }}>
                {NAV_TABS.map((t) => (
                  <Link
                    key={t.to}
                    to={t.to}
                    className={clsx("nav-link nav-link-pill", t.match(location.pathname) && "nav-link-active")}
                    aria-current={t.match(location.pathname) ? "page" : undefined}
                    title={t.label}
                  >
                    <span aria-hidden className="nav-link-icon">{t.icon}</span>
                    <span className="nav-link-label">{t.label}</span>
                  </Link>
                ))}
              </nav>
              <div
                className="app-header-theme"
                style={{
                  marginLeft: 6,
                  display: "flex",
                  border: "1px solid var(--color-hairline)",
                  borderRadius: "var(--radius-full)",
                  padding: 2,
                  gap: 2,
                }}
              >
                <button
                  type="button"
                  onClick={() => theme !== "light" && toggleTheme()}
                  aria-label="라이트 테마"
                  title="라이트"
                  className={clsx("app-header-theme-btn", theme === "light" && "app-header-theme-btn-active")}
                  style={{ fontSize: 13, padding: "3px 8px" }}
                >
                  ☀️
                </button>
                <button
                  type="button"
                  onClick={() => theme !== "dark" && toggleTheme()}
                  aria-label="다크 테마"
                  title="다크"
                  className={clsx("app-header-theme-btn", theme === "dark" && "app-header-theme-btn-active")}
                  style={{ fontSize: 13, padding: "3px 8px" }}
                >
                  🌙
                </button>
              </div>
            </div>
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