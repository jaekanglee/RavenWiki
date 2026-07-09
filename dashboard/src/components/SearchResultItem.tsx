import { Link } from "react-router-dom";

interface SearchResultItemProps {
  vault: string;
  result: any;
  compact?: boolean;
  interactive?: boolean;
  active?: boolean;
  optionId?: string;
  onSelect?: () => void;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
}

export function SearchResultItem({
  vault,
  result,
  compact = false,
  interactive = false,
  active = false,
  optionId,
  onSelect,
  onMouseEnter,
  onMouseLeave,
}: SearchResultItemProps) {
  const body = (
    <>
      <div style={{ fontSize: compact ? 15 : 16, fontWeight: 600, marginBottom: 4, color: "var(--color-ink)" }}>
        {result.title}
      </div>
      {result.snippet && (
        <div
          style={{
            fontSize: compact ? 12 : 13,
            color: "var(--color-muted)",
            marginBottom: 4,
            lineHeight: 1.4,
          }}
          dangerouslySetInnerHTML={{ __html: result.snippet }}
        />
      )}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          flexWrap: "wrap",
          fontSize: compact ? 11 : 12,
          color: "var(--color-muted)",
        }}
      >
        {result.type && (
          <span
            className="chip"
            style={{ padding: compact ? "2px 8px" : "3px 8px", fontSize: compact ? 11 : 12 }}
          >
            {result.type}
          </span>
        )}
        <span style={{ fontFamily: "ui-monospace, SFMono-Regular, monospace" }}>
          {result.path ?? result.slug}
        </span>
        {typeof result.score === "number" && (
          <span style={{ fontSize: compact ? 11 : 12, opacity: 0.85 }}>
            • {result.method === "hybrid" ? "하이브리드" : result.method === "bm25_fallback" ? "FTS5" : "점수"}: {result.score.toFixed(3)}
          </span>
        )}
      </div>
    </>
  );

  if (interactive) {
    return (
      <li
        id={optionId}
        role="option"
        aria-selected={active}
        onPointerDown={(e) => {
          e.preventDefault();
          onSelect?.();
        }}
        onClick={onSelect}
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
        style={{
          padding: "10px 12px",
          cursor: "pointer",
          borderRadius: 8,
          background: active ? "var(--color-surface-soft)" : "transparent",
        }}
      >
        {body}
      </li>
    );
  }

  return (
    <li
      style={{
        borderBottom: "1px solid var(--color-hairline)",
        paddingBottom: 16,
        marginBottom: 16,
      }}
    >
      <Link to={`/page/${vault}/${result.slug}`} className="link-ink" style={{ textDecoration: "none" }}>
        {body}
      </Link>
    </li>
  );
}
