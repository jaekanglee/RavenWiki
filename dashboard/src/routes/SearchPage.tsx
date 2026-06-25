import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { initSearch, search } from "../lib/search";

export function SearchPage() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<any[]>([]);

  useEffect(() => {
    initSearch().catch(console.error);
  }, []);

  useEffect(() => {
    if (!q) return setResults([]);
    try {
      setResults(search(q));
    } catch {
      setResults([]);
    }
  }, [q]);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">🔍 검색</h1>
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="검색어를 입력하세요"
        className="w-full px-3 py-2 border rounded mb-4 dark:bg-gray-900"
        autoFocus
      />
      {q && (
        <ul className="space-y-2">
          {results.length === 0 ? (
            <li className="text-gray-500">결과 없음</li>
          ) : (
            results.map((r) => (
              <li key={r.slug} className="border-b pb-2">
                <Link
                  to={`/page/${r.slug}`}
                  className="font-medium text-cyan-600 hover:underline"
                >
                  {r.title}
                </Link>
                <div className="text-xs text-gray-500">{r.path}</div>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
