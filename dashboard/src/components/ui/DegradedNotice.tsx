interface DegradedNoticeProps {
  title: string;
  reason?: string;
}

export function DegradedNotice({ title, reason }: DegradedNoticeProps) {
  return (
    <div
      role="status"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 4,
        background: "var(--color-warning-bg)",
        border: "1px solid var(--color-warning-border)",
        color: "var(--color-warning-text)",
        borderRadius: "var(--radius-md)",
        padding: "10px 12px",
        marginBottom: 16,
        fontSize: 13,
      }}
    >
      <strong style={{ fontWeight: 700 }}>⚠️ {title}</strong>
      {reason ? <span style={{ lineHeight: 1.5 }}>{reason}</span> : null}
    </div>
  );
}
