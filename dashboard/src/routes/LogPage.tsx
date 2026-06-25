import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { fetchLog, fetchLogStatus, type LogEntry, type LogStatus } from "../lib/api";

/**
 * LogPage — log.md timeline viewer.
 *
 * 카파시 LLM Wiki 패턴: vault의 작업 이력을 시간순으로 표시.
 * - 최근 N개 (default 50)
 * - 액션 필터 (create/update/build/lint/...)
 * - status 패널 (entries 수, rotation 필요)
 * - raw 모드 (grep-style)
 */
export function LogPage() {
  const { vault } = useOutletContext<{ vault: string }>();
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<LogStatus | null>(null);
  const [actionFilter, setActionFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [rawMode, setRawMode] = useState(false);
  const [rawText, setRawText] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [log, st] = await Promise.all([
        fetchLog(vault, { tail: 100, ...(actionFilter ? { action: actionFilter } : {}) }),
        fetchLogStatus(vault),
      ]);
      setEntries(log.entries);
      setTotal(log.total);
      setStatus(st);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [vault, actionFilter]);

  const loadRaw = async () => {
    const r = await fetch(`/api/vaults/${vault}/log?tail=100`);
    if (r.ok) {
      // fetchLog already returns parsed; for raw we use a separate endpoint
      // fallback: use status endpoint, or just don't show raw if not implemented
      // → use show endpoint if exists
    }
  };

  // Action color
  const actionColor = (a: string) => {
    if (a === "build") return "bg-blue-100 text-blue-700";
    if (a === "create") return "bg-green-100 text-green-700";
    if (a === "update") return "bg-cyan-100 text-cyan-700";
    if (a === "archive" || a === "delete") return "bg-red-100 text-red-700";
    if (a === "lint") return "bg-yellow-100 text-yellow-700";
    if (a === "ingest") return "bg-purple-100 text-purple-700";
    if (a === "migrate") return "bg-orange-100 text-orange-700";
    return "bg-gray-100 text-gray-700";
  };

  return (
    <div>
      <h1 className="text-3xl font-bold mb-4">📜 Vault Log</h1>

      {/* Status panel */}
      {status && (
        <div className="bg-white dark:bg-gray-800 border rounded-lg p-4 mb-4 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div>
            <div className="text-gray-500">path</div>
            <div className="font-mono text-xs truncate" title={status.log_path}>
              {status.log_path.replace(/^.*\//, "~/")}
            </div>
          </div>
          <div>
            <div className="text-gray-500">entries</div>
            <div className="text-2xl font-bold">
              {status.total_entries} <span className="text-sm text-gray-500">/ {status.rotate_threshold}</span>
            </div>
          </div>
          <div>
            <div className="text-gray-500">last</div>
            <div className="text-xs">
              {status.last_entry
                ? `[${status.last_entry.date}] ${status.last_entry.action}`
                : "—"}
            </div>
          </div>
          <div>
            <div className="text-gray-500">rotation</div>
            <div className={status.needs_rotate ? "text-red-600 font-bold" : "text-green-600"}>
              {status.needs_rotate ? "⚠️ rotate 권장" : "✅ OK"}
            </div>
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center gap-3 mb-3 flex-wrap">
        <label className="text-sm">
          액션:&nbsp;
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="border rounded px-2 py-1 text-sm"
          >
            <option value="">전체</option>
            {["ingest", "update", "create", "archive", "delete", "lint", "build", "migrate", "chore"].map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        </label>
        <button
          onClick={load}
          className="text-sm px-3 py-1 border rounded hover:bg-gray-100 dark:hover:bg-gray-700"
        >
          🔄 새로고침
        </button>
        <button
          onClick={() => setRawMode(!rawMode)}
          className="text-sm px-3 py-1 border rounded hover:bg-gray-100 dark:hover:bg-gray-700"
        >
          {rawMode ? "📋 리스트" : "🗒 raw"}
        </button>
        <span className="text-xs text-gray-500 ml-auto">
          showing {entries.length} / {total}
        </span>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading…</p>
      ) : rawMode ? (
        <pre className="bg-white dark:bg-gray-800 border rounded p-4 text-xs overflow-x-auto font-mono whitespace-pre-wrap">
{status?.log_path && `# ${status.log_path}\n\n# (raw mode: log.md 직접 보기)\n# 카파시 grep tip:  grep "^## \\[" log.md | tail -5\n`}
        </pre>
      ) : entries.length === 0 ? (
        <p className="text-gray-500">entry 없음 — 첫 작업 시 자동 생성</p>
      ) : (
        <ul className="space-y-1">
          {entries.slice().reverse().map((e, i) => (
            <li
              key={i}
              className="bg-white dark:bg-gray-800 border rounded px-3 py-2 text-sm flex items-start gap-3"
            >
              <span className="text-gray-500 font-mono text-xs whitespace-nowrap">
                {e.date}
              </span>
              <span
                className={`px-2 py-0.5 rounded text-xs font-mono whitespace-nowrap ${actionColor(e.action)}`}
              >
                {e.action}
              </span>
              <div className="flex-1 min-w-0">
                <div className="font-medium truncate">{e.subject}</div>
                {e.details.length > 0 && (
                  <div className="text-xs text-gray-600 dark:text-gray-400 mt-0.5">
                    {e.details.join(" · ")}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
