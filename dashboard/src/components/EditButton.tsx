import { useState } from "react";
import { updatePage } from "../lib/api";

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
        className="btn-secondary"
        style={{ height: 36, padding: "8px 16px", fontSize: 13 }}
      >
        ✏️ 편집
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
            style={{
              maxWidth: 960,
              width: "100%",
              maxHeight: "90vh",
              padding: 32,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <h2 style={{ marginBottom: 16 }}>
              편집: <code style={{ fontSize: 14, color: "var(--color-muted)" }}>{slug}</code>
            </h2>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              style={{
                flex: 1,
                minHeight: 400,
                border: "1px solid var(--color-hairline-strong)",
                borderRadius: "var(--radius-sm)",
                padding: 12,
                fontSize: 13,
                fontFamily: "ui-monospace, SFMono-Regular, monospace",
                outline: "none",
                resize: "vertical",
                background: "var(--color-canvas)",
                color: "var(--color-ink)",
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
                }}
              >
                {msg}
              </div>
            )}
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 16 }}>
              <button
                onClick={() => setOpen(false)}
                disabled={busy}
                className="btn-secondary"
                style={{ height: 40, padding: "10px 20px", fontSize: 14 }}
              >
                취소
              </button>
              <button
                onClick={save}
                disabled={busy}
                className="btn-primary"
                style={{ height: 40, padding: "10px 20px", fontSize: 14 }}
              >
                {busy ? "저장 중…" : "저장"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}