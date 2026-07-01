interface PageHeaderProps {
  title: string;
  subtitle?: string;
  contextLabel?: string;
  titleSize?: number;
  bottomSpacing?: number;
  meta?: React.ReactNode;
  actions?: React.ReactNode;
}

export function PageHeader({
  title,
  subtitle,
  contextLabel,
  titleSize = 28,
  bottomSpacing = 32,
  meta,
  actions,
}: PageHeaderProps) {
  return (
    <section style={{ marginBottom: bottomSpacing }}>
      <div
        style={{
          display: "flex",
          alignItems: "baseline",
          justifyContent: "space-between",
          gap: 16,
          flexWrap: "wrap",
          marginBottom: subtitle || meta ? 8 : 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
          <h1 style={{ margin: 0, fontSize: titleSize }}>{title}</h1>
          {contextLabel && (
            <span style={{ color: "var(--color-muted)", fontSize: 14 }}>{contextLabel}</span>
          )}
        </div>
        {actions}
      </div>
      {subtitle && (
        <p
          className="text-muted"
          style={{ fontSize: 14, marginTop: 0, marginBottom: meta ? 10 : 0, maxWidth: 720 }}
        >
          {subtitle}
        </p>
      )}
      {meta}
    </section>
  );
}
