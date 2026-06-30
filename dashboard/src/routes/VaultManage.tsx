import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";

interface VaultMeta {
  name: string;
  path: string;
  mode: string;
  owner: string;
  default: boolean;
}

interface VaultStats {
  pages: number;
  size_bytes: number;
  log_entries: number;
  broken_links: number;
}

interface DeletePreview {
  ok: false;
  vault: string;
  reason: string;
  stats: { pages: number; log_present: boolean };
  hint: string;
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
  const [locks, setLocks] = useState<Record<string, Record<string, any>>>({});
  const [loading, setLoading] = useState(true);
  const [editingName, setEditingName] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [confirmDelete, setConfirmDelete] = useState<{
    name: string;
    preview: DeletePreview | null;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadVaults = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch("/api/vaults");
      const d = await r.json();
      const vs: VaultMeta[] = d.vaults || [];
      setVaults(vs);
      // fetch stats and locks for each in parallel
      const enrichedResults = await Promise.all(
        vs.map(async (v) => {
          try {
            const [sr, lr] = await Promise.all([
              fetch(`/api/vaults/${encodeURIComponent(v.name)}/stats`),
              fetch(`/api/vaults/${encodeURIComponent(v.name)}/locks`),
            ]);
            const sd = await sr.json();
            const ld = await lr.json();
            return [v.name, sd, ld] as const;
          } catch {
            return [v.name, null, null] as const;
          }
        })
      );
      const statsMap: Record<string, VaultStats> = {};
      const locksMap: Record<string, Record<string, any>> = {};
      for (const [name, sd, ld] of enrichedResults) {
        if (sd && sd.ok) statsMap[name] = sd;
        if (ld && ld.ok) locksMap[name] = ld.locks || {};
      }
      setStats(statsMap);
      setLocks(locksMap);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadVaults();
  }, [loadVaults]);

  // ─── rename ────────────────────────────────────────
  async function doRename() {
    if (!editingName || !newName.trim() || newName === editingName) return;
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`/api/vaults/${encodeURIComponent(editingName)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName.trim() }),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${r.status}`);
      }
      setEditingName(null);
      setNewName("");
      await loadVaults();
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setBusy(false);
    }
  }

  // ─── delete (2-step: preview then force) ──────────
  async function requestDelete(name: string) {
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`/api/vaults/${encodeURIComponent(name)}`, {
        method: "DELETE",
      });
      const d = await r.json();
      if (!d.ok && d.reason === "vault contains content") {
        // need confirm with force
        setConfirmDelete({ name, preview: d as DeletePreview });
      } else if (d.ok) {
        await loadVaults();
      } else {
        throw new Error(d.detail || JSON.stringify(d));
      }
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setBusy(false);
    }
  }

  async function confirmForceDelete() {
    if (!confirmDelete) return;
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(
        `/api/vaults/${encodeURIComponent(confirmDelete.name)}?force=true`,
        { method: "DELETE" }
      );
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${r.status}`);
      }
      setConfirmDelete(null);
      await loadVaults();
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ maxWidth: 960 }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
        Vault 관리
      </h1>
      <p style={{ fontSize: 13, color: "var(--color-muted)", marginBottom: 24 }}>
        모든 vault의 통계 확인 / 이름 변경 / 삭제
      </p>

      {error && (
        <div
          role="alert"
          style={{
            padding: 12,
            marginBottom: 16,
            background: "var(--cds-danger, #fff1f1)",
            border: "1px solid var(--cds-danger-border, #fa7878)",
            borderRadius: 4,
            color: "var(--cds-danger-text, #a2191f)",
            fontSize: 13,
          }}
        >
          ⚠ {error}
        </div>
      )}

      {loading ? (
        <div style={{ padding: 16, color: "var(--color-muted)" }}>loading…</div>
      ) : vaults.length === 0 ? (
        <div style={{ padding: 16, color: "var(--color-muted)" }}>
          등록된 vault 없음
        </div>
      ) : (
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: 13,
            background: "var(--color-canvas)",
          }}
        >
          <thead>
            <tr style={{ borderBottom: "2px solid var(--color-hairline)" }}>
              <th style={{ textAlign: "left", padding: "10px 8px" }}>이름</th>
              <th style={{ textAlign: "left", padding: "10px 8px" }}>모드</th>
              <th style={{ textAlign: "left", padding: "10px 8px" }}>경로</th>
              <th style={{ textAlign: "right", padding: "10px 8px" }}>페이지</th>
              <th style={{ textAlign: "right", padding: "10px 8px" }}>log</th>
              <th style={{ textAlign: "right", padding: "10px 8px" }}>broken</th>
              <th style={{ textAlign: "right", padding: "10px 8px" }}>락</th>
              <th style={{ textAlign: "right", padding: "10px 8px" }}>크기</th>
              <th style={{ textAlign: "right", padding: "10px 8px" }}>액션</th>
            </tr>
          </thead>
          <tbody>
            {vaults.map((v) => {
              const s = stats[v.name];
              const isEditing = editingName === v.name;
              return (
                <tr key={v.name} style={{ borderBottom: "1px solid var(--color-hairline)" }}>
                  <td style={{ padding: "8px" }}>
                    {v.default && (
                      <span
                        style={{
                          fontSize: 10,
                          color: "var(--color-primary)",
                          marginRight: 4,
                        }}
                        aria-label="default"
                      >
                        ★
                      </span>
                    )}
                    {isEditing ? (
                      <input
                        autoFocus
                        value={newName}
                        onChange={(e) => setNewName(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") doRename();
                          if (e.key === "Escape") {
                            setEditingName(null);
                            setNewName("");
                          }
                        }}
                        style={{
                          padding: "4px 6px",
                          fontSize: 13,
                          border: "1px solid var(--cds-border-subtle-01, #e0e0e0)",
                          borderRadius: 3,
                          fontFamily: "ui-monospace, SFMono-Regular, monospace",
                        }}
                      />
                    ) : (
                      <span style={{ fontWeight: 600 }}>{v.name}</span>
                    )}
                  </td>
                  <td style={{ padding: "8px" }}>
                    <span
                      style={{
                        fontSize: 11,
                        padding: "2px 6px",
                        background: "var(--cds-field-01, #f4f4f4)",
                        borderRadius: 8,
                      }}
                    >
                      {v.mode}
                    </span>
                  </td>
                  <td
                    style={{
                      padding: "8px",
                      fontFamily: "ui-monospace, SFMono-Regular, monospace",
                      fontSize: 11,
                      color: "var(--color-muted)",
                      maxWidth: 280,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                    title={v.path}
                  >
                    {v.path}
                  </td>
                  <td style={{ padding: "8px", textAlign: "right" }}>
                    {s ? s.pages : "—"}
                  </td>
                  <td style={{ padding: "8px", textAlign: "right" }}>
                    {s ? s.log_entries : "—"}
                  </td>
                  <td
                    style={{
                      padding: "8px",
                      textAlign: "right",
                      color: s && s.broken_links > 0 ? "var(--cds-danger, #a2191f)" : undefined,
                      fontWeight: s && s.broken_links > 0 ? 600 : undefined,
                    }}
                  >
                    {s ? s.broken_links : "—"}
                  </td>
                  <td style={{ padding: "8px", textAlign: "right" }}>
                    {locks[v.name] ? Object.keys(locks[v.name]).length : 0}
                  </td>
                  <td style={{ padding: "8px", textAlign: "right" }}>
                    {s ? formatBytes(s.size_bytes) : "—"}
                  </td>
                  <td style={{ padding: "8px", textAlign: "right" }}>
                    {isEditing ? (
                      <>
                        <button
                          onClick={doRename}
                          disabled={busy || !newName.trim() || newName === v.name}
                          style={btnPrimary}
                        >
                          저장
                        </button>
                        <button
                          onClick={() => {
                            setEditingName(null);
                            setNewName("");
                          }}
                          style={btnGhost}
                        >
                          취소
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={() => {
                            setEditingName(v.name);
                            setNewName(v.name);
                          }}
                          disabled={busy}
                          style={btnGhost}
                          aria-label={`rename ${v.name}`}
                        >
                          ✏️
                        </button>
                        <button
                          onClick={() => requestDelete(v.name)}
                          disabled={busy}
                          style={{ ...btnGhost, color: "var(--cds-danger, #a2191f)" }}
                          aria-label={`delete ${v.name}`}
                        >
                          🗑️
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      <div style={{ marginTop: 16, fontSize: 12, color: "var(--color-muted)" }}>
        💡 새 vault는 <a href="/vault/new">/vault/new</a>에서 만드세요
      </div>

      {/* ─── Active locks section ───────────────────── */}
      {Object.values(locks).some((lMap) => Object.keys(lMap).length > 0) && (
        <div style={{ marginTop: 40 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12, display: "flex", alignItems: "center", gap: 6 }}>
            🔒 활성 락 현황
          </h2>
          <p style={{ fontSize: 13, color: "var(--color-muted)", marginBottom: 16 }}>
            에이전트가 쓰기 작업을 진행하는 동안 충돌을 방지하기 위해 획득한 lock 목록입니다.
          </p>
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              fontSize: 13,
              background: "var(--color-canvas)",
            }}
          >
            <thead>
              <tr style={{ borderBottom: "2px solid var(--color-hairline)" }}>
                <th style={{ textAlign: "left", padding: "10px 8px" }}>보관소</th>
                <th style={{ textAlign: "left", padding: "10px 8px" }}>대상 문서 (slug)</th>
                <th style={{ textAlign: "left", padding: "10px 8px" }}>소유자 (holder)</th>
                <th style={{ textAlign: "left", padding: "10px 8px" }}>획득 시각</th>
                <th style={{ textAlign: "left", padding: "10px 8px" }}>만료 예정</th>
              </tr>
            </thead>
            <tbody>
              {vaults.flatMap((v) => {
                const lMap = locks[v.name] || {};
                return Object.entries(lMap).map(([slug, info]: [string, any]) => (
                  <tr key={`${v.name}-${slug}`} style={{ borderBottom: "1px solid var(--color-hairline)" }}>
                    <td style={{ padding: "8px", fontWeight: 600 }}>{v.name}</td>
                    <td style={{ padding: "8px", fontFamily: "ui-monospace, SFMono-Regular, monospace" }}>
                      <a href={`/page/${v.name}/${slug}`} style={{ color: "var(--color-ink)", textDecoration: "underline" }}>
                        {slug}
                      </a>
                    </td>
                    <td style={{ padding: "8px" }}>{info.holder || "unknown"}</td>
                    <td style={{ padding: "8px", color: "var(--color-muted)" }}>
                      {info.acquired_at ? new Date(info.acquired_at * 1000).toLocaleString() : "—"}
                    </td>
                    <td style={{ padding: "8px", color: "var(--color-muted)" }}>
                      {info.expires_at ? new Date(info.expires_at * 1000).toLocaleString() : "—"}
                    </td>
                  </tr>
                ));
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ─── delete confirm modal ───────────────────── */}
      {confirmDelete && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-modal-title"
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 200,
          }}
        >
          <div
            style={{
              background: "var(--color-canvas)",
              borderRadius: 8,
              padding: 24,
              maxWidth: 480,
              width: "90%",
              boxShadow: "0 8px 32px rgba(0,0,0,0.2)",
            }}
          >
            <h2
              id="delete-modal-title"
              style={{ fontSize: 18, fontWeight: 700, marginBottom: 12 }}
            >
              🗑️ <code>{confirmDelete.name}</code> 정말 삭제?
            </h2>
            {confirmDelete.preview && (
              <div
                style={{
                  padding: 12,
                  marginBottom: 16,
                  background: "var(--cds-warning, #fff8e1)",
                  border: "1px solid var(--cds-warning-border, #f1c21b)",
                  borderRadius: 4,
                  fontSize: 13,
                }}
              >
                ⚠ 이 vault에 컨텐츠가 있어요:
                <ul style={{ margin: "8px 0 0", paddingLeft: 20 }}>
                  <li>
                    페이지: <strong>{confirmDelete.preview.stats.pages}개</strong>
                  </li>
                  <li>
                    log:{" "}
                    <strong>
                      {confirmDelete.preview.stats.log_present ? "있음" : "없음"}
                    </strong>
                  </li>
                </ul>
                <div style={{ marginTop: 8, color: "var(--cds-danger, #a2191f)" }}>
                  강제 삭제 시 디렉토리 전체가 사라집니다 (복구 불가).
                </div>
              </div>
            )}
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button
                onClick={() => setConfirmDelete(null)}
                disabled={busy}
                style={btnGhost}
              >
                취소
              </button>
              <button
                onClick={confirmForceDelete}
                disabled={busy}
                style={{
                  ...btnPrimary,
                  background: "var(--cds-danger, #da1e28)",
                  color: "#fff",
                  borderColor: "var(--cds-danger, #da1e28)",
                }}
              >
                {busy ? "삭제 중…" : "예, 강제 삭제"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const btnPrimary: React.CSSProperties = {
  padding: "4px 10px",
  fontSize: 12,
  fontWeight: 600,
  background: "var(--color-primary)",
  color: "#fff",
  border: "1px solid var(--color-primary)",
  borderRadius: 4,
  cursor: "pointer",
  fontFamily: "inherit",
  marginRight: 4,
};

const btnGhost: React.CSSProperties = {
  padding: "4px 10px",
  fontSize: 12,
  background: "transparent",
  color: "var(--color-ink)",
  border: "1px solid var(--cds-border-subtle-01, #e0e0e0)",
  borderRadius: 4,
  cursor: "pointer",
  fontFamily: "inherit",
  marginRight: 4,
};