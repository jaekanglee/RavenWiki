import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Toast } from "../components/ui/Toast";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { Button } from "../components/ui/Button";
import { Modal } from "../components/ui/Modal";

// v0.7.72+: 4개 action icon 이모지 → Lucide SVG (currentColor → var(--color-ink) 자동 상속).
// ui-ux 스킬 §P: 이모지 ❌ (OS별 렌더링 차이, 다크모드 깨짐).
const ActionIcon = {
  Search: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true">
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  ),
  Refresh: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true">
      <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
      <path d="M21 3v5h-5" />
      <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
      <path d="M8 16H3v5" />
    </svg>
  ),
  Edit: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
    </svg>
  ),
  Trash: () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true">
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
      <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
    </svg>
  ),
};

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
  reason: string;
  stats: { pages: number; log_present: boolean };
  hint: string;
}

interface BootstrapStatus {
  ok: boolean;
  mismatched_files: string[];
  missing_files: string[];
  empty_files: string[];
  summary: string;
  error?: string;
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function VaultManage() {
  const navigate = useNavigate();
  const [isCompact, setIsCompact] = useState(false);
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
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [unlockTarget, setUnlockTarget] = useState<{ vaultName: string; slug: string } | null>(null);
  const [confirmBootstrap, setConfirmBootstrap] = useState<string | null>(null);
  // v0.7.82+: banner 자세히 모달 (mismatch/missing 파일 목록)
  const [bootstrapDetail, setBootstrapDetail] = useState<string | null>(null);
  // v0.7.75+: vault 일괄 bootstrap 상태 (페이지 진입 시 자동 검사)
  const [bootstrapStatus, setBootstrapStatus] = useState<Record<string, BootstrapStatus>>({});
  const [bulkUpdating, setBulkUpdating] = useState(false);

  // ─── bootstrap / verify ─────────────────────────────
  async function handleVerify(name: string) {
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`/api/vaults/${encodeURIComponent(name)}/verify`, {
        method: "POST",
      });
      if (r.ok) {
        showToast("✅ 지침 검증 성공: 보관소 지침 파일이 원본 템플릿과 완전히 일치합니다.");
      } else {
        const d = await r.json().catch(() => ({}));
        if (r.status === 409) {
          showToast("⚠️ 지침 불일치 발견: 일부 지침 파일이 원본과 다릅니다. '당겨오기'로 갱신할 수 있습니다.", "error");
        } else {
          throw new Error(d.detail || `HTTP ${r.status}`);
        }
      }
    } catch (e) {
      const msg = String(e instanceof Error ? e.message : e);
      setError(msg);
      showToast(`지침 검증 중 오류 발생: ${msg}`, "error");
    } finally {
      setBusy(false);
    }
  }

  // v0.7.75+: 모든 vault 일괄 verify-all 호출.
  // 페이지 진입 시 자동 (loadVaults → loadBootstrapStatus 체인).
  // §13.1: 단일 fetch 함수로 모음.
  const loadBootstrapStatus = useCallback(async () => {
    try {
      const r = await fetch("/api/vaults/verify-all", { method: "POST" });
      const d = await r.json();
      if (!d || !d.ok && d.results === undefined) return;
      const map: Record<string, BootstrapStatus> = {};
      for (const entry of d.results || []) {
        map[entry.name] = {
          ok: Boolean(entry.ok),
          mismatched_files: entry.mismatched_files || [],
          missing_files: entry.missing_files || [],
          empty_files: entry.empty_files || [],
          summary: entry.summary || "",
          error: entry.error,
        };
      }
      setBootstrapStatus(map);
    } catch {
      // silent — verify 실패가 페이지 로딩을 막아서는 안 됨
    }
  }, []);

  // v0.7.75+: 일괄 업뎃 — 불일치 vault들에 대해 per-vault bootstrap POST.
  // 백엔드는 per-vault bootstrap endpoint만 존재 (commit 1 결정) — 프론트가 루프.
  async function handleBulkUpdateBootstrap() {
    const mismatchedNames = vaults
      .filter((v) => bootstrapStatus[v.name] && !bootstrapStatus[v.name].ok)
      .map((v) => v.name);
    if (mismatchedNames.length === 0) return;
    setBulkUpdating(true);
    setError(null);
    let successCount = 0;
    let failCount = 0;
    for (const name of mismatchedNames) {
      try {
        const r = await fetch(
          `/api/vaults/${encodeURIComponent(name)}/bootstrap`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ profile: "llm-wiki" }),
          }
        );
        if (r.ok) successCount++;
        else failCount++;
      } catch {
        failCount++;
      }
    }
    setBulkUpdating(false);
    if (failCount === 0) {
      showToast(`✅ ${successCount}개 vault 지침 일괄 업뎃 완료`);
    } else {
      showToast(
        `⚠️ ${successCount}개 성공, ${failCount}개 실패 — 콘솔/개별 vault 로그 확인`,
        "error"
      );
    }
    await loadBootstrapStatus(); // 재검증
  }

  async function handleBootstrap(name: string) {
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`/api/vaults/${encodeURIComponent(name)}/bootstrap`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile: "llm-wiki" }),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${r.status}`);
      }
      setConfirmBootstrap(null);
      showToast(`✅ '${name}' 보관소 지침 파일들을 최신 템플릿으로 갱신(당겨오기)했습니다.`);
      await loadVaults();
    } catch (e) {
      const msg = String(e instanceof Error ? e.message : e);
      setError(msg);
      showToast(`지침 당겨오기 실패: ${msg}`, "error");
    } finally {
      setBusy(false);
    }
  }

  // v0.7.71+: showToast는 단순 setToast만. auto-close는 아래 useEffect가 담당 (race-free).
  function showToast(message: string, type: "success" | "error" = "success") {
    setToast({ message, type });
  }

  // v0.7.71+: 2400ms 자동 닫기. unmount 시 cleanup으로 race condition 회피.
  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 2400);
    return () => window.clearTimeout(timer);
  }, [toast]);

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
    // v0.7.75+: vault 로드 후 즉시 bootstrap 일괄 검증 (사용자 누름 불필요)
    void loadBootstrapStatus();
  }, [loadBootstrapStatus]);

  useEffect(() => {
    loadVaults();
  }, [loadVaults]);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 1024px)");
    const sync = () => setIsCompact(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);

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
      showToast(`✅ 보관소 이름을 '${newName.trim()}'로 변경했습니다.`);
      await loadVaults();
    } catch (e) {
      const msg = String(e instanceof Error ? e.message : e);
      setError(msg);
      showToast(`이름 변경 실패: ${msg}`, "error");
    } finally {
      setBusy(false);
    }
  }

  // ─── delete (2-step: preview then force) ──────────
  function initiateDelete(name: string) {
    setConfirmDelete({ name, preview: null });
  }

  async function requestDelete(name: string) {
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`/api/vaults/${encodeURIComponent(name)}`, {
        method: "DELETE",
      });
      const d = await r.json().catch(() => ({}));
      if (r.status === 409 && d.detail?.reason === "vault contains content") {
        // need confirm with force
        setConfirmDelete({ name, preview: d.detail as DeletePreview });
      } else if (r.ok && d.ok) {
        showToast(`✅ '${name}' 보관소를 제거했습니다.`);
        setConfirmDelete(null);
        await loadVaults();
      } else {
        throw new Error(d.detail?.reason || d.detail || JSON.stringify(d));
      }
    } catch (e) {
      const msg = String(e instanceof Error ? e.message : e);
      setError(msg);
      showToast(`삭제 실패: ${msg}`, "error");
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
      showToast(`✅ '${confirmDelete.name}' 보관소를 강제 삭제했습니다.`);
      await loadVaults();
    } catch (e) {
      const msg = String(e instanceof Error ? e.message : e);
      setError(msg);
      showToast(`강제 삭제 실패: ${msg}`, "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleUnlock(vaultName: string, slug: string) {
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(
        `/api/vaults/${encodeURIComponent(vaultName)}/locks?slug=${encodeURIComponent(slug)}`,
        { method: "DELETE" }
      );
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${r.status}`);
      }
      setUnlockTarget(null);
      showToast(`✅ '${slug}' 락을 해제했습니다.`);
      await loadVaults();
    } catch (e) {
      const msg = String(e instanceof Error ? e.message : e);
      setError(msg);
      showToast(`락 해제 실패: ${msg}`, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ maxWidth: 960 }}>
      <Toast open={Boolean(toast)} message={toast?.message ?? ""} type={toast?.type ?? "success"} />
      {/* v0.7.82+: banner 자세히 모달 — mismatch/missing 파일 목록 */}
      <Modal
        open={Boolean(bootstrapDetail)}
        onClose={() => setBootstrapDetail(null)}
        maxWidth={680}
      >
        {bootstrapDetail && bootstrapStatus[bootstrapDetail] && (
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <span style={{ fontSize: 18, fontWeight: 700, color: "var(--color-ink)" }}>
                {bootstrapDetail}
              </span>
              <span
                style={{
                  fontSize: 11,
                  padding: "2px 8px",
                  borderRadius: 8,
                  fontWeight: 600,
                  background: bootstrapStatus[bootstrapDetail].ok
                    ? "var(--color-success-bg)"
                    : "var(--color-danger-bg)",
                  color: bootstrapStatus[bootstrapDetail].ok
                    ? "var(--color-success-text)"
                    : "var(--color-danger-text)",
                }}
              >
                {bootstrapStatus[bootstrapDetail].ok ? "✓ 지침 일치" : "⚠ 지침 불일치"}
              </span>
            </div>
            <p style={{ fontSize: 13, color: "var(--color-muted)", marginBottom: 16 }}>
              {bootstrapStatus[bootstrapDetail].summary}
            </p>
            {bootstrapStatus[bootstrapDetail].mismatched_files.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "var(--color-ink)", marginBottom: 6 }}>
                  Mismatch 파일
                </div>
                <ul style={{ margin: 0, paddingLeft: 20, fontSize: 12, fontFamily: "ui-monospace, SFMono-Regular, monospace", color: "var(--color-danger-text)" }}>
                  {bootstrapStatus[bootstrapDetail].mismatched_files.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
              </div>
            )}
            {bootstrapStatus[bootstrapDetail].missing_files.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "var(--color-ink)", marginBottom: 6 }}>
                  Missing 파일
                </div>
                <ul style={{ margin: 0, paddingLeft: 20, fontSize: 12, fontFamily: "ui-monospace, SFMono-Regular, monospace", color: "var(--color-danger-text)" }}>
                  {bootstrapStatus[bootstrapDetail].missing_files.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
              </div>
            )}
            {bootstrapStatus[bootstrapDetail].empty_files.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "var(--color-ink)", marginBottom: 6 }}>
                  Empty 파일
                </div>
                <ul style={{ margin: 0, paddingLeft: 20, fontSize: 12, fontFamily: "ui-monospace, SFMono-Regular, monospace", color: "var(--color-muted)" }}>
                  {bootstrapStatus[bootstrapDetail].empty_files.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
              </div>
            )}
            {bootstrapStatus[bootstrapDetail].mismatched_files.length === 0 &&
              bootstrapStatus[bootstrapDetail].missing_files.length === 0 &&
              bootstrapStatus[bootstrapDetail].empty_files.length === 0 && (
                <p style={{ fontSize: 13, color: "var(--color-success-text)" }}>
                  모든 Lite bootstrap 파일이 원본 템플릿과 일치합니다.
                </p>
              )}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
              <Button variant="secondary" onClick={() => setBootstrapDetail(null)}>
                닫기
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  const name = bootstrapDetail;
                  setBootstrapDetail(null);
                  if (name) handleBulkUpdateBootstrap();
                }}
                disabled={bulkUpdating || (bootstrapStatus[bootstrapDetail]?.ok ?? false)}
                data-testid="bootstrap-detail-update"
              >
                {bulkUpdating ? "업뎃 중…" : "이 vault 지침 업뎃"}
              </Button>
            </div>
          </div>
        )}
      </Modal>
      <ConfirmDialog
        open={Boolean(unlockTarget)}
        onClose={() => !busy && setUnlockTarget(null)}
        onConfirm={() => {
          if (unlockTarget) {
            handleUnlock(unlockTarget.vaultName, unlockTarget.slug);
          }
        }}
        busy={busy}
        tone="danger"
        title="락을 강제로 해제할까요?"
        description={
          unlockTarget
            ? `'${unlockTarget.slug}' 문서의 활성 락을 제거합니다. 다른 에이전트 작업과 충돌할 수 있습니다.`
            : ""
        }
        confirmLabel="락 해제"
      />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>
            Vault 관리
          </h1>
          <p style={{ fontSize: 13, color: "var(--color-muted)" }}>
            모든 vault의 통계 확인 / 이름 변경 / 삭제
          </p>
        </div>
        <Button variant="pillPrimary" onClick={() => navigate("/vault/new")}>
          ➕ 새 vault 만들기
        </Button>
      </div>

      {error && (
        <div
          role="alert"
          style={{
            padding: 12,
            marginBottom: 16,
            background: "var(--color-danger-bg)",
            border: "1px solid var(--color-danger-border)",
            borderRadius: 4,
            color: "var(--color-danger-text)",
            fontSize: 13,
          }}
        >
          ⚠ {error}
        </div>
      )}

      {/* v0.7.75+: 일괄 지침 업뎃 banner — 진입 시 자동 검사, 불일치 vault가 있으면 표시 */}
      {(() => {
        const mismatched = vaults.filter(
          (v) => bootstrapStatus[v.name] && !bootstrapStatus[v.name].ok
        );
        if (mismatched.length === 0) return null;
        return (
          <div
            role="status"
            data-testid="bulk-bootstrap-banner"
            style={{
              padding: 16,
              marginBottom: 16,
              background: "var(--color-surface-soft)",
              border: "1px solid var(--color-warning-border, #e0a82e)",
              borderRadius: "var(--radius-md)",
              display: "flex",
              alignItems: "center",
              gap: 16,
              flexWrap: "wrap",
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 14, fontWeight: 600, color: "var(--color-ink)", marginBottom: 4 }}>
                ⚠ {mismatched.length}개 vault의 지침이 원본 템플릿과 일치하지 않습니다
              </div>
              <div style={{ fontSize: 12, color: "var(--color-muted)" }}>
                {mismatched.map((v) => v.name).join(", ")}
              </div>
              <div style={{ fontSize: 11, color: "var(--color-muted)", marginTop: 6 }}>
                Raven 버전 업뎃 또는 수동 변경 시 발생할 수 있습니다. SCHEMA.md / PROJECT-WORKFLOW.md / log.md 일치 여부를 검사합니다.
              </div>
            </div>
            <Button
              type="button"
              variant="pillPrimary"
              onClick={handleBulkUpdateBootstrap}
              disabled={bulkUpdating}
              data-testid="bulk-bootstrap-update"
            >
              {bulkUpdating
                ? "업뎃 중…"
                : `🔄 ${mismatched.length}개 vault 일괄 업뎃`}
            </Button>
            <Button
              type="button"
              variant="pillSecondary"
              onClick={() => setBootstrapDetail(mismatched[0].name)}
              data-testid="bulk-bootstrap-detail"
              aria-label="불일치 상세 보기"
            >
              자세히 →
            </Button>
          </div>
        );
      })()}

      {loading ? (
        <div style={{ padding: 16, color: "var(--color-muted)" }}>loading…</div>
      ) : vaults.length === 0 ? (
        <div style={{ padding: 16, color: "var(--color-muted)" }}>
          등록된 vault 없음
        </div>
      ) : !isCompact ? (
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
                          border: "1px solid var(--color-hairline)",
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
                        background: "var(--color-surface-soft)",
                        borderRadius: 8,
                      }}
                    >
                      {v.mode}
                    </span>
                    {/* v0.7.75+: vault별 bootstrap 일치 상태 chip */}
                    {(() => {
                      const bs = bootstrapStatus[v.name];
                      if (!bs) return null;
                      const isOk = bs.ok;
                      return (
                        <span
                          data-testid={`bootstrap-status-${v.name}`}
                          title={isOk ? bs.summary : `불일치: ${bs.summary}`}
                          style={{
                            fontSize: 11,
                            padding: "2px 6px",
                            marginLeft: 4,
                            background: isOk
                              ? "var(--color-success-bg)"
                              : "var(--color-danger-bg)",
                            color: isOk
                              ? "var(--color-success-text)"
                              : "var(--color-danger-text)",
                            borderRadius: 8,
                            fontWeight: 600,
                          }}
                        >
                          {isOk ? "✓ 지침 일치" : "⚠ 지침 불일치"}
                        </span>
                      );
                    })()}
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
                      color: s && s.broken_links > 0 ? "var(--color-danger-text)" : undefined,
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
                          onClick={() => handleVerify(v.name)}
                          disabled={busy}
                          style={btnGhost}
                          title="지침 검증"
                          aria-label={`verify bootstrap for ${v.name}`}
                        >
                          <ActionIcon.Search />
                        </button>
                        <button
                          onClick={() => setConfirmBootstrap(v.name)}
                          disabled={busy}
                          style={btnGhost}
                          title="지침 당겨오기 (부트스트랩 갱신)"
                          aria-label={`bootstrap update for ${v.name}`}
                        >
                          <ActionIcon.Refresh />
                        </button>
                        <button
                          onClick={() => {
                            setEditingName(v.name);
                            setNewName(v.name);
                          }}
                          disabled={busy}
                          style={btnGhost}
                          aria-label={`rename ${v.name}`}
                        >
                          <ActionIcon.Edit />
                        </button>
                        <button
                          onClick={() => initiateDelete(v.name)}
                          disabled={busy}
                          style={{ ...btnGhost, color: "var(--color-danger-text)" }}
                          aria-label={`delete ${v.name}`}
                        >
                          <ActionIcon.Trash />
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <div style={{ display: "grid", gap: 12 }}>
          {vaults.map((v) => {
            const s = stats[v.name];
            const isEditing = editingName === v.name;
            const lockCount = locks[v.name] ? Object.keys(locks[v.name]).length : 0;
            return (
              <div key={v.name} className="card-flat" style={{ padding: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
                  <strong style={{ fontSize: 16 }}>{v.name}</strong>
                  {v.default && <span className="chip">기본</span>}
                  <span className="chip">{v.mode}</span>
                  {lockCount > 0 && <span className="chip">락 {lockCount}</span>}
                </div>
                <div style={{ display: "grid", gap: 8, marginBottom: 12 }}>
                  <MetricRow label="경로" value={v.path} mono />
                  <MetricRow label="페이지" value={s ? String(s.pages) : "—"} />
                  <MetricRow label="로그" value={s ? String(s.log_entries) : "—"} />
                  <MetricRow label="깨진 링크" value={s ? String(s.broken_links) : "—"} accent={Boolean(s && s.broken_links > 0)} />
                  <MetricRow label="크기" value={s ? formatBytes(s.size_bytes) : "—"} />
                </div>
                {isEditing ? (
                  <div style={{ display: "grid", gap: 8 }}>
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
                        padding: "10px 12px",
                        fontSize: 13,
                        border: "1px solid var(--color-hairline-strong)",
                        borderRadius: 6,
                        fontFamily: "ui-monospace, SFMono-Regular, monospace",
                      }}
                    />
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                      <button
                        onClick={doRename}
                        disabled={busy || !newName.trim() || newName === v.name}
                        style={{ ...btnPrimary, marginRight: 0, width: "100%" }}
                      >
                        저장
                      </button>
                      <button
                        onClick={() => {
                          setEditingName(null);
                          setNewName("");
                        }}
                        style={{ ...btnGhost, marginRight: 0, width: "100%" }}
                      >
                        취소
                      </button>
                    </div>
                  </div>
                ) : (
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                    <button
                      onClick={() => handleVerify(v.name)}
                      disabled={busy}
                      style={{ ...btnGhost, marginRight: 0, width: "100%" }}
                    >
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                        <ActionIcon.Search />지침 검증
                      </span>
                    </button>
                    <button
                      onClick={() => setConfirmBootstrap(v.name)}
                      disabled={busy}
                      style={{ ...btnGhost, marginRight: 0, width: "100%" }}
                    >
                      <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                        <ActionIcon.Refresh />지침 당겨오기
                      </span>
                    </button>
                    <button
                      onClick={() => {
                        setEditingName(v.name);
                        setNewName(v.name);
                      }}
                      disabled={busy}
                      style={{ ...btnGhost, marginRight: 0, width: "100%" }}
                    >
                      이름 변경
                    </button>
                    <button
                      onClick={() => initiateDelete(v.name)}
                      disabled={busy}
                      style={{ ...btnGhost, marginRight: 0, width: "100%", color: "var(--color-danger-text)" }}
                    >
                      삭제
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
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
          {!isCompact ? (
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
                <th style={{ textAlign: "right", padding: "10px 8px" }}>액션</th>
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
                    <td style={{ padding: "8px" }}>{info.actor || "unknown"}</td>
                    <td style={{ padding: "8px", color: "var(--color-muted)" }}>
                      {info.since ? new Date(info.since).toLocaleString() : "—"}
                    </td>
                    <td style={{ padding: "8px", color: "var(--color-muted)" }}>
                      {info.expires_at ? new Date(info.expires_at).toLocaleString() : "—"}
                    </td>
                    <td style={{ padding: "8px", textAlign: "right" }}>
                      <button
                        onClick={() => setUnlockTarget({ vaultName: v.name, slug })}
                        disabled={busy}
                        style={{ ...btnGhost, color: "var(--color-danger-text)", margin: 0 }}
                        title="락 해제"
                      >
                        🔓 해제
                      </button>
                    </td>
                  </tr>
                ));
              })}
            </tbody>
          </table>
          ) : (
            <div style={{ display: "grid", gap: 12 }}>
              {vaults.flatMap((v) => {
                const lMap = locks[v.name] || {};
                return Object.entries(lMap).map(([slug, info]: [string, any]) => (
                  <div key={`${v.name}-${slug}`} className="card-flat" style={{ padding: 16 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
                      <strong>{v.name}</strong>
                      <span className="chip">활성 락</span>
                    </div>
                    <div style={{ display: "grid", gap: 8, marginBottom: 12 }}>
                      <MetricRow label="대상" value={slug} mono />
                      <MetricRow label="소유자" value={info.actor || "unknown"} />
                      <MetricRow label="획득 시각" value={info.since ? new Date(info.since).toLocaleString() : "—"} />
                      <MetricRow label="만료 예정" value={info.expires_at ? new Date(info.expires_at).toLocaleString() : "—"} />
                    </div>
                    <button
                      onClick={() => setUnlockTarget({ vaultName: v.name, slug })}
                      disabled={busy}
                      style={{ ...btnGhost, marginRight: 0, width: "100%", color: "var(--color-danger-text)" }}
                    >
                      🔓 락 해제
                    </button>
                  </div>
                ));
              })}
            </div>
          )}
        </div>
      )}

      {/* ─── bootstrap confirm modal ─────────────────── */}
      <ConfirmDialog
        open={Boolean(confirmBootstrap)}
        onClose={() => !busy && setConfirmBootstrap(null)}
        onConfirm={() => confirmBootstrap && handleBootstrap(confirmBootstrap)}
        busy={busy}
        tone="danger"
        title="지침 파일 갱신 (당겨오기)"
        confirmLabel="당겨오기"
      >
        {confirmBootstrap && (
          <div style={{ fontSize: 14, color: "var(--color-ink)", lineHeight: 1.5 }}>
            <strong>{confirmBootstrap}</strong> 보관소의 지침 파일들(<code>SCHEMA.md</code>, <code>PROJECT-WORKFLOW.md</code>, <code>log.md</code>)을 Raven 소스코드에 포함된 최신 템플릿 원본으로 덮어씁니다.<br/>
            <span style={{ fontSize: 13, color: "var(--color-warning-text)", display: "block", marginTop: 8 }}>
              ⚠️ 이미 직접 수정한 지침 내용이 있다면 덮어쓰기되어 손실될 수 있습니다. 진행하시겠습니까?
            </span>
          </div>
        )}
      </ConfirmDialog>

      {/* ─── delete confirm modal ───────────────────── */}
      <ConfirmDialog
        open={Boolean(confirmDelete)}
        onClose={() => !busy && setConfirmDelete(null)}
        onConfirm={
          confirmDelete?.preview
            ? confirmForceDelete
            : () => confirmDelete && requestDelete(confirmDelete.name)
        }
        busy={busy}
        tone="danger"
        title={
          confirmDelete
            ? confirmDelete.preview
              ? `⚠️ '${confirmDelete.name}' 강제 삭제 경고`
              : `🗑️ '${confirmDelete.name}' 보관소 제거`
            : ""
        }
        confirmLabel={confirmDelete?.preview ? "예, 강제 삭제 (복구 불가)" : "제거 진행"}
      >
        {confirmDelete && (
          confirmDelete.preview ? (
            <div
              style={{
                padding: 12,
                marginBottom: 4,
                background: "var(--color-warning-bg)",
                border: "1px solid var(--color-warning-border)",
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
              <div style={{ marginTop: 8, color: "var(--color-danger-text)" }}>
                강제 삭제 시 디렉토리 전체가 사라집니다 (복구 불가).
              </div>
            </div>
          ) : (
            <div style={{ fontSize: 14, color: "var(--color-ink)", lineHeight: 1.5 }}>
              <strong>{confirmDelete.name}</strong> 보관소를 레이븐 레지스트리에서 제거하시겠습니까?<br/>
              <span style={{ fontSize: 13, color: "var(--color-muted)", display: "block", marginTop: 4 }}>
                (디바이스 디스크의 실제 파일은 삭제되지 않으며 등록만 해제됩니다.)
              </span>
            </div>
          )
        )}
      </ConfirmDialog>
    </div>
  );
}

const btnPrimary: React.CSSProperties = {
  padding: "4px 10px",
  fontSize: 12,
  fontWeight: 600,
  background: "var(--color-primary)",
  color: "var(--color-on-primary)",
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
  border: "1px solid var(--color-hairline)",
  borderRadius: 4,
  cursor: "pointer",
  fontFamily: "inherit",
  marginRight: 4,
};

function MetricRow({
  label,
  value,
  mono = false,
  accent = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
  accent?: boolean;
}) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
      <span style={{ fontSize: 12, color: "var(--color-muted)", flexShrink: 0 }}>{label}</span>
      <span
        style={{
          fontSize: 13,
          color: accent ? "var(--color-danger-text)" : "var(--color-ink)",
          fontWeight: accent ? 700 : 500,
          textAlign: "right",
          wordBreak: "break-all",
          fontFamily: mono ? "ui-monospace, SFMono-Regular, monospace" : "inherit",
        }}
      >
        {value}
      </span>
    </div>
);
}
