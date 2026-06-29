import { useState } from "react";
import { deletePage } from "../lib/api";

export function DeleteButton({
  vault,
  slug,
  onDeleted,
}: {
  vault: string;
  slug: string;
  onDeleted?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function del() {
    if (confirm !== slug) {
      setMsg(`확인: "${slug}" 정확히 입력`);
      return;
    }
    setBusy(true);
    setMsg(null);
    try {
      const r = await deletePage(vault, slug);
      setMsg(`✅ 삭제 (archive: ${r.archived_to?.split("/").pop()})`);
      setTimeout(() => {
        setOpen(false);
        onDeleted?.();
      }, 600);
    } catch (e: any) {
      setMsg(`❌ ${e.message}`);
      setBusy(false);
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="btn-secondary page-action-icon"
        style={{
          borderColor: "var(--color-error-text)",
          color: "var(--color-error-text)",
        }}
        aria-label="삭제"
        title="삭제"
      >
        <span aria-hidden>🗑</span>
      </button>

      {open && (
        <div
          onClick={() => !busy && setOpen(false)}
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 50,
            padding: 16,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="card"
            style={{ maxWidth: 480, width: "100%", padding: 32 }}
          >
            <h2 style={{ marginBottom: 12, color: "var(--color-error-text)" }}>
              페이지 삭제
            </h2>
            <p style={{ fontSize: 14, marginBottom: 16, color: "var(--color-body)" }}>
              <code
                style={{
                  background: "var(--color-surface-soft)",
                  padding: "2px 6px",
                  borderRadius: 4,
                  fontSize: 13,
                }}
              >
                {slug}
              </code>{" "}
              을(를) vault <strong>{vault}</strong>에서 삭제합니다. _archive/ 로 백업됨.
            </p>
            <label style={{ display: "block", marginBottom: 16 }}>
              <span
                style={{
                  display: "block",
                  fontSize: 13,
                  fontWeight: 500,
                  marginBottom: 6,
                  color: "var(--color-ink)",
                }}
              >
                확인 — slug 입력
              </span>
              <input
                className="input-base"
                style={{ height: 48, fontFamily: "ui-monospace, SFMono-Regular, monospace" }}
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder={slug}
              />
            </label>
            {msg && (
              <div
                style={{
                  marginBottom: 16,
                  padding: 12,
                  background: "var(--color-surface-soft)",
                  fontSize: 13,
                  borderRadius: "var(--radius-sm)",
                  color: "var(--color-ink)",
                }}
              >
                {msg}
              </div>
            )}
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button
                onClick={() => setOpen(false)}
                disabled={busy}
                className="btn-secondary"
                style={{ height: 40, padding: "10px 20px", fontSize: 14 }}
              >
                취소
              </button>
              <button
                onClick={del}
                disabled={busy}
                className="btn-primary"
                style={{
                  height: 40,
                  padding: "10px 20px",
                  fontSize: 14,
                  background: "var(--color-error-text)",
                }}
              >
                {busy ? "삭제 중…" : "삭제"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}