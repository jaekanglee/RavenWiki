import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { SearchResultItem } from "./SearchResultItem";
import { useHybridSearch } from "../lib/useHybridSearch";

/**
 * SearchBar — pill-shaped (search-bar-pill token).
 * 9999px radius, header 64px / sidebar 40px height, hairline + shadow border.
 * Single Rausch "search orb" button on the right.
 *
 * ARIA combobox with full keyboard navigation + touch selection.
 *
 * v0.7.69+: 220ms debounce 통일 (SearchPage와 동일). useDebounced hook 사용 —
 * §13 재사용 hook 추출. IME 조합 중 / 빠른 typing 시 /api/vaults/{}/search 폭주 방지.
 *
 * v0.7.97+: variant prop. header (default, 64px) / sidebar (40px) — 헤더 그룹화
 * 사이클에서 검색을 사이드바로 이관하면서 추가. dropdown combobox 동작은 동일.
 */
export function SearchBar({
  vault,
  onSelect,
  variant = "header",
}: {
  vault: string;
  onSelect?: (slug: string) => void;
  variant?: "header" | "sidebar";
}) {
  const [q, setQ] = useState("");
  const [focused, setFocused] = useState(false);
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // v0.7.201+: PropertiesPanel 연결 문서 검색과 동일한 hybrid-search 결과를
  // 공유 (§A 검색 로직 통합, 2026-07-10 스펙) — 중복 fetch/debounce 제거.
  const results = useHybridSearch(vault, q, { limit: 8 });

  const listboxId = `search-results-${vault}`;
  // v0.7.97+: variant별 사이즈 토큰.
  const SIZE = variant === "sidebar"
    ? { height: 40, btn: 36, fontSize: 14, paddingX: 16, btnFont: 16 }
    : { height: 64, btn: 48, fontSize: 15, paddingX: 24, btnFont: 18 };

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

  const selectResult = (slug: string) => {
    if (onSelect) onSelect(slug);
    else navigate(`/page/${vault}/${slug}`);
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
          height: SIZE.height,
          background: "var(--color-canvas)",
          border: focused
            ? "2px solid var(--color-ink)"
            : "1px solid var(--color-hairline-strong)",
          borderRadius: "var(--radius-full)",
          boxShadow: focused
            ? "var(--shadow-card)"
            : "0 1px 2px var(--shadow-base)",
          padding: `0 6px 0 ${SIZE.paddingX}px`,
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
            fontSize: SIZE.fontSize,
            color: "var(--color-ink)",
            fontFamily: "inherit",
          }}
        />
        <button
          aria-label="검색"
          style={{
            width: SIZE.btn,
            height: SIZE.btn,
            borderRadius: "var(--radius-full)",
            background: "var(--color-primary)",
            color: "var(--color-on-primary)",
            border: "none",
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: SIZE.btnFont,
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
              <SearchResultItem
                key={r.slug}
                vault={vault}
                result={r}
                compact
                interactive
                active={isActive}
                optionId={`search-opt-${vault}-${i}`}
                onSelect={() => selectResult(r.slug)}
                onMouseEnter={() => setActiveIndex(i)}
                onMouseLeave={() => {
                  if (activeIndex === i) setActiveIndex(null);
                }}
              />
            );
          })}
        </ul>
      )}
    </div>
  );
}
