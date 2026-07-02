/**
 * InlineMarkdownEditor — inline MD split-view editor (v0.7.51+, AGENTS.md §6 인라인 편집 우선)
 *
 * 동작:
 *   - mode='view'  : MDEditor.Markdown (preview only, 기존 MarkdownView와 동일)
 *   - mode='edit'  : MDEditor full editor (좌 source / 우 preview, 50:50 split)
 *
 * UX:
 *   - "✏ 편집" 클릭 → mode='edit', draft = page.content
 *   - source 변경 감지 → dirty=true, "💾 저장" 버튼 primary 강조
 *   - "💾 저장" → updatePage() → 토스트 "✅ 저장 완료" 2400ms → mode='view' + onSaved()
 *   - "✕ 취소" → draft 원복 + mode='view'
 *   - Cmd+E (Mac) / Ctrl+E (Win) → mode toggle
 *
 * Jira/Notion-style: 본문이 modal/sheet에 안 뜨고, 같은 자리에서 즉시 편집.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import MDEditor from "@uiw/react-md-editor";
import { useNavigate } from "react-router-dom";
import { updatePage } from "../lib/api";
import { Button } from "./ui/Button";
import { TextField } from "./ui/TextField";

interface InlineMarkdownEditorProps {
  vault: string;
  slug: string;
  title: string;
  content: string;
  onSaved?: () => void;
  onDelete?: () => void;
}

export function InlineMarkdownEditor({
  vault,
  slug,
  title,
  content,
  onSaved,
  onDelete,
}: InlineMarkdownEditorProps) {
  const [mode, setMode] = useState<"view" | "edit">("view");
  const [draft, setDraft] = useState(content);
  const [titleVal, setTitleVal] = useState(title);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [colorMode, setColorMode] = useState<"light" | "dark">(() => {
    if (typeof document === "undefined") return "light";
    return document.documentElement.classList.contains("dark") ? "dark" : "light";
  });
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);

  // 외부에서 content/title 변경 (다른 vault에서 페이지 fetch) 시 draft/titleVal reset
  useEffect(() => {
    setDraft(content);
    setTitleVal(title);
    setMode("view");
  }, [content, title, vault, slug]);

  // dark mode sync
  useEffect(() => {
    if (typeof document === "undefined") return;
    const root = document.documentElement;
    const sync = () => setColorMode(root.classList.contains("dark") ? "dark" : "light");
    sync();
    const observer = new MutationObserver(sync);
    observer.observe(root, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);

  // Cmd+E / Ctrl+E → mode toggle
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "e") {
        e.preventDefault();
        setMode((m) => (m === "view" ? "edit" : "view"));
      } else if (e.key === "Escape" && mode === "edit") {
        e.preventDefault();
        cancel();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, draft, titleVal]);

  const dirty =
    draft !== content || titleVal !== title;

  const cancel = useCallback(() => {
    setDraft(content);
    setTitleVal(title);
    setMode("view");
  }, [content, title]);

  const save = async () => {
    if (busy) return;
    setBusy(true);
    setToast(null);
    try {
      await updatePage(vault, slug, { content: draft, title: titleVal });
      setToast("✅ 저장 완료");
      setTimeout(() => {
        setMode("view");
        setToast(null);
        onSaved?.();
      }, 2400);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setToast(`❌ 저장 실패: ${msg}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div ref={containerRef}>
      {/* Header: title + mode-aware actions */}
      <div
        className="inline-md-header"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          marginBottom: 12,
        }}
      >
        {mode === "view" ? (
          <h1
            style={{
              margin: 0,
              fontSize: 28,
              fontWeight: 700,
              flex: 1,
            }}
          >
            {titleVal}
          </h1>
        ) : (
          <TextField
            label=""
            value={titleVal}
            onChange={(e) => setTitleVal(e.target.value)}
            placeholder="문서 제목"
            disabled={busy}
            style={{ flex: 1, fontSize: 22, fontWeight: 700 }}
          />
        )}

        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          {mode === "view" ? (
            <>
              {onDelete && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={onDelete}
                  title="삭제"
                  aria-label="삭제"
                >
                  🗑
                </Button>
              )}
              <Button
                type="button"
                variant="primary"
                size="sm"
                onClick={() => setMode("edit")}
                title="편집 (Cmd+E)"
              >
                ✏ 편집
              </Button>
            </>
          ) : (
            <>
              {dirty && (
                <span
                  style={{
                    fontSize: 11,
                    color: "var(--color-warning, #c00)",
                    fontWeight: 600,
                    padding: "0 6px",
                  }}
                  title="저장되지 않은 변경"
                >
                  ●
                </span>
              )}
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={cancel}
                disabled={busy}
                title="취소 (Esc)"
              >
                ✕ 취소
              </Button>
              <Button
                type="button"
                variant="primary"
                size="sm"
                onClick={save}
                disabled={busy || !dirty}
                title="저장"
              >
                {busy ? "저장 중…" : "💾 저장"}
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div
          role="status"
          style={{
            padding: "8px 12px",
            marginBottom: 12,
            background: toast.startsWith("❌")
              ? "var(--color-danger-soft, #fee)"
              : "var(--color-success-soft, #e6ffe6)",
            color: toast.startsWith("❌")
              ? "var(--color-danger, #c00)"
              : "var(--color-success, #080)",
            fontSize: 13,
            borderRadius: 6,
            border: "1px solid var(--color-hairline)",
          }}
        >
          {toast}
        </div>
      )}

      {/* Body: view vs edit */}
      <div className="inline-md-body" data-color-mode={colorMode}>
        {mode === "view" ? (
          <MDEditor.Markdown
            source={draft ?? ""}
            style={{
              backgroundColor: "transparent",
              color: "var(--color-body)",
            }}
          />
        ) : (
          <div
            className="inline-md-editor"
            style={{
              border: "1px solid var(--color-hairline)",
              borderRadius: 8,
              overflow: "hidden",
            }}
          >
            <MDEditor
              value={draft}
              onChange={(v) => setDraft(v ?? "")}
              height={500}
              preview="live"
              visibleDragbar={false}
              data-color-mode={colorMode}
            />
          </div>
        )}
      </div>
    </div>
  );
}
