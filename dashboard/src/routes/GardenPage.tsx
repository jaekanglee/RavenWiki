import { useEffect, useState } from "react";
import { useOutletContext, useNavigate, Link } from "react-router-dom";
import {
  fetchGarden,
  deletePage,
  fetchPage,
  updatePage,
  fetchPages,
  type StalePage,
  type OrphanPage,
} from "../lib/api";
import { EmptyState } from "../components/ui/EmptyState";

export function GardenPage() {
  const { vault } = useOutletContext<{ vault: string }>();
  const navigate = useNavigate();
  const [stalePages, setStalePages] = useState<StalePage[]>([]);
  const [orphanPages, setOrphanPages] = useState<OrphanPage[]>([]);
  const [selectedStaleSlugs, setSelectedStaleSlugs] = useState<string[]>([]);
  const [allPages, setAllPages] = useState<any[]>([]);
  const [activeManualConnect, setActiveManualConnect] = useState<string | null>(null);
  const [manualTargetSlug, setManualTargetSlug] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const loadGardenData = async () => {
    if (!vault) return;
    setLoading(true);
    try {
      const data = await fetchGarden(vault);
      if (data && data.ok) {
        setStalePages(data.stale || []);
        setOrphanPages(data.orphan || []);
        setSelectedStaleSlugs([]);
      }
      const pagesData = await fetchPages(vault);
      setAllPages(pagesData || []);
    } catch (e) {
      console.error(e);
      showToast("데이터를 불러오는 중 오류가 발생했습니다.", "error");
    } finally {
      setLoading(false);
    }
  };

  const showToast = (message: string, type: "success" | "error" = "success") => {
    setToast({ message, type });
    // 2400ms 지속 규칙 준수
    setTimeout(() => {
      setToast(null);
    }, 2400);
  };

  const handleArchive = async (slug: string) => {
    if (!window.confirm(`문서 '${slug}'를 아카이브 폴더로 이동하시겠습니까?`)) {
      return;
    }
    try {
      await deletePage(vault, slug);
      showToast(`✅ 문서 '${slug}' 아카이빙 완료`);
      loadGardenData();
    } catch (e) {
      console.error(e);
      showToast("아카이빙 중 오류가 발생했습니다.", "error");
    }
  };

  const handleBatchArchive = async () => {
    const count = selectedStaleSlugs.length;
    if (count === 0) return;
    if (!window.confirm(`선택한 ${count}개의 문서를 아카이브 폴더로 이동하시겠습니까?`)) {
      return;
    }
    setLoading(true);
    try {
      await Promise.all(selectedStaleSlugs.map((slug) => deletePage(vault, slug)));
      showToast(`✅ 문서 ${count}개 일괄 아카이빙 완료`);
      setSelectedStaleSlugs([]);
      await loadGardenData();
    } catch (e) {
      console.error(e);
      showToast("일괄 아카이빙 중 오류가 발생했습니다.", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleConnectLink = async (orphanSlug: string, targetSlug: string) => {
    try {
      // 1. 대상 문서 가져오기
      const pageData = await fetchPage(vault, targetSlug);
      if (!pageData || !pageData.ok) {
        throw new Error("Target page load failed");
      }

      // 2. 본문 끝에 wikilink 추가
      const newContent = `${pageData.content.trim()}\n\n---\n*   **관련 연결**: [[${orphanSlug}]]`;

      // 3. 업데이트 요청
      await updatePage(vault, targetSlug, {
        content: newContent,
      });

      showToast(`✅ '${targetSlug}' 문서에 [[${orphanSlug}]] 링크 연결 완료`);
      loadGardenData();
    } catch (e) {
      console.error(e);
      showToast("링크 연결 중 오류가 발생했습니다.", "error");
    }
  };

  useEffect(() => {
    loadGardenData();
  }, [vault]);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: "100px 0" }}>
        <span style={{ fontSize: 16, color: "var(--color-muted)" }}>🌱 지식 정원을 불러오는 중...</span>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1120, position: "relative" }}>
      {toast && (
        <div
          style={{
            position: "fixed",
            bottom: 24,
            right: 24,
            padding: "12px 20px",
            backgroundColor: toast.type === "success" ? "#0f172a" : "#991b1b",
            color: "#ffffff",
            borderRadius: "var(--radius-md)",
            boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
            zIndex: 1000,
            fontSize: 14,
            fontWeight: 500,
            animation: "fade-in 0.2s ease-out",
          }}
        >
          {toast.message}
        </div>
      )}

      <div style={{ marginBottom: 32 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
          <h1 style={{ margin: 0 }}>🌱 지식 정원 가꾸기</h1>
          <span style={{ color: "var(--color-muted)", fontSize: 14 }}>in {vault}</span>
        </div>
        <p className="text-muted" style={{ fontSize: 14, marginTop: 8, marginBottom: 0 }}>
          방치된 지식(Stale)을 아카이빙하고 연결이 끊긴 고아 문서(Orphan)에 추천 링크를 바인딩하여 보관소 지식의 생동감을 유지하세요.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 24,
          alignItems: "start",
        }}
      >
        {/* Left column: Stale Pages */}
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
            🗑️ 방치된 잡초 (Stale Pages)
            <span
              style={{
                fontSize: 12,
                fontWeight: 600,
                padding: "2px 8px",
                borderRadius: 12,
                backgroundColor: "var(--color-surface-soft)",
                color: "var(--color-ink)",
              }}
            >
              {stalePages.length}
            </span>
          </h2>
          
          {stalePages.length === 0 ? (
            <EmptyState
              icon="✨"
              title="잡초 없음"
              description="90일 이상 갱신되지 않고 방치된 문서가 없습니다. 지식이 활발하게 순환 중입니다."
            />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {stalePages.length > 0 && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    marginBottom: 4,
                    padding: "8px 12px",
                    background: "var(--color-surface-soft)",
                    borderRadius: "var(--radius-sm)",
                    border: "1px solid var(--color-border)",
                  }}
                >
                  <label style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 13, cursor: "pointer", color: "var(--color-ink)", fontWeight: 500 }}>
                    <input
                      type="checkbox"
                      checked={stalePages.length > 0 && selectedStaleSlugs.length === stalePages.length}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedStaleSlugs(stalePages.map((p) => p.slug));
                        } else {
                          setSelectedStaleSlugs([]);
                        }
                      }}
                      style={{ accentColor: "var(--color-primary)", cursor: "pointer" }}
                    />
                    전체 선택 ({selectedStaleSlugs.length}/{stalePages.length})
                  </label>
                  {selectedStaleSlugs.length > 0 && (
                    <button
                      onClick={handleBatchArchive}
                      style={{
                        padding: "4px 10px",
                        fontSize: 12,
                        borderRadius: "var(--radius-sm)",
                        border: "none",
                        backgroundColor: "#fee2e2",
                        color: "#991b1b",
                        cursor: "pointer",
                        fontWeight: 600,
                      }}
                    >
                      선택 아카이브
                    </button>
                  )}
                </div>
              )}
              {stalePages.map((p) => {
                const isVeryOld = p.age_days >= 120;
                const isChecked = selectedStaleSlugs.includes(p.slug);
                const toggleSelect = (slug: string) => {
                  setSelectedStaleSlugs((prev) =>
                    prev.includes(slug) ? prev.filter((s) => s !== slug) : [...prev, slug]
                  );
                };
                return (
                  <div
                    key={p.slug}
                    className="card-flat"
                    style={{
                      padding: 16,
                      display: "flex",
                      gap: 12,
                      borderLeft: isVeryOld ? "4px solid #ef4444" : "4px solid #eab308",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center" }}>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleSelect(p.slug)}
                        style={{ accentColor: "var(--color-primary)", cursor: "pointer", width: 15, height: 15 }}
                      />
                    </div>
                    <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 12 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
                        <Link
                          to={`/page/${vault}/${p.slug}`}
                          style={{
                            fontWeight: 600,
                            fontSize: 14,
                            color: "var(--color-ink)",
                            textDecoration: "none",
                            wordBreak: "break-all",
                          }}
                        >
                          {p.slug}
                        </Link>
                        <span
                          style={{
                            fontSize: 11,
                            fontWeight: 600,
                            padding: "2px 6px",
                            borderRadius: 4,
                            backgroundColor: isVeryOld ? "#fef2f2" : "#fef9c3",
                            color: isVeryOld ? "#991b1b" : "#854d0e",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {p.age_days}일 경과
                        </span>
                      </div>

                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12 }}>
                        <span style={{ color: "var(--color-muted)" }}>마지막 갱신: {p.updated}</span>
                        <div style={{ display: "flex", gap: 8 }}>
                          <button
                            onClick={() => navigate(`/page/${vault}/${p.slug}`)}
                            style={{
                              padding: "4px 8px",
                              fontSize: 12,
                              borderRadius: "var(--radius-sm)",
                              border: "1px solid var(--color-border)",
                              backgroundColor: "transparent",
                              color: "var(--color-ink)",
                              cursor: "pointer",
                            }}
                          >
                            편집
                          </button>
                          <button
                            onClick={() => handleArchive(p.slug)}
                            style={{
                              padding: "4px 8px",
                              fontSize: 12,
                              borderRadius: "var(--radius-sm)",
                              border: "none",
                              backgroundColor: "#fee2e2",
                              color: "#991b1b",
                              cursor: "pointer",
                              fontWeight: 500,
                            }}
                          >
                            아카이브
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right column: Orphan Pages */}
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
            🕸️ 고립된 문서 (Orphan Pages)
            <span
              style={{
                fontSize: 12,
                fontWeight: 600,
                padding: "2px 8px",
                borderRadius: 12,
                backgroundColor: "var(--color-surface-soft)",
                color: "var(--color-ink)",
              }}
            >
              {orphanPages.length}
            </span>
          </h2>

          {orphanPages.length === 0 ? (
            <EmptyState
              icon="🕸️"
              title="고립된 문서 없음"
              description="인바운드 링크가 없는 고아 문서가 없습니다. 모든 지식이 하나 이상 유기적으로 연결되어 있습니다."
            />
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {orphanPages.map((p) => (
                <div
                  key={p.slug}
                  className="card-flat"
                  style={{
                    padding: 16,
                    display: "flex",
                    flexDirection: "column",
                    gap: 12,
                  }}
                >
                  <div>
                    <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                      <Link
                        to={`/page/${vault}/${p.slug}`}
                        style={{
                          fontWeight: 600,
                          fontSize: 14,
                          color: "var(--color-ink)",
                          textDecoration: "none",
                          wordBreak: "break-all",
                        }}
                      >
                        {p.title}
                      </Link>
                      <span style={{ fontSize: 11, color: "var(--color-muted)" }}>({p.type})</span>
                    </div>
                    <span style={{ fontSize: 12, color: "var(--color-muted)", wordBreak: "break-all" }}>
                      path: {p.slug}
                    </span>
                  </div>

                  <div style={{ borderTop: "1px solid var(--color-border)", paddingTop: 12 }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: "var(--color-ink)", display: "block", marginBottom: 8 }}>
                      💡 지식 추천 연결 후보
                    </span>
                    {(!p.link_candidates || p.link_candidates.length === 0) ? (
                      <span style={{ fontSize: 12, color: "var(--color-muted)", fontStyle: "italic" }}>
                        추천 연결 대상이 발견되지 않았습니다.
                      </span>
                    ) : (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                        {p.link_candidates.map((cand) => (
                          <div
                            key={cand}
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: 6,
                              padding: "4px 8px",
                              backgroundColor: "var(--color-surface-soft)",
                              borderRadius: 4,
                              border: "1px solid var(--color-border)",
                            }}
                          >
                            <span style={{ fontSize: 12, color: "var(--color-ink)", wordBreak: "break-all" }}>
                              {cand}
                            </span>
                            <button
                              onClick={() => handleConnectLink(p.slug, cand)}
                              style={{
                                padding: "2px 6px",
                                fontSize: 10,
                                borderRadius: 3,
                                border: "none",
                                backgroundColor: "var(--color-ink)",
                                color: "var(--color-surface-soft)",
                                cursor: "pointer",
                                fontWeight: 600,
                              }}
                            >
                              연결
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* 수동 연결 UI */}
                  <div style={{ borderTop: "1px dashed var(--color-border)", marginTop: 12, paddingTop: 8 }}>
                    {activeManualConnect === p.slug ? (
                      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <select
                          value={manualTargetSlug}
                          onChange={(e) => setManualTargetSlug(e.target.value)}
                          style={{
                            flex: 1,
                            fontSize: 12,
                            padding: "4px 8px",
                            borderRadius: "var(--radius-sm)",
                            border: "1px solid var(--color-border)",
                            backgroundColor: "var(--color-canvas)",
                            color: "var(--color-ink)",
                          }}
                        >
                          <option value="">-- 연결 대상 문서 선택 --</option>
                          {allPages
                            .filter((page) => page.slug !== p.slug)
                            .map((page) => (
                              <option key={page.slug} value={page.slug}>
                                {page.slug} ({page.title})
                              </option>
                            ))}
                        </select>
                        <button
                          onClick={async () => {
                            if (!manualTargetSlug) return;
                            await handleConnectLink(p.slug, manualTargetSlug);
                            setActiveManualConnect(null);
                            setManualTargetSlug("");
                          }}
                          disabled={!manualTargetSlug}
                          style={{
                            padding: "4px 8px",
                            fontSize: 11,
                            borderRadius: "var(--radius-sm)",
                            border: "none",
                            backgroundColor: "var(--color-primary)",
                            color: "#fff",
                            cursor: "pointer",
                            fontWeight: 600,
                            opacity: !manualTargetSlug ? 0.6 : 1,
                          }}
                        >
                          연결
                        </button>
                        <button
                          onClick={() => {
                            setActiveManualConnect(null);
                            setManualTargetSlug("");
                          }}
                          style={{
                            padding: "4px 8px",
                            fontSize: 11,
                            borderRadius: "var(--radius-sm)",
                            border: "1px solid var(--color-border)",
                            backgroundColor: "transparent",
                            color: "var(--color-ink)",
                            cursor: "pointer",
                          }}
                        >
                          취소
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => {
                          const candidates = allPages.filter((page) => page.slug !== p.slug);
                          setActiveManualConnect(p.slug);
                          setManualTargetSlug(candidates[0]?.slug || "");
                        }}
                        style={{
                          padding: "2px 6px",
                          fontSize: 11,
                          borderRadius: "var(--radius-sm)",
                          border: "1px solid var(--color-border)",
                          backgroundColor: "transparent",
                          color: "var(--color-ink)",
                          cursor: "pointer",
                        }}
                      >
                        🔎 수동 연결...
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
