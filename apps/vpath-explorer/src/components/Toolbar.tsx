"use client";

import {
  Upload,
  FolderPlus,
  ClipboardPaste,
  LayoutGrid,
  List,
  ChevronRight,
  Search,
} from "lucide-react";
import { useRef } from "react";

type SortField = "name" | "size" | "modified" | "type";

type ToolbarProps = {
  currentPath: string;
  onNavigate: (path: string) => void;
  viewMode: "grid" | "list";
  onViewModeChange: (mode: "grid" | "list") => void;
  sortField: SortField;
  onSortFieldChange: (field: SortField) => void;
  searchQuery: string;
  onSearchQueryChange: (q: string) => void;
  hasClipboard: boolean;
  onPaste: () => void;
  onNewFolder: () => void;
  onUpload: (files: File[]) => void;
};

function parseBreadcrumb(path: string): { label: string; path: string }[] {
  if (path === "/") return [{ label: "Root", path: "/" }];
  const parts = path.split("/").filter(Boolean);
  const crumbs = [{ label: "Root", path: "/" }];
  let accumulated = "";
  for (const part of parts) {
    accumulated += `/${part}`;
    crumbs.push({ label: part, path: accumulated });
  }
  return crumbs;
}

export function Toolbar({
  currentPath,
  onNavigate,
  viewMode,
  onViewModeChange,
  sortField,
  onSortFieldChange,
  searchQuery,
  onSearchQueryChange,
  hasClipboard,
  onPaste,
  onNewFolder,
  onUpload,
}: ToolbarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const breadcrumbs = parseBreadcrumb(currentPath);

  return (
    <div
      className="flex items-center gap-2 px-4 h-[41px] border-b border-[var(--vp-border-subtle)] bg-[var(--vp-bg-base)] shrink-0"
      data-testid="explorer-toolbar"
    >
      {/* Breadcrumb */}
      <nav className="flex items-center gap-0.5 min-w-0 flex-1 overflow-hidden" data-testid="breadcrumb">
        {breadcrumbs.map((crumb, idx) => (
          <span key={crumb.path} className="flex items-center shrink-0">
            {idx > 0 && (
              <ChevronRight size={12} className="text-[var(--vp-text-tertiary)] mx-0.5" />
            )}
            <button
              type="button"
              onClick={() => onNavigate(crumb.path)}
              className={`text-[13px] px-1 py-0.5 rounded hover:bg-[var(--vp-bg-hover)] ${
                idx === breadcrumbs.length - 1
                  ? "text-[var(--vp-text-primary)] font-medium"
                  : "text-[var(--vp-text-secondary)]"
              }`}
            >
              {crumb.label}
            </button>
          </span>
        ))}
      </nav>

      {/* Actions */}
      <div className="flex items-center gap-1 shrink-0">
        <button
          type="button"
          data-testid="btn-upload"
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center gap-1.5 px-2 py-1 text-[13px] text-[var(--vp-text-secondary)] rounded hover:bg-[var(--vp-bg-hover)] hover:text-[var(--vp-text-primary)]"
          title="Upload files"
        >
          <Upload size={14} />
          <span className="hidden sm:inline">Upload</span>
        </button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              onUpload(Array.from(e.target.files));
              e.target.value = "";
            }
          }}
        />

        <button
          type="button"
          data-testid="btn-new-folder"
          onClick={onNewFolder}
          className="flex items-center gap-1.5 px-2 py-1 text-[13px] text-[var(--vp-text-secondary)] rounded hover:bg-[var(--vp-bg-hover)] hover:text-[var(--vp-text-primary)]"
          title="New folder"
        >
          <FolderPlus size={14} />
          <span className="hidden sm:inline">New Folder</span>
        </button>

        {hasClipboard && (
          <button
            type="button"
            onClick={onPaste}
            className="flex items-center gap-1.5 px-2 py-1 text-[13px] text-[var(--vp-accent)] rounded hover:bg-[var(--vp-bg-hover)]"
            title="Paste"
          >
            <ClipboardPaste size={14} />
            <span className="hidden sm:inline">Paste</span>
          </button>
        )}

        <div className="w-px h-5 bg-[var(--vp-border-subtle)] mx-1" />

        {/* View mode toggle */}
        <button
          type="button"
          onClick={() => onViewModeChange("grid")}
          className={`p-1.5 rounded ${
            viewMode === "grid"
              ? "bg-[var(--vp-bg-active)] text-[var(--vp-text-primary)]"
              : "text-[var(--vp-text-tertiary)] hover:text-[var(--vp-text-primary)]"
          }`}
          title="Grid view"
        >
          <LayoutGrid size={14} />
        </button>
        <button
          type="button"
          onClick={() => onViewModeChange("list")}
          className={`p-1.5 rounded ${
            viewMode === "list"
              ? "bg-[var(--vp-bg-active)] text-[var(--vp-text-primary)]"
              : "text-[var(--vp-text-tertiary)] hover:text-[var(--vp-text-primary)]"
          }`}
          title="List view"
        >
          <List size={14} />
        </button>

        {/* Sort */}
        <select
          value={sortField}
          onChange={(e) => onSortFieldChange(e.target.value as SortField)}
          className="ml-1 px-2 py-1 text-[13px] bg-[var(--vp-bg-input)] border border-[var(--vp-border-subtle)] rounded text-[var(--vp-text-secondary)] focus:outline-none focus:border-[var(--vp-accent)]"
          data-testid="sort-select"
        >
          <option value="name">Name</option>
          <option value="size">Size</option>
          <option value="modified">Modified</option>
          <option value="type">Type</option>
        </select>

        <div className="w-px h-5 bg-[var(--vp-border-subtle)] mx-1" />

        {/* Search */}
        <div className="relative">
          <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-[var(--vp-text-tertiary)]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchQueryChange(e.target.value)}
            placeholder="Search..."
            className="pl-7 pr-2 py-1 w-36 text-[13px] bg-[var(--vp-bg-input)] border border-[var(--vp-border-subtle)] rounded text-[var(--vp-text-primary)] placeholder:text-[var(--vp-text-tertiary)] focus:outline-none focus:border-[var(--vp-accent)]"
            data-testid="search-input"
          />
        </div>
      </div>
    </div>
  );
}
