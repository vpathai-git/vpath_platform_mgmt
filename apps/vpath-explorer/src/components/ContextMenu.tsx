"use client";

import { useEffect, useRef } from "react";

export type ContextMenuItem =
  | { label: string; action: () => void; disabled?: boolean; danger?: boolean; divider?: never }
  | { divider: true; label?: never; action?: never; disabled?: never; danger?: never };

type ContextMenuProps = {
  x: number;
  y: number;
  items: ContextMenuItem[];
  onDismiss: () => void;
};

export function ContextMenu({ x, y, items, onDismiss }: ContextMenuProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onDismiss();
      }
    };
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onDismiss();
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onDismiss]);

  // Adjust position to keep menu within viewport
  const adjustedX = Math.min(x, window.innerWidth - 200);
  const adjustedY = Math.min(y, window.innerHeight - items.length * 32 - 16);

  return (
    <div
      ref={ref}
      className="fixed z-50 min-w-[160px] py-1 rounded-md border border-[var(--vp-border-subtle)] bg-[var(--vp-bg-elevated)]"
      style={{ left: adjustedX, top: adjustedY }}
      data-testid="context-menu"
    >
      {items.map((item, idx) => {
        if (item.divider) {
          return (
            <div
              key={`div-${idx}`}
              className="my-1 h-px bg-[var(--vp-border-subtle)]"
            />
          );
        }
        return (
          <button
            key={item.label}
            type="button"
            onClick={item.disabled ? undefined : item.action}
            disabled={item.disabled}
            className={`w-full text-left px-3 py-1.5 text-[13px] transition-colors ${
              item.disabled
                ? "text-[var(--vp-text-tertiary)] cursor-not-allowed"
                : item.danger
                  ? "text-[var(--vp-status-error)] hover:bg-[var(--vp-danger-bg)]"
                  : "text-[var(--vp-text-primary)] hover:bg-[var(--vp-bg-hover)]"
            }`}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
