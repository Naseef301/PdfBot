import { CheckCircle2, X, XCircle } from "lucide-react";

export function Toast({ toast, onClose }) {
  if (!toast) return null;
  return (
    <div className={`toast ${toast.type}`} role="status">
      {toast.type === "error" ? <XCircle size={19} /> : <CheckCircle2 size={19} />}
      <span>{toast.message}</span>
      <button type="button" onClick={onClose} aria-label="Dismiss notification"><X size={16} /></button>
    </div>
  );
}
