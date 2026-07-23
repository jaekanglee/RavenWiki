/**
 * CommandPalette — Cmd+K 글로벌 커맨드 팔레트 (P0-2).
 *
 * Obsidian 벤치마크: 페이지 검색 + 섹션 이동을 하나의 팔레트에서.
 * 상단 중앙 패널, fuzzy match, 키보드 네비게이션.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchPages } from "../lib/api";
import type { Page } from "../types";

// ── 섹션 액션 (GLOBAL_NAV 미러) ──
const SECTIONS = [
  { label: "홈", icon: "🏠", to: "/" },
  { label: "그래프", icon: "🕸", to: "/graph" },
  { label: "검색", icon: "🔍", to: "/search" },
  { label: "로그", icon: "📋", to: "/log" },
  { label: "린트", icon: "🛠", to: "/lint" },
  { label: "정원", icon: "🌱", to: "/garden" },
  { label: "워크스페이스", icon: "💻", to: "/workspace" },
  { label: "관리", icon: "⚙", to: "/vault/manage" },
  { label: "보관함", icon: "🗄", to: "/archive" },
];

interface PaletteItem {
  id: string;
  label: string;
  icon: string;
  hint?: string;
  action: () => void;
}

/** Simple fuzzy: query chars appear in order within target. */
function fuzzyMatch(query: string, target: string): boolean {
  const q = query.toLowerCase();
  const t = target.toLowerCase();
  if (!q) return true;
  let qi = 0;
  for (let ti = 0; ti < t.length && qi < q.length; ti++) {
    if (t[ti] === q[qi]) qi++;
  }
  return qi === q.length;
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  vault: string;
}

export function CommandPalette({ open, onClose, vault }: CommandPaletteProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [pages, setPages] = useState<Page[]>([]);
  const [selected, setSelected] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // ── 페이지 로드 (팔레트 열릴 때) ──
  useEffect(() => {
    if (!open || !vault) return;
    setQuery("");
    setSelected(0);
    fetchPages(vault).then((p: Page[]) => setPages(p)).catch(() => setPages([]));
  }, [open, vault]);

  // ── 포커스 ──
  useEffect(() => {
    if (open) {
      // 약간의 delay로 portal 렌더 후 포커스
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  // ── 결과 계산 ──
  const items = useMemo<PaletteItem[]>(() => {
    const out: PaletteItem[] = [];

    // 섹션 (항상 표시, query로 필터)
    for (const s of SECTIONS) {
      if (fuzzyMatch(query, s.label)) {
        out.push({
          id: `sec:${s.to}`,
          label: s.label,
          icon: s.icon,
          hint: "섹션",
          action: () => { navigate(s.to); onClose(); },
        });
      }
    }

    // 페이지 (query 있을 때만, 최대 20개)
    if (query) {
      const matched = pages.filter(
        (p) => fuzzyMatch(query, p.title) || fuzzyMatch(query, p.slug)
      );
      for (const p of matched.slice(0, 20)) {
        out.push({
          id: `page:${p.slug}`,
          label: p.title,
          icon: "📄",
          hint: p.type || p.slug,
          action: () => { navigate(`/page/${vault}/${p.slug}`); onClose(); },
        });
      }
    }

    return out;
  }, [query, pages, navigate, onClose, vault]);

  // ── 선택 인덱스 clamp ──
  useEffect(() => {
    setSelected((s) => Math.min(s, Math.max(0, items.length - 1)));
  }, [items.length]);

  // ── 키보드 ──
  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelected((s) => Math.min(s + 1, items.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelected((s) => Math.max(s - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        items[selected]?.action();
      } else if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    },
    [items, selected, onClose]
  );

  // ── 선택 행 스크롤 ──
  useEffect(() => {
    const el = listRef.current?.children[selected] as HTMLElement | undefined;
    el?.scrollIntoView({ block: "nearest" });
  }, [selected]);

  if (!open) return null;

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "var(--color-overlay)",
        display: "flex",
        justifyContent: "center",
        alignItems: "flex-start",
        paddingTop: "15vh",
        zIndex: 100,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="card"
        style={{
          width: "100%",
          maxWidth: 560,
          padding: 0,
          overflow: "hidden",
          borderRadius: "var(--radius-md, 10px)",
          boxShadow: "0 16px 48px rgba(0,0,0,0.25)",
        }}
      >
        {/* ── 입력 ── */}
        <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--color-hairline)" }}>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelected(0); }}
            onKeyDown={onKeyDown}
            placeholder="페이지 검색 또는 섹션 이동…"
            style={{
              width: "100%",
              border: "none",
              outline: "none",
              background: "transparent",
              fontSize: 15,
              color: "var(--color-ink)",
            }}
            aria-label="커맨드 팔레트 검색"
          />
        </div>

        {/* ── 결과 목록 ── */}
        <div ref={listRef} style={{ maxHeight: 320, overflowY: "auto", padding: "4px 0" }}>
          {items.length === 0 && (
            <p style={{ padding: "16px", textAlign: "center", color: "var(--color-muted)", fontSize: 13 }}>
              결과 없음
            </p>
          )}
          {items.map((item, i) => (
            <div
              key={item.id}
              onClick={() => item.action()}
              onMouseEnter={() => setSelected(i)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "8px 16px",
                cursor: "pointer",
                background: i === selected ? "var(--color-surface-soft)" : "transparent",
              }}
            >
              <span style={{ fontSize: 15, flexShrink: 0 }}>{item.icon}</span>
              <span style={{ flex: 1, fontSize: 14, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {item.label}
              </span>
              {item.hint && (
                <span style={{ fontSize: 11, color: "var(--color-muted)", flexShrink: 0 }}>
                  {item.hint}
                </span>
              )}
            </div>
          ))}
        </div>

        {/* ── 푸터 힌트 ── */}
        <div
          style={{
            padding: "8px 16px",
            borderTop: "1px solid var(--color-hairline)",
            fontSize: 11,
            color: "var(--color-muted)",
            display: "flex",
            gap: 12,
          }}
        >
          <span>↑↓ 이동</span>
          <span>↵ 선택</span>
          <span>esc 닫기</span>
        </div>
      </div>
    </div>
  );
}
