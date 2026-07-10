import { useState } from "react";
import { suggestTags } from "../lib/api";
import { Button } from "./ui/Button";

interface AITagSuggestionProps {
  vault: string;
  content: string;
  title?: string;
  onAccept: (tags: string[]) => void;
  style?: React.CSSProperties;
}

export function AITagSuggestion({
  vault,
  content,
  title,
  onAccept,
  style,
}: AITagSuggestionProps) {
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const getSuggestions = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await suggestTags(vault, { content, title });
      if (res.ok) {
        setSuggestions(res.tags);
        if (res.tags.length === 0) {
          setError("추천할 태그를 찾지 못했습니다.");
        }
      } else {
        setError("태그 추천에 실패했습니다.");
      }
    } catch (err: any) {
      setError(err?.message || "오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, ...style }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={getSuggestions}
          disabled={loading}
          style={{
            borderColor: "var(--color-primary)",
            color: "var(--color-primary)",
            background: "transparent",
            fontWeight: 600,
          }}
        >
          {loading ? "⌛ 분석 중..." : "✨ AI 태그 추천"}
        </Button>

        {error && (
          <span style={{ fontSize: 12, color: "var(--color-error-text)", fontWeight: 500 }}>
            {error}
          </span>
        )}
      </div>

      {suggestions.length > 0 && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            flexWrap: "wrap",
            background: "var(--color-surface-soft)",
            padding: "8px 12px",
            borderRadius: "var(--radius-md)",
            border: "1px dashed var(--color-hairline-strong)",
          }}
        >
          <span style={{ fontSize: 12, color: "var(--color-muted)", fontWeight: 600 }}>
            추천 태그:
          </span>
          {suggestions.map((tag) => (
            <button
              key={tag}
              type="button"
              onClick={() => onAccept([tag])}
              style={{
                fontSize: 12,
                padding: "2px 8px",
                borderRadius: "var(--radius-full)",
                background: "var(--color-primary-bg)",
                color: "var(--color-primary)",
                border: "1px solid var(--color-primary-disabled)",
                cursor: "pointer",
                fontWeight: 600,
                transition: "all 0.1s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "var(--color-primary)";
                e.currentTarget.style.color = "var(--color-on-primary)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "var(--color-primary-bg)";
                e.currentTarget.style.color = "var(--color-primary)";
              }}
            >
              ＋ {tag}
            </button>
          ))}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => onAccept(suggestions)}
            style={{
              fontSize: 11,
              marginLeft: "auto",
              color: "var(--color-primary)",
              fontWeight: 700,
            }}
          >
            모두 추가 (Accept All)
          </Button>
        </div>
      )}
    </div>
  );
}
