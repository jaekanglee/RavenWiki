import { Outlet, Link } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { SearchBar } from "./SearchBar";
import { useEffect, useState } from "react";
import type { TreeNode } from "../types";

export function Layout() {
  const [tree, setTree] = useState<TreeNode | null>(null);

  useEffect(() => {
    fetch("/api/index.json")
      .then((r) => (r.ok ? r.json() : null))
      .then(setTree)
      .catch(() => setTree(null));
  }, []);

  return (
    <div className="flex h-screen">
      <Sidebar tree={tree} />
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="border-b p-3 flex items-center gap-3">
          <SearchBar onSelect={(s) => location.assign(`/page/${s}`)} />
          <Link to="/graph" className="text-sm whitespace-nowrap">
            🕸 Graph
          </Link>
          <Link to="/search" className="text-sm whitespace-nowrap">
            🔍 Search
          </Link>
        </header>
        <div className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
