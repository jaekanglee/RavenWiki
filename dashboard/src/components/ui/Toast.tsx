interface ToastProps {
  open: boolean;
  message: string;
  type?: "success" | "error";
}

export function Toast({ open, message, type = "success" }: ToastProps) {
  if (!open) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        position: "fixed",
        bottom: 24,
        right: 24,
        padding: "12px 20px",
        backgroundColor:
          type === "success" ? "var(--graph-surface-strong)" : "var(--color-danger-bg)",
        color: type === "success" ? "var(--graph-text)" : "var(--color-danger-text)",
        border: `1px solid ${
          type === "success" ? "var(--graph-border)" : "var(--color-danger-border)"
        }`,
        borderRadius: "var(--radius-md)",
        boxShadow: "var(--shadow-overlay)",
        zIndex: 1000,
        fontSize: 14,
        fontWeight: 500,
        maxWidth: 420,
      }}
    >
      {message}
    </div>
  );
}
