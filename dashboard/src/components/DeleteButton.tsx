import { useState } from "react";
import { deletePage } from "../lib/api";
import { TextField } from "./ui/TextField";
import { Modal } from "./ui/Modal";
import { Button } from "./ui/Button";

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
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          aria-hidden="true" style={{ display: "block" }}>
          <polyline points="3 6 5 6 21 6" />
          <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
          <path d="M10 11v6" />
          <path d="M14 11v6" />
          <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
        </svg>
      </button>

      <Modal
        open={open}
        onClose={() => !busy && setOpen(false)}
        maxWidth={480}
        zIndex={50}
        disableBackdropClose={busy}
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
        <TextField
          label="확인 — slug 입력"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          placeholder={slug}
          style={{ fontFamily: "ui-monospace, SFMono-Regular, monospace" }}
        />
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
          <Button variant="secondary" onClick={() => setOpen(false)} disabled={busy}>
            취소
          </Button>
          <Button variant="danger" onClick={del} disabled={busy}>
            {busy ? "삭제 중…" : "삭제"}
          </Button>
        </div>
      </Modal>
    </>
  );
}