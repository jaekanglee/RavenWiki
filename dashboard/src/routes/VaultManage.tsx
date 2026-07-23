import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/Button";

interface VaultMeta {
  name: string;
  path: string;
  mode: string;
  default: boolean;
}

interface VaultStats {
  pages: number;
  size_bytes: number;
  broken_links: number;
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function VaultManage() {
  const navigate = useNavigate();
  const [vaults, setVaults] = useState<VaultMeta[]>([]);
  const [stats, setStats] = useState<Record<string, VaultStats>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [editingName, setEditingName] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const loadVaults = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch("/api/vaults");
      const d = await r.json();
      const items: VaultMeta[] = d.vaults || [];
      setVaults(items);
      const entries = await Promise.all(
        items.map(async (vault) => {
          try {
            const response = await fetch(`/api/vaults/${encodeURIComponent(vault.name)}/stats`);
            const data = await response.json();
            return [vault.name, data.ok ? data as VaultStats : null] as const;
          } catch {
            return [vault.name, null] as const;
          }
        })
      );
      setStats(Object.fromEntries(entries.filter(([, value]) => value)) as Record<string, VaultStats>);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadVaults();
  }, [loadVaults]);

  async function renameVault() {
    if (!editingName || !newName.trim() || newName === editingName) return;
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`/api/vaults/${encodeURIComponent(editingName)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName.trim() }),
      });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `HTTP ${r.status}`);
      setEditingName(null);
      setNewName("");
      await loadVaults();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function deleteVault(name: string) {
    if (!window.confirm(`'${name}' vault 등록을 제거할까요?`)) return;
    setBusy(true);
    setError(null);
    try {
      let r = await fetch(`/api/vaults/${encodeURIComponent(name)}`, { method: "DELETE" });
      if (r.status === 409 && window.confirm("문서가 남아 있습니다. vault 폴더까지 강제 삭제할까요?")) {
        r = await fetch(`/api/vaults/${encodeURIComponent(name)}?force=true`, { method: "DELETE" });
      }
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `HTTP ${r.status}`);
      await loadVaults();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ maxWidth: 1100 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, margin: "0 0 4px" }}>Vault 관리</h1>
          <p className="text-muted" style={{ margin: 0, fontSize: 13 }}>
            등록된 Markdown workspace를 확인하고 이름을 변경하거나 연결을 해제합니다.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Button variant="secondary" onClick={() => navigate("/archive")}>🗄 보관함</Button>
          <Button variant="pillPrimary" onClick={() => navigate("/vault/new")}>새 vault 만들기</Button>
        </div>
      </div>

      {error && <p role="alert" style={{ color: "var(--color-danger-text)", fontSize: 13 }}>{error}</p>}
      {loading ? (
        <p className="text-muted">불러오는 중…</p>
      ) : vaults.length === 0 ? (
        <p className="text-muted">등록된 vault가 없습니다.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ borderBottom: "2px solid var(--color-hairline)" }}>
              <th style={{ textAlign: "left", padding: "10px 8px" }}>이름</th>
              <th style={{ textAlign: "left", padding: "10px 8px" }}>경로</th>
              <th style={{ textAlign: "right", padding: "10px 8px" }}>문서</th>
              <th style={{ textAlign: "right", padding: "10px 8px" }}>링크</th>
              <th style={{ textAlign: "right", padding: "10px 8px" }}>크기</th>
              <th style={{ textAlign: "right", padding: "10px 8px" }}>작업</th>
            </tr>
          </thead>
          <tbody>
            {vaults.map((vault) => {
              const detail = stats[vault.name];
              const editing = editingName === vault.name;
              return (
                <tr key={vault.name} style={{ borderBottom: "1px solid var(--color-hairline)" }}>
                  <td style={{ padding: "10px 8px", fontWeight: 600 }}>
                    {editing ? (
                      <input value={newName} onChange={(e) => setNewName(e.target.value)} aria-label={`${vault.name} 새 이름`} />
                    ) : <>{vault.default ? "★ " : ""}{vault.name}</>}
                  </td>
                  <td style={{ padding: "10px 8px", color: "var(--color-muted)", fontFamily: "ui-monospace, SFMono-Regular, monospace", fontSize: 11 }}>{vault.path}</td>
                  <td style={{ padding: "10px 8px", textAlign: "right" }}>{detail?.pages ?? "—"}</td>
                  <td style={{ padding: "10px 8px", textAlign: "right", color: detail?.broken_links ? "var(--color-danger-text)" : undefined }}>{detail?.broken_links ?? "—"}</td>
                  <td style={{ padding: "10px 8px", textAlign: "right" }}>{detail ? formatBytes(detail.size_bytes) : "—"}</td>
                  <td style={{ padding: "10px 8px", textAlign: "right" }}>
                    {editing ? (
                      <><Button variant="secondary" size="sm" disabled={busy} onClick={() => void renameVault()}>저장</Button>{" "}<Button variant="secondary" size="sm" disabled={busy} onClick={() => setEditingName(null)}>취소</Button></>
                    ) : (
                      <><Button variant="secondary" size="sm" disabled={busy} onClick={() => { setEditingName(vault.name); setNewName(vault.name); }}>이름 변경</Button>{" "}<Button variant="danger" size="sm" disabled={busy} onClick={() => void deleteVault(vault.name)}>삭제</Button></>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
