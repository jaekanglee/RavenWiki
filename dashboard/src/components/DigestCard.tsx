import type { ReactNode } from "react";

/**
 * DigestCard — Dashboard digest 페이지의 section 카드 atom.
 *
 * BMW + Carbon 디자인 시스템:
 *   - background: cds-layer-01 (surface-soft, surface layering)
 *   - border: cds-border-subtle (1px hairline)
 *   - radius: radius-lg (12px, Carbon 식)
 *   - padding: 20px (16–24px 사이, digest 정보 밀도 고려)
 *   - title: 11px uppercase / 700 / 0.32px letter-spacing (label tone)
 *   - value: 24–28px / 700 ink
 *
 * 상단 right slot 으로 quick action (filter chip 등) 가능.
 */
export function DigestCard({
  label,
  title,
  accent = false,
  right,
  children,
}: {
  label: string;          // uppercase label (e.g. "TODAY", "THIS WEEK")
  title?: string;         // optional secondary headline
  accent?: boolean;       // 강조 (Rausch blue tint) — critical 상태 등
  right?: ReactNode;      // optional top-right action slot
  children: ReactNode;    // card body
}) {
  return (
    <section
      className="digest-card"
      style={{
        background: accent ? "var(--cds-tag-blue-bg)" : "var(--cds-layer-01)",
        border: "1px solid var(--cds-border-subtle)",
        borderRadius: "var(--radius-lg)",
        padding: 20,
        display: "flex",
        flexDirection: "column",
        gap: 12,
        minHeight: 200,
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          gap: 8,
        }}
      >
        <div>
          <div
            style={{
              fontSize: 11,
              fontWeight: 700,
              letterSpacing: "0.32px",
              textTransform: "uppercase",
              color: accent ? "var(--color-primary)" : "var(--color-muted)",
              marginBottom: title ? 4 : 0,
            }}
          >
            {label}
          </div>
          {title && (
            <h3 style={{ fontSize: 16, fontWeight: 700, color: "var(--color-ink)" }}>
              {title}
            </h3>
          )}
        </div>
        {right && <div style={{ flexShrink: 0 }}>{right}</div>}
      </header>
      <div style={{ flex: 1, minWidth: 0 }}>{children}</div>
    </section>
  );
}