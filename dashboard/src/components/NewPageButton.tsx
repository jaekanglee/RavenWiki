import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import { createPage, fetchTree, getActiveVault } from "../lib/api";
import type { TreeNode } from "../types";

interface NewPageButtonProps {
  vault?: string;
  variant?: "pill" | "icon";
  label?: string;
  initialSlug?: string;
  /** Called once when the trigger button is clicked, before the modal opens.
   *  Used by mobile sidebar to auto-close the drawer so the modal isn't
   *  covered by it. Optional — omit to keep old behavior (regression safe). */
  onOpen?: () => void;
}

export function NewPageButton({
  vault: vaultProp,
  variant = "pill",
  label = "새 페이지",
  initialSlug = "",
  onOpen,
}: NewPageButtonProps) {
  const [open, setOpen] = useState(false);
  const nav = useNavigate();
  const vault = vaultProp || getActiveVault() || "default";

  const [slug, setSlug] = useState("");
  const [title, setTitle] = useState("");
  const [type, setType] = useState("concept");
  const [tags, setTags] = useState("");
  const [content, setContent] = useState("# 새 페이지\n\n");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  // v0.6.19+: 경로 피커 — modal 열릴 때 vault 트리 fetch, 폴더 클릭 시 slug prefix 주입
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [treeErr, setTreeErr] = useState(false);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    fetchTree(vault)
      .then((t) => {
        if (!cancelled) setTree(t);
      })
      .catch(() => {
        if (!cancelled) setTreeErr(true);
      });
    return () => {
      cancelled = true;
    };
  }, [open, vault]);

  function pickFolder(folderPath: string) {
    // 기존 slug에 다른 prefix가 있으면 제거하고 새 prefix 적용
    // 사용자가 파일명을 이어서 입력할 수 있도록 trailing slash 유지
    setSlug((prev) => {
      const trimmed = prev.replace(/^content\//, "").replace(/\/[^/]*$/, "");
      if (folderPath === "content") return trimmed ? `content/${trimmed}` : "content/";
      return `${folderPath}/${trimmed}`.replace(/\/+$/, "/");
    });
  }

  async function submit() {
    setErr(null);
    if (!slug || !title) {
      setErr("파일 경로와 제목을 입력해 주세요.");
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
          onOpen?.();
          setOpen(true);
        }}
        className={variant === "icon" ? "sidebar-icon-action" : "btn-pill-primary"}
        style={variant === "pill" ? { width: "100%" } : undefined}
        aria-label={`${vault}에 ${label} 만들기`}
        title={`${vault}에 ${label} 만들기`}
      >
        {variant === "icon" ? "＋" : `➕ ${label}`}
      </button>

      {open && createPortal(
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
              maxWidth: 880,
              width: "100%",
              maxHeight: "90vh",
              overflow: "hidden", // 2-column scroll 처리
              padding: 32,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <h2 style={{ marginBottom: 8 }}>
              새 페이지 만들기{" "}
              <span style={{ fontSize: 14, fontWeight: 400, color: "var(--color-muted)" }}>
                in {vault}
              </span>
            </h2>
            <p className="text-muted" style={{ fontSize: 13, marginBottom: 24 }}>
              제목과 저장 위치만 정하면 바로 만들 수 있습니다.
            </p>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(180px, 240px) 1fr",
                gap: 24,
                overflowY: "auto",
                flex: 1,
                minHeight: 0,
              }}
            >
              {/* 좌측: 경로 피커 (vault 트리) */}
              <div>
                <div
                  style={{
                    fontSize: 13,
                    fontWeight: 500,
                    marginBottom: 8,
                    color: "var(--color-ink)",
                  }}
                >
                  저장 위치
                </div>
                {treeErr ? (
                  <div
                    style={{
                      fontSize: 12,
                      color: "var(--color-muted)",
                      padding: "12px 8px",
                      border: "1px solid var(--color-hairline)",
                      borderRadius: "var(--radius-sm)",
                    }}
                  >
                    트리를 불러올 수 없습니다. 우측에서 직접 입력해 주세요.
                  </div>
                ) : tree ? (
                  <PathPicker tree={tree} currentPrefix={slug} onPick={pickFolder} />
                ) : (
                  <div style={{ fontSize: 12, color: "var(--color-muted)" }}>트리 불러오는 중…</div>
                )}
              </div>

              {/* 우측: 폼 */}
              <div>
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
                    경로 *
                  </span>
                  <input
                    className="input-base"
                    style={{ height: 48 }}
                    value={slug}
                    onChange={(e) => setSlug(e.target.value)}
                    placeholder="content/my-concept"
                  />
                  <span style={{ fontSize: 12, color: "var(--color-muted)" }}>
                    좌측에서 폴더를 클릭하거나 직접 입력하세요. 마지막 segment가 파일명입니다.
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
                    제목 *
                  </span>
                  <input
                    className="input-base"
                    style={{ height: 48 }}
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="내 컨셉"
                  />
                </label>

            <button
              type="button"
              className="btn-secondary"
              onClick={() => setShowAdvanced((v) => !v)}
              style={{ height: 34, padding: "6px 12px", fontSize: 13, marginBottom: 16 }}
            >
              {showAdvanced ? "세부 옵션 숨기기" : "세부 옵션"}
            </button>

            {showAdvanced && (
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
                    문서 분류
                  </span>
                  <select
                    className="input-base"
                    style={{ height: 48 }}
                    value={type}
                    onChange={(e) => setType(e.target.value)}
                  >
                    <option value="concept">일반 노트</option>
                    <option value="person">사람</option>
                    <option value="comparison">비교</option>
                    <option value="project">프로젝트</option>
                    <option value="tool">도구</option>
                    <option value="rule">규칙</option>
                    <option value="query">질문/검색</option>
                    <option value="journal">기록</option>
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
                    태그 (쉼표 구분)
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
            )}

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
                본문
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
              </div>{/* 우측 폼 닫기 */}
            </div>{/* grid 닫기 */}
          </div>
        </div>,
        document.body
      )}
    </>
  );
}

// ─── PathPicker — vault 트리에서 폴더 클릭 → slug prefix 주입 ────────
// v0.6.19+: 페이지 생성 모달 좌측에 표시. 빈 폴더도 포함 (ADR 05311e0).
function PathPicker({
  tree,
  currentPrefix,
  onPick,
}: {
  tree: TreeNode;
  currentPrefix: string;
  onPick: (folderPath: string) => void;
}) {
  // 현재 slug의 prefix가 어떤 폴더에 해당하는지 하이라이트용
  const activePrefix = currentPrefix.replace(/\/[^/]*$/, "").replace(/\/+$/, "");
  return (
    <div
      style={{
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-sm)",
        padding: 8,
        maxHeight: 360,
        overflowY: "auto",
        background: "var(--color-canvas)",
        fontSize: 13,
      }}
    >
      <PickerNode node={tree} depth={0} activePrefix={activePrefix} onPick={onPick} />
    </div>
  );
}

function PickerNode({
  node,
  depth,
  activePrefix,
  onPick,
}: {
  node: TreeNode;
  depth: number;
  activePrefix: string;
  onPick: (folderPath: string) => void;
}) {
  if (node.type === "page") return null;
  const isActive = activePrefix === node.path;
  const label = node.path.split("/").pop() || node.path;
  return (
    <div>
      <button
        type="button"
        onClick={() => onPick(node.path)}
        data-path={node.path}
        style={{
          display: "block",
          width: "100%",
          textAlign: "left",
          background: isActive ? "var(--color-surface-soft)" : "transparent",
          border: "none",
          padding: `6px 8px 6px ${8 + depth * 12}px`,
          borderRadius: "var(--radius-sm)",
          cursor: "pointer",
          fontSize: 13,
          color: "var(--color-ink)",
          fontFamily: "var(--font-display)",
        }}
      >
        📁 {label}
      </button>
      {(node.children ?? [])
        .filter((c) => c.type === "dir")
        .map((c) => (
          <PickerNode
            key={c.path}
            node={c}
            depth={depth + 1}
            activePrefix={activePrefix}
            onPick={onPick}
          />
        ))}
    </div>
  );
}