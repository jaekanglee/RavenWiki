import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import {
  fetchLint,
  fetchLintSummary,
  fetchBuild,
  createPage,
  fetchPage,
  updatePage,
  type LintIssue,
  type LintSeverity,
  type LintSummary,
  type LintResult,
  type BuildResult,
} from "../lib/api";
import { EmptyState } from "../components/ui/EmptyState";
import { EmptyIcon } from "../lib/emptyIcons";
import { Button } from "../components/ui/Button";
import { ButtonIcon } from "../components/ui/ButtonIcon";
import { PageHeader } from "../components/ui/PageHeader";
import { Toast } from "../components/ui/Toast";

/**
 * LintPage — vault lint 12개 viewer.
 *
 * 위키 dashboard 톤: 데이터 테이블, Rausch는 status badge accent만.
 * yellow/red는 ink 기반 다층 표현으로 대체 (체크/이니셜 라벨).
 */
const CHECK_NAMES: Record<string, string> = {
  "#1": "깨진 위키링크",
  "#2": "깨진 의도 링크 오탐",
  "#3": "누락된 위키링크",
  "#4": "고아 문서 (7일 유예)",
  "#5": "모순 감지",
  "#6": "신뢰도 낮음",
  "#7": "오래된 문서 (90일+)",
  "#8": "문서 길이 초과 (> 200줄)",
  "#9": "핵심 분류 밖 태그",
  "#10": "frontmatter 완전성",
  "#11": "index 완전성 (FS↔DB)",
  "#12": "로그 크기 과다 (500+)",
  "#13": "인지 거버넌스",
  "#14": "계층 무결성 (누수)",
};

const SEVERITY_LABELS: Record<LintSeverity, string> = {
  critical: "치명",
  warning: "주의",
  info: "정보",
};

export function LintPage() {
  const { vault } = useOutletContext<{ vault: string }>();
  const [summary, setSummary] = useState<LintSummary | null>(null);
  const [result, setResult] = useState<LintResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkFilter, setCheckFilter] = useState<string>("");
  const [severityFilter, setSeverityFilter] = useState<LintSeverity | "">("");
  const [writeLog, setWriteLog] = useState(false);
  const [lastWriteResult, setLastWriteResult] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [building, setBuilding] = useState(false);
  const [buildResult, setBuildResult] = useState<BuildResult | null>(null);

  const showToast = (message: string, type: "success" | "error" = "success") => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 2400);
  };

  const load = async () => {
    setLoading(true);
    try {
      const [sum, full] = await Promise.all([
        fetchLintSummary(vault),
        fetchLint(vault, {
          ...(checkFilter ? { check: checkFilter } : {}),
          ...(severityFilter ? { severity: severityFilter } : {}),
          ...(writeLog ? { write_log: true } : {}),
        }),
      ]);
      setSummary(sum);
      setResult(full);
      if (writeLog && full) {
        setLastWriteResult(`[${new Date().toLocaleTimeString()}] log 기록됨`);
        setWriteLog(false);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRebuild = async () => {
    setBuilding(true);
    setBuildResult(null);
    try {
      const res = await fetchBuild(vault);
      if (!res) {
        showToast("리빌드 실패: 서버 응답 없음", "error");
        return;
      }
      setBuildResult(res);
      if (res.lint) {
        setResult(res.lint);
        setSummary(
          res.lint.ok
            ? { ok: true, vault, counts: res.lint.counts, by_check: {} }
            : null
        );
      }
      showToast(
        `리빌드 완료 — ${res.build.pages} pages, status=${res.build.ok ? "ok" : "error"}`,
        res.build.ok ? "success" : "error"
      );
      setTimeout(() => setBuildResult(null), 3000);
    } catch (e) {
      console.error(e);
      showToast("리빌드 중 오류가 발생했습니다.", "error");
    } finally {
      setBuilding(false);
    }
  };

  useEffect(() => {
    load();
  }, [vault, checkFilter, severityFilter]);

  return (
    <div style={{ maxWidth: 1120 }}>
      <PageHeader
        title="린트"
        contextLabel={`${vault} 보관소`}
        subtitle="14개 lint check 결과 요약입니다."
      />

      {/* Counts header */}
      {summary && (
        <div className="card-flat" style={{ marginBottom: 24, padding: 24 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              marginBottom: 20,
            }}
          >
            <span style={{ fontSize: 24 }}>{summary.ok ? "✓" : "!"}</span>
            <span style={{ fontSize: 20, fontWeight: 700 }}>{summary.vault}</span>
            <span style={{ marginLeft: "auto", color: "var(--color-muted)", fontSize: 13 }}>
              총 {summary.counts.total}개 이슈
            </span>
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 12,
            }}
          >
            <SeverityCard
              label="critical"
              count={summary.counts.critical}
              isActive={severityFilter === "critical"}
              onClick={() => setSeverityFilter(severityFilter === "critical" ? "" : "critical")}
            />
            <SeverityCard
              label="warning"
              count={summary.counts.warning}
              isActive={severityFilter === "warning"}
              onClick={() => setSeverityFilter(severityFilter === "warning" ? "" : "warning")}
            />
            <SeverityCard
              label="info"
              count={summary.counts.info}
              isActive={severityFilter === "info"}
              onClick={() => setSeverityFilter(severityFilter === "info" ? "" : "info")}
            />
          </div>
        </div>
      )}

      {/* By-check bar chart */}
      {summary && (
        <div className="card-flat" style={{ marginBottom: 24, padding: 24 }}>
          <h3 style={{ marginBottom: 16, fontSize: 18 }}>체크별 이슈 분포</h3>
          {Array.from({ length: 14 }, (_, i) => `#${i + 1}`).map((cid) => {
            const n = summary.by_check[cid] || 0;
            const max = Math.max(...Object.values(summary.by_check), 1);
            const width = `${(n / max) * 100}%`;
            // ink + rausch two-tier, no yellow
            const isAccent = cid === "#1" || cid === "#2" || cid === "#11";
            const isActive = checkFilter === cid;
            return (
              <div
                key={cid}
                onClick={() => setCheckFilter(isActive ? "" : cid)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  marginBottom: 6,
                  fontSize: 13,
                  cursor: "pointer",
                  padding: "4px 8px",
                  borderRadius: "var(--radius-sm)",
                  backgroundColor: isActive ? "var(--color-surface-soft, #f4f4f4)" : "transparent",
                  transition: "background-color 0.15s ease",
                }}
                className="hover-bg-soft"
                title={`${CHECK_NAMES[cid]} 필터링 토글 (${n}개)`}
              >
                <span
                  style={{
                    fontFamily: "ui-monospace, SFMono-Regular, monospace",
                    width: 32,
                    textAlign: "right",
                    color: "var(--color-muted)",
                  }}
                >
                  {cid}
                </span>
                <span
                  style={{
                    width: 192,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    color: "var(--color-body)",
                  }}
                >
                  {CHECK_NAMES[cid]}
                </span>
                <div
                  style={{
                    flex: 1,
                    background: "var(--color-surface-soft)",
                    borderRadius: 4,
                    height: 8,
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width,
                      height: "100%",
                      background: isAccent
                        ? "var(--color-primary)"
                        : "var(--color-ink)",
                      transition: "width 0.2s ease",
                    }}
                    title={`${n} issues`}
                  />
                </div>
                <span
                  style={{
                    fontFamily: "ui-monospace, SFMono-Regular, monospace",
                    width: 40,
                    textAlign: "right",
                    color: "var(--color-ink)",
                  }}
                >
                  {n}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Controls */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 16,
          flexWrap: "wrap",
        }}
      >
        <label style={{ fontSize: 13, color: "var(--color-muted)" }}>
          체크&nbsp;
          <select
            value={checkFilter}
            onChange={(e) => setCheckFilter(e.target.value)}
            style={{
              border: "1px solid var(--color-hairline-strong)",
              borderRadius: "var(--radius-full)",
              padding: "6px 14px",
              fontSize: 13,
              background: "var(--color-canvas)",
              color: "var(--color-ink)",
              fontFamily: "inherit",
              outline: "none",
            }}
          >
            <option value="">전체</option>
            {Array.from({ length: 14 }, (_, i) => `#${i + 1}`).map((cid) => (
              <option key={cid} value={cid}>
                {cid} {CHECK_NAMES[cid]}
              </option>
            ))}
          </select>
        </label>
        <label style={{ fontSize: 13, color: "var(--color-muted)" }}>
          심각도&nbsp;
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value as LintSeverity | "")}
            style={{
              border: "1px solid var(--color-hairline-strong)",
              borderRadius: "var(--radius-full)",
              padding: "6px 14px",
              fontSize: 13,
              background: "var(--color-canvas)",
              color: "var(--color-ink)",
              fontFamily: "inherit",
              outline: "none",
            }}
          >
            <option value="">전체</option>
            <option value="critical">{SEVERITY_LABELS.critical}</option>
            <option value="warning">{SEVERITY_LABELS.warning}</option>
            <option value="info">{SEVERITY_LABELS.info}</option>
          </select>
        </label>
        <Button onClick={load} variant="secondary" size="sm" disabled={building}>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <ButtonIcon.Refresh />새로고침
          </span>
        </Button>
        <Button
          onClick={handleRebuild}
          variant="secondary"
          size="sm"
          disabled={building}
          id="rebuild-btn"
        >
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              opacity: building ? 0.5 : 1,
              cursor: building ? "not-allowed" : "pointer",
            }}
          >
            {building ? "⌛" : "🔨"} wiki.db 리빌드
          </span>
        </Button>
        {buildResult && (
          <span
            style={{
              fontSize: 12,
              color: buildResult.build.ok
                ? "var(--color-primary)"
                : "var(--color-error-text)",
            }}
          >
            {buildResult.build.pages} pages · {buildResult.build.ok ? "✓ ok" : "✗ error"}
          </span>
        )}
        <label
          style={{
            fontSize: 13,
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            color: "var(--color-muted)",
          }}
        >
          <input
            type="checkbox"
            checked={writeLog}
            onChange={(e) => setWriteLog(e.target.checked)}
            style={{ accentColor: "var(--color-primary)" }}
          />
          log 기록
        </label>
        {lastWriteResult && (
          <span style={{ fontSize: 12, color: "var(--color-primary)" }}>
            {lastWriteResult}
          </span>
        )}
      </div>

      {/* Issue list — data table with ink + rausch accent badges only */}
      {loading ? (
        <p className="text-muted">불러오는 중…</p>
      ) : !result ? (
        <p style={{ color: "var(--color-error-text)" }}>API 응답 실패</p>
      ) : result.issues.length === 0 ? (
        <EmptyState
          icon={<EmptyIcon.Check />}
          title="이슈 없음"
          description="현재 Vault에 등록된 마크다운 문서들 중 어떠한 무결성 린트 오류도 검출되지 않았습니다."
        />
      ) : (
        <div style={{ border: "1px solid var(--color-hairline)", borderRadius: "var(--radius-md)", overflow: "hidden" }}>
          {result.issues.slice(0, 200).map((iss, i) => (
            <IssueRow
              key={i}
              issue={iss}
              isLast={i === Math.min(199, result.issues.length - 1)}
              vault={vault}
              onFixSuccess={load}
              showToast={showToast}
            />
          ))}
          {result.issues.length > 200 && (
            <p
              style={{
                fontSize: 12,
                color: "var(--color-muted)",
                padding: 16,
                background: "var(--color-surface-soft)",
              }}
            >
              … +{result.issues.length - 200}개 더 있음 (필터로 좁히세요)
            </p>
          )}
        </div>
      )}

      <Toast open={Boolean(toast)} message={toast?.message ?? ""} type={toast?.type ?? "success"} />
    </div>
  );
}

function SeverityCard({
  label,
  count,
  isActive,
  onClick,
}: {
  label: LintSeverity;
  count: number;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      style={{
        border: isActive ? "2px solid var(--color-primary)" : "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-md)",
        padding: isActive ? "15px" : "16px",
        background: isActive ? "var(--color-surface-soft, #f8f9fa)" : "var(--color-surface-soft)",
        cursor: "pointer",
        transition: "border-color 0.15s ease",
      }}
      title={`${label} 등급 필터 토글`}
    >
      <div
        style={{
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: "0.32px",
          textTransform: "uppercase",
          color: isActive ? "var(--color-primary)" : "var(--color-muted)",
        }}
      >
        {SEVERITY_LABELS[label]}
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, marginTop: 4, color: "var(--color-ink)" }}>
        {count}
      </div>
    </div>
  );
}

function IssueRow({
  issue,
  isLast,
  vault,
  onFixSuccess,
  showToast,
}: {
  issue: LintIssue;
  isLast: boolean;
  vault: string;
  onFixSuccess: () => void;
  showToast: (msg: string, type?: "success" | "error") => void;
}) {
  const [busy, setBusy] = useState(false);

  async function handleFixBrokenLink() {
    if (!issue.target) return;
    setBusy(true);
    try {
      const basename = issue.target.split("/").pop() || issue.target;
      await createPage(vault, {
        slug: issue.target,
        title: basename,
        type: "concept",
        tags: ["stub"],
        content: `# ${basename}\n\n> *이 문서는 깨진 링크 복구용 stub 문서입니다. 내용을 채워 넣어 완성해 주세요.*\n`,
      });
      showToast(`⚡ 빈 문서 '${issue.target}' 생성 및 복구 완료`);
      onFixSuccess();
    } catch (e) {
      console.error(e);
      showToast("복구 문서 생성 중 오류가 발생했습니다.", "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleFixFrontmatter() {
    setBusy(true);
    try {
      const page = await fetchPage(vault, issue.slug);
      if (!page || !page.ok) {
        throw new Error("페이지 로드 실패");
      }
      let newContent = page.content;
      const basename = issue.slug.split("/").pop() || issue.slug;
      const today = new Date().toISOString().split("T")[0];
      const fmHeader = `---\ntitle: ${basename}\ntype: concept\ncreated: ${today}\ntags: []\n---\n\n`;

      if (!newContent.startsWith("---")) {
        newContent = fmHeader + newContent;
      } else {
        newContent = fmHeader + newContent;
      }

      await updatePage(vault, issue.slug, { content: newContent });
      showToast(`⚡ '${issue.slug}' 기본 Frontmatter 삽입 완료`);
      onFixSuccess();
    } catch (e) {
      console.error(e);
      showToast("Frontmatter 수정 중 오류가 발생했습니다.", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: 12,
        padding: "12px 16px",
        fontSize: 13,
        borderBottom: isLast ? "none" : "1px solid var(--color-hairline)",
      }}
    >
      <span
        className="chip-strong"
        style={{
          background: issue.severity === "critical" ? "var(--color-primary)" : "var(--color-ink)",
        }}
      >
        {SEVERITY_LABELS[issue.severity]}
      </span>
      <span
        style={{
          fontFamily: "ui-monospace, SFMono-Regular, monospace",
          fontSize: 11,
          fontWeight: 700,
          width: 32,
          color: "var(--color-muted)",
        }}
      >
        {issue.id}
      </span>
      <a
        href={`/page/${vault}/${issue.slug}`}
        style={{
          fontFamily: "ui-monospace, SFMono-Regular, monospace",
          fontSize: 12,
          color: "var(--color-ink)",
          textDecoration: "underline",
          textUnderlineOffset: 2,
          maxWidth: 320,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
        title={issue.slug}
      >
        {issue.slug}
      </a>
      <span style={{ flex: 1, fontSize: 13, color: "var(--color-body)" }}>{issue.message}</span>
      
      {/* Quick Fix Button (only show for #1 with target or #10) */}
      {issue.id === "#1" && issue.target && (
        <button
          onClick={handleFixBrokenLink}
          disabled={busy}
          className="btn-secondary"
          style={{ padding: "2px 8px", fontSize: 11, height: 24, alignSelf: "center", whiteSpace: "nowrap" }}
          title="깨진 링크 대상 빈 페이지 자동 생성"
        >
          {busy ? "복구 중..." : "⚡ 퀵픽스 (stub 생성)"}
        </button>
      )}
      {issue.id === "#10" && (
        <button
          onClick={handleFixFrontmatter}
          disabled={busy}
          className="btn-secondary"
          style={{ padding: "2px 8px", fontSize: 11, height: 24, alignSelf: "center", whiteSpace: "nowrap" }}
          title="누락된 frontmatter 기본값 자동 생성 삽입"
        >
          {busy ? "수정 중..." : "⚡ 퀵픽스 (헤더 생성)"}
        </button>
      )}
    </div>
  );
}
