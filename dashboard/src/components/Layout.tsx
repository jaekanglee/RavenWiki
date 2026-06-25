import { Outlet, Link } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { SearchBar } from "./SearchBar";
import { VaultPicker } from "./VaultPicker";
import { useEffect, useState } from "react";
import { fetchPages, getActiveVault, setActiveVault } from "../lib/api";
import type { TreeNode } from "../types";

export function Layout() {
  const [vault, setVault] = useState<string>(() => getActiveVault() || "default");
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

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
              child = { slug: fullSlug, title: i === parts.length - 1 ? p.title : part, type: p.type, children: [] };
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

  return (
    <div className="flex h-screen">
      <Sidebar vault={vault} tree={tree} onTreeChange={() => setRefreshKey((k) => k + 1)} />
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="border-b p-3 flex items-center gap-3">
          <VaultPicker
            active={vault}
            onChange={(name) => {
              setVault(name);
              setActiveVault(name);
              setRefreshKey((k) => k + 1);
            }}
          />
          <SearchBar vault={vault} onSelect={(s) => location.assign(`/page/${s}`)} />
          <Link to="/graph" className="text-sm whitespace-nowrap">
            🕸 Graph
          </Link>
          <Link to="/search" className="text-sm whitespace-nowrap">
            🔍 Search
          </Link>
          <Link to="/log" className="text-sm whitespace-nowrap">
            📜 Log
          </Link>
          <Link to="/lint" className="text-sm whitespace-nowrap">
            🔧 Lint
          </Link>
        </header>
        <div className="flex-1 overflow-y-auto p-6">
          <Outlet context={{ vault, refresh: () => setRefreshKey((k) => k + 1) }} />
        </div>
      </main>
    </div>
  );
}
