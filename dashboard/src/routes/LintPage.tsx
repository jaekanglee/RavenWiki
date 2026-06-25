import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import {
  fetchLint,
  fetchLintSummary,
  type LintIssue,
  type LintSeverity,
  type LintSummary,
  type LintResult,
} from "../lib/api";

/**
 * LintPage — vault lint 12개 viewer.
 *
 * 위키 dashboard 톤: 데이터 테이블, Rausch는 status badge accent만.
 * yellow/red는 ink 기반 다층 표현으로 대체 (체크/이니셜 라벨).
 */
const CHECK_NAMES: Record<string, string> = {
  "#1": "broken wikilink",
  "#2": "broken-intent false positive",
  "#3": "missing wikilink",
  "#4": "orphan (7d grace)",
  "#5": "contradictions",
  "#6": "confidence low",
  "#7": "stale (90d+)",
  "#8": "page size > 200",
  "#9": "tag not in core",
  "#10": "frontmatter 완전성",
  "#11": "index 완전성 (FS↔DB)",
  "#12": "log size ≥ 500",
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

  useEffect(() => {
    load();
  }, [vault, checkFilter, severityFilter]);

  return (
    <div style={{ maxWidth: 1120 }}>
      <h1 style={{ marginBottom: 8 }}>Vault Lint</h1>
      <p className="text-muted" style={{ fontSize: 14, marginBottom: 32 }}>
        12개 lint check 결과 요약입니다.
      </p>

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
              total {summary.counts.total} issues
            </span>
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 12,
            }}
          >
            <SeverityCard label="critical" count={summary.counts.critical} />
            <SeverityCard label="warning" count={summary.counts.warning} />
            <SeverityCard label="info" count={summary.counts.info} />
          </div>
        </div>
      )}

      {/* By-check bar chart */}
      {summary && (
        <div className="card-flat" style={{ marginBottom: 24, padding: 24 }}>
          <h3 style={{ marginBottom: 16, fontSize: 18 }}>12 check by-count</h3>
          {Array.from({ length: 12 }, (_, i) => `#${i + 1}`).map((cid) => {
            const n = summary.by_check[cid] || 0;
            const max = Math.max(...Object.values(summary.by_check), 1);
            const width = `${(n / max) * 100}%`;
            // ink + rausch two-tier, no yellow
            const isAccent = cid === "#1" || cid === "#2" || cid === "#11";
            return (
              <div
                key={cid}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  marginBottom: 6,
                  fontSize: 13,
                }}
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
          check&nbsp;
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
            {Array.from({ length: 12 }, (_, i) => `#${i + 1}`).map((cid) => (
              <option key={cid} value={cid}>
                {cid} {CHECK_NAMES[cid]}
              </option>
            ))}
          </select>
        </label>
        <label style={{ fontSize: 13, color: "var(--color-muted)" }}>
          severity&nbsp;
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
            <option value="critical">critical</option>
            <option value="warning">warning</option>
            <option value="info">info</option>
          </select>
        </label>
        <button
          onClick={load}
          className="btn-secondary"
          style={{ height: 36, padding: "8px 16px", fontSize: 13 }}
        >
          🔄 새로고침
        </button>
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
        <p className="text-muted">Loading…</p>
      ) : !result ? (
        <p style={{ color: "var(--color-error-text)" }}>API 응답 실패</p>
      ) : result.issues.length === 0 ? (
        <p className="text-muted">✓ 이슈 없음</p>
      ) : (
        <div style={{ border: "1px solid var(--color-hairline)", borderRadius: "var(--radius-md)", overflow: "hidden" }}>
          {result.issues.slice(0, 200).map((iss, i) => (
            <IssueRow key={i} issue={iss} isLast={i === Math.min(199, result.issues.length - 1)} />
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
              … +{result.issues.length - 200} more (필터로 좁히세요)
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function SeverityCard({ label, count }: { label: string; count: number }) {
  return (
    <div
      style={{
        border: "1px solid var(--color-hairline)",
        borderRadius: "var(--radius-md)",
        padding: 16,
        background: "var(--color-surface-soft)",
      }}
    >
      <div
        style={{
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: "0.32px",
          textTransform: "uppercase",
          color: "var(--color-muted)",
        }}
      >
        {label}
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, marginTop: 4, color: "var(--color-ink)" }}>
        {count}
      </div>
    </div>
  );
}

function IssueRow({ issue, isLast }: { issue: LintIssue; isLast: boolean }) {
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
        {issue.severity}
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
        href={`/page/${issue.slug}`}
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
    </div>
  );
}