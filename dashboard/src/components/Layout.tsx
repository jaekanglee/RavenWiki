import { Outlet, Link, useLocation, useMatch, Navigate } from "react-router-dom";
import clsx from "clsx";
import { Sidebar } from "./Sidebar";
import { fetchRawList, fetchVaults, fetchTree, getActiveVault, setActiveVault, type RawItem } from "../lib/api";
import { useEffect, useState } from "react";
import type { TreeNode, VaultMeta } from "../types";

// v0.7.97.3+: 헤더에서 sub-nav 레일로 분리. 전역 섹션 nav (앱 내 페이지 전환).
// 탭 레일은 헤더 아래 별도 1줄 좌정렬. PKM "탐색 / 섹션 / 콘텐츠" 3단 분리.
const GLOBAL_NAV = [
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

export function Layout() {
  const [vault, setVault] = useState<string>(() => getActiveVault() || "");
  const [vaults, setVaults] = useState<VaultMeta[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [trees, setTrees] = useState<Record<string, TreeNode | null>>({});
  const [rawItems, setRawItems] = useState<Record<string, RawItem[]>>({});
  const [refreshKey, setRefreshKey] = useState(0);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const location = useLocation();

  // v0.7.99+: 현재 path에서 page slug 추출. /page/:vault/* 패턴에 매치될 때만.
  // Sidebar의 VaultTreeGroup activeSlug prop으로 흘러서, PageView 진입 시
  // 사이드바 트리에서 해당 문서 행이 active 강조됨 (v0.7.97 §6 후속).
  // App.tsx 라우트 정의: /page/:vault/* — wildcard `*`에 slug가 들어옴.
  const pageMatch = useMatch("/page/:vault/*");
  const activeSlug = pageMatch?.params["*"] ?? null;

  // theme state — 헤더에서 toggle
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
        activeSlug={activeSlug}
        onSelectVault={(name) => { setVault(name); setActiveVault(name); setRefreshKey((k) => k + 1); }}
        onRefresh={() => setRefreshKey((k) => k + 1)}
        open={mobileNavOpen}
        onClose={() => setMobileNavOpen(false)}
      />

      {mobileNavOpen && <div className="sidebar-backdrop" onClick={() => setMobileNavOpen(false)} aria-hidden />}

      <main className="flex-1 flex flex-col overflow-hidden" style={{ minWidth: 0 }}>
        {/* v0.7.97.3+: 헤더 — 유틸리티. brand + 현재 vault + theme만.
            가운데 안 비고, 과밀 안 됨. 탭 레일은 헤더 아래 별도 1줄. */}
        <header
          className="app-header"
          style={{
            height: 52,
            borderBottom: "1px solid var(--color-hairline)",
            background: "var(--color-canvas)",
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
              display: "flex",
              alignItems: "center",
              padding: "0 16px 0 20px",
              gap: 16,
            }}
          >
            {/* Left — 햄버거 + 브랜드 */}
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
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

            {/* Center spacer — 탭 레일이 헤더 바로 아래로 빠지면서 가운데에 공간이 필요 없게 됨 */}

            {/* Right — theme 토글 (slim pill) */}
            <div
              className="app-header-theme"
              style={{
                marginLeft: "auto",
                display: "flex",
                border: "1px solid var(--color-hairline)",
                borderRadius: "var(--radius-full)",
                padding: 2,
                gap: 2,
                flexShrink: 0,
              }}
            >
              <button
                type="button"
                onClick={() => theme !== "light" && toggleTheme()}
                aria-label="라이트 테마"
                title="라이트"
                className={clsx("app-header-theme-btn", theme === "light" && "app-header-theme-btn-active")}
                style={{ fontSize: 13, padding: "4px 10px" }}
              >
                ☀️
              </button>
              <button
                type="button"
                onClick={() => theme !== "dark" && toggleTheme()}
                aria-label="다크 테마"
                title="다크"
                className={clsx("app-header-theme-btn", theme === "dark" && "app-header-theme-btn-active")}
                style={{ fontSize: 13, padding: "4px 10px" }}
              >
                🌙
              </button>
            </div>
          </div>
        </header>

        {/* v0.7.97.3+: Global section nav 레일 — 헤더 바로 아래 1줄 좌정렬 가로 탭.
            8개가 좁아도 가로 스크롤. vault tree 탐색과 섹션 전환의 위계 분리. */}
        <nav
          className="global-section-nav"
          aria-label="주요 섹션"
          style={{
            height: 44,
            display: "flex",
            alignItems: "center",
            gap: 2,
            padding: "0 16px 0 20px",
            background: "var(--color-canvas)",
            borderBottom: "1px solid var(--color-hairline)",
            overflowX: "auto",
            overflowY: "hidden",
            flexShrink: 0,
            position: "sticky",
            top: 52,
            zIndex: 49,
          }}
        >
          {GLOBAL_NAV.map((t) => {
            const isActive = t.match(location.pathname);
            return (
              <Link
                key={t.to}
                to={t.to}
                className={clsx("section-nav-tab", isActive && "section-nav-tab-active")}
                aria-current={isActive ? "page" : undefined}
                style={{ flexShrink: 0 }}
              >
                <span aria-hidden style={{ fontSize: 14 }}>{t.icon}</span>
                <span>{t.label}</span>
              </Link>
            );
          })}
        </nav>

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