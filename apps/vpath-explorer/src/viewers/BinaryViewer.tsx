"use client";

import { FileText, Download } from "lucide-react";
import type { ViewerProps } from "./ViewerProps";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getMimeType(filename: string): string {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  const mimeMap: Record<string, string> = {
    zip: "application/zip",
    tar: "application/x-tar",
    gz: "application/gzip",
    exe: "application/x-executable",
    bin: "application/octet-stream",
    iso: "application/x-iso-image",
    dmg: "application/x-apple-diskimage",
    deb: "application/x-deb",
    rpm: "application/x-rpm",
    wasm: "application/wasm",
  };
  return mimeMap[ext] ?? "application/octet-stream";
}

export function BinaryViewer({ filename, size, onDownload }: ViewerProps) {
  const mimeType = getMimeType(filename);
  const ext = filename.split(".").pop()?.toUpperCase() ?? "FILE";

  return (
    <div
      className="flex flex-col items-center justify-center h-full gap-4 p-8"
      data-testid="binary-viewer"
    >
      <FileText size={56} className="text-[var(--vp-text-tertiary)] opacity-40" />
      <p className="text-[16px] font-medium text-[var(--vp-text-primary)]">
        {filename}
      </p>
      <div className="flex items-center gap-3">
        <span className="px-2 py-0.5 text-[11px] text-[var(--vp-text-tertiary)] bg-[var(--vp-bg-base)] border border-[var(--vp-border-subtle)] rounded">
          {ext}
        </span>
        <span className="text-[13px] text-[var(--vp-text-secondary)] tabular-nums">
          {formatSize(size)}
        </span>
      </div>
      <p className="text-[13px] text-[var(--vp-text-tertiary)]">{mimeType}</p>
      <button
        type="button"
        onClick={onDownload}
        className="flex items-center gap-2 px-4 py-2 mt-2 text-[13px] rounded bg-[var(--vp-accent)] hover:opacity-90"
        style={{ color: "var(--vp-on-accent)" }}
      >
        <Download size={16} />
        Download
      </button>
    </div>
  );
}
