import { useState, useEffect } from "react";
import { useOutletContext, useNavigate } from "react-router-dom";
import { PageHeader } from "../components/ui/PageHeader";
import { TextField } from "../components/ui/TextField";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { EmptyIcon } from "../lib/emptyIcons";
import { generateDraft, commitDraft, fetchPages } from "../lib/api";

export function DraftPage() {
  const { vault, refresh } = useOutletContext<{ vault: string; refresh: () => void }>();
  const navigate = useNavigate();

  // Inputs
  const [topic, setTopic] = useState("");
  const [outline, setOutline] = useState("");
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
      });
      if (res.ok) {
        setDraftResult({
          title: res.title,
          slug: res.slug,
          path: res.path,
          content: res.content,
        });
        setEditedContent(res.content);
        setToastMessage("🤖 임시 초안이 생성되었습니다.");
      } else {
        setError("초안 생성에 실패했습니다.");
      }
    } catch (err: any) {
      setError(err.message || "초안 생성 오류");
    } finally {
      setGenerating(false);
    }
  };

  const handleCommit = async () => {
    if (!draftResult) return;
    setCommitting(true);
    setError(null);

    try {
      const res = await commitDraft(vault, {
        draft_slug: draftResult.slug,
        content: editedContent,
      });
      if (res.ok) {
        setToastMessage("✅ 보관소로 발행 완료");
        refresh();
        
        // 1-click UX로 자연스럽게 생성된 정식 문서 View로 이동
        const targetSlug = res.slug.replace(/^content\//, "");
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
        subtitle="주제와 아웃라인을 입력하면 AI가 위키링크가 삽입된 정제된 초안을 작성합니다. 초안은 임시 보관되며, 승인 시 정식 페이지로 등록됩니다."
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
                <Button variant="primary" size="sm" onClick={handleCommit} disabled={committing}>
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
    </div>
  );
}
