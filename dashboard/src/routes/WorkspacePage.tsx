import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { fetchGitStatus, fetchGitDiff, updateWorkspace, type GitChange, type GitStatusResult } from "../lib/api";

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
    if (s.includes("M")) return { background: "rgba(217, 119, 6, 0.15)", color: "#d97706" }; // Amber (Modified)
    if (s.includes("A") || s.includes("?")) return { background: "rgba(22, 163, 74, 0.15)", color: "#16a34a" }; // Green (Added/Untracked)
    if (s.includes("D")) return { background: "rgba(220, 38, 38, 0.15)", color: "#dc2626" }; // Red (Deleted)
    return { background: "rgba(107, 114, 128, 0.15)", color: "#6b7280" }; // Gray
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
                backgroundColor: "rgba(220, 38, 38, 0.1)", 
                color: "#dc2626", 
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
        <div className="card-flat" style={{ padding: 32, borderLeft: "4px solid #dc2626" }}>
          <h2>⚠ 워크스페이스 디렉토리 오류</h2>
          <p className="text-muted" style={{ margin: "12px 0 24px", fontSize: 14 }}>
            설정된 경로 <code>{status.workspace_path}</code>가 로컬 시스템에 존재하지 않거나 접근이 거부되었습니다.
          </p>
          <div style={{ display: "flex", gap: 12 }}>
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
        </div>
      </div>
    );
  }

  // 3. Linked State, but not a Git Repo
  if (!status.is_git) {
    return (
      <div style={{ maxWidth: 640, margin: "40px auto 0", padding: "0 24px" }}>
        <div className="card-flat" style={{ padding: 32, textAlign: "center" }}>
          <span style={{ fontSize: 32 }}>ℹ</span>
          <h2 style={{ marginTop: 16 }}>Git 저장소가 아님</h2>
          <p className="text-muted" style={{ margin: "12px 0 24px", fontSize: 14 }}>
            연동된 워크스페이스 폴더 <code>{status.workspace_path}</code>에서 Git 저장소를 찾을 수 없습니다. 
            해당 폴더에서 <code>git init</code>을 수행하거나 Git 저장소인 폴더로 다시 연동해주세요.
          </p>
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
        </div>
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
            <h1 style={{ margin: 0, fontSize: 24 }}>Workspace Changes</h1>
            <span style={{ color: "var(--color-muted)", fontSize: 13 }}>
              🌿 {status.branch} @ {status.commit}
            </span>
          </div>
          <p className="text-muted" style={{ fontSize: 13, marginTop: 4, marginBottom: 0 }}>
            워크스페이스: <code>{status.workspace_path}</code>
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
            style={{ fontSize: 12, padding: "6px 12px", height: 32, border: "1px solid rgba(220, 38, 38, 0.3)", color: "#dc2626" }}
          >
            연결 해제
          </button>
        </div>
      </div>

      {/* Main Workspace split view */}
      <div style={{ display: "flex", flex: 1, minHeight: 0, gap: 16 }}>
        {/* Left Side: Changes List */}
        <div 
          style={{ 
            width: 320, 
            display: "flex", 
            flexDirection: "column", 
            borderRight: "1px solid var(--color-hairline)",
            paddingRight: 16,
            overflowY: "auto"
          }}
        >
          <div style={{ fontSize: 12, fontWeight: 700, color: "var(--color-muted)", marginBottom: 12, textTransform: "uppercase" }}>
            변경 사항 ({changesList.length})
          </div>

          {changesList.length === 0 ? (
            <div style={{ padding: "40px 16px", textAlign: "center", border: "1px dashed var(--color-hairline)", borderRadius: "var(--radius-md)" }}>
              <span style={{ fontSize: 24 }}>✨</span>
              <p className="text-muted" style={{ fontSize: 13, marginTop: 8, marginBottom: 0 }}>
                변경 사항이 없습니다.<br />워크스페이스가 깨끗합니다.
              </p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {changesList.map((c) => {
                const isSelected = selectedFile === c.file;
                return (
                  <button
                    key={c.file}
                    onClick={() => setSelectedFile(c.file)}
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

        {/* Right Side: Diff Viewer */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
          {selectedFile ? (
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
          ) : (
            <div style={{ display: "flex", flex: 1, alignItems: "center", justifyContent: "center", flexDirection: "column", border: "1px dashed var(--color-hairline)", borderRadius: "var(--radius-md)", color: "var(--color-muted)" }}>
              <span style={{ fontSize: 32, marginBottom: 12 }}>🔍</span>
              <span style={{ fontSize: 13 }}>왼쪽 목록에서 변경된 파일을 클릭해 diff를 비교해보세요.</span>
            </div>
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
          style = { backgroundColor: "rgba(34, 197, 94, 0.12)", color: "#16a34a", display: "block" };
        } else if (line.startsWith("-")) {
          style = { backgroundColor: "rgba(239, 68, 68, 0.12)", color: "#dc2626", display: "block" };
        } else if (line.startsWith("@@")) {
          style = { color: "var(--color-primary, #3b82f6)", opacity: 0.8, display: "block", backgroundColor: "rgba(59, 130, 246, 0.05)" };
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
