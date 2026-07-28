"use client";

import { X, CheckCircle2, AlertTriangle, XCircle, Info } from "lucide-react";

export type ToastType = "success" | "error" | "warning" | "info";

type ToastProps = {
  type: ToastType;
  title: string;
  message?: string;
  onDismiss: () => void;
};

const borderColors: Record<ToastType, string> = {
  success: "var(--vp-status-success)",
  error: "var(--vp-status-error)",
  warning: "var(--vp-status-warning)",
  info: "var(--vp-status-info)",
};

const icons: Record<ToastType, typeof CheckCircle2> = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

export function Toast({ type, title, message, onDismiss }: ToastProps) {
  const Icon = icons[type];
  const color = borderColors[type];

  return (
    <div
      className="pointer-events-auto flex items-start gap-2.5 px-3 py-2.5 rounded-md border border-[var(--vp-border-subtle)] bg-[var(--vp-bg-elevated)] min-w-[280px] max-w-[380px]"
      style={{ borderLeftWidth: "3px", borderLeftColor: color }}
      data-testid="toast"
    >
      <Icon size={16} className="shrink-0 mt-0.5" style={{ color }} />
      <div className="flex-1 min-w-0">
        <p className="text-[13px] font-medium text-[var(--vp-text-primary)]">{title}</p>
        {message && (
          <p className="text-[13px] text-[var(--vp-text-secondary)] mt-0.5 truncate">{message}</p>
        )}
      </div>
      <button
        type="button"
        onClick={onDismiss}
        className="shrink-0 p-0.5 text-[var(--vp-text-tertiary)] hover:text-[var(--vp-text-primary)]"
        aria-label="Dismiss"
      >
        <X size={14} />
      </button>
    </div>
  );
}
