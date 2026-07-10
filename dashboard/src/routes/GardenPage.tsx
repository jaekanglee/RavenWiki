import { useEffect, useState } from "react";
import { useOutletContext, useNavigate, Link } from "react-router-dom";
import {
  fetchGarden,
  deletePage,
  fetchPage,
  updatePage,
  fetchPages,
  fetchContradictions,
  resolveContradiction,
  type StalePage,
  type OrphanPage,
  type Contradiction,
} from "../lib/api";
import { EmptyState } from "../components/ui/EmptyState";
import { Button } from "../components/ui/Button";
import { EmptyIcon } from "../lib/emptyIcons";
import { Toast } from "../components/ui/Toast";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";

type GardenConfirmState =
  | { kind: "archiveOne"; slug: string }
  | { kind: "archiveBatch"; slugs: string[] }
  | null;

export function GardenPage() {
  const { vault } = useOutletContext<{ vault: string }>();
  const navigate = useNavigate();
  const [isCompact, setIsCompact] = useState(false);
  const [stalePages, setStalePages] = useState<StalePage[]>([]);
  const [orphanPages, setOrphanPages] = useState<OrphanPage[]>([]);
  const [selectedStaleSlugs, setSelectedStaleSlugs] = useState<string[]>([]);
  const [allPages, setAllPages] = useState<any[]>([]);
  const [activeManualConnect, setActiveManualConnect] = useState<string | null>(null);
  const [manualTargetSlug, setManualTargetSlug] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [confirmState, setConfirmState] = useState<GardenConfirmState>(null);
  const [contradictions, setContradictions] = useState<Contradiction[]>([]);
  const [loadingContradictions, setLoadingContradictions] = useState(false);

  const loadGardenData = async () => {
    if (!vault) return;
    setLoading(true);
    setLoadingContradictions(true);
    try {
      const data = await fetchGarden(vault);
      if (data && data.ok) {
        setStalePages(data.stale || []);
        setOrphanPages(data.orphan || []);
        setSelectedStaleSlugs([]);
      }
      const pagesData = await fetchPages(vault);
      setAllPages(pagesData || []);

      const contraData = await fetchContradictions(vault);
      if (contraData && contraData.ok) {
        setContradictions(contraData.contradictions || []);
      }
    } catch (e) {
      console.error(e);
      showToast("데이터를 불러오는 중 오류가 발생했습니다.", "error");
    } finally {
      setLoading(false);
      setLoadingContradictions(false);
    }
  };

  const handleResolveContradiction = async (
    c: Contradiction,
    action: "update_relation" | "add_backlink"
  ) => {
    setLoading(true);
    try {
      const res = await resolveContradiction(vault, {
        source_slug: c.source_slug,
        target_slug: c.target_slug,
        relation_type: c.proposed_data.relation_type,
        action: action,
        evidence: c.proposed_data.evidence,
        reason: c.proposed_data.reason,
      });
      if (res && res.ok) {
        showToast("✅ 모순 해결 및 관계 적용 완료");
        await loadGardenData();
      } else {
        showToast("모순 해결 적용에 실패했습니다.", "error");
      }
    } catch (e: any) {
      console.error(e);
      showToast(`오류: ${e?.message || e}`, "error");
    } finally {
      setLoading(false);
    }
  };

  const showToast = (message: string, type: "success" | "error" = "success") => {
    // v0.7.71+: Toast 컴포넌트 + auto-close useEffect 사용. unmount race 회피.
    // 이전엔 self-implemented setTimeout → 페이지 전환 시 setState on unmounted 컴포넌트 경고.
    setToast({ message, type });
  };

  // v0.7.71+: toast 표시 후 2400ms 자동 닫기 (race-free: unmount 시 cleanup).
  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 2400);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const handleArchive = async (slug: string) => {
    setConfirmState({ kind: "archiveOne", slug });
  };

  const handleBatchArchive = async () => {
    const count = selectedStaleSlugs.length;
    if (count === 0) return;
    setConfirmState({ kind: "archiveBatch", slugs: [...selectedStaleSlugs] });
  };

  const confirmArchive = async () => {
    if (!confirmState) return;
    setLoading(true);
    try {
      if (confirmState.kind === "archiveOne") {
        await deletePage(vault, confirmState.slug);
        showToast(`✅ 문서 '${confirmState.slug}' 아카이빙 완료`);
      } else {
        await Promise.all(confirmState.slugs.map((slug) => deletePage(vault, slug)));
        showToast(`✅ 문서 ${confirmState.slugs.length}개 일괄 아카이빙 완료`);
      }
      setSelectedStaleSlugs([]);
      setConfirmState(null);
      await loadGardenData();
    } catch (e) {
      console.error(e);
      showToast("아카이빙 중 오류가 발생했습니다.", "error");
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

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 1024px)");
    const sync = () => setIsCompact(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", padding: "100px 0" }}>
        <span style={{ fontSize: 16, color: "var(--color-muted)" }}>🌱 지식 정원을 불러오는 중...</span>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1120, position: "relative" }}>
      <Toast open={Boolean(toast)} message={toast?.message ?? ""} type={toast?.type ?? "success"} />
      <ConfirmDialog
        open={Boolean(confirmState)}
        onClose={() => !loading && setConfirmState(null)}
        onConfirm={confirmArchive}
        busy={loading}
        tone="danger"
        title={
          confirmState?.kind === "archiveBatch"
            ? "선택 문서를 아카이브할까요?"
            : "문서를 아카이브할까요?"
        }
        description={
          confirmState?.kind === "archiveBatch"
            ? `${confirmState.slugs.length}개 문서를 _archive/ 로 이동합니다.`
            : confirmState?.kind === "archiveOne"
            ? `'${confirmState.slug}' 문서를 _archive/ 로 이동합니다.`
            : ""
        }
        confirmLabel="아카이브"
      />

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
          gridTemplateColumns: isCompact ? "1fr" : "1fr 1fr",
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
              icon={<EmptyIcon.Sparkles />}
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
                    border: "1px solid var(--color-hairline)",
                    flexWrap: "wrap",
                    gap: 12,
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
                    <Button
                      onClick={handleBatchArchive}
                      variant="danger"
                      size="sm"
                    >
                      선택 아카이브
                    </Button>
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
                      flexDirection: isCompact ? "column" : "row",
                      gap: 12,
                      borderLeft: isVeryOld
                        ? "4px solid var(--color-danger-text)"
                        : "4px solid var(--color-warning-text)",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: isCompact ? "space-between" : "flex-start" }}>
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleSelect(p.slug)}
                        style={{ accentColor: "var(--color-primary)", cursor: "pointer", width: 15, height: 15 }}
                      />
                      {isCompact && (
                        <span
                          style={{
                            fontSize: 11,
                            fontWeight: 600,
                            padding: "2px 6px",
                            borderRadius: 4,
                            backgroundColor: isVeryOld
                              ? "var(--color-danger-bg)"
                              : "var(--color-warning-bg)",
                            color: isVeryOld
                              ? "var(--color-danger-text)"
                              : "var(--color-warning-text)",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {p.age_days}일 경과
                        </span>
                      )}
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
                        {!isCompact && (
                          <span
                            style={{
                              fontSize: 11,
                              fontWeight: 600,
                              padding: "2px 6px",
                              borderRadius: 4,
                              backgroundColor: isVeryOld
                                ? "var(--color-danger-bg)"
                                : "var(--color-warning-bg)",
                              color: isVeryOld
                                ? "var(--color-danger-text)"
                                : "var(--color-warning-text)",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {p.age_days}일 경과
                          </span>
                        )}
                      </div>

                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: isCompact ? "stretch" : "center", fontSize: 12, gap: 10, flexDirection: isCompact ? "column" : "row" }}>
                        <span style={{ color: "var(--color-muted)" }}>마지막 갱신: {p.updated}</span>
                        <div style={{ display: "flex", gap: 8, flexDirection: isCompact ? "column" : "row", width: isCompact ? "100%" : undefined }}>
                          <Button
                            onClick={() => navigate(`/page/${vault}/${p.slug}`)}
                            variant="secondary"
                            size="sm"
                            style={isCompact ? { width: "100%" } : undefined}
                          >
                            편집
                          </Button>
                          <Button
                            onClick={() => handleArchive(p.slug)}
                            variant="danger"
                            size="sm"
                            style={isCompact ? { width: "100%" } : undefined}
                          >
                            아카이브
                          </Button>
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
              icon={<EmptyIcon.Network />}
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

                  <div style={{ borderTop: "1px solid var(--color-hairline)", paddingTop: 12 }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: "var(--color-ink)", display: "block", marginBottom: 8 }}>
                      💡 지식 추천 연결 후보
                    </span>
                    {(!p.link_candidates || p.link_candidates.length === 0) ? (
                      <span style={{ fontSize: 12, color: "var(--color-muted)", fontStyle: "italic" }}>
                        추천 연결 대상이 발견되지 않았습니다.
                      </span>
                    ) : (
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                        {p.link_candidates.map((cand) => {
                          const candSlug = typeof cand === "string" ? cand : cand.slug;
                          const candTitle = typeof cand === "string" ? cand : cand.title || cand.slug;
                          const candReason = typeof cand === "string" ? "" : cand.reason || "";
                          return (
                            <div
                              key={candSlug}
                              title={candReason}
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 6,
                                padding: "4px 8px",
                                backgroundColor: "var(--color-surface-soft)",
                                borderRadius: 4,
                                border: "1px solid var(--color-hairline)",
                              }}
                            >
                              <span style={{ fontSize: 12, color: "var(--color-ink)", wordBreak: "break-all" }}>
                                {candTitle}
                              </span>
                              <Button
                                onClick={() => handleConnectLink(p.slug, candSlug)}
                                variant="secondary"
                                size="sm"
                                style={{ padding: "2px 6px", fontSize: 10 }}
                              >
                                연결
                              </Button>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* 수동 연결 UI */}
                  <div style={{ borderTop: "1px dashed var(--color-hairline-strong)", marginTop: 12, paddingTop: 8 }}>
                    {activeManualConnect === p.slug ? (
                      <div style={{ display: "flex", gap: 8, alignItems: isCompact ? "stretch" : "center", flexDirection: isCompact ? "column" : "row" }}>
                        <select
                          value={manualTargetSlug}
                          onChange={(e) => setManualTargetSlug(e.target.value)}
                          style={{
                            flex: 1,
                            fontSize: 12,
                            padding: "4px 8px",
                            borderRadius: "var(--radius-sm)",
                            border: "1px solid var(--color-hairline)",
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
                            ...primaryButtonStyle,
                            width: isCompact ? "100%" : undefined,
                            opacity: !manualTargetSlug ? 0.6 : 1,
                          }}
                        >
                          연결
                        </button>
                        <Button
                          onClick={() => {
                            setActiveManualConnect(null);
                            setManualTargetSlug("");
                          }}
                          variant="secondary"
                          size="sm"
                          style={isCompact ? { width: "100%" } : undefined}
                        >
                          취소
                        </Button>
                      </div>
                    ) : (
                      <Button
                        onClick={() => {
                          const candidates = allPages.filter((page) => page.slug !== p.slug);
                          setActiveManualConnect(p.slug);
                          setManualTargetSlug(candidates[0]?.slug || "");
                        }}
                        variant="secondary"
                        size="sm"
                        style={{ padding: "2px 6px", fontSize: 11 }}
                      >
                        🔎 수동 연결...
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ─── AI 논리적 모순 탐지 (Logical Contradictions) ─── */}
      <div style={{ marginTop: 40, borderTop: "1px solid var(--color-hairline)", paddingTop: 32 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
          ⚖️ AI 논리적 모순 탐지 (Logical Contradictions)
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
            {contradictions.length}
          </span>
        </h2>
        <p className="text-muted" style={{ fontSize: 13, marginBottom: 20 }}>
          인접하거나 유사한 문서 간 기술 명세, 상태 등 논리적 불일치를 AI가 감지합니다. 승인하면 관계가 자동 업데이트되거나 상호 보완 역참조가 추가됩니다.
        </p>

        {loadingContradictions ? (
          <div style={{ padding: 20, color: "var(--color-muted)" }}>모순 검출 검사 중...</div>
        ) : contradictions.length === 0 ? (
          <EmptyState
            icon={<EmptyIcon.Sparkles />}
            title="모순 없음"
            description="보관소 지식 구조 내에서 충돌이나 논리적 모순이 발견되지 않았습니다."
          />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {contradictions.map((c, idx) => (
              <div
                key={`${c.source_slug}-${c.target_slug}-${idx}`}
                className="card-flat"
                style={{
                  padding: 20,
                  borderLeft: "4px solid var(--color-error-text)",
                  background: "var(--color-canvas)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12, marginBottom: 12 }}>
                  <div>
                    <span style={{ fontSize: 11, fontWeight: 700, color: "var(--color-error-text)", textTransform: "uppercase", display: "block", marginBottom: 4 }}>
                      충돌 감지 노드 쌍
                    </span>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                      <Link to={`/page/${vault}/${c.source_slug}`} style={{ fontWeight: 600, fontSize: 14, color: "var(--color-ink)", textDecoration: "none" }}>
                        {c.source_title || c.source_slug}
                      </Link>
                      <span style={{ color: "var(--color-muted)", fontSize: 12 }}>↔</span>
                      <Link to={`/page/${vault}/${c.target_slug}`} style={{ fontWeight: 600, fontSize: 14, color: "var(--color-ink)", textDecoration: "none" }}>
                        {c.target_title || c.target_slug}
                      </Link>
                    </div>
                  </div>
                  <span style={{ fontSize: 11, background: "var(--color-danger-bg)", color: "var(--color-danger-text)", padding: "2px 8px", borderRadius: 4, fontWeight: 600 }}>
                    관계 타입: {c.relation_type}
                  </span>
                </div>

                <div style={{ fontSize: 13, color: "var(--color-body)", marginBottom: 16, background: "var(--color-surface-soft)", padding: 12, borderRadius: 6, border: "1px solid var(--color-hairline)" }}>
                  <strong>🤖 AI 분석 결과:</strong> {c.description}
                </div>

                {c.proposed_data && (
                  <div style={{ fontSize: 12, color: "var(--color-muted)", marginBottom: 16 }}>
                    <div style={{ marginBottom: 4 }}><strong>제안 조치:</strong> {c.proposed_action === "update_relation" ? "관계 정보 업데이트" : "상호 역참조 연결"}</div>
                    <div style={{ marginBottom: 4 }}><strong>근거(Evidence):</strong> {c.proposed_data.evidence}</div>
                    <div><strong>이유(Reason):</strong> {c.proposed_data.reason}</div>
                  </div>
                )}

                <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                  <Button
                    onClick={() => handleResolveContradiction(c, "update_relation")}
                    variant="primary"
                    size="sm"
                  >
                    관계 업데이트 적용
                  </Button>
                  <Button
                    onClick={() => handleResolveContradiction(c, "add_backlink")}
                    variant="secondary"
                    size="sm"
                  >
                    상호 역참조 추가
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const primaryButtonStyle: React.CSSProperties = {
  padding: "4px 8px",
  fontSize: 11,
  borderRadius: 4,
  border: "none",
  backgroundColor: "var(--color-primary)",
  color: "var(--color-on-primary)",
  cursor: "pointer",
  fontWeight: 600,
};

