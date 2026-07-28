import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/Button";
import {
  fetchLinkCheck, runExport, repairVault, cloneVault,
  fetchLocks, releaseLock, apiFetch,
  type LinkCheckResult, type LockEntry,
} from "../lib/api";

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

  // ── P2 도구 상태 ──
  const [toolVault, setToolVault] = useState("");
  const [linkResult, setLinkResult] = useState<LinkCheckResult | null>(null);
  const [locks, setLocks] = useState<Record<string, LockEntry> | null>(null);
  const [toolMsg, setToolMsg] = useState<string | null>(null);
  const [toolBusy, setToolBusy] = useState(false);
  const [repairPath, setRepairPath] = useState("");
  const [cloneName, setCloneName] = useState("");
  const [clonePath, setClonePath] = useState("");

  const loadVaults = useCallback(async () => {
    setLoading(true);
    try {
      const r = await apiFetch("/api/vaults");
      const d = await r.json();
      const items: VaultMeta[] = d.vaults || [];
      setVaults(items);
      const entries = await Promise.all(
        items.map(async (vault) => {
          try {
            const response = await apiFetch(`/api/vaults/${encodeURIComponent(vault.name)}/stats`);
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
      const r = await apiFetch(`/api/vaults/${encodeURIComponent(editingName)}`, {
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
      let r = await apiFetch(`/api/vaults/${encodeURIComponent(name)}`, { method: "DELETE" });
      if (r.status === 409 && window.confirm("문서가 남아 있습니다. vault 폴더까지 강제 삭제할까요?")) {
        r = await apiFetch(`/api/vaults/${encodeURIComponent(name)}?force=true`, { method: "DELETE" });
      }
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `HTTP ${r.status}`);
      await loadVaults();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  // ── P2 도구 핸들러 ──
  const tv = toolVault || vaults[0]?.name || "";

  async function runLinkCheck() {
    if (!tv) return;
    setToolBusy(true); setToolMsg(null); setLinkResult(null);
    try {
      const r = await fetchLinkCheck(tv);
      setLinkResult(r);
      setToolMsg(`링크 점검 완료 — 깨짐 ${r.broken.length}, 누락 ${r.missing.length}`);
    } catch (e) { setToolMsg(`❌ ${e instanceof Error ? e.message : String(e)}`); }
    finally { setToolBusy(false); }
  }

  async function runExportVault() {
    if (!tv) return;
    setToolBusy(true); setToolMsg(null);
    try {
      const r = await runExport(tv);
      setToolMsg(r.ok ? "✅ 정적 export 완료" : "❌ export 실패");
    } catch (e) { setToolMsg(`❌ ${e instanceof Error ? e.message : String(e)}`); }
    finally { setToolBusy(false); }
  }

  async function runRepair() {
    if (!tv || !repairPath.trim()) return;
    if (!window.confirm(`'${tv}' vault 경로를 '${repairPath}' 로 수정할까요?`)) return;
    setToolBusy(true); setToolMsg(null);
    try {
      const r = await repairVault(tv, repairPath.trim());
      setToolMsg(`✅ 경로 수정 완료 → ${r.path}`);
      setRepairPath("");
      await loadVaults();
    } catch (e) { setToolMsg(`❌ ${e instanceof Error ? e.message : String(e)}`); }
    finally { setToolBusy(false); }
  }

  async function runClone() {
    if (!tv || !cloneName.trim() || !clonePath.trim()) return;
    setToolBusy(true); setToolMsg(null);
    try {
      const r = await cloneVault({ src: tv, name: cloneName.trim(), path: clonePath.trim() });
      setToolMsg(`✅ 클론 완료 → ${r.vault} (${r.path})`);
      setCloneName(""); setClonePath("");
      await loadVaults();
    } catch (e) { setToolMsg(`❌ ${e instanceof Error ? e.message : String(e)}`); }
    finally { setToolBusy(false); }
  }

  async function runLocks() {
    if (!tv) return;
    setToolBusy(true); setToolMsg(null); setLocks(null);
    try {
      const r = await fetchLocks(tv);
      setLocks(r.locks);
      const n = Object.keys(r.locks).length;
      setToolMsg(n ? `활성 락 ${n}개` : "활성 락 없음");
    } catch (e) { setToolMsg(`❌ ${e instanceof Error ? e.message : String(e)}`); }
    finally { setToolBusy(false); }
  }

  async function runReleaseLock(slug: string) {
    if (!tv) return;
    setToolBusy(true);
    try {
      await releaseLock(tv, slug);
      setToolMsg(`✅ 락 해제: ${slug}`);
      const r = await fetchLocks(tv);
      setLocks(r.locks);
    } catch (e) { setToolMsg(`❌ ${e instanceof Error ? e.message : String(e)}`); }
    finally { setToolBusy(false); }
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

      {/* ── P2 도구 섹션 ── */}
      {vaults.length > 0 && (
        <div style={{ marginTop: 32, borderTop: "2px solid var(--color-hairline)", paddingTop: 24 }}>
          <h2 style={{ fontSize: 17, margin: "0 0 12px" }}>🔧 도구</h2>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
            <label style={{ fontSize: 13, color: "var(--color-muted)" }}>대상 vault</label>
            <select
              value={tv}
              onChange={(e) => { setToolVault(e.target.value); setLinkResult(null); setLocks(null); setToolMsg(null); }}
              style={{ fontSize: 13, padding: "4px 8px", borderRadius: 6, border: "1px solid var(--color-hairline)" }}
            >
              {vaults.map((v) => <option key={v.name} value={v.name}>{v.name}</option>)}
            </select>
            <Button variant="secondary" size="sm" disabled={toolBusy} onClick={() => void runLinkCheck()}>🔗 링크 점검</Button>
            <Button variant="secondary" size="sm" disabled={toolBusy} onClick={() => void runExportVault()}>📦 Export</Button>
            <Button variant="secondary" size="sm" disabled={toolBusy} onClick={() => void runLocks()}>🔒 락 현황</Button>
          </div>

          {toolMsg && <p style={{ fontSize: 13, margin: "0 0 12px", color: toolMsg.startsWith("❌") ? "var(--color-danger-text)" : "var(--color-muted)" }}>{toolMsg}</p>}

          {/* 링크 점검 결과 */}
          {linkResult && (linkResult.broken.length > 0 || linkResult.missing.length > 0) && (
            <div style={{ fontSize: 12, marginBottom: 16 }}>
              {linkResult.broken.length > 0 && (
                <details style={{ marginBottom: 8 }}>
                  <summary style={{ cursor: "pointer", fontWeight: 600 }}>깨진 링크 ({linkResult.broken.length})</summary>
                  <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 4 }}>
                    <thead><tr style={{ borderBottom: "1px solid var(--color-hairline)" }}>
                      <th style={{ textAlign: "left", padding: "4px 6px" }}>문서</th>
                      <th style={{ textAlign: "left", padding: "4px 6px" }}>대상</th>
                    </tr></thead>
                    <tbody>{linkResult.broken.map((b, i) => (
                      <tr key={i} style={{ borderBottom: "1px solid var(--color-hairline)" }}>
                        <td style={{ padding: "4px 6px", fontFamily: "monospace" }}>{b.slug}</td>
                        <td style={{ padding: "4px 6px", fontFamily: "monospace", color: "var(--color-danger-text)" }}>{b.target}</td>
                      </tr>
                    ))}</tbody>
                  </table>
                </details>
              )}
              {linkResult.missing.length > 0 && (
                <details>
                  <summary style={{ cursor: "pointer", fontWeight: 600 }}>누락 링크 ({linkResult.missing.length})</summary>
                  <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 4 }}>
                    <thead><tr style={{ borderBottom: "1px solid var(--color-hairline)" }}>
                      <th style={{ textAlign: "left", padding: "4px 6px" }}>문서</th>
                      <th style={{ textAlign: "left", padding: "4px 6px" }}>대상</th>
                    </tr></thead>
                    <tbody>{linkResult.missing.map((m, i) => (
                      <tr key={i} style={{ borderBottom: "1px solid var(--color-hairline)" }}>
                        <td style={{ padding: "4px 6px", fontFamily: "monospace" }}>{m.slug}</td>
                        <td style={{ padding: "4px 6px", fontFamily: "monospace", color: "var(--color-warning-text, #b45309)" }}>{m.target}</td>
                      </tr>
                    ))}</tbody>
                  </table>
                </details>
              )}
            </div>
          )}

          {/* 락 현황 */}
          {locks && Object.keys(locks).length > 0 && (
            <div style={{ fontSize: 12, marginBottom: 16 }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead><tr style={{ borderBottom: "1px solid var(--color-hairline)" }}>
                  <th style={{ textAlign: "left", padding: "4px 6px" }}>slug</th>
                  <th style={{ textAlign: "left", padding: "4px 6px" }}>holder</th>
                  <th style={{ textAlign: "left", padding: "4px 6px" }}>획득 시각</th>
                  <th style={{ textAlign: "right", padding: "4px 6px" }}>작업</th>
                </tr></thead>
                <tbody>{Object.entries(locks).map(([slug, entry]) => (
                  <tr key={slug} style={{ borderBottom: "1px solid var(--color-hairline)" }}>
                    <td style={{ padding: "4px 6px", fontFamily: "monospace" }}>{slug}</td>
                    <td style={{ padding: "4px 6px" }}>{entry.holder}</td>
                    <td style={{ padding: "4px 6px", color: "var(--color-muted)" }}>{entry.acquired_at}</td>
                    <td style={{ padding: "4px 6px", textAlign: "right" }}>
                      <Button variant="danger" size="sm" disabled={toolBusy} onClick={() => void runReleaseLock(slug)}>해제</Button>
                    </td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}

          {/* 경로 repair + 클론 */}
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
            <div style={{ flex: "1 1 280px" }}>
              <h3 style={{ fontSize: 14, margin: "0 0 8px" }}>경로 Repair</h3>
              <div style={{ display: "flex", gap: 6 }}>
                <input
                  value={repairPath}
                  onChange={(e) => setRepairPath(e.target.value)}
                  placeholder="올바른 vault 경로"
                  style={{ flex: 1, fontSize: 12, padding: "5px 8px", borderRadius: 6, border: "1px solid var(--color-hairline)", fontFamily: "monospace" }}
                />
                <Button variant="secondary" size="sm" disabled={toolBusy || !repairPath.trim()} onClick={() => void runRepair()}>수정</Button>
              </div>
            </div>
            <div style={{ flex: "1 1 280px" }}>
              <h3 style={{ fontSize: 14, margin: "0 0 8px" }}>Vault 클론</h3>
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                <input
                  value={cloneName}
                  onChange={(e) => setCloneName(e.target.value)}
                  placeholder="새 vault 이름"
                  style={{ flex: "1 1 120px", fontSize: 12, padding: "5px 8px", borderRadius: 6, border: "1px solid var(--color-hairline)" }}
                />
                <input
                  value={clonePath}
                  onChange={(e) => setClonePath(e.target.value)}
                  placeholder="대상 경로"
                  style={{ flex: "2 1 160px", fontSize: 12, padding: "5px 8px", borderRadius: 6, border: "1px solid var(--color-hairline)", fontFamily: "monospace" }}
                />
                <Button variant="secondary" size="sm" disabled={toolBusy || !cloneName.trim() || !clonePath.trim()} onClick={() => void runClone()}>클론</Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
