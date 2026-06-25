import { Link } from "react-router-dom";

export function BacklinksPanel({
  backlinks,
}: {
  backlinks: { source_slug: string; source_title: string }[];
}) {
  if (!backlinks || backlinks.length === 0) {
    return (
      <aside className="text-sm text-gray-500">
        <h3 className="font-semibold mb-2">🔗 Backlinks</h3>
        <p>아직 참조 없음</p>
      </aside>
    );
  }

  return (
    <aside className="text-sm">
      <h3 className="font-semibold mb-2">🔗 Backlinks ({backlinks.length})</h3>
      <ul className="space-y-1">
        {backlinks.map((b) => (
          <li key={b.source_slug}>
            <Link
              to={`/page/${b.source_slug}`}
              className="text-cyan-600 hover:underline"
            >
              ← {b.source_title}
            </Link>
          </li>
        ))}
      </ul>
    </aside>
  );
}
