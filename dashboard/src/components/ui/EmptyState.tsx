import React from "react";

interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon = "📭", title, description, action }: EmptyStateProps) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "48px 24px",
        textAlign: "center",
        background: "var(--color-surface-soft)",
        border: "1px dashed var(--color-hairline-strong)",
        borderRadius: "var(--radius-md)",
        color: "var(--color-ink)",
      }}
    >
      <span style={{ fontSize: 40, marginBottom: 12, userSelect: "none" }} aria-hidden>
        {icon}
      </span>
      <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0, color: "var(--color-ink)" }}>
        {title}
      </h3>
      {description && (
        <p style={{ fontSize: 13, color: "var(--color-muted)", marginTop: 6, marginBottom: 0, maxWidth: 360 }}>
          {description}
        </p>
      )}
      {action && <div style={{ marginTop: 16 }}>{action}</div>}
    </div>
  );
}
