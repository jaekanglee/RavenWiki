import { useState, useEffect } from "react";
import { useOutletContext, useNavigate } from "react-router-dom";
import { PageHeader } from "../components/ui/PageHeader";
import { TextField } from "../components/ui/TextField";
import { SelectField } from "../components/ui/SelectField";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { Modal } from "../components/ui/Modal";
import { EmptyIcon } from "../lib/emptyIcons";
import { generateDraft, commitDraft, fetchPages, DraftConflictResult } from "../lib/api";

const DRAFT_TYPE_OPTIONS = [
  { value: "concept",    label: "concept — 개념 정의" },
  { value: "person",     label: "person — 인물/팀" },
  { value: "tool",       label: "tool — 도구/라이브러리" },
  { value: "comparison", label: "comparison — 비교분석" },
  { value: "project",    label: "project — 프로젝트" },
  { value: "rule",       label: "rule — 정책/규칙" },
  { value: "query",      label: "query — 조회/리포트" },
  { value: "journal",    label: "journal — 일지/메모" },
  { value: "issue",      label: "issue — 이슈 추적" },
];

export function DraftPage() {
  const { vault, refresh } = useOutletContext<{ vault: string; refresh: () => void }>();
  const navigate = useNavigate();

  // Inputs
  const [topic, setTopic] = useState("");
  const [outline, setOutline] = useState("");
  const [draftType, setDraftType] = useState("concept");
  const [pages, setPages] = useState<any[]>([]);
  const [selectedPages, setSelectedPages] = useState<string[]>([]);
  const [searchPageQuery, setSearchPageQuery] = useState("");

  // Loading / Status states
  const [generating, setGenerating] = useState(false);
  const [committing, setCommitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Result state
  const [draftResult, setDraftResult] = useState<{
    title: string;
    slug: string;
    path: string;
    content: string;
  } | null>(null);

  // Edited content in preview
  const [editedContent, setEditedContent] = useState("");

  // Conflict dialog state
  const [conflictData, setConflictData] = useState<DraftConflictResult | null>(null);
  const [conflictView, setConflictView] = useState<"existing" | "draft">("draft");

  // Load pages list for selection
  useEffect(() => {
    fetchPages(vault)
      .then((ps) => setPages(ps))
      .catch(() => setPages([]));
  }, [vault]);

  // Toast auto-dismiss after 2400ms (규칙 준수)
  useEffect(() => {
    if (toastMessage) {
      const timer = setTimeout(() => {
        setToastMessage(null);
      }, 2400);
      return () => clearTimeout(timer);
    }
  }, [toastMessage]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    setGenerating(true);
    setError(null);
    setDraftResult(null);

    try {
      const res = await generateDraft(vault, {
        topic,
        outline,
        associated_pages: selectedPages,
        draft_type: draftType,
      });
      if (res.ok) {
        setDraftResult({
          title: res.title,
          slug: res.slug,
          path: res.path,
          content: res.content,
        });
        setEditedContent(res.content);
        setToastMessage(`🤖 임시 초안이 생성되었습니다. (타입: ${draftType})`);
      } else {
        setError("초안 생성에 실패했습니다.");
      }
    } catch (err: any) {
      setError(err.message || "초안 생성 오류");
    } finally {
      setGenerating(false);
    }
  };

  const handleCommit = async (overwrite: boolean = false) => {
    if (!draftResult) return;
    setCommitting(true);
    setError(null);

    try {
      const res = await commitDraft(vault, {
        draft_slug: draftResult.slug,
        content: editedContent,
        overwrite,
      });

      // 충돌 감지 (HTTP 409)
      if ("conflict" in res && res.conflict) {
        setConflictData(res as DraftConflictResult);
        setCommitting(false);
        return;
      }

      const successRes = res as { ok: boolean; slug: string; path: string; db_rebuild: any };
      if (successRes.ok) {
        setToastMessage("✅ 보관소로 발행 완료");
        setConflictData(null);
        refresh();

        const targetSlug = successRes.slug.replace(/^content\//, "");
        setTimeout(() => {
          navigate(`/page/${vault}/${targetSlug}`);
        }, 1200);
      } else {
        setError("보관소 발행에 실패했습니다.");
      }
    } catch (err: any) {
      setError(err.message || "보관소 발행 오류");
    } finally {
      setCommitting(false);
    }
  };

  const togglePageSelection = (slug: string) => {
    setSelectedPages((prev) =>
      prev.includes(slug) ? prev.filter((s) => s !== slug) : [...prev, slug]
    );
  };

  const filteredPages = pages.filter((p) => {
    const q = searchPageQuery.toLowerCase();
    const title = (p.title || "").toLowerCase();
    const slug = (p.slug || "").toLowerCase();
    return title.includes(q) || slug.includes(q);
  });

  return (
    <div style={{ maxWidth: 1200 }}>
      {toastMessage && (
        <div
          style={{
            position: "fixed",
            bottom: 24,
            right: 24,
            background: "var(--color-ink)",
            color: "var(--color-canvas)",
            padding: "12px 24px",
            borderRadius: 8,
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
            zIndex: 1000,
            fontSize: 14,
            fontWeight: 500,
            animation: "fadeIn 0.2s ease-out",
          }}
        >
          {toastMessage}
        </div>
      )}

      <PageHeader
        title="🤖 AI 초안 작성기"
        contextLabel={`in ${vault}`}
        subtitle="주제와 아웃라인을 입력하면 AI가 위키링크가 삽입된 정제된 초안을 작성합니다. 타입별 템플릿(vault/_templates/)이 있으면 자동 참조합니다."
        bottomSpacing={24}
      />

      {error && (
        <div
          style={{
            background: "var(--color-error-text)",
            color: "white",
            padding: "12px 16px",
            borderRadius: 6,
            marginBottom: 24,
            fontSize: 14,
          }}
        >
          ⚠️ {error}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.2fr", gap: 32 }}>
        {/* Left: Input Form */}
        <div
          style={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-hairline)",
            borderRadius: 8,
            padding: 24,
            display: "flex",
            flexDirection: "column",
            gap: 20,
            height: "fit-content",
          }}
        >
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: "var(--color-ink)" }}>초안 파라미터</h3>
          <form onSubmit={handleGenerate} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <TextField
              label="주제 (Topic)"
              required
              placeholder="예: 지식 보관소 자율 린터 통합 가이드"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
            />

            {/* Draft Type 선택기 — 타입별 _templates/{type}.md 연동 */}
            <SelectField
              label="문서 타입 (Draft Type)"
              value={draftType}
              onChange={(e) => setDraftType(e.target.value)}
              options={DRAFT_TYPE_OPTIONS}
              helper={`vault/_templates/${draftType}.md 가 있으면 AI 프롬프트에 자동 반영됩니다.`}
            />

            <TextField
              label="예상 아웃라인 (Outline)"
              multiline
              rows={6}
              placeholder={`예:\n1. 자율 린터 개요\n2. 14가지 정적 린트 규칙 설명\n3. CI/CD 파이프라인 적용 방법`}
              value={outline}
              onChange={(e) => setOutline(e.target.value)}
            />

            <div>
              <span
                style={{
                  display: "block",
                  fontSize: 13,
                  fontWeight: 500,
                  marginBottom: 6,
                  color: "var(--color-ink)",
                }}
              >
                연관 문서 선택 (Outbound Wiki-link)
              </span>
              <input
                type="text"
                className="input-base"
                placeholder="문서 제목 또는 slug로 검색..."
                value={searchPageQuery}
                onChange={(e) => setSearchPageQuery(e.target.value)}
                style={{ marginBottom: 10, width: "100%" }}
              />
              <div
                style={{
                  maxHeight: 200,
                  overflowY: "auto",
                  border: "1px solid var(--color-hairline)",
                  borderRadius: 6,
                  padding: 8,
                  display: "flex",
                  flexDirection: "column",
                  gap: 6,
                  background: "var(--color-canvas)",
                }}
              >
                {filteredPages.length === 0 ? (
                  <span style={{ fontSize: 12, color: "var(--color-muted)", padding: 4 }}>
                    검색 결과 또는 페이지가 없습니다.
                  </span>
                ) : (
                  filteredPages.map((p) => {
                    const isSelected = selectedPages.includes(p.slug);
                    return (
                      <label
                        key={p.slug}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          fontSize: 13,
                          cursor: "pointer",
                          padding: "4px 8px",
                          borderRadius: 4,
                          background: isSelected ? "var(--bg-soft)" : "transparent",
                          color: "var(--color-ink)",
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => togglePageSelection(p.slug)}
                        />
                        <span>{p.title || p.slug}</span>
                      </label>
                    );
                  })
                )}
              </div>
            </div>

            <Button type="submit" disabled={generating || !topic.trim()} fullWidth style={{ marginTop: 8 }}>
              {generating ? "🤖 초안 빌드 중..." : "✨ AI 초안 작성"}
            </Button>
          </form>
        </div>

        {/* Right: Preview & Inline Editor */}
        <div
          style={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-hairline)",
            borderRadius: 8,
            padding: 24,
            display: "flex",
            flexDirection: "column",
            gap: 20,
            minHeight: 500,
          }}
        >
          {draftResult ? (
            <>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  borderBottom: "1px solid var(--color-hairline)",
                  paddingBottom: 12,
                  gap: 16,
                }}
              >
                <div style={{ minWidth: 0, flex: 1 }}>
                  <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: "var(--color-ink)" }}>
                    📝 임시 초안 편집기
                  </h3>
                  <span style={{ fontSize: 12, color: "var(--color-muted)", display: "block", textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap" }}>
                    임시 격리 경로: {draftResult.path} (린트 예외 대상)
                  </span>
                </div>
                <Button variant="primary" size="sm" onClick={() => handleCommit(false)} disabled={committing}>
                  {committing ? "보관소 발행 중..." : "🚀 보관소로 발행 (Commit)"}
                </Button>
              </div>

              <textarea
                value={editedContent}
                onChange={(e) => setEditedContent(e.target.value)}
                style={{
                  flex: 1,
                  width: "100%",
                  minHeight: 400,
                  fontFamily: "var(--font-mono, Monaco, monospace)",
                  fontSize: 14,
                  lineHeight: "1.6",
                  color: "var(--color-ink)",
                  background: "var(--color-canvas)",
                  border: "1px solid var(--color-hairline)",
                  borderRadius: 6,
                  padding: 16,
                  resize: "vertical",
                  outline: "none",
                }}
              />
            </>
          ) : (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <EmptyState
                icon={<EmptyIcon.File />}
                title="임시 초안 미리보기"
                description="왼쪽 폼에 주제와 아웃라인을 입력하고 생성 단추를 누르면, 이곳에 임시 초안 마크다운이 로드되어 직접 인라인 편집할 수 있습니다."
              />
            </div>
          )}
        </div>
      </div>

      {/* 충돌 감지 다이얼로그 (HTTP 409) */}
      <Modal
        open={!!conflictData}
        onClose={() => setConflictData(null)}
        maxWidth={900}
        disableBackdropClose
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div>
            <h3 style={{ margin: "0 0 6px 0", fontSize: 18, fontWeight: 700, color: "var(--color-ink)" }}>
              ⚠️ 덮어쓰기 충돌 감지
            </h3>
            <p style={{ margin: 0, fontSize: 14, color: "var(--color-muted)" }}>
              {conflictData?.error}
            </p>
          </div>

          {/* 버전 비교 탭 */}
          <div style={{ display: "flex", gap: 8, borderBottom: "1px solid var(--color-hairline)", paddingBottom: 8 }}>
            <button
              onClick={() => setConflictView("draft")}
              style={{
                padding: "6px 14px",
                borderRadius: 6,
                border: "1px solid var(--color-hairline)",
                background: conflictView === "draft" ? "var(--color-ink)" : "transparent",
                color: conflictView === "draft" ? "var(--color-canvas)" : "var(--color-ink)",
                cursor: "pointer",
                fontSize: 13,
                fontWeight: 500,
              }}
            >
              📝 새 초안 (Draft)
            </button>
            <button
              onClick={() => setConflictView("existing")}
              style={{
                padding: "6px 14px",
                borderRadius: 6,
                border: "1px solid var(--color-hairline)",
                background: conflictView === "existing" ? "var(--color-ink)" : "transparent",
                color: conflictView === "existing" ? "var(--color-canvas)" : "var(--color-ink)",
                cursor: "pointer",
                fontSize: 13,
                fontWeight: 500,
              }}
            >
              📄 기존 문서 (Existing)
            </button>
          </div>

          <textarea
            readOnly
            value={conflictView === "draft" ? (conflictData?.draft_content ?? "") : (conflictData?.existing_content ?? "")}
            style={{
              width: "100%",
              minHeight: 280,
              fontFamily: "var(--font-mono, Monaco, monospace)",
              fontSize: 13,
              lineHeight: "1.55",
              color: "var(--color-ink)",
              background: "var(--color-canvas)",
              border: "1px solid var(--color-hairline)",
              borderRadius: 6,
              padding: 14,
              resize: "vertical",
              outline: "none",
            }}
          />

          <p style={{ margin: 0, fontSize: 13, color: "var(--color-muted)" }}>
            두 버전을 비교한 뒤 행동을 선택하세요. "덮어쓰기"는 기존 content/ 파일을 즉시 대체합니다.
          </p>

          <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
            <Button variant="ghost" size="sm" onClick={() => setConflictData(null)}>
              취소 — 초안 유지
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => handleCommit(true)}
              disabled={committing}
            >
              {committing ? "발행 중..." : "⚡ 덮어쓰기 발행 (Overwrite)"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
