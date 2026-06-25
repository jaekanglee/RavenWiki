import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

export function SearchBar({
  vault,
  onSelect,
}: {
  vault: string;
  onSelect?: (slug: string) => void;
}) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    if (!q.trim()) {
      setResults([]);
      return;
    }
    const ctrl = new AbortController();
    fetch(`/api/vaults/${vault}/search?q=${encodeURIComponent(q)}&top_k=8`, {
      signal: ctrl.signal,
    })
      .then((r) => (r.ok ? r.json() : { results: [] }))
      .then((d) => setResults(d.results || []))
      .catch(() => setResults([]));
    return () => ctrl.abort();
  }, [q, vault]);

  return (
    <div className="relative flex-1">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder={`🔍 ${vault} 검색…`}
        className="w-full px-3 py-2 border rounded dark:bg-gray-900"
      />
      {results.length > 0 && (
        <ul className="absolute w-full mt-1 bg-white dark:bg-gray-900 border rounded shadow-lg z-10 max-h-96 overflow-y-auto">
          {results.map((r) => (
            <li
              key={r.slug}
              onClick={() => {
                if (onSelect) onSelect(r.slug);
                else navigate(`/page/${r.slug}`);
                setQ("");
              }}
              className="px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer text-sm"
            >
              <div className="font-medium">{r.title}</div>
              <div className="text-xs text-gray-500">
                {r.type} · score {r.score}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
