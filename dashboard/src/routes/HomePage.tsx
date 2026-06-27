import { Link, useNavigate } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import type { Page } from "../types";

/**
 * HomePage — v0.6.4: "vault 운영 콘솔" 3영역 재구성.
 *
 * Desktop (≥745px):
 *   ┌──────────────────────────────────────────────────────────┐
 *   │  Hero (h1 + vault 요약)                                 │
 *   │  ┌─────────┐                                            │
 *   │  │ Quick   │  4 large action cards (2x2):                │
 *   │  │ Actions │  · Search  · New page                      │
 *   │  │ (left)  │  · Graph   · Digest                        │
 *   │  └─────────┘                                            │
 *   ├──────────────────────────────────────────────────────────┤
 *   │  Recent pages (3-col grid)                              │
 *   └──────────────────────────────────────────────────────────┘
 *
 * Mobile (≤744px):
 *   ┌──────────────────┐
 *   │  Hero (compact)  │
 *   │  Quick actions   │  ← full-width 2-col grid (2x2)
 *   │  Recent pages    │  ← 1-col stack (larger tap targets)
 *   └──────────────────┘
 *
 * Mobile pain 해소: 검색·새페이지·그래프·디제스트 모두 1-tap 도달.
 * (Sidebar 진입 2-tap 회피.)
 *
 * "안정적이고 심플" 원칙 준수: 새 라우트/상태 0, 기존 Sidebar 그대로.
 */

interface VaultSummary {
  name: string;
  path: string;
  default: boolean;
}

interface QuickAction {
  to: string;
  label: string;
  description: string;
  icon: string;
  primary?: boolean;
}

const ACTIONS: QuickAction[] = [
  {
    to: "/search",
    label: "검색",
    description: "vault 전체에서 BM25 검색",
    icon: "🔍",
  },
  {
    to: "/vault/new",
    label: "새 페이지",
    description: "지금 만드는 마크다운 페이지",
    icon: "✚",
    primary: true,
  },
  {
    to: "/graph",
    label: "그래프",
    description: "vault 페이지 연결 관계",
    icon: "⬡",
  },
  {
    to: "/digest",
    label: "디제스트",
    description: "오늘 vault 운영 요약",
    icon: "◐",
  },
];

// 744px = Layout 모바일 breakpoint와 일치.
const MOBILE_MQ = "(max-width: 744px)";

export function HomePage() {
  const [index, setIndex] = useState<Page[]>([]);
  const [vault, setVault] = useState<VaultSummary | null>(null);
  const [isMobile, setIsMobile] = useState(false);
  const navigate = useNavigate();

  // ─── data fetch ────────────────────────────────────────
  useEffect(() => {
    fetch("/api/index.json")
      .then((r) => (r.ok ? r.json() : []))
      .then(setIndex)
      .catch(() => setIndex([]));

    fetch("/api/vaults")
      .then((r) => (r.ok ? r.json() : { vaults: [] }))
      .then((d) => {
        const def = d.vaults?.find((v: VaultSummary) => v.default) || d.vaults?.[0];
        setVault(def || null);
      })
      .catch(() => setVault(null));
  }, []);

  // ─── viewport ────────────────────────────────────────
  useEffect(() => {
    const mql = window.matchMedia(MOBILE_MQ);
    setIsMobile(mql.matches);
    const onChange = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  // ─── derivations ──────────────────────────────────────
  const recent = useMemo(
    () =>
      [...index]
        .sort((a, b) => String(b.updated).localeCompare(String(a.updated)))
        .slice(0, isMobile ? 8 : 12),
    [index, isMobile]
  );
  const types = useMemo(
    () => Array.from(new Set(index.map((p) => p.type))).filter(Boolean),
    [index]
  );

  return (
    <div style={{ maxWidth: 1120 }}>
      {/* ─── Hero ──────────────────────────────────────────── */}
      <section
        style={{
          paddingTop: isMobile ? 8 : 16,
          paddingBottom: isMobile ? 24 : 48,
        }}
      >
        <h1 style={{ marginBottom: 8, fontSize: isMobile ? 22 : 28 }}>
          {vault ? vault.name : "Wiki"}
        </h1>
        <p
          className="text-body"
          style={{
            fontSize: isMobile ? 14 : 16,
            maxWidth: 640,
            color: "var(--color-muted)",
            margin: 0,
          }}
        >
          {index.length === 0
            ? "아직 페이지가 없음. 새 페이지를 만들어보세요."
            : `전체 ${index.length}개 페이지 · ${types.length}개 타입 · ${vault?.path ?? "—"}`}
        </p>
      </section>

      {/* ─── Quick actions (2x2 grid; mobile & desktop) ──────── */}
      <section style={{ paddingBottom: isMobile ? 24 : 40 }}>
        <h2
          style={{
            fontSize: 14,
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.32px",
            color: "var(--color-muted)",
            marginBottom: 16,
          }}
        >
          빠른 액션
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: isMobile
              ? "repeat(2, 1fr)"
              : "repeat(4, 1fr)",
            gap: 12,
          }}
        >
          {ACTIONS.map((a) => (
            <ActionCard key={a.to} action={a} isMobile={isMobile} />
          ))}
        </div>
      </section>

      {/* ─── Recent pages ──────────────────────────────────── */}
      <section style={{ paddingBottom: 64 }}>
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            justifyContent: "space-between",
            marginBottom: 16,
          }}
        >
          <h2 style={{ fontSize: 18 }}>최근 수정</h2>
          <Link
            to="/search"
            className="link-muted"
            style={{ fontSize: 13 }}
          >
            전체 검색 →
          </Link>
        </div>

        {recent.length === 0 ? (
          <p className="text-muted">아직 페이지가 없음</p>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: isMobile
                ? "1fr"
                : "repeat(auto-fill, minmax(280px, 1fr))",
              gap: 12,
            }}
          >
            {recent.map((p) => (
              <RecentCard
                key={p.slug}
                page={p}
                isMobile={isMobile}
                onOpen={() => navigate(`/page/${p.slug}`)}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

// ────────────────────────── sub-components ────────────────────────

function ActionCard({
  action,
  isMobile,
}: {
  action: QuickAction;
  isMobile: boolean;
}) {
  // 모바일: 44px 이상 tap target (Apple HIG / Material).
  // 데스크탑: 기존 card-flat hover 유지.
  const base: CSSProperties = {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
    textAlign: "left",
    padding: isMobile ? 16 : 20,
    background: "var(--cds-field-01, #fff)",
    border: "1px solid var(--cds-border-subtle-01, #e0e0e0)",
    borderRadius: 8,
    minHeight: isMobile ? 88 : 96,
    color: "var(--color-ink)",
    textDecoration: "none",
    cursor: "pointer",
    transition: "box-shadow 0.12s ease, transform 0.12s ease, border-color 0.12s ease",
  };
  if (action.primary) {
    base.borderColor = "var(--color-primary, #1c69d4)";
    base.background = "var(--cds-background-brand, #f4f7fc)";
  }
  return (
    <Link
      to={action.to}
      style={base}
      onMouseEnter={(e) => {
        if (isMobile) return;
        const el = e.currentTarget as HTMLElement;
        el.style.boxShadow = "var(--shadow-card, 0 2px 6px rgba(0,0,0,0.08))";
        el.style.transform = "translateY(-1px)";
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget as HTMLElement;
        el.style.boxShadow = "none";
        el.style.transform = "none";
      }}
    >
      <div
        style={{
          fontSize: isMobile ? 20 : 22,
          marginBottom: 6,
          lineHeight: 1,
        }}
        aria-hidden
      >
        {action.icon}
      </div>
      <div
        style={{
          fontSize: isMobile ? 14 : 15,
          fontWeight: 600,
          marginBottom: 2,
        }}
      >
        {action.label}
      </div>
      <div
        style={{
          fontSize: 11,
          color: "var(--color-muted)",
          lineHeight: 1.3,
        }}
      >
        {action.description}
      </div>
    </Link>
  );
}

function RecentCard({
  page,
  isMobile,
  onOpen,
}: {
  page: Page;
  isMobile: boolean;
  onOpen: () => void;
}) {
  return (
    <Link
      to={`/page/${page.slug}`}
      onClick={(e) => {
        // 모바일에서 nav-bar 없는 경우 카드 전체가 tap target.
        // onOpen은 click default 동작으로 충분하므로 별도 처리 없음.
        if (isMobile) e.preventDefault();
        onOpen();
      }}
      className="card-flat"
      style={{
        display: "block",
        textDecoration: "none",
        padding: isMobile ? 16 : 18,
        minHeight: isMobile ? 64 : undefined,
        borderRadius: 8,
        transition: "box-shadow 0.12s ease, transform 0.12s ease",
      }}
      onMouseEnter={(e) => {
        if (isMobile) return;
        const el = e.currentTarget as HTMLElement;
        el.style.boxShadow = "var(--shadow-card, 0 2px 6px rgba(0,0,0,0.08))";
        el.style.transform = "translateY(-1px)";
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget as HTMLElement;
        el.style.boxShadow = "none";
        el.style.transform = "none";
      }}
    >
      <div
        style={{
          display: "flex",
          gap: 8,
          marginBottom: 8,
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        <span className="chip">{page.type}</span>
        {page.updated && (
          <span
            style={{
              fontSize: 11,
              color: "var(--color-muted)",
              fontFamily: "ui-monospace, SFMono-Regular, monospace",
            }}
          >
            {String(page.updated).slice(0, 10)}
          </span>
        )}
      </div>
      <div
        style={{
          fontSize: isMobile ? 15 : 16,
          fontWeight: 600,
          color: "var(--color-ink)",
          marginBottom: 4,
          lineHeight: 1.3,
        }}
      >
        {page.title}
      </div>
      <div
        style={{
          fontSize: 12,
          color: "var(--color-muted)",
          fontFamily: "ui-monospace, SFMono-Regular, monospace",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {page.path}
      </div>
    </Link>
  );
}
