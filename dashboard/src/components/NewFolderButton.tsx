import { useState } from "react";
import { createFolder } from "../lib/api";

interface NewFolderButtonProps {
  vault: string;
  parentPath?: string;
  onCreated?: () => void;
  /** Called once when the trigger button is clicked, before the modal opens.
   *  Used by mobile sidebar to auto-close the drawer so the modal isn't
   *  covered by it. Optional — omit to keep old behavior (regression safe). */
  onOpen?: () => void;
}

/**
 * 폴더 만들기 버튼 (v0.6.16+, 폴더 1차 시민).
 *
 * - 사이드바 폴더 row 우측에 위치.
 * - 클릭 시 화면 중앙 모달 (페이지 모달과 분리).
 * - 폴더 경로 1개 입력. depth 무제한. 부수 파일 생성 안 함.
 */
export function NewFolderButton({ vault, parentPath = "", onCreated, onOpen }: NewFolderButtonProps) {
  const [open, setOpen] = useState(false);
  const [path, setPath] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // 입력 보정: 슬래시/공백 trim. parentPath가 있으면 자동 prefix.
  function normalize(raw: string): string {
    const trimmed = raw.trim().replace(/^\/+|\/+$/g, "");
    if (!trimmed) return "";
    // 사용자가 parentPath 명시한 경우엔 그대로 (전체 경로 입력 의도)
    if (trimmed.startsWith("content/")) return trimmed;
    return parentPath ? `${parentPath}/${trimmed}` : trimmed;
  }

  async function submit() {
    setErr(null);
    const finalPath = normalize(path);
    if (!finalPath) {
      setErr("폴더 이름을 입력해 주세요.");
      return;
    }
    setBusy(true);
    try {
      await createFolder(vault, { path: finalPath });
      setOpen(false);
      setPath("");
      onCreated?.();
    } catch (e: any) {
      setErr(`❌ ${e.message || e}`);
      setBusy(false);
    }
  }

  return (
    <>
      <button
        type="button"
        className="sidebar-icon-action"
        onClick={(e) => {
          e.stopPropagation();
          onOpen?.();
          setOpen(true);
        }}
        aria-label={`${vault}에 폴더 만들기`}
        title="폴더 만들기"
      >
        ＋
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
            zIndex: 80,
            padding: 16,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="card"
            style={{
              maxWidth: 480,
              width: "100%",
              padding: 28,
            }}
          >
            <h2 style={{ marginBottom: 8 }}>
              새 폴더 만들기{" "}
              <span style={{ fontSize: 14, fontWeight: 400, color: "var(--color-muted)" }}>
                in {vault}
              </span>
            </h2>
            <p className="text-muted" style={{ fontSize: 13, marginBottom: 20 }}>
              폴더 이름만 정하면 됩니다. 빈 폴더도 sidebar에 그대로 나타나요.
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
                폴더 이름
              </span>
              <input
                className="input-base"
                style={{ height: 48 }}
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder={parentPath ? `${parentPath.split("/").pop()}-하위` : "폴더 이름"}
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === "Enter") submit();
                }}
              />
              <span style={{ fontSize: 12, color: "var(--color-muted)" }}>
                예: <code>사용자</code> · <code>참고/논문</code> ·{" "}
                <code>content/users/admin</code> (전체 경로 직접 입력도 가능)
              </span>
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
                {busy ? "만드는 중…" : "만들기"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}