import { Modal } from "./Modal";
import { Button } from "./Button";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "default" | "danger";
  busy?: boolean;
  onConfirm: () => void;
  onClose: () => void;
  children?: React.ReactNode;
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "확인",
  cancelLabel = "취소",
  tone = "default",
  busy = false,
  onConfirm,
  onClose,
  children,
}: ConfirmDialogProps) {
  return (
    <Modal
      open={open}
      onClose={() => !busy && onClose()}
      maxWidth={480}
      zIndex={90}
      disableBackdropClose={busy}
    >
      <h2
        style={{
          marginBottom: 12,
          color: tone === "danger" ? "var(--color-error-text)" : "var(--color-ink)",
        }}
      >
        {title}
      </h2>
      {description && (
        <p style={{ fontSize: 14, marginBottom: children ? 12 : 20, color: "var(--color-body)" }}>
          {description}
        </p>
      )}
      {children}
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 20 }}>
        <Button variant="secondary" onClick={onClose} disabled={busy}>
          {cancelLabel}
        </Button>
        <Button variant={tone === "danger" ? "danger" : "primary"} onClick={onConfirm} disabled={busy}>
          {busy ? "처리 중…" : confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}
