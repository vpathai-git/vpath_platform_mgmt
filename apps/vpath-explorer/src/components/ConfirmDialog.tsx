"use client";

import { useEffect, useCallback } from "react";

type ConfirmDialogProps = {
  title: string;
  message: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmDialog({
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    },
    [onCancel]
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: "var(--vp-glass-bg)" }}
      data-testid="confirm-dialog"
    >
      <div className="w-full max-w-sm rounded-lg border border-[var(--vp-border-subtle)] bg-[var(--vp-bg-elevated)] p-5">
        <h3 className="text-[15px] font-semibold text-[var(--vp-text-primary)] mb-2">
          {title}
        </h3>
        <p className="text-[13px] text-[var(--vp-text-secondary)] mb-5">
          {message}
        </p>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="px-3 py-1.5 text-[13px] rounded border border-[var(--vp-border-subtle)] text-[var(--vp-text-secondary)] hover:bg-[var(--vp-bg-hover)]"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="px-3 py-1.5 text-[13px] rounded bg-[var(--vp-danger)] hover:opacity-90"
            style={{ color: "var(--vp-on-accent)" }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
