import { useEffect, useRef, useState } from "react";

interface VaultMeta {
  name: string;
  path: string;
  mode: string;
  owner: string;
  default: boolean;
}

const ACTIVE_KEY = "wikisys:active_vault";

export function VaultPicker({ active, onChange }: { active: string; onChange: (name: string) => void }) {
  const [vaults, setVaults] = useState<VaultMeta[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);

  // new vault form state
  const [newName, setNewName] = useState("");
  const [newPath, setNewPath] = useState("");
  const [newMode, setNewMode] = useState("personal");
  const [newBusy, setNewBusy] = useState(false);
  const [newErr, setNewErr] = useState<string | null>(null);

  const wrapperRef = useRef<HTMLDivElement>(null);

  // ─── load vaults ────────────────────────────────────────
  function loadVaults() {
    setLoading(true);
    fetch("/api/vaults")
      .then((r) => (r.ok ? r.json() : { vaults: [] }))
      .then((d) => {
        setVaults(d.vaults || []);
        setLoading(false);
        if (!active && d.vaults?.length) {
          const def = d.vaults.find((v: VaultMeta) => v.default) || d.vaults[0];
          if (def) {
            onChange(def.name);
            localStorage.setItem(ACTIVE_KEY, def.name);
          }
        }
      })
      .catch(() => setLoading(false));
  }

  useEffect(() => {
    loadVaults();
  }, []);

  // ─── close on outside click ──────────────────────────────
  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
        setShowCreate(false);
      }
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  // ─── select vault ────────────────────────────────────────
  function select(name: string) {
    onChange(name);
    localStorage.setItem(ACTIVE_KEY, name);
    setOpen(false);
    setShowCreate(false);
    fetch(`/api/vaults/${name}/select`, { method: "POST" }).catch(() => {});
    window.location.reload();
  }

  // ─── create vault ────────────────────────────────────────
  async function createVault() {
    setNewErr(null);
    if (!newName || !newPath) {
      setNewErr("name + path 필수");
      return;
    }
    setNewBusy(true);
    try {
      const r = await fetch("/api/vaults/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName, path: newPath, mode: newMode }),
      });
      const d = await r.json();
      if (!r.ok || !d.ok) throw new Error(d.error || `HTTP ${r.status}`);
      // success — refresh list, close form
      setShowCreate(false);
      setNewName("");
      setNewPath("");
      loadVaults();
    } catch (e: any) {
      setNewErr(e.message || String(e));
    } finally {
      setNewBusy(false);
    }
  }

  const current = vaults.find((v) => v.name === active);

  return (
    <div className="relative" ref={wrapperRef}>
      <button
        onClick={() => setOpen(!open)}
        className="text-sm px-2 py-1 rounded border hover:bg-gray-100 dark:hover:bg-gray-800 whitespace-nowrap"
        disabled={loading}
      >
        {loading ? "…" : `📁 ${current?.name || active || "vault"}`}
      </button>

      {open && (
        <div className="absolute top-full mt-1 left-0 bg-white dark:bg-gray-900 border rounded shadow-lg z-50 min-w-[280px]">
          <div className="p-2 border-b text-xs uppercase text-gray-500">vaults ({vaults.length})</div>

          {vaults.length === 0 ? (
            <div className="p-3 text-sm text-gray-500">no vaults registered.</div>
          ) : (
            <div className="max-h-64 overflow-y-auto">
              {vaults.map((v) => (
                <button
                  key={v.name}
                  onClick={() => select(v.name)}
                  className={`block w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-800 ${
                    v.name === active ? "bg-cyan-50 dark:bg-cyan-950" : ""
                  }`}
                >
                  <div className="font-medium">
                    {v.default ? "★ " : "  "}
                    {v.name}
                  </div>
                  <div className="text-xs text-gray-500">
                    {v.mode} · {v.owner} · {v.path}
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* ─── create form ──────────────────────────────── */}
          {!showCreate ? (
            <button
              onClick={() => setShowCreate(true)}
              className="block w-full text-left px-3 py-2 text-sm border-t hover:bg-cyan-50 dark:hover:bg-cyan-950 text-cyan-700 dark:text-cyan-300"
            >
              ➕ 새 vault 등록
            </button>
          ) : (
            <div className="border-t p-3 space-y-2 bg-gray-50 dark:bg-gray-950">
              <div className="text-xs uppercase text-gray-500">새 vault</div>
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="name (예: work)"
                className="w-full border rounded px-2 py-1 text-sm"
              />
              <input
                value={newPath}
                onChange={(e) => setNewPath(e.target.value)}
                placeholder="/absolute/path (예: ~/vaults/work)"
                className="w-full border rounded px-2 py-1 text-sm"
              />
              <select
                value={newMode}
                onChange={(e) => setNewMode(e.target.value)}
                className="w-full border rounded px-2 py-1 text-sm"
              >
                <option value="personal">personal</option>
                <option value="shared">shared</option>
                <option value="agent">agent</option>
              </select>
              {newErr && (
                <div className="text-xs text-red-600 dark:text-red-400">{newErr}</div>
              )}
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => {
                    setShowCreate(false);
                    setNewErr(null);
                    setNewName("");
                    setNewPath("");
                  }}
                  disabled={newBusy}
                  className="px-3 py-1 text-xs rounded border hover:bg-gray-100"
                >
                  취소
                </button>
                <button
                  onClick={createVault}
                  disabled={newBusy}
                  className="px-3 py-1 text-xs rounded bg-cyan-600 text-white hover:bg-cyan-700 disabled:opacity-50"
                >
                  {newBusy ? "생성 중…" : "생성"}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
