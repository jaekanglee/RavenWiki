import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

/**
 * SearchBar — pill-shaped (search-bar-pill token).
 * 9999px radius, 64px height, hairline + shadow border.
 * Single Rausch "search orb" button on the right.
 *
 * ARIA combobox with full keyboard navigation + touch selection.
 */
export function SearchBar({
  vault,
  onSelect,
}: {
  vault: string;
  onSelect?: (slug: string) => void;
}) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [focused, setFocused] = useState(false);
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const listboxId = `search-results-${vault}`;

  // Reset activeIndex whenever query changes.
  useEffect(() => {
    setActiveIndex(null);
  }, [q]);

  // `open` = focused AND has results.
  useEffect(() => {
    setOpen(focused && results.length > 0);
  }, [focused, results.length]);

  // Outside pointerdown closes dropdown.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      const root = rootRef.current;
      if (root && !root.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [open]);

  // Document-level Escape closes dropdown (in addition to the input handler).
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        setActiveIndex(null);
        inputRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  // Debounced fetch with AbortController.
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

  const selectResult = (slug: string) => {
    if (onSelect) onSelect(slug);
    else navigate(`/page/${slug}`);
    setQ("");
    setActiveIndex(null);
    setOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      if (results.length === 0) return;
      e.preventDefault();
      setActiveIndex((i) => (i === null ? 0 : (i + 1) % results.length));
    } else if (e.key === "ArrowUp") {
      if (results.length === 0) return;
      e.preventDefault();
      setActiveIndex((i) =>
        i === null ? results.length - 1 : (i - 1 + results.length) % results.length
      );
    } else if (e.key === "Home") {
      if (results.length === 0) return;
      e.preventDefault();
      setActiveIndex(0);
    } else if (e.key === "End") {
      if (results.length === 0) return;
      e.preventDefault();
      setActiveIndex(results.length - 1);
    } else if (e.key === "Enter") {
      if (activeIndex !== null && results[activeIndex]) {
        e.preventDefault();
        selectResult(results[activeIndex].slug);
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      setOpen(false);
      setActiveIndex(null);
    }
  };

  return (
    <div ref={rootRef} className="relative w-full">
      <div
        className="search-bar-pill"
        style={{
          display: "flex",
          alignItems: "center",
          height: 64,
          background: "var(--color-canvas)",
          border: focused
            ? "2px solid var(--color-ink)"
            : "1px solid var(--color-hairline-strong)",
          borderRadius: "var(--radius-full)",
          boxShadow: focused
            ? "var(--shadow-card)"
            : "0 1px 2px rgba(0,0,0,0.04)",
          padding: "0 6px 0 24px",
          transition: "border-color 0.12s ease, box-shadow 0.12s ease",
        }}
      >
        <input
          ref={inputRef}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onKeyDown={handleKeyDown}
          placeholder={`${vault}에서 검색…`}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls={listboxId}
          aria-activedescendant={
            activeIndex !== null
              ? `search-opt-${vault}-${activeIndex}`
              : undefined
          }
          inputMode="search"
          enterKeyHint="search"
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
          style={{
            flex: 1,
            minWidth: 0,
            border: "none",
            outline: "none",
            background: "transparent",
            fontSize: 15,
            color: "var(--color-ink)",
            fontFamily: "inherit",
          }}
        />
        <button
          aria-label="검색"
          style={{
            width: 48,
            height: 48,
            borderRadius: "var(--radius-full)",
            background: "var(--color-primary)",
            color: "var(--color-on-primary)",
            border: "none",
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 18,
            flexShrink: 0,
          }}
        >
          🔎
        </button>
      </div>

      {open && (
        <ul
          id={listboxId}
          role="listbox"
          style={{
            position: "absolute",
            width: "100%",
            marginTop: 8,
            background: "var(--color-canvas)",
            border: "1px solid var(--color-hairline)",
            borderRadius: "var(--radius-md)",
            boxShadow: "var(--shadow-card)",
            zIndex: 10,
            maxHeight: 384,
            overflowY: "auto",
            padding: 8,
            listStyle: "none",
          }}
        >
          {results.map((r, i) => {
            const isActive = activeIndex === i;
            return (
              <li
                key={r.slug}
                id={`search-opt-${vault}-${i}`}
                role="option"
                aria-selected={isActive}
                onPointerDown={(e) => {
                  e.preventDefault();
                  selectResult(r.slug);
                }}
                onClick={() => selectResult(r.slug)}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.background =
                    "var(--color-surface-soft)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.background = isActive
                    ? "var(--color-surface-soft)"
                    : "transparent";
                }}
                style={{
                  padding: "10px 12px",
                  cursor: "pointer",
                  fontSize: 14,
                  borderRadius: 8,
                  background: isActive
                    ? "var(--color-surface-soft)"
                    : "transparent",
                }}
              >
                <div style={{ fontWeight: 500, color: "var(--color-ink)" }}>
                  {r.title}
                </div>
                <div
                  style={{
                    fontSize: 12,
                    color: "var(--color-muted)",
                    marginTop: 2,
                  }}
                >
                  {r.type} · score {r.score}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
