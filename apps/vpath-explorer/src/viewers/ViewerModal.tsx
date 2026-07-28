"use client";

import { Suspense, useEffect, useCallback } from "react";
import { X, Download, FileText } from "lucide-react";
import { getViewer } from "./ViewerRegistry";
import { BinaryViewer } from "./BinaryViewer";

type ViewerModalProps = {
  filename: string;
  contentUrl: string;
  size: number;
  onClose: () => void;
  onDownload: () => void;
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ViewerModal({
  filename,
  contentUrl,
  size,
  onClose,
  onDownload,
}: ViewerModalProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose]
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const LazyViewer = getViewer(filename);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: "var(--vp-glass-bg)" }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      data-testid="viewer-modal"
    >
      <div className="w-[90vw] h-[90vh] flex flex-col rounded-lg border border-[var(--vp-border-subtle)] bg-[var(--vp-bg-elevated)] overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-3 px-4 py-2.5 border-b border-[var(--vp-border-subtle)] shrink-0">
          <FileText size={16} className="text-[var(--vp-text-tertiary)] shrink-0" />
          <span className="text-[14px] font-medium text-[var(--vp-text-primary)] truncate flex-1">
            {filename}
          </span>
          <span className="text-[11px] text-[var(--vp-text-tertiary)] px-2 py-0.5 rounded bg-[var(--vp-bg-base)] border border-[var(--vp-border-subtle)] tabular-nums shrink-0">
            {formatSize(size)}
          </span>
          <button
            type="button"
            onClick={onDownload}
            className="p-1.5 text-[var(--vp-text-secondary)] hover:text-[var(--vp-text-primary)] rounded hover:bg-[var(--vp-bg-hover)]"
            title="Download"
          >
            <Download size={16} />
          </button>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-[var(--vp-text-secondary)] hover:text-[var(--vp-text-primary)] rounded hover:bg-[var(--vp-bg-hover)]"
            title="Close"
          >
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto">
          <Suspense
            fallback={
              <div className="flex items-center justify-center h-full">
                <p className="text-[var(--vp-text-tertiary)] text-[13px]">Loading viewer...</p>
              </div>
            }
          >
            {LazyViewer ? (
              <LazyViewer
                filename={filename}
                contentUrl={contentUrl}
                size={size}
                onClose={onClose}
                onDownload={onDownload}
              />
            ) : (
              <BinaryViewer
                filename={filename}
                contentUrl={contentUrl}
                size={size}
                onClose={onClose}
                onDownload={onDownload}
              />
            )}
          </Suspense>
        </div>
      </div>
    </div>
  );
}
