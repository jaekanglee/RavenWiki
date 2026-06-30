import { useState } from "react";
import { updatePage } from "../lib/api";
import { Button } from "./ui/Button";

export function EditButton({
  vault,
  slug,
  content,
  onSaved,
}: {
  vault: string;
  slug: string;
  content: string;
  onSaved?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [body, setBody] = useState(content);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function save() {
    setBusy(true);
    setMsg(null);
    try {
      await updatePage(vault, slug, { content: body });
      setMsg("✅ 저장 완료");
      setTimeout(() => {
        setOpen(false);
        onSaved?.();
      }, 2400);
    } catch (e: any) {
      setMsg(`❌ ${e.message}`);
      setBusy(false);
    }
  }

  return (
    <>
      <button
        onClick={() => {
          setBody(content);
          setOpen(true);
        }}
        className="btn-secondary page-action-icon"
        aria-label="편집"
        title="편집"
      >
        <span aria-hidden>✏️</span>
      </button>

      {open && (
        <>
          {/* Backdrop */}
          <div
            onClick={() => !busy && setOpen(false)}
            style={{
              position: "fixed",
              inset: 0,
              background: "rgba(0, 0, 0, 0.4)",
              zIndex: 99,
              backdropFilter: "blur(2px)",
            }}
          />

          {/* Side Sheet Panel */}
          <div
            style={{
              position: "fixed",
              top: 0,
              right: 0,
              bottom: 0,
              width: "100%",
              maxWidth: 600,
              background: "var(--color-canvas)",
              borderLeft: "1px solid var(--color-hairline-strong)",
              boxShadow: "var(--shadow-overlay)",
              zIndex: 100,
              padding: "24px",
              display: "flex",
              flexDirection: "column",
              boxSizing: "border-box",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 16,
              }}
            >
              <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>
                편집: <code style={{ fontSize: 13, color: "var(--color-muted)" }}>{slug}</code>
              </h2>
              <button
                onClick={() => !busy && setOpen(false)}
                style={{
                  background: "transparent",
                  border: "none",
                  fontSize: 24,
                  cursor: "pointer",
                  color: "var(--color-muted)",
                }}
                disabled={busy}
              >
                ×
              </button>
            </div>

            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              style={{
                flex: 1,
                width: "100%",
                border: "1px solid var(--color-hairline-strong)",
                borderRadius: "var(--radius-sm)",
                padding: 16,
                fontSize: 13,
                fontFamily: "ui-monospace, SFMono-Regular, monospace",
                outline: "none",
                resize: "none",
                background: "var(--color-canvas)",
                color: "var(--color-ink)",
                lineHeight: 1.5,
              }}
            />

            {msg && (
              <div
                style={{
                  marginTop: 12,
                  padding: 12,
                  background: "var(--color-surface-soft)",
                  fontSize: 13,
                  borderRadius: "var(--radius-sm)",
                  color: "var(--color-ink)",
                  border: "1px solid var(--color-hairline)",
                }}
              >
                {msg}
              </div>
            )}

            <div style={{ display: "flex", gap: 12, justifyContent: "flex-end", marginTop: 16 }}>
              <Button variant="secondary" onClick={() => setOpen(false)} disabled={busy}>
                취소
              </Button>
              <Button variant="primary" onClick={save} disabled={busy}>
                {busy ? "저장 중…" : "저장"}
              </Button>
            </div>
          </div>
        </>
      )}
    </>
  );
}