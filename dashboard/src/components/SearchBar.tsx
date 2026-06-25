import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { initSearch, search } from "../lib/search";

export function SearchBar({ onSelect }: { onSelect?: (slug: string) => void }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    initSearch().catch(console.error);
  }, []);

  useEffect(() => {
    if (!q.trim()) return setResults([]);
    try {
      setResults(search(q).slice(0, 8));
    } catch {
      setResults([]);
    }
  }, [q]);

  return (
    <div className="relative flex-1">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="🔍 검색 (BM25)"
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
              <div className="text-xs text-gray-500">{r.path}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
