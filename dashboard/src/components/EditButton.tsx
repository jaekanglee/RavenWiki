import { useState } from "react";
import { createPortal } from "react-dom";
import { updatePage } from "../lib/api";
import { Button } from "./ui/Button";
import { TextField } from "./ui/TextField";

export function EditButton({
  vault,
  slug,
  title,
  content,
  onSaved,
}: {
  vault: string;
  slug: string;
  title: string;
  content: string;
  onSaved?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [titleVal, setTitleVal] = useState(title);
  const [body, setBody] = useState(content);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function save() {
    setBusy(true);
    setMsg(null);
    try {
      await updatePage(vault, slug, { content: body, title: titleVal });
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
          setTitleVal(title);
          setBody(content);
          setOpen(true);
        }}
        className="btn-secondary page-action-icon"
        aria-label="편집"
        title="편집"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          aria-hidden="true" style={{ display: "block" }}>
          <path d="M12 20h9" />
          <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
        </svg>
      </button>

      {open && createPortal(
        <>
          {/* Backdrop */}
          <div
            onClick={() => !busy && setOpen(false)}
            style={{
              position: "fixed",
              inset: 0,
              background: "var(--bg-overlay)",
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

            <TextField
              label="제목"
              value={titleVal}
              onChange={(e) => setTitleVal(e.target.value)}
              placeholder="문서 제목을 입력하세요"
              required
              disabled={busy}
            />

            <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0, marginBottom: 16 }}>
              <span style={{ display: "block", fontSize: 13, fontWeight: 500, marginBottom: 6, color: "var(--color-ink)" }}>
                본문
              </span>
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                disabled={busy}
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
            </div>

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
        </>,
        document.body
      )}
    </>
  );
}