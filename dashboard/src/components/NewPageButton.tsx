import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createPage, getActiveVault } from "../lib/api";

interface NewPageButtonProps {
  vault?: string;
  variant?: "pill" | "icon";
  label?: string;
  initialSlug?: string;
}

export function NewPageButton({
  vault: vaultProp,
  variant = "pill",
  label = "새 페이지",
  initialSlug = "",
}: NewPageButtonProps) {
  const [open, setOpen] = useState(false);
  const nav = useNavigate();
  const vault = vaultProp || getActiveVault() || "default";

  const [slug, setSlug] = useState("");
  const [title, setTitle] = useState("");
  const [type, setType] = useState("concept");
  const [tags, setTags] = useState("");
  const [content, setContent] = useState("# 새 페이지\n\n");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit() {
    setErr(null);
    if (!slug || !title) {
      setErr("slug + title 필수");
      return;
    }
    setBusy(true);
    try {
      await createPage(vault, {
        slug,
        title,
        type,
        content,
        tags: tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      });
      setOpen(false);
      nav(`/page/${encodeURIComponent(vault)}/${slug}`);
      window.location.reload();
    } catch (e: any) {
      setErr(`❌ ${e.message}`);
      setBusy(false);
    }
  }

  return (
    <>
      {/* Trigger — sidebar explorer action. Default is full pill; icon variant is used in Vault row. */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          if (initialSlug && !slug) setSlug(initialSlug);
          setOpen(true);
        }}
        className={variant === "icon" ? "sidebar-icon-action" : "btn-pill-primary"}
        style={variant === "pill" ? { width: "100%" } : undefined}
        aria-label={`${vault}에 ${label} 만들기`}
        title={`${vault}에 ${label} 만들기`}
      >
        {variant === "icon" ? "＋" : `➕ ${label}`}
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
              maxWidth: 720,
              width: "100%",
              maxHeight: "90vh",
              overflowY: "auto",
              padding: 32,
            }}
          >
            <h2 style={{ marginBottom: 8 }}>
              새 페이지{" "}
              <span style={{ fontSize: 14, fontWeight: 400, color: "var(--color-muted)" }}>
                in {vault}
              </span>
            </h2>
            <p className="text-muted" style={{ fontSize: 13, marginBottom: 24 }}>
              slug와 title은 필수 항목입니다.
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
                slug *
              </span>
              <input
                className="input-base"
                style={{ height: 48 }}
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder={initialSlug || "content/my-concept"}
              />
              <span style={{ fontSize: 12, color: "var(--color-muted)" }}>
                vault-relative path
              </span>
            </label>

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
                title *
              </span>
              <input
                className="input-base"
                style={{ height: 48 }}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="내 컨셉"
              />
            </label>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 16,
                marginBottom: 16,
              }}
            >
              <label style={{ display: "block" }}>
                <span
                  style={{
                    display: "block",
                    fontSize: 13,
                    fontWeight: 500,
                    marginBottom: 6,
                    color: "var(--color-ink)",
                  }}
                >
                  type
                </span>
                <select
                  className="input-base"
                  style={{ height: 48 }}
                  value={type}
                  onChange={(e) => setType(e.target.value)}
                >
                  <option value="concept">concept</option>
                  <option value="person">person</option>
                  <option value="comparison">comparison</option>
                  <option value="project">project</option>
                  <option value="tool">tool</option>
                  <option value="rule">rule</option>
                  <option value="query">query</option>
                  <option value="journal">journal</option>
                </select>
              </label>
              <label style={{ display: "block" }}>
                <span
                  style={{
                    display: "block",
                    fontSize: 13,
                    fontWeight: 500,
                    marginBottom: 6,
                    color: "var(--color-ink)",
                  }}
                >
                  tags (쉼표 구분)
                </span>
                <input
                  className="input-base"
                  style={{ height: 48 }}
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder="ai, llm"
                />
              </label>
            </div>

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
                본문 (markdown)
              </span>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={10}
                style={{
                  width: "100%",
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
            </label>

            {err && (
              <div
                style={{
                  marginBottom: 16,
                  padding: 12,
                  background: "var(--color-surface-soft)",
                  fontSize: 13,
                  borderRadius: "var(--radius-sm)",
                  color: "var(--color-error-text)",
                }}
              >
                {err}
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
                onClick={submit}
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