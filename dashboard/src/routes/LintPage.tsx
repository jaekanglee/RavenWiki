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
 * 카파시 LLM Wiki 패턴: 12개 lint check 결과를 한눈에.
 * - by-check bar chart (#1-#12)
 * - severity counts (critical/warning/info)
 * - issue list (필터: check, severity)
 * - write_log 옵션 (lint action을 log.md에 기록)
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
        setWriteLog(false); // 한 번만 실행
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [vault, checkFilter, severityFilter]);

  return (
    <div>
      <h1 className="text-3xl font-bold mb-4">🔍 Vault Lint</h1>

      {/* Counts header */}
      {summary && (
        <div className="bg-white dark:bg-gray-800 border rounded-lg p-4 mb-4">
          <div className="flex items-center gap-3 mb-3">
            <span className={`text-2xl ${summary.ok ? "✅" : "❌"}`}>
              {summary.ok ? "✅" : "❌"}
            </span>
            <span className="text-2xl font-bold">
              {summary.vault}
            </span>
            <span className="text-gray-500 ml-auto">
              total {summary.counts.total} issues
            </span>
          </div>
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="border rounded p-2 bg-red-50 dark:bg-red-900/20">
              <div className="text-xs text-red-700 dark:text-red-300">critical</div>
              <div className="text-2xl font-bold text-red-700 dark:text-red-300">
                {summary.counts.critical}
              </div>
              <div className="text-xs text-red-600">🔴</div>
            </div>
            <div className="border rounded p-2 bg-yellow-50 dark:bg-yellow-900/20">
              <div className="text-xs text-yellow-700 dark:text-yellow-300">warning</div>
              <div className="text-2xl font-bold text-yellow-700 dark:text-yellow-300">
                {summary.counts.warning}
              </div>
              <div className="text-xs text-yellow-600">🟡</div>
            </div>
            <div className="border rounded p-2 bg-blue-50 dark:bg-blue-900/20">
              <div className="text-xs text-blue-700 dark:text-blue-300">info</div>
              <div className="text-2xl font-bold text-blue-700 dark:text-blue-300">
                {summary.counts.info}
              </div>
              <div className="text-xs text-blue-600">🔵</div>
            </div>
          </div>
        </div>
      )}

      {/* By-check bar chart */}
      {summary && (
        <div className="bg-white dark:bg-gray-800 border rounded-lg p-4 mb-4">
          <h2 className="text-lg font-semibold mb-3">📊 12 check by-count</h2>
          {Array.from({ length: 12 }, (_, i) => `#${i + 1}`).map((cid) => {
            const n = summary.by_check[cid] || 0;
            const max = Math.max(...Object.values(summary.by_check), 1);
            const width = `${(n / max) * 100}%`;
            const color =
              cid === "#1" || cid === "#2" || cid === "#11"
                ? "bg-red-500"
                : cid === "#4" || cid === "#5" || cid === "#9"
                ? "bg-yellow-500"
                : "bg-blue-400";
            return (
              <div key={cid} className="flex items-center gap-2 mb-1 text-sm">
                <span className="font-mono w-8 text-right text-gray-600">{cid}</span>
                <span className="w-48 truncate text-gray-700 dark:text-gray-300">
                  {CHECK_NAMES[cid]}
                </span>
                <div className="flex-1 bg-gray-100 dark:bg-gray-700 rounded h-5 overflow-hidden">
                  <div
                    className={`h-full ${color} transition-all`}
                    style={{ width }}
                    title={`${n} issues`}
                  />
                </div>
                <span className="font-mono w-10 text-right text-gray-700 dark:text-gray-300">
                  {n}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center gap-3 mb-3 flex-wrap">
        <label className="text-sm">
          check:&nbsp;
          <select
            value={checkFilter}
            onChange={(e) => setCheckFilter(e.target.value)}
            className="border rounded px-2 py-1 text-sm"
          >
            <option value="">전체</option>
            {Array.from({ length: 12 }, (_, i) => `#${i + 1}`).map((cid) => (
              <option key={cid} value={cid}>
                {cid} {CHECK_NAMES[cid]}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          severity:&nbsp;
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value as LintSeverity | "")}
            className="border rounded px-2 py-1 text-sm"
          >
            <option value="">전체</option>
            <option value="critical">critical</option>
            <option value="warning">warning</option>
            <option value="info">info</option>
          </select>
        </label>
        <button
          onClick={load}
          className="text-sm px-3 py-1 border rounded hover:bg-gray-100 dark:hover:bg-gray-700"
        >
          🔄 새로고침
        </button>
        <label className="text-sm flex items-center gap-1">
          <input
            type="checkbox"
            checked={writeLog}
            onChange={(e) => setWriteLog(e.target.checked)}
          />
          log 기록
        </label>
        {lastWriteResult && (
          <span className="text-xs text-green-600">{lastWriteResult}</span>
        )}
      </div>

      {/* Issue list */}
      {loading ? (
        <p className="text-gray-500">Loading…</p>
      ) : !result ? (
        <p className="text-red-500">API 응답 실패</p>
      ) : result.issues.length === 0 ? (
        <p className="text-gray-500">✅ 이슈 없음</p>
      ) : (
        <div className="space-y-1">
          {result.issues.slice(0, 200).map((iss, i) => (
            <IssueRow key={i} issue={iss} />
          ))}
          {result.issues.length > 200 && (
            <p className="text-xs text-gray-500 mt-2">
              … +{result.issues.length - 200} more (필터로 좁히세요)
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function IssueRow({ issue }: { issue: LintIssue }) {
  const sevColor =
    issue.severity === "critical"
      ? "bg-red-50 border-red-200 text-red-900 dark:bg-red-900/20 dark:text-red-200"
      : issue.severity === "warning"
      ? "bg-yellow-50 border-yellow-200 text-yellow-900 dark:bg-yellow-900/20 dark:text-yellow-200"
      : "bg-blue-50 border-blue-200 text-blue-900 dark:bg-blue-900/20 dark:text-blue-200";

  const sevIcon =
    issue.severity === "critical" ? "🔴" : issue.severity === "warning" ? "🟡" : "🔵";

  return (
    <div className={`border rounded px-3 py-2 text-sm flex items-start gap-2 ${sevColor}`}>
      <span className="text-base leading-none">{sevIcon}</span>
      <span className="font-mono text-xs font-bold w-8">{issue.id}</span>
      <a
        href={`/page/${issue.slug}`}
        className="font-mono text-xs underline truncate max-w-md"
        title={issue.slug}
      >
        {issue.slug}
      </a>
      <span className="flex-1 text-xs">{issue.message}</span>
    </div>
  );
}
