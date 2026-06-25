import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

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

  useEffect(() => {
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
  }, []);

  function select(name: string) {
    onChange(name);
    localStorage.setItem(ACTIVE_KEY, name);
    setOpen(false);
    // notify server-side active (optional; client-side cache invalidation is the main effect)
    fetch(`/api/vaults/${name}/select`, { method: "POST" }).catch(() => {});
    window.location.reload();
  }

  const current = vaults.find((v) => v.name === active);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="text-sm px-2 py-1 rounded border hover:bg-gray-100 dark:hover:bg-gray-800 whitespace-nowrap"
        disabled={loading}
      >
        {loading ? "…" : `📁 ${current?.name || active || "vault"}`}
      </button>

      {open && (
        <div className="absolute top-full mt-1 left-0 bg-white dark:bg-gray-900 border rounded shadow-lg z-50 min-w-[260px]">
          <div className="p-2 border-b text-xs uppercase text-gray-500">
            vaults ({vaults.length})
          </div>
          {vaults.length === 0 ? (
            <div className="p-3 text-sm text-gray-500">
              no vaults registered.
              <br />
              <code className="text-xs">wikisys vault create &lt;name&gt; &lt;path&gt;</code>
            </div>
          ) : (
            vaults.map((v) => (
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
            ))
          )}
          <div className="border-t p-2 text-xs text-gray-500">
            💡 CLI: <code>wikisys vault list</code>
            <br />
            <Link to="/new-vault" className="text-cyan-600 hover:underline" onClick={() => setOpen(false)}>
              + 새 vault 등록
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
