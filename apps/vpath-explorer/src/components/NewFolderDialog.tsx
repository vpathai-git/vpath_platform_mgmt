"use client";

import { useState, useEffect, useCallback } from "react";
import { useCreateFolder } from "@/hooks/useFileSystem";
import { useToast } from "@/hooks/useToast";

type NewFolderDialogProps = {
  rootId: string;
  parentPath: string;
  onCreate: () => void;
  onCancel: () => void;
};

export function NewFolderDialog({
  rootId,
  parentPath,
  onCreate,
  onCancel,
}: NewFolderDialogProps) {
  const [name, setName] = useState("");
  const createMutation = useCreateFolder();
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
    if (!trimmed) return;

    try {
      const path = parentPath ? `${parentPath}/${trimmed}` : trimmed;
      await createMutation.mutateAsync({ rootId, path });
      toast("success", "Created", `Folder "${trimmed}" created`);
      onCreate();
    } catch (err) {
      toast("error", "Create failed", err instanceof Error ? err.message : "Unknown error");
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: "var(--vp-glass-bg)" }}
      data-testid="new-folder-dialog"
    >
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm rounded-lg border border-[var(--vp-border-subtle)] bg-[var(--vp-bg-elevated)] p-5"
      >
        <h3 className="text-[15px] font-semibold text-[var(--vp-text-primary)] mb-3">
          New Folder
        </h3>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Folder name"
          autoFocus
          className="w-full px-3 py-2 text-[13px] bg-[var(--vp-bg-input)] border border-[var(--vp-border-subtle)] rounded text-[var(--vp-text-primary)] placeholder:text-[var(--vp-text-tertiary)] focus:outline-none focus:border-[var(--vp-accent)]"
          data-testid="new-folder-input"
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
            Create
          </button>
        </div>
      </form>
    </div>
  );
}
