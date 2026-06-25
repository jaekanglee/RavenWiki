import { useEffect, useRef, useState } from "react";

interface VaultMeta {
  name: string;
  path: string;
  mode: string;
  owner: string;
  default: boolean;
}

const ACTIVE_KEY = "raven:active_vault";

export function VaultPicker({
  active,
  onChange,
}: {
  active: string;
  onChange: (name: string) => void;
}) {
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
    function onDoc(e: MouseEvent | PointerEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
        setShowCreate(false);
      }
    }
    document.addEventListener("pointerdown", onDoc, { capture: true });
    document.addEventListener("mousedown", onDoc, { capture: true });
    return () => {
      document.removeEventListener("pointerdown", onDoc, { capture: true } as any);
      document.removeEventListener("mousedown", onDoc, { capture: true } as any);
    };
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
        disabled={loading}
        style={{
          fontSize: 14,
          fontWeight: 500,
          padding: "8px 14px",
          borderRadius: "var(--radius-full)",
          border: "1px solid var(--color-hairline-strong)",
          background: "var(--color-canvas)",
          color: "var(--color-ink)",
          cursor: loading ? "not-allowed" : "pointer",
          whiteSpace: "nowrap",
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
        }}
      >
        {loading ? "…" : `📁 ${current?.name || active || "vault"}`}
      </button>

      {open && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 8px)",
            left: 0,
            background: "var(--color-canvas)",
            border: "1px solid var(--color-hairline)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--shadow-card)",
            zIndex: 50,
            minWidth: 320,
          }}
        >
          <div
            style={{
              padding: "12px 16px 8px",
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.32px",
              textTransform: "uppercase",
              color: "var(--color-muted)",
            }}
          >
            Vaults ({vaults.length})
          </div>

          {vaults.length === 0 ? (
            <div style={{ padding: 16, fontSize: 13, color: "var(--color-muted)" }}>
              no vaults registered.
            </div>
          ) : (
            <div style={{ maxHeight: 256, overflowY: "auto" }}>
              {vaults.map((v) => (
                <button
                  key={v.name}
                  onClick={() => select(v.name)}
                  style={{
                    display: "block",
                    width: "100%",
                    textAlign: "left",
                    padding: "10px 16px",
                    fontSize: 14,
                    background:
                      v.name === active ? "var(--color-surface-soft)" : "transparent",
                    border: "none",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ fontWeight: 500, color: "var(--color-ink)" }}>
                    {v.default ? "★ " : ""}
                    {v.name}
                  </div>
                  <div style={{ fontSize: 12, color: "var(--color-muted)", marginTop: 2 }}>
                    {v.mode} · {v.owner} · {v.path}
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* ─── create form ──────────────────────────────── */}
          <div style={{ borderTop: "1px solid var(--color-hairline)" }}>
            {!showCreate ? (
              <button
                onClick={() => setShowCreate(true)}
                style={{
                  display: "block",
                  width: "100%",
                  textAlign: "left",
                  padding: "10px 16px",
                  fontSize: 14,
                  fontWeight: 500,
                  color: "var(--color-primary)",
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                }}
              >
                ➕ 새 vault 등록
              </button>
            ) : (
              <div style={{ padding: 16, background: "var(--color-surface-soft)" }}>
                <div
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    letterSpacing: "0.32px",
                    textTransform: "uppercase",
                    color: "var(--color-muted)",
                    marginBottom: 8,
                  }}
                >
                  새 vault
                </div>
                <input
                  className="input-pill"
                  style={{
                    background: "var(--color-canvas)",
                    marginBottom: 8,
                    height: 40,
                  }}
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="name (예: work)"
                />
                <input
                  className="input-pill"
                  style={{
                    background: "var(--color-canvas)",
                    marginBottom: 8,
                    height: 40,
                  }}
                  value={newPath}
                  onChange={(e) => setNewPath(e.target.value)}
                  placeholder="/absolute/path"
                />
                <select
                  className="input-pill"
                  style={{
                    background: "var(--color-canvas)",
                    marginBottom: 8,
                    height: 40,
                  }}
                  value={newMode}
                  onChange={(e) => setNewMode(e.target.value)}
                >
                  <option value="personal">personal</option>
                  <option value="shared">shared</option>
                  <option value="agent">agent</option>
                </select>
                {newErr && (
                  <div style={{ fontSize: 12, color: "var(--color-error-text)", marginBottom: 8 }}>
                    {newErr}
                  </div>
                )}
                <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                  <button
                    onClick={() => {
                      setShowCreate(false);
                      setNewErr(null);
                      setNewName("");
                      setNewPath("");
                    }}
                    disabled={newBusy}
                    className="btn-secondary"
                    style={{ height: 36, padding: "8px 16px", fontSize: 13 }}
                  >
                    취소
                  </button>
                  <button
                    onClick={createVault}
                    disabled={newBusy}
                    className="btn-primary"
                    style={{ height: 36, padding: "8px 16px", fontSize: 13 }}
                  >
                    {newBusy ? "생성 중…" : "생성"}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}