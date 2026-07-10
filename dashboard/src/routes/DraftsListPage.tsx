import { useState, useEffect, useCallback } from "react";
import { useOutletContext, useNavigate, Link } from "react-router-dom";
import { PageHeader } from "../components/ui/PageHeader";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { EmptyIcon } from "../lib/emptyIcons";
import {
  fetchDraftsList,
  commitDraft,
  deleteDraft,
  type DraftListItem,
  type DraftConflictResult,
} from "../lib/api";

const TYPE_BADGE_COLOR: Record<string, string> = {
  concept: "#6366f1",
  person: "#0891b2",
  tool: "#059669",
  comparison: "#d97706",
  project: "#7c3aed",
  rule: "#db2777",
  query: "#2563eb",
  journal: "#64748b",
  issue: "#dc2626",
};

function TypeBadge({ type }: { type: string }) {
  const color = TYPE_BADGE_COLOR[type] || "#64748b";
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: 12,
        fontSize: 11,
        fontWeight: 600,
        background: `${color}22`,
        color,
        border: `1px solid ${color}44`,
        letterSpacing: "0.03em",
      }}
    >
      {type}
    </span>
  );
}

export function DraftsListPage() {
  const { vault, refresh } = useOutletContext<{ vault: string; refresh: () => void }>();
  const navigate = useNavigate();

  const [drafts, setDrafts] = useState<DraftListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [toastType, setToastType] = useState<"success" | "error">("success");
  const [busySlug, setBusySlug] = useState<string | null>(null);

  // Conflict dialog state
  const [conflictDraft, setConflictDraft] = useState<DraftListItem | null>(null);

  const loadDrafts = useCallback(async () => {
    setLoading(true);
    try {
      const list = await fetchDraftsList(vault);
      setDrafts(list);
    } catch {
      setDrafts([]);
    } finally {
      setLoading(false);
    }
  }, [vault]);

  useEffect(() => {
    loadDrafts();
  }, [loadDrafts]);

  // Toast auto-dismiss
  useEffect(() => {
    if (!toastMessage) return;
    const t = setTimeout(() => setToastMessage(null), 2400);
    return () => clearTimeout(t);
  }, [toastMessage]);

  const showToast = (msg: string, type: "success" | "error" = "success") => {
    setToastType(type);
    setToastMessage(msg);
  };

  const handlePublish = async (draft: DraftListItem, overwrite = false) => {
    setBusySlug(draft.slug);
    try {
      const res = await commitDraft(vault, {
        draft_slug: draft.slug,
        overwrite,
      });

      if ("conflict" in res && (res as DraftConflictResult).conflict) {
        setConflictDraft(draft);
        return;
      }

      const ok = (res as { ok: boolean; slug: string }).ok;
      if (ok) {
        showToast(`✅ '${draft.title}' 발행 완료`);
        setConflictDraft(null);
        refresh();
        await loadDrafts();
        const slug = (res as { ok: boolean; slug: string }).slug.replace(/^content\//, "");
        setTimeout(() => navigate(`/page/${vault}/${slug}`), 1000);
      } else {
        showToast("❌ 발행 실패", "error");
      }
    } catch (e: any) {
      showToast(`❌ ${e.message || "발행 오류"}`, "error");
    } finally {
      setBusySlug(null);
    }
  };

  const handleDelete = async (draft: DraftListItem) => {
    if (!window.confirm(`'${draft.title}' 초안을 삭제하시겠습니까?`)) return;
    setBusySlug(draft.slug);
    try {
      const stem = draft.slug.replace(/^drafts\//, "");
      await deleteDraft(vault, stem);
      showToast(`🗑 '${draft.title}' 삭제 완료`);
      await loadDrafts();
    } catch (e: any) {
      showToast(`❌ ${e.message || "삭제 오류"}`, "error");
    } finally {
      setBusySlug(null);
    }
  };

  const handleEdit = (draft: DraftListItem) => {
    navigate("/draft", { state: { prefillSlug: draft.slug } });
  };

  return (
    <div style={{ maxWidth: 1100 }}>
      {/* Toast */}
      {toastMessage && (
        <div
          style={{
            position: "fixed",
            bottom: 24,
            right: 24,
            background: toastType === "success" ? "var(--color-ink)" : "#ef4444",
            color: "var(--color-canvas)",
            padding: "12px 24px",
            borderRadius: 8,
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
            zIndex: 1000,
            fontSize: 14,
            fontWeight: 500,
          }}
        >
          {toastMessage}
        </div>
      )}

      <PageHeader
        title="📋 초안 목록"
        contextLabel={`in ${vault}`}
        subtitle={`vault/drafts/ 에 있는 미발행 초안 목록입니다. 편집·발행·삭제를 1-click으로 수행하세요.`}
        bottomSpacing={24}
        actions={
          <Link to="/draft">
            <Button variant="primary" size="sm">
              ✨ 새 초안 작성
            </Button>
          </Link>
        }
      />

      {loading ? (
        <p style={{ color: "var(--color-muted)", fontSize: 14 }}>초안 목록 불러오는 중…</p>
      ) : drafts.length === 0 ? (
        <EmptyState
          icon={<EmptyIcon.File />}
          title="초안이 없습니다"
          description="아직 저장된 초안이 없습니다. AI 초안 작성기에서 새 초안을 만들어보세요."
        />
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
            gap: 20,
          }}
        >
          {drafts.map((draft) => {
            const isBusy = busySlug === draft.slug;
            return (
              <div
                key={draft.slug}
                style={{
                  background: "var(--color-surface)",
                  border: draft.conflict
                    ? "1px solid rgba(239, 68, 68, 0.5)"
                    : "1px solid var(--color-hairline)",
                  borderRadius: 10,
                  padding: "18px 20px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                  transition: "box-shadow 0.2s ease, transform 0.2s ease",
                  position: "relative",
                  overflow: "hidden",
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.boxShadow =
                    "0 6px 24px rgba(0,0,0,0.10)";
                  (e.currentTarget as HTMLElement).style.transform = "translateY(-2px)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.boxShadow = "none";
                  (e.currentTarget as HTMLElement).style.transform = "none";
                }}
              >
                {/* Conflict badge */}
                {draft.conflict && (
                  <div
                    style={{
                      position: "absolute",
                      top: 0,
                      right: 0,
                      background: "rgba(239, 68, 68, 0.85)",
                      color: "#fff",
                      fontSize: 10,
                      fontWeight: 700,
                      padding: "3px 10px",
                      borderBottomLeftRadius: 8,
                      letterSpacing: "0.05em",
                    }}
                  >
                    ⚠ 충돌
                  </div>
                )}

                {/* Header */}
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                    <TypeBadge type={draft.type} />
                    {draft.updated && (
                      <span style={{ fontSize: 11, color: "var(--color-muted)" }}>
                        {draft.updated}
                      </span>
                    )}
                  </div>
                  <h3
                    style={{
                      margin: 0,
                      fontSize: 15,
                      fontWeight: 600,
                      color: "var(--color-ink)",
                      lineHeight: 1.35,
                      wordBreak: "break-word",
                    }}
                  >
                    {draft.title}
                  </h3>
                  <span
                    style={{
                      display: "block",
                      fontSize: 11,
                      color: "var(--color-muted)",
                      marginTop: 4,
                      fontFamily: "var(--font-mono, monospace)",
                    }}
                  >
                    {draft.filename}
                  </span>
                </div>

                {/* Conflict warning */}
                {draft.conflict && (
                  <div
                    style={{
                      background: "rgba(239, 68, 68, 0.08)",
                      border: "1px solid rgba(239, 68, 68, 0.2)",
                      borderRadius: 6,
                      padding: "8px 10px",
                      fontSize: 12,
                      color: "#ef4444",
                      lineHeight: 1.4,
                    }}
                  >
                    content/{draft.filename}이 이미 존재합니다. 발행 시 덮어쓰기 여부를 선택하세요.
                  </div>
                )}

                {/* Actions */}
                <div style={{ display: "flex", gap: 8, marginTop: "auto" }}>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleEdit(draft)}
                    disabled={isBusy}
                    style={{ flex: 1 }}
                  >
                    ✏️ 편집
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() =>
                      draft.conflict ? setConflictDraft(draft) : handlePublish(draft)
                    }
                    disabled={isBusy}
                    style={{ flex: 1 }}
                  >
                    {isBusy ? "처리 중…" : "🚀 발행"}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(draft)}
                    disabled={isBusy}
                    style={{
                      color: "#ef4444",
                      border: "1px solid rgba(239,68,68,0.3)",
                      background: "rgba(239,68,68,0.05)",
                    }}
                  >
                    🗑
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Conflict resolution dialog */}
      {conflictDraft && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.5)",
            zIndex: 999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          onClick={() => setConflictDraft(null)}
        >
          <div
            style={{
              background: "var(--color-surface)",
              borderRadius: 12,
              padding: 28,
              maxWidth: 480,
              width: "90%",
              boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
              display: "flex",
              flexDirection: "column",
              gap: 16,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div>
              <h3 style={{ margin: "0 0 6px 0", fontSize: 17, fontWeight: 700 }}>
                ⚠️ 덮어쓰기 충돌 감지
              </h3>
              <p style={{ margin: 0, fontSize: 13, color: "var(--color-muted)" }}>
                <strong>{conflictDraft.filename}</strong>이 이미 content/ 에 존재합니다.
                어떻게 처리하시겠습니까?
              </p>
            </div>
            <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setConflictDraft(null)}
              >
                취소
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  handlePublish(conflictDraft, true);
                }}
                disabled={busySlug === conflictDraft.slug}
              >
                {busySlug === conflictDraft.slug ? "발행 중…" : "⚡ 덮어쓰기 발행"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
