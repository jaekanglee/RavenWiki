import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import {
  fetchGitStatus,
  fetchGitDiff,
  updateWorkspace,
  fetchWorkspaceTree,
  fetchWorkspaceFile,
  type GitChange,
  type GitStatusResult,
  type WorkspaceTreeNode,
} from "../lib/api";
import { EmptyState } from "../components/ui/EmptyState";

// v0.7.62+ 모바일 breakpoint (744px). 744 이하면 세로 stack 레이아웃으로 전환.
const MOBILE_BREAKPOINT = 744;

// v0.7.64+ 좌측 패널 모드. 워크스페이스 트리 / Git 변경사항 리스트 분리.
type LeftTab = "workspace" | "changes";

export function WorkspacePage() {
  const { vault } = useOutletContext<{ vault: string }>();
  const [status, setStatus] = useState<GitStatusResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [diffText, setDiffText] = useState<string>("");
  const [diffLoading, setDiffLoading] = useState(false);
  
  // Setup inputs
  const [workspaceInput, setWorkspaceInput] = useState("");
  const [setupError, setSetupError] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  // Resize State & Logic
  const [leftWidth, setLeftWidth] = useState(320);
  const [isResizing, setIsResizing] = useState(false);

  // v0.7.62+ 모바일 여부. window.innerWidth 기반, resize 시 재계산.
  const [isMobile, setIsMobile] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return window.innerWidth < MOBILE_BREAKPOINT;
  });
  useEffect(() => {
    if (typeof window === "undefined") return;
    const onResize = () => setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  // v0.7.61+ Workspace OS tree (read-only) — workspace 디렉토리 트리 + .md 인라인 미리보기.
  const [treeNodes, setTreeNodes] = useState<WorkspaceTreeNode[]>([]);
  const [treePath, setTreePath] = useState<string>("");        // 현재 보고 있는 서브 경로
  const [treeLoading, setTreeLoading] = useState(false);
  const [showHidden, setShowHidden] = useState(false);
  const [previewContent, setPreviewContent] = useState<{ path: string; content: string; truncated: boolean; size: number; is_binary: boolean } | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string>("");

  // v0.7.64+ 좌측 패널 active 탭. 워크스페이스 트리 / 변경사항 리스트 분리.
  // v0.7.63에서 우측 탭으로 잘못 구현된 것 정정 — 두 트리 자체가 같은 패널에
  // stacked 되어 있어 "어느 트리 결과인지" 헷갈리는 UX였음. 좌측 자체를 탭으로.
  const [activeLeftTab, setActiveLeftTab] = useState<LeftTab>("workspace");

  const startResize = (clientX: number) => {
    setIsResizing(true);
    const startWidth = leftWidth;
    const startX = clientX;

    const doResize = (moveX: number) => {
      const deltaX = moveX - startX;
      const newWidth = Math.max(200, Math.min(800, startWidth + deltaX));
      setLeftWidth(newWidth);
    };

    const handleMouseMove = (e: MouseEvent) => {
      doResize(e.clientX);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (e.touches.length > 0) {
        doResize(e.touches[0].clientX);
      }
    };

    const handleTouchEnd = () => {
      setIsResizing(false);
      document.removeEventListener("touchmove", handleTouchMove);
      document.removeEventListener("touchend", handleTouchEnd);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    document.addEventListener("touchmove", handleTouchMove, { passive: true });
    document.addEventListener("touchend", handleTouchEnd);
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    startResize(e.clientX);
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length > 0) {
      startResize(e.touches[0].clientX);
    }
  };

  const loadStatus = async () => {
    setLoading(true);
    try {
      const res = await fetchGitStatus(vault);
      setStatus(res);
      if (res?.has_workspace && res.workspace_path) {
        setWorkspaceInput(res.workspace_path);
      }
    } catch {
      setStatus(null);
    } finally {
      setLoading(false);
    }
  };

  // v0.7.61+ workspace tree 로더. 워크스페이스 부재/미연동 시 silent.
  const loadTree = async (subPath: string, hidden: boolean) => {
    setTreeLoading(true);
    try {
      const res = await fetchWorkspaceTree(vault, { path: subPath, hidden });
      setTreeNodes(res?.nodes ?? []);
      setTreePath(subPath);
    } catch {
      setTreeNodes([]);
    } finally {
      setTreeLoading(false);
    }
  };

  // 트리 hidden 토글 변경 시 즉시 refetch.
  useEffect(() => {
    if (status?.has_workspace && status.is_git) {
      loadTree("", showHidden);
    }
  }, [showHidden, status?.has_workspace, status?.is_git, vault]);

  // 디렉토리 클릭 → 해당 경로로 트리 refetch (1단계 lazy load).
  const handleTreeDirClick = (node: WorkspaceTreeNode) => {
    loadTree(node.path, showHidden);
    setPreviewContent(null);
    setPreviewError("");
    setActiveLeftTab("workspace");
  };

  // v0.7.61+: 모든 텍스트 파일 미리보기. binary만 거부 (백엔드 is_binary 감지).
  const handleTreeFileClick = async (node: WorkspaceTreeNode) => {
    setPreviewLoading(true);
    setPreviewError("");
    setPreviewContent(null);
    setActiveLeftTab("workspace");
    try {
      const res = await fetchWorkspaceFile(vault, node.path);
      if (res) {
        setPreviewContent({
          path: res.path,
          content: res.content,
          truncated: res.truncated,
          size: res.size,
          is_binary: res.is_binary,
        });
      } else {
        setPreviewError("파일 읽기 실패");
      }
    } catch {
      setPreviewError("파일 읽기 실패");
    } finally {
      setPreviewLoading(false);
    }
  };

  // 트리 한 단계 위로 (상위 경로).
  const handleTreeUp = () => {
    if (!treePath) return;
    const parent = treePath.includes("/")
      ? treePath.split("/").slice(0, -1).join("/")
      : "";
    loadTree(parent, showHidden);
    setPreviewContent(null);
    setPreviewError("");
    setActiveLeftTab("workspace");
  };

  useEffect(() => {
    loadStatus();
    setSelectedFile(null);
    setDiffText("");
  }, [vault]);

  const loadDiff = async (file: string | null) => {
    if (!file) {
      setDiffText("");
      return;
    }
    setDiffLoading(true);
    try {
      const res = await fetchGitDiff(vault, file);
      setDiffText(res?.diff || "");
    } catch (e: any) {
      setDiffText(`diff를 가져오는 데 실패했습니다: ${e.message}`);
    } finally {
      setDiffLoading(false);
    }
  };

  useEffect(() => {
    if (selectedFile) {
      loadDiff(selectedFile);
    }
  }, [selectedFile]);

  const handleLink = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceInput.trim()) return;
    setSetupError("");
    setActionLoading(true);
    try {
      await updateWorkspace(vault, { workspace_path: workspaceInput });
      await loadStatus();
    } catch (err: any) {
      setSetupError(err.message || "워크스페이스 연결에 실패했습니다.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleUnlink = async () => {
    if (!window.confirm("워크스페이스 연결을 해제하시겠습니까?")) return;
    setActionLoading(true);
    try {
      await updateWorkspace(vault, { workspace_path: "", unlink: true });
      setSelectedFile(null);
      setDiffText("");
      await loadStatus();
    } catch (err: any) {
      alert(err.message || "연결 해제 실패");
    } finally {
      setActionLoading(false);
    }
  };

  // Status badges color & label helper
  const getBadgeStyle = (statusStr: string): React.CSSProperties => {
    const s = statusStr.trim();
    if (s.includes("M")) return { background: "var(--color-warning-bg)", color: "var(--color-warning-text)" }; // Amber (Modified)
    if (s.includes("A") || s.includes("?")) return { background: "var(--color-success-bg)", color: "var(--color-success-text)" }; // Green (Added/Untracked)
    if (s.includes("D")) return { background: "var(--color-danger-bg)", color: "var(--color-danger)" }; // Red (Deleted)
    return { background: "var(--color-surface-strong)", color: "var(--color-muted)" }; // Gray
  };

  if (loading) {
    return (
      <div style={{ padding: 24 }}>
        <p className="text-muted">워크스페이스 상태 확인 중...</p>
      </div>
    );
  }

  // 1. Unlinked State: Show onboarding
  if (!status || !status.has_workspace) {
    return (
      <div style={{ maxWidth: 640, margin: "40px auto 0", padding: "0 24px" }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <span style={{ fontSize: 48 }}>💻</span>
          <h1 style={{ marginTop: 16, marginBottom: 8 }}>워크스페이스 연결</h1>
          <p className="text-muted" style={{ fontSize: 15 }}>
            이 보관소와 연동하여 코드 소스 변경 사항을 추적할 폴더를 지정합니다.
          </p>
        </div>

        <form onSubmit={handleLink} className="card-flat" style={{ padding: 32 }}>
          <div style={{ marginBottom: 24 }}>
            <label 
              style={{ 
                display: "block", 
                fontSize: 13, 
                fontWeight: 600, 
                color: "var(--color-ink)", 
                marginBottom: 8 
              }}
            >
              워크스페이스 CWD 절대 경로
            </label>
            <input 
              type="text"
              placeholder="예: /Users/username/Projects/my-app"
              value={workspaceInput}
              onChange={(e) => setWorkspaceInput(e.target.value)}
              disabled={actionLoading}
              required
              style={{
                width: "100%",
                padding: "10px 14px",
                fontSize: 14,
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--color-hairline-strong)",
                background: "var(--color-canvas)",
                color: "var(--color-ink)",
                outline: "none",
                transition: "border-color 0.15s ease",
              }}
            />
            <p className="text-muted" style={{ fontSize: 12, marginTop: 8, lineHeight: 1.4 }}>
              개발 중인 소스코드 Git 프로젝트 폴더의 경로를 작성해주세요. 연결 시 Raven 대시보드에서 Git 변경 이력을 볼 수 있습니다.
            </p>
          </div>

          {setupError && (
            <div
              style={{
                padding: "12px 16px",
                backgroundColor: "var(--danger-bg-soft)",
                color: "var(--danger-fg)",
                borderRadius: "var(--radius-sm)",
                fontSize: 13,
                marginBottom: 20
              }}
            >
              ⚠ {setupError}
            </div>
          )}

          <button 
            type="submit" 
            className="btn-primary" 
            disabled={actionLoading}
            style={{ width: "100%", height: 42, fontSize: 14, fontWeight: 600 }}
          >
            {actionLoading ? "연결 중..." : "워크스페이스 연결하기"}
          </button>
        </form>
      </div>
    );
  }

  // 2. Linked State, but Workspace Folder does not exist on disk (Error)
  if (status.error) {
    return (
      <div style={{ maxWidth: 640, margin: "40px auto 0", padding: "0 24px" }}>
        <EmptyState
          icon="⚠"
          title="워크스페이스 디렉토리 오류"
          description={`설정된 경로 ${status.workspace_path}가 로컬 시스템에 존재하지 않거나 접근이 거부되었습니다.`}
          action={
            <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
              <button 
                onClick={() => { setWorkspaceInput(""); setStatus(null); }}
                className="btn-primary"
                style={{ fontSize: 13, padding: "8px 16px" }}
              >
                다른 폴더 연결
              </button>
              <button 
                onClick={handleUnlink}
                className="btn-secondary"
                style={{ fontSize: 13, padding: "8px 16px" }}
              >
                연결 해제
              </button>
            </div>
          }
        />
      </div>
    );
  }

  // 3. Linked State, but not a Git Repo
  if (!status.is_git) {
    return (
      <div style={{ maxWidth: 640, margin: "40px auto 0", padding: "0 24px" }}>
        <EmptyState
          icon="ℹ"
          title="Git 저장소가 아님"
          description={`연동된 워크스페이스 폴더 ${status.workspace_path}에서 Git 저장소를 찾을 수 없습니다. 해당 폴더에서 git init을 수행하거나 Git 저장소인 폴더로 다시 연동해주세요.`}
          action={
            <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
              <button 
                onClick={() => { setWorkspaceInput(""); setStatus(null); }}
                className="btn-primary"
                style={{ fontSize: 13, padding: "8px 16px" }}
              >
                다른 폴더 연결
              </button>
              <button 
                onClick={handleUnlink}
                className="btn-secondary"
                style={{ fontSize: 13, padding: "8px 16px" }}
              >
                연결 해제
              </button>
            </div>
          }
        />
      </div>
    );
  }

  // 4. Fully Connected Workspace & Git Repo
  const changesList = status.changes || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header Info */}
      <div 
        style={{ 
          paddingBottom: 16, 
          borderBottom: "1px solid var(--color-hairline)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 12,
          marginBottom: 16
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
            <h1 style={{ margin: 0, fontSize: 24 }}>
              워크스페이스 변경사항 <span style={{ color: "var(--color-muted)", fontSize: 14, fontWeight: "normal" }}>in {vault}</span>
            </h1>
            <span style={{ color: "var(--color-muted)", fontSize: 13 }}>
              🌿 {status.branch} @ {status.commit}
            </span>
          </div>
          <p className="text-muted" style={{ fontSize: 13, marginTop: 4, marginBottom: 0 }}>
            워크스페이스 경로: <code>{status.workspace_path}</code>
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button 
            onClick={loadStatus}
            className="btn-secondary"
            style={{ fontSize: 12, padding: "6px 12px", height: 32 }}
          >
            🔄 새로고침
          </button>
          <button
            onClick={handleUnlink}
            className="btn-secondary"
            style={{ fontSize: 12, padding: "6px 12px", height: 32, border: "1px solid var(--danger-border)", color: "var(--color-danger)" }}
          >
            연결 해제
          </button>
        </div>
      </div>

      {/* Main Workspace split view */}
      <div
        style={{
          display: "flex",
          flex: 1,
          minHeight: 0,
          gap: 0,
          position: "relative",
          userSelect: isResizing ? "none" : "auto",
          // v0.7.62+: 모바일은 세로 stack (트리 / 변경사항 / 미리보기).
          flexDirection: isMobile ? "column" : "row",
        }}
      >
        {/* Left Side: Workspace Tree or Changes List (tabs, v0.7.64+) */}
        <div
          style={{
            width: isMobile ? "100%" : leftWidth,
            display: "flex",
            flexDirection: "column",
            borderRight: isMobile ? "none" : "1px solid var(--color-hairline)",
            borderBottom: isMobile ? "1px solid var(--color-hairline)" : "none",
            paddingRight: isMobile ? 0 : 16,
            paddingBottom: isMobile ? 12 : 0,
            overflowY: "auto",
            flexShrink: 0,
            gap: 12,
            // v0.7.62+: 모바일에서는 트리 / 변경사항 탭 영역이 화면 폭 full, max-height로 분할.
            maxHeight: isMobile ? "50vh" : "none",
          }}
        >
          {/* v0.7.64+ 좌측 패널 탭 헤더 */}
          <div
            role="tablist"
            style={{
              display: "flex",
              borderBottom: "1px solid var(--color-hairline)",
              marginBottom: 4,
            }}
          >
            <button
              type="button"
              role="tab"
              aria-selected={activeLeftTab === "workspace"}
              onClick={() => setActiveLeftTab("workspace")}
              style={{
                background: "transparent",
                border: "none",
                borderBottom: activeLeftTab === "workspace"
                  ? "2px solid var(--color-primary)"
                  : "2px solid transparent",
                padding: "8px 12px",
                cursor: "pointer",
                fontSize: 12,
                fontWeight: activeLeftTab === "workspace" ? 600 : 500,
                color: activeLeftTab === "workspace" ? "var(--color-ink)" : "var(--color-muted)",
                marginBottom: -1,
                transition: "color 0.15s ease, border-color 0.15s ease",
              }}
            >
              🌳 워크스페이스
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeLeftTab === "changes"}
              onClick={() => setActiveLeftTab("changes")}
              style={{
                background: "transparent",
                border: "none",
                borderBottom: activeLeftTab === "changes"
                  ? "2px solid var(--color-primary)"
                  : "2px solid transparent",
                padding: "8px 12px",
                cursor: "pointer",
                fontSize: 12,
                fontWeight: activeLeftTab === "changes" ? 600 : 500,
                color: activeLeftTab === "changes" ? "var(--color-ink)" : "var(--color-muted)",
                marginBottom: -1,
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                transition: "color 0.15s ease, border-color 0.15s ease",
              }}
            >
              📋 변경사항
              {changesList.length > 0 && (
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 600,
                    padding: "1px 5px",
                    borderRadius: 8,
                    backgroundColor: activeLeftTab === "changes" ? "var(--color-primary)" : "var(--color-surface-soft)",
                    color: activeLeftTab === "changes" ? "var(--color-on-primary)" : "var(--color-muted)",
                  }}
                >
                  {changesList.length}
                </span>
              )}
            </button>
          </div>

          {activeLeftTab === "workspace" ? (
            /* v0.7.61+ Workspace OS tree (read-only) */
            <div style={{ display: "flex", flexDirection: "column", minHeight: 0, flex: 1 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-muted)", textTransform: "uppercase" }}>
                  파일 목록 {treeLoading && "…"}
                </div>
                <label
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                    fontSize: 11,
                    color: "var(--color-muted)",
                    cursor: "pointer",
                    userSelect: "none",
                  }}
                  title="숨김 파일/폴더 (.git, .venv 등) 표시"
                >
                  <input
                    type="checkbox"
                    checked={showHidden}
                    onChange={(e) => setShowHidden(e.target.checked)}
                    style={{ margin: 0, cursor: "pointer" }}
                  />
                  숨김
                </label>
              </div>

              {/* breadcrumb + up */}
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8, fontSize: 12 }}>
                {treePath && (
                  <button
                    type="button"
                    onClick={handleTreeUp}
                    style={{
                      background: "transparent",
                      border: "1px solid var(--color-hairline)",
                      borderRadius: "var(--radius-sm)",
                      cursor: "pointer",
                      padding: "2px 8px",
                      fontSize: 11,
                      color: "var(--color-body)",
                    }}
                    title="상위 디렉토리"
                  >
                    ⬆
                  </button>
                )}
                <code style={{ fontSize: 11, color: "var(--color-muted)", wordBreak: "break-all" }}>
                  /{treePath || status.workspace_path?.split("/").slice(-1)[0]}
                </code>
              </div>

              {treeNodes.length === 0 && !treeLoading ? (
                <div style={{ fontSize: 12, color: "var(--color-muted)", padding: "8px 0" }}>
                  비어 있음
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 2, flex: 1, overflowY: "auto" }}>
                  {treeNodes.map((node) => (
                    <button
                      key={node.path}
                      type="button"
                      onClick={() =>
                        node.type === "dir" ? handleTreeDirClick(node) : handleTreeFileClick(node)
                      }
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                        width: "100%",
                        padding: "4px 8px",
                        border: "none",
                        borderRadius: "var(--radius-sm)",
                        backgroundColor: "transparent",
                        color: "var(--color-body)",
                        cursor: "pointer",
                        textAlign: "left",
                        fontSize: 12,
                        fontFamily: "ui-monospace, SFMono-Regular, monospace",
                        wordBreak: "break-all",
                        opacity: node.is_hidden ? 0.55 : 1,
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = "var(--hover-overlay)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = "transparent";
                      }}
                      title={`${node.path} (${node.type === "dir" ? "dir" : `${node.size}B`})`}
                    >
                      <span style={{ flexShrink: 0, fontSize: 11 }}>
                        {node.type === "dir" ? "📁" : "📄"}
                      </span>
                      <span style={{ flex: 1 }}>{node.name}</span>
                      {node.type === "file" && node.size != null && (
                        <span style={{ fontSize: 10, color: "var(--color-muted)", flexShrink: 0 }}>
                          {formatSize(node.size)}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            /* 기존 Git 변경사항 목록 */
            <div style={{ display: "flex", flexDirection: "column", minHeight: 0, flex: 1 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-muted)", marginBottom: 12, textTransform: "uppercase" }}>
                변경 파일 목록 ({changesList.length})
              </div>

              {changesList.length === 0 ? (
                <EmptyState
                  icon="✨"
                  title="변경 사항 없음"
                  description="워크스페이스가 깨끗합니다."
                />
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1, overflowY: "auto" }}>
                  {changesList.map((c) => {
                    const isSelected = selectedFile === c.file;
                    return (
                      <button
                        key={c.file}
                        onClick={() => {
                          setSelectedFile(c.file);
                          setActiveLeftTab("changes");
                        }}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          width: "100%",
                          padding: "8px 12px",
                          border: "none",
                          borderRadius: "var(--radius-sm)",
                          backgroundColor: isSelected ? "var(--color-surface-soft)" : "transparent",
                          color: isSelected ? "var(--color-ink)" : "var(--color-body)",
                          cursor: "pointer",
                          textAlign: "left",
                          fontSize: 13,
                          fontFamily: "ui-monospace, SFMono-Regular, monospace",
                          wordBreak: "break-all",
                          transition: "background-color 0.15s ease",
                        }}
                      >
                        <span
                          style={{
                            fontSize: 10,
                            fontWeight: "bold",
                            width: 20,
                            height: 20,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            borderRadius: 3,
                            flexShrink: 0,
                            ...getBadgeStyle(c.status)
                          }}
                        >
                          {c.status.trim()}
                        </span>
                        <span style={{ flex: 1, textDecoration: c.status.includes("D") ? "line-through" : "none" }}>
                          {c.file}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Resizer Divider Bar — v0.7.62+ 모바일에서는 숨김 (column stack + 폭 고정 불필요) */}
        {!isMobile && (
          <div
            onMouseDown={handleMouseDown}
            onTouchStart={handleTouchStart}
            style={{
              width: 12,
              cursor: "col-resize",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              position: "relative",
            zIndex: 10,
            marginLeft: -6,
            marginRight: 4,
            transition: "background-color 0.2s ease",
            backgroundColor: isResizing ? "var(--focus-overlay)" : "transparent",
          }}
          onMouseEnter={(e) => {
            if (!isResizing) e.currentTarget.style.backgroundColor = "var(--hover-overlay)";
          }}
          onMouseLeave={(e) => {
            if (!isResizing) e.currentTarget.style.backgroundColor = "transparent";
          }}
        >
          <div
            style={{
              width: 2,
              height: "40px",
              borderRadius: 1,
              backgroundColor: isResizing ? "var(--color-primary)" : "var(--color-hairline-strong)",
              transition: "background-color 0.2s ease"
            }}
          />
        </div>
        )}

        {/* Right Side: Diff Viewer or File Preview (v0.7.64+) */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, paddingLeft: isMobile ? 0 : 12, paddingTop: isMobile ? 12 : 0 }}>
          {activeLeftTab === "workspace" ? (
            /* 워크스페이스 탭 — 트리에서 선택한 파일 미리보기. */
            previewLoading ? (
              <div style={{ padding: 24, color: "var(--color-muted)" }}>파일 읽는 중…</div>
            ) : previewError ? (
              <div style={{ padding: 24, color: "var(--color-muted)" }}>{previewError}</div>
            ) : previewContent ? (
              <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
                <div style={{ marginBottom: 12, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 14, fontWeight: 600, fontFamily: "ui-monospace, SFMono-Regular, monospace", color: "var(--color-ink)", wordBreak: "break-all" }}>
                    📝 {previewContent.path}
                  </span>
                  <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 11, color: "var(--color-muted)", flexShrink: 0 }}>
                    <span>{formatSize(previewContent.size)}</span>
                    {previewContent.truncated && (
                      <span style={{ color: "var(--color-warning-text, var(--warning-fg))" }}>⚠ truncated</span>
                    )}
                    <button
                      type="button"
                      onClick={() => { setPreviewContent(null); setPreviewError(""); }}
                      style={{
                        background: "transparent",
                        border: "1px solid var(--color-hairline)",
                        borderRadius: "var(--radius-sm)",
                        padding: "2px 8px",
                        cursor: "pointer",
                        fontSize: 11,
                        color: "var(--color-body)",
                      }}
                    >
                      ✕ 닫기
                    </button>
                  </div>
                </div>
                <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
                  {previewContent.is_binary ? (
                    <div
                      style={{
                        padding: 24,
                        background: "var(--bg-surface)",
                        border: "1px solid var(--color-hairline)",
                        borderRadius: "var(--radius-sm)",
                        color: "var(--color-muted)",
                        fontSize: 13,
                      }}
                    >
                      <div style={{ fontWeight: 600, color: "var(--color-body)", marginBottom: 8 }}>
                        🔒 binary 파일 — 미리보기 미지원
                      </div>
                      <div>
                        {previewContent.path} · {formatSize(previewContent.size)} · 외부 도구로 열어보세요.
                      </div>
                    </div>
                  ) : (
                    <pre
                      style={{
                        margin: 0,
                        padding: 16,
                        background: "var(--code-block-bg)",
                        color: "var(--code-block-fg)",
                        borderRadius: "var(--radius-sm)",
                        fontSize: 13,
                        fontFamily: "ui-monospace, SFMono-Regular, monospace",
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                      }}
                    >
                      {previewContent.content}
                    </pre>
                  )}
                </div>
              </div>
            ) : (
              <EmptyState
                icon="🌳"
                title="워크스페이스 트리에서 파일 선택"
                description="왼쪽 트리에서 파일을 클릭하면 여기에 미리보기가 표시됩니다."
              />
            )
          ) : /* changes 탭 — Git 변경파일 diff. */
            selectedFile ? (
              <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
                <div style={{ marginBottom: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 14, fontWeight: 600, fontFamily: "ui-monospace, SFMono-Regular, monospace", color: "var(--color-ink)", wordBreak: "break-all" }}>
                    📄 {selectedFile}
                  </span>
                </div>
                <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>
                  {diffLoading ? (
                    <div style={{ padding: 24, color: "var(--color-muted)" }}>diff 생성 중...</div>
                  ) : (
                    <DiffViewer diff={diffText} />
                  )}
                </div>
              </div>
            ) : changesList.length > 0 ? (
              <EmptyState
                icon="📋"
                title="비교할 파일 선택"
                description="왼쪽 변경사항 목록에서 파일을 골라 diff를 확인하세요."
              />
            ) : (
              <EmptyState
                icon="✨"
                title="변경사항 없음"
                description="Git 워크스페이스가 깨끗합니다."
              />
            )}
        </div>
      </div>
    </div>
  );
}

function DiffViewer({ diff }: { diff: string }) {
  if (!diff) return <div style={{ padding: 16, color: "var(--color-muted)", fontStyle: "italic", fontSize: 13 }}>변경 사항 데이터가 없습니다 (바이너리 파일이거나 빈 파일일 수 있습니다).</div>;

  const lines = diff.split("\n");
  return (
    <pre
      style={{
        margin: 0,
        padding: 16,
        fontFamily: "ui-monospace, SFMono-Regular, monospace",
        fontSize: 13,
        lineHeight: 1.5,
        overflowX: "auto",
        whiteSpace: "pre",
        background: "var(--color-surface-soft)",
        color: "var(--color-body)",
        borderRadius: "var(--radius-md)",
        border: "1px solid var(--color-hairline)"
      }}
    >
      {lines.map((line, idx) => {
        let style: React.CSSProperties = {};
        if (line.startsWith("+")) {
          style = { backgroundColor: "var(--success-bg-strong)", color: "var(--color-success-text)", display: "block" };
        } else if (line.startsWith("-")) {
          style = { backgroundColor: "var(--danger-bg-strong)", color: "var(--color-danger)", display: "block" };
        } else if (line.startsWith("@@")) {
          style = { color: "var(--color-primary)", opacity: 0.8, display: "block", backgroundColor: "var(--accent-softest)" };
        } else if (line.startsWith("diff ") || line.startsWith("index ") || line.startsWith("--- ") || line.startsWith("+++ ")) {
          style = { fontWeight: "bold", color: "var(--color-muted)", display: "block" };
        }
        return (
          <span key={idx} style={style}>
            {line}
          </span>
        );
      })}
    </pre>
  );
}

// v0.7.61+: 파일 크기 표시 헬퍼 (Bytes → KB / MB).
function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}
