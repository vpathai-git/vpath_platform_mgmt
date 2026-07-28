"use client";

import { useState, useEffect, useCallback } from "react";
import { useRenameItem } from "@/hooks/useFileSystem";
import { useToast } from "@/hooks/useToast";

type RenameDialogProps = {
  rootId: string;
  currentName: string;
  itemPath: string;
  onRename: () => void;
  onCancel: () => void;
};

export function RenameDialog({
  rootId,
  currentName,
  itemPath,
  onRename,
  onCancel,
}: RenameDialogProps) {
  const [name, setName] = useState(currentName);
  const renameMutation = useRenameItem();
  const { toast } = useToast();

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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed || trimmed === currentName) {
      onCancel();
      return;
    }
    try {
      const parentDir = itemPath.includes("/")
        ? itemPath.split("/").slice(0, -1).join("/")
        : "";
      const toPath = parentDir ? `${parentDir}/${trimmed}` : trimmed;
      await renameMutation.mutateAsync({ rootId, fromPath: itemPath, toPath });
      toast("success", "Renamed", `${currentName} -> ${trimmed}`);
      onRename();
    } catch (err) {
      toast("error", "Rename failed", err instanceof Error ? err.message : "Unknown error");
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: "var(--vp-glass-bg)" }}
      data-testid="rename-dialog"
    >
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-lg border border-[var(--vp-border-subtle)] bg-[var(--vp-bg-elevated)] p-5"
      >
        <h3 className="text-[15px] font-semibold text-[var(--vp-text-primary)] mb-3">
          Rename
        </h3>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoFocus
          className="w-full px-3 py-2 text-[13px] bg-[var(--vp-bg-input)] border border-[var(--vp-border-subtle)] rounded text-[var(--vp-text-primary)] focus:outline-none focus:border-[var(--vp-accent)]"
          data-testid="rename-input"
        />
        <div className="flex justify-end gap-2 mt-4">
          <button
            type="button"
            onClick={onCancel}
            className="px-3 py-1.5 text-[13px] rounded border border-[var(--vp-border-subtle)] text-[var(--vp-text-secondary)] hover:bg-[var(--vp-bg-hover)]"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="px-3 py-1.5 text-[13px] rounded bg-[var(--vp-accent)] hover:opacity-90"
            style={{ color: "var(--vp-on-accent)" }}
          >
            OK
          </button>
        </div>
      </form>
    </div>
  );
}
