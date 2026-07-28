"use client";

import {
  Folder,
  FileText,
  FileSpreadsheet,
  FileImage,
  File,
  FileCode,
} from "lucide-react";

type FileCardProps = {
  name: string;
  type: "file" | "folder";
  size?: number;
  selected: boolean;
  onClick: () => void;
  onDoubleClick: () => void;
  onContextMenu: (e: React.MouseEvent) => void;
};

function getIcon(name: string, type: "file" | "folder") {
  if (type === "folder") return Folder;
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  if (["pdf", "txt", "md", "log", "doc", "docx"].includes(ext)) return FileText;
  if (["csv", "json", "jsonl", "yaml", "yml", "xlsx", "xls"].includes(ext)) return FileSpreadsheet;
  if (["png", "jpg", "jpeg", "gif", "svg", "webp", "bmp"].includes(ext)) return FileImage;
  if (["ts", "tsx", "js", "jsx", "py", "go", "rs", "java", "html", "css"].includes(ext)) return FileCode;
  return File;
}

function iconColor(type: "file" | "folder"): string {
  return type === "folder"
    ? "var(--vp-status-info)"
    : "var(--vp-text-tertiary)";
}

function formatSize(bytes?: number): string {
  if (bytes === undefined) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FileCard({
  name,
  type,
  size,
  selected,
  onClick,
  onDoubleClick,
  onContextMenu,
}: FileCardProps) {
  const Icon = getIcon(name, type);

  return (
    <button
      type="button"
      onClick={onClick}
      onDoubleClick={onDoubleClick}
      onContextMenu={onContextMenu}
      className={`flex flex-col items-center gap-1.5 p-3 rounded-md text-center cursor-pointer transition-colors border ${
        selected
          ? "border-[var(--vp-accent)] bg-[var(--vp-bg-active)]"
          : "border-transparent hover:bg-[var(--vp-bg-hover)]"
      }`}
      data-testid={`file-card-${name}`}
    >
      <Icon size={32} style={{ color: iconColor(type) }} className="shrink-0" />
      <span className="text-[13px] text-[var(--vp-text-primary)] truncate w-full leading-tight">
        {name}
      </span>
      {type === "file" && size !== undefined && (
        <span className="text-[10px] text-[var(--vp-text-tertiary)] tabular-nums">
          {formatSize(size)}
        </span>
      )}
    </button>
  );
}
