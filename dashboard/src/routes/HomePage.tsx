import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import type { Page } from "../types";

export function HomePage() {
  const [index, setIndex] = useState<Page[]>([]);

  useEffect(() => {
    fetch("/api/index.json")
      .then((r) => (r.ok ? r.json() : []))
      .then(setIndex)
      .catch(() => setIndex([]));
  }, []);

  const recent = [...index]
    .sort((a, b) => String(b.updated).localeCompare(String(a.updated)))
    .slice(0, 10);

  return (
    <div>
      <h1 className="text-3xl font-bold mb-4">🏠 Wiki 홈</h1>
      <p className="text-gray-600 mb-6">총 {index.length}개 페이지</p>

      <h2 className="text-xl font-semibold mb-2">📅 최근 수정</h2>
      {recent.length === 0 ? (
        <p className="text-gray-500">아직 페이지가 없음</p>
      ) : (
        <ul className="space-y-1">
          {recent.map((p) => (
            <li key={p.slug}>
              <Link
                to={`/page/${p.slug}`}
                className="text-cyan-600 hover:underline"
              >
                {p.title}
              </Link>
              <span className="text-xs text-gray-500 ml-2">{p.path}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
