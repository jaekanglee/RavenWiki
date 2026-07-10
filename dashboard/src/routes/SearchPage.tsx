import { useState, useEffect } from "react";
import { useOutletContext, Link } from "react-router-dom";
import { EmptyState } from "../components/ui/EmptyState";
import { PageHeader } from "../components/ui/PageHeader";
import { SearchResultItem } from "../components/SearchResultItem";
import { useDebounced } from "../lib/useDebounced";
import { EmptyIcon } from "../lib/emptyIcons";

export function SearchPage() {
  const { vault } = useOutletContext<{ vault: string }>();
  const [q, setQ] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  // RAG 상태 관리
  const [ragAnswer, setRagAnswer] = useState<string | null>(null);
  const [ragLoading, setRagLoading] = useState(false);
  const [ragCitations, setRagCitations] = useState<any[]>([]);

  // Debounced fetch with AbortController (v0.7.69+): useDebounced hook으로 통일.
  const debouncedQ = useDebounced(q, 220);

  useEffect(() => {
    // 검색어가 바뀔 때마다 RAG 상태 초기화
    setRagAnswer(null);
    setRagCitations([]);
    setRagLoading(false);

    if (!debouncedQ.trim()) {
      setResults([]);
      setLoading(false);
      setHasSearched(false);
      return;
    }

    const ctrl = new AbortController();
    setLoading(true);
    setHasSearched(true);

    // FTS5 대신 신규 hybrid-search 엔드포인트 연동
    fetch(`/api/vaults/${encodeURIComponent(vault)}/hybrid-search?query=${encodeURIComponent(debouncedQ)}&limit=20`, {
      signal: ctrl.signal,
    })
      .then((r) => (r.ok ? r.json() : { results: [] }))
      .then((d) => setResults(d.results || []))
      .catch(() => setResults([]))
      .finally(() => setLoading(false));

    return () => {
      ctrl.abort();
    };
  }, [debouncedQ, vault]);

  const handleAskAI = async () => {
    if (!q.trim()) return;
    setRagLoading(true);
    setRagAnswer(null);
    setRagCitations([]);

    try {
      const resp = await fetch(`/api/vaults/${encodeURIComponent(vault)}/rag/query?query=${encodeURIComponent(q)}`);
      if (resp.ok) {
        const data = await resp.json();
        setRagAnswer(data.answer || "답변을 생성할 수 없습니다.");
        setRagCitations(data.citations || []);
      } else {
        setRagAnswer("⚠️ AI 답변 요청 중 오류가 발생했습니다.");
      }
    } catch (err) {
      setRagAnswer("⚠️ AI 답변 요청에 실패했습니다.");
    } finally {
      setRagLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 880 }}>
      <PageHeader
        title="검색"
        contextLabel={`${vault} 보관소`}
        subtitle="FTS5 및 로컬 임베딩 벡터가 결합된 하이브리드 지식 검색 및 AI Q&A 서비스를 제공합니다."
        titleSize={24}
        bottomSpacing={16}
      />

      <div style={{ marginBottom: 32 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            height: 48,
            background: "var(--color-canvas)",
            border: "1px solid var(--color-hairline-strong)",
            borderRadius: "var(--radius-full)",
            padding: "0 24px",
            boxShadow: "0 1px 2px var(--shadow-base)",
          }}
        >
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="검색어나 질문을 입력하세요"
            autoFocus
            style={{
              flex: 1,
              border: "none",
              outline: "none",
              background: "transparent",
              fontSize: 16,
              color: "var(--color-ink)",
              fontFamily: "inherit",
            }}
          />
        </div>
      </div>

      {!q && (
        <EmptyState
          icon={<EmptyIcon.Search />}
          title="검색어를 입력하세요"
          description="자연어 질문 또는 키워드를 기반으로 하이브리드 검색 및 AI Q&A 탐색을 시작합니다."
        />
      )}

      {q && (
        <>
          {/* AI Q&A (RAG) 블록 */}
          <div
            style={{
              background: "linear-gradient(135deg, var(--bg-soft) 0%, var(--bg-surface) 100%)",
              border: "1px solid var(--border-strong)",
              borderRadius: "var(--radius-lg)",
              padding: "20px",
              marginBottom: "24px",
              boxShadow: "var(--shadow-raised)",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "12px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  fontWeight: "bold",
                  fontSize: "15px",
                  color: "var(--accent)",
                }}
              >
                <span>🤖 AI 지식 탐색 답변 (RAG)</span>
              </div>
              {!ragAnswer && !ragLoading && (
                <button
                  onClick={handleAskAI}
                  style={{
                    background: "var(--btn-primary-bg)",
                    color: "var(--btn-primary-fg)",
                    border: "none",
                    borderRadius: "6px",
                    padding: "6px 14px",
                    fontSize: "13px",
                    fontWeight: 600,
                    cursor: "pointer",
                    transition: "background 0.2s",
                  }}
                  onMouseOver={(e) => (e.currentTarget.style.background = "var(--btn-primary-bg-hover)")}
                  onMouseOut={(e) => (e.currentTarget.style.background = "var(--btn-primary-bg)")}
                >
                  ✨ AI Q&A 답변 받기
                </button>
              )}
            </div>

            {ragLoading && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  color: "var(--fg-muted)",
                  padding: "10px 0",
                }}
              >
                <div
                  className="spinner"
                  style={{
                    width: "18px",
                    height: "18px",
                    border: "2px solid var(--border-subtle)",
                    borderTop: "2px solid var(--accent)",
                    borderRadius: "50%",
                    animation: "spin 1s linear infinite",
                  }}
                />
                <style>{`
                  @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                  }
                `}</style>
                <span style={{ fontSize: "13px" }}>보관소 문서들을 결합하여 AI가 답변을 도출하고 있습니다...</span>
              </div>
            )}

            {ragAnswer && (
              <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                <div
                  style={{
                    fontSize: "14px",
                    lineHeight: "1.6",
                    color: "var(--fg-default)",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {ragAnswer}
                </div>

                {ragCitations.length > 0 && (
                  <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "12px", marginTop: "4px" }}>
                    <div style={{ fontSize: "12px", fontWeight: "bold", color: "var(--fg-muted)", marginBottom: "8px" }}>
                      참조된 지식 문서:
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                      {ragCitations.map((cit) => (
                        <Link
                          key={cit.slug}
                          to={`/page/${vault}/${cit.slug}`}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            background: "var(--bg-soft)",
                            border: "1px solid var(--border-subtle)",
                            borderRadius: "4px",
                            padding: "4px 8px",
                            fontSize: "12px",
                            color: "var(--accent)",
                            textDecoration: "none",
                            transition: "background 0.2s",
                          }}
                          onMouseOver={(e) => (e.currentTarget.style.background = "var(--border-subtle)")}
                          onMouseOut={(e) => (e.currentTarget.style.background = "var(--bg-soft)")}
                        >
                          📄 {cit.title}
                        </Link>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* 검색 결과 목록 */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontSize: 13,
              color: "var(--color-muted)",
              marginBottom: 16,
            }}
          >
            <span>
              {loading
                ? "하이브리드 매칭 중…"
                : `하이브리드 검색 매칭: ${results.length}개 결과`}
            </span>
            {hasSearched && !loading && (
              <span>{`"${q}"`}</span>
            )}
          </div>

          {!loading && results.length === 0 ? (
            <EmptyState
              icon={<EmptyIcon.Folder />}
              title="검색 결과 없음"
              description="다른 키워드나 더 짧은 검색어로 다시 시도해 보세요."
            />
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {results.map((r) => (
                <SearchResultItem
                  key={r.slug}
                  vault={vault}
                  result={r}
                />
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}

