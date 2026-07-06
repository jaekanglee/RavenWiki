import { Link, useNavigate } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import {
  fetchVaults,
  getActiveVault,
  setActiveVault as setActiveVaultLS,
  type VaultInfo,
} from "../lib/api";
import { NewPageInline } from "../components/NewPageInline";
import { Button } from "../components/ui/Button";
import { PageHeader } from "../components/ui/PageHeader";

/**
 * HomePage — v0.6.10 (P16): 종합 홈 (vault 미선택).
 *
 * 이전: HomePage가 useOutletContext<{vault}>로 활성 vault를 받아 그 vault
 *   한 곳의 페이지/통계만 표시 = "vault 운영 콘솔"로 동작.
 * 변경: Home = "vault를 선택하거나 새로 만드는 곳"으로 재정의.
 *   - 활성 vault에 의존 ❌ (outlet context 무시)
 *   - 모든 vault 카드 리스트 (GET /api/vaults + 각 stats)
 *   - hero: "vault를 선택하거나 새로 만드세요"
 *   - Quick Actions는 vault 선택 시 활성화, 미선택 시 disabled + 안내
 *
 * Desktop (≥745px):
 *   ┌──────────────────────────────────────────────────────────┐
 *   │  Hero: "Raven — vault를 선택하거나 새로 만드세요"        │
 *   │  Quick Actions (4-up grid; 미선택 vault 시 disabled)    │
 *   ├──────────────────────────────────────────────────────────┤
 *   │  Vaults (3-col grid of cards)                           │
 *   │   · 각 카드: 이름, 모드, 페이지 수, 깨진 링크, 로그     │
 *   │   · 클릭 → /vault/manage 또는 /page/<vault>/content/.. │
 *   └──────────────────────────────────────────────────────────┘
 *
 * Mobile (≤744px): 1-col stack.
 */

interface VaultStats {
  ok: boolean;
  vault: string;
  pages: number;
  size_bytes: number;
  log_entries: number;
  broken_links: number;
}

interface VaultWithStats {
  meta: VaultInfo;
  stats: VaultStats | null;
  statsError?: string;
}

// VaultMeta = VaultInfo (lib/api의 정식 이름 사용)
type VaultMeta = VaultInfo;

interface QuickAction {
  to: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  primary?: boolean;
  requiresVault?: boolean;
}

// Lucide-style SVG icons (v0.7.69+): 이모지 ❌ (OS별 렌더링 차이, 다크모드 깨짐)
// → inline SVG (currentColor → var(--color-ink) 자동 적용, hover 시 var(--color-accent)).
// InlineMarkdownEditor Icon 패턴과 동일 — 24x24 viewBox, stroke 2.
const ActionIcon = {
  Search: () => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true">
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  ),
  Plus: () => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true">
      <path d="M12 5v14" />
      <path d="M5 12h14" />
    </svg>
  ),
  Graph: () => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true">
      <circle cx="6" cy="6" r="3" />
      <circle cx="18" cy="6" r="3" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="18" cy="18" r="3" />
      <path d="M8.5 7.5 15.5 16.5" />
      <path d="M15.5 7.5 8.5 16.5" />
      <path d="M9 6h6" />
      <path d="M9 18h6" />
    </svg>
  ),
  Digest: () => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
      aria-hidden="true">
      <path d="M12 2a10 10 0 1 0 10 10" />
      <path d="M12 6v6l4 2" />
    </svg>
  ),
};

const ACTIONS: QuickAction[] = [
  {
    to: "/search",
    label: "검색",
    description: "활성 vault 전체 BM25",
    icon: <ActionIcon.Search />,
    requiresVault: true,
  },
  {
    to: "/vault/new",
    label: "새 vault",
    description: "지금 만드는 새 vault",
    icon: <ActionIcon.Plus />,
    primary: true,
  },
  {
    to: "/graph",
    label: "그래프",
    description: "vault 페이지 연결",
    icon: <ActionIcon.Graph />,
    requiresVault: true,
  },
  {
    to: "/digest",
    label: "디제스트",
    description: "오늘 vault 운영 요약",
    icon: <ActionIcon.Digest />,
    requiresVault: true,
  },
];

// Plan v1 묶음 B: "새 페이지" Quick Action — onClick으로 인라인 폼을 토글한다.
interface NewPageAction {
  kind: "new-page";
  label: string;
  description: string;
  icon: string;
  requiresVault: true;
}

const MOBILE_MQ = "(max-width: 744px)";

export function HomePage() {
  const [vaults, setVaults] = useState<VaultWithStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeVault, setActiveVault] = useState<string | null>(null);
  const [isMobile, setIsMobile] = useState(false);
  // Plan v1 묶음 B (Tasks 5-7): 인라인 폼 트리거.
  const [showNewPageForm, setShowNewPageForm] = useState(false);
  const navigate = useNavigate();

  // ─── viewport ────────────────────────────────────────
  useEffect(() => {
    const mql = window.matchMedia(MOBILE_MQ);
    setIsMobile(mql.matches);
    const onChange = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, []);

  // ─── data fetch: vaults + per-vault stats ─────────────
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    (async () => {
      const metas = await fetchVaults();
      if (cancelled) return;
      // active vault: localStorage(Sidebar/VaultPicker 동기화) → default → first
      const stored = getActiveVault();
      const active =
        (stored && metas.find((v) => v.name === stored)?.name) ||
        metas.find((v) => v.default)?.name ||
        metas[0]?.name ||
        null;
      setActiveVault(active);
      // stats fetch in parallel
      const enriched = await Promise.all(
        metas.map(async (meta): Promise<VaultWithStats> => {
          try {
            const r = await fetch(
              `/api/vaults/${encodeURIComponent(meta.name)}/stats`
            );
            if (!r.ok) {
              return { meta, stats: null, statsError: `HTTP ${r.status}` };
            }
            const s = (await r.json()) as VaultStats;
            return { meta, stats: s };
          } catch (e: any) {
            return { meta, stats: null, statsError: e?.message ?? "fetch error" };
          }
        })
      );
      if (cancelled) return;
      setVaults(enriched);
      setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const sorted = useMemo(
    () =>
      [...vaults].sort((a, b) => {
        // default first, then by name
        if (a.meta.default !== b.meta.default) return a.meta.default ? -1 : 1;
        return a.meta.name.localeCompare(b.meta.name);
      }),
    [vaults]
  );

  return (
    <div style={{ maxWidth: 1120 }}>
      {/* ─── Hero ──────────────────────────────────────────── */}
      <section
        style={{
          paddingTop: isMobile ? 8 : 16,
          paddingBottom: isMobile ? 24 : 40,
        }}
      >
        <PageHeader
          title="🐦 Raven"
          titleSize={isMobile ? 22 : 30}
          bottomSpacing={0}
          subtitle={
            loading
              ? "vault 목록을 불러오는 중…"
              : vaults.length === 0
              ? "아직 등록된 vault가 없습니다. 새 vault를 만들어 시작하세요."
              : activeVault
              ? `vault를 선택하거나 새로 만드세요. 현재 활성: ${activeVault}`
              : "vault를 선택하거나 새로 만드세요."
          }
        />
      </section>

      {/* ─── Quick actions ─────────────────────────────────── */}
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
            <ActionCard
              key={a.to}
              action={a}
              isMobile={isMobile}
              disabled={Boolean(a.requiresVault) && !activeVault}
            />
          ))}
          {/* 묶음 B: "새 페이지" 카드 — 클릭 시 인라인 폼 토글. */}
          <NewPageCard
            isMobile={isMobile}
            disabled={!activeVault}
            active={showNewPageForm}
            onToggle={() => setShowNewPageForm((v) => !v)}
          />
        </div>
        {!activeVault && vaults.length > 0 && (
          <p
            className="text-muted"
            style={{ fontSize: 12, marginTop: 12, marginBottom: 0 }}
          >
            💡 vault를 선택하면 검색·그래프·디제스트가 활성화됩니다.
          </p>
        )}
      </section>

      {/* ─── Inline new-page form (묶음 B, Tasks 5-7) ─────── */}
      {showNewPageForm && activeVault && (
        <NewPageInline
          vault={activeVault}
          onClose={() => setShowNewPageForm(false)}
        />
      )}

      {/* ─── Vaults ────────────────────────────────────────── */}
      <section style={{ paddingBottom: 64 }}>
        <div
          style={{
            display: "flex",
            alignItems: "baseline",
            justifyContent: "space-between",
            marginBottom: 16,
          }}
        >
          <h2 style={{ fontSize: 18 }}>
            보관소{" "}
            <span
              className="text-muted"
              style={{ fontSize: 13, fontWeight: 400 }}
            >
              ({sorted.length})
            </span>
          </h2>
          <Link
            to="/vault/manage"
            className="link-muted"
            style={{ fontSize: 13 }}
          >
            vault 관리 →
          </Link>
        </div>

        {loading ? (
          <p className="text-muted">불러오는 중…</p>
        ) : sorted.length === 0 ? (
          <div className="card-flat" style={{ padding: 24, borderRadius: 8 }}>
            <p className="text-muted" style={{ marginBottom: 12 }}>
              등록된 vault가 없습니다.
            </p>
            <Link
              to="/vault/new"
              className="btn-pill-primary"
              style={{ display: "inline-flex", alignItems: "center", gap: 6 }}
            >
              <ActionIcon.Plus />첫 vault 만들기
            </Link>
          </div>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: isMobile
                ? "1fr"
                : "repeat(auto-fill, minmax(300px, 1fr))",
              gap: 12,
            }}
          >
            {sorted.map((v) => (
              <VaultCard
                key={v.meta.name}
                v={v}
                isMobile={isMobile}
                isActive={v.meta.name === activeVault}
                onOpen={async () => {
                  setActiveVaultLS(v.meta.name);
                  setActiveVault(v.meta.name);
                  // 옛 vault는 content/index 없음. 첫 페이지 또는 manage로 fallback.
                  try {
                    const r = await fetch(
                      `/api/vaults/${encodeURIComponent(v.meta.name)}/pages?top_k=1`
                    );
                    const d = await r.json();
                    const slug = d?.pages?.[0]?.slug;
                    if (slug) {
                      navigate(`/page/${encodeURIComponent(v.meta.name)}/${slug}`);
                    } else {
                      navigate(`/vault/manage`);
                    }
                  } catch {
                    navigate(`/vault/manage`);
                  }
                }}
                onManage={() => navigate("/vault/manage")}
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
  disabled,
}: {
  action: QuickAction;
  isMobile: boolean;
  disabled: boolean;
}) {
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
    cursor: disabled ? "not-allowed" : "pointer",
    transition:
      "box-shadow 0.12s ease, transform 0.12s ease, border-color 0.12s ease",
    opacity: disabled ? 0.45 : 1,
    pointerEvents: disabled ? "none" : "auto",
  };
  if (action.primary) {
    base.borderColor = "var(--color-primary)";
    base.background = "var(--cds-background-brand, #f4f7fc)";
  }
  return (
    <Link
      to={action.to}
      style={base}
      aria-disabled={disabled || undefined}
      onClick={(e) => {
        if (disabled) e.preventDefault();
      }}
      onMouseEnter={(e) => {
        if (isMobile || disabled) return;
        const el = e.currentTarget as HTMLElement;
        el.style.boxShadow = "var(--shadow-card)";
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

function VaultCard({
  v,
  isMobile,
  isActive,
  onOpen,
  onManage,
}: {
  v: VaultWithStats;
  isMobile: boolean;
  isActive: boolean;
  onOpen: () => void;
  onManage: () => void;
}) {
  const s = v.stats;
  const bytesKb = s ? Math.max(1, Math.round(s.size_bytes / 1024)) : null;
  return (
    <div
      className="card-flat"
      style={{
        padding: isMobile ? 16 : 18,
        borderRadius: 8,
        display: "flex",
        flexDirection: "column",
        gap: 10,
        border: isActive
          ? "1.5px solid var(--color-primary)"
          : undefined,
        transition:
          "box-shadow 0.12s ease, transform 0.12s ease, border-color 0.12s ease",
      }}
      onMouseEnter={(e) => {
        if (isMobile) return;
        const el = e.currentTarget as HTMLElement;
        el.style.boxShadow = "var(--shadow-card)";
        el.style.transform = "translateY(-1px)";
      }}
      onMouseLeave={(e) => {
        const el = e.currentTarget as HTMLElement;
        el.style.boxShadow = "none";
        el.style.transform = "none";
      }}
    >
      {/* header: name + badge */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            fontSize: isMobile ? 16 : 17,
            fontWeight: 700,
            color: "var(--color-ink)",
          }}
        >
          {v.meta.name}
        </span>
        {v.meta.default && (
          <span
            className="chip"
            style={{ fontSize: 10, background: "var(--color-info-bg)", color: "var(--color-info-text)" }}
          >
            default
          </span>
        )}
        {isActive && (
          <span
            className="chip"
            style={{ fontSize: 10, background: "var(--color-success-bg)", color: "var(--color-success-text)" }}
          >
            active
          </span>
        )}
        <span
          className="chip"
          style={{
            fontSize: 10,
            marginLeft: "auto",
            background: "var(--color-surface-soft)",
            color: "var(--color-muted)",
          }}
        >
          {v.meta.mode}
        </span>
      </div>

      {/* path */}
      <div
        style={{
          fontSize: 11,
          color: "var(--color-muted)",
          fontFamily: "ui-monospace, SFMono-Regular, monospace",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {v.meta.path}
      </div>

      {/* stats row */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 8,
          marginTop: 4,
        }}
      >
        <Stat label="페이지" value={s ? s.pages : "—"} />
        <Stat
          label="깨진 링크"
          value={s ? s.broken_links : "—"}
          tone={s && s.broken_links > 0 ? "warn" : "default"}
        />
        <Stat
          label="용량"
          value={bytesKb !== null ? `${bytesKb} KB` : "—"}
          hint={s ? `${s.log_entries} log` : undefined}
        />
      </div>

      {v.statsError && (
        <div style={{ fontSize: 11, color: "var(--color-danger-text)" }}>
          stats 오류: {v.statsError}
        </div>
      )}

      {/* actions */}
      <div
        style={{
          display: "flex",
          gap: 8,
          marginTop: 6,
        }}
      >
        <Button variant="pillPrimary" onClick={onOpen} style={{ flex: 1, fontSize: 13 }}>
          열기
        </Button>
        <Button variant="pill" onClick={onManage} style={{ flex: 1, fontSize: 13 }}>
          관리
        </Button>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  tone = "default",
  hint,
}: {
  label: string;
  value: string | number;
  tone?: "default" | "warn";
  hint?: string;
}) {
  const color =
    tone === "warn" ? "var(--color-warning-text)" : "var(--color-ink, #161616)";
  return (
    <div
      style={{
        padding: "6px 8px",
        background: "var(--cds-background, #f4f4f4)",
        borderRadius: 4,
      }}
    >
      <div
        style={{
          fontSize: 10,
          color: "var(--color-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.3px",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 14,
          fontWeight: 700,
          color,
          lineHeight: 1.2,
        }}
      >
        {value}
      </div>
      {hint && (
        <div style={{ fontSize: 10, color: "var(--color-muted)" }}>
          {hint}
        </div>
      )}
    </div>
  );
}

// ─── 묶음 B: "새 페이지" Quick Action 카드 ──────────────────
// ActionCard와 동일 비주얼이지만 Link가 아닌 button — 클릭 시 인라인 폼 토글.
function NewPageCard({
  isMobile,
  disabled,
  active,
  onToggle,
}: {
  isMobile: boolean;
  disabled: boolean;
  active: boolean;
  onToggle: () => void;
}) {
  const base: CSSProperties = {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
    textAlign: "left",
    padding: isMobile ? 16 : 20,
    background: active
      ? "var(--cds-background-brand, #f4f7fc)"
      : "var(--cds-field-01, #fff)",
    border: active
      ? "1.5px solid var(--color-primary)"
      : "1px solid var(--cds-border-subtle-01, #e0e0e0)",
    borderRadius: 8,
    minHeight: isMobile ? 88 : 96,
    color: "var(--color-ink)",
    textDecoration: "none",
    cursor: disabled ? "not-allowed" : "pointer",
    transition:
      "box-shadow 0.12s ease, transform 0.12s ease, border-color 0.12s ease",
    opacity: disabled ? 0.45 : 1,
    pointerEvents: disabled ? "none" : "auto",
    fontFamily: "inherit",
    width: "100%",
  };
  return (
    <button
      type="button"
      style={base}
      aria-disabled={disabled || undefined}
      aria-pressed={active}
      onClick={() => {
        if (disabled) return;
        onToggle();
      }}
      onMouseEnter={(e) => {
        if (isMobile || disabled) return;
        const el = e.currentTarget as HTMLElement;
        el.style.boxShadow = "var(--shadow-card)";
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
        {active ? "✕" : "➕"}
      </div>
      <div
        style={{
          fontSize: isMobile ? 14 : 15,
          fontWeight: 600,
          marginBottom: 2,
        }}
      >
        {active ? "폼 닫기" : "새 페이지"}
      </div>
      <div
        style={{
          fontSize: 11,
          color: "var(--color-muted)",
          lineHeight: 1.3,
        }}
      >
        {active ? "인라인 폼이 열려 있습니다" : "인라인 폼으로 만들기"}
      </div>
    </button>
  );
}
