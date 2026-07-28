"use client";

import { useMemo, useCallback } from "react";
import { VpathDropZone } from "@vpath/sdk";
import { FileCard } from "./FileCard";
import { useStorageListing, useStorageSearch, useUploadFile } from "@/hooks/useFileSystem";
import { useToast } from "@/hooks/useToast";

type SortField = "name" | "size" | "modified" | "type";

type FolderViewProps = {
  rootId: string | null;
  currentPath: string;
  viewMode: "grid" | "list";
  sortField: SortField;
  searchQuery: string;
  selectedItem: string | null;
  onSelect: (path: string) => void;
  onNavigate: (path: string) => void;
  onOpenFile: (path: string, filename: string, size: number) => void;
  onContextMenu: (e: React.MouseEvent, path: string, isFolder: boolean) => void;
};

function formatSize(bytes?: number): string {
  if (bytes === undefined) return "--";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(ts?: number): string {
  if (!ts) return "--";
  return new Date(ts * 1000).toLocaleDateString();
}

function entryPath(currentPath: string, name: string): string {
  return currentPath ? `${currentPath}/${name}` : name;
}

export function FolderView({
  rootId,
  currentPath,
  viewMode,
  sortField,
  searchQuery,
  selectedItem,
  onSelect,
  onNavigate,
  onOpenFile,
  onContextMenu,
}: FolderViewProps) {
  const { data, isLoading, error } = useStorageListing(rootId ?? "", currentPath);
  const searchResult = useStorageSearch(rootId ?? "", currentPath, searchQuery);
  const uploadMutation = useUploadFile();
  const { toast } = useToast();

  const entries = useMemo(() => {
    const raw = searchQuery.length >= 2
      ? (searchResult.data ?? []).map((r) => ({
          name: r.name,
          type: (r.type === "directory" ? "folder" : "file") as "file" | "folder",
          size: r.size,
          modified: r.modified,
        }))
      : (data ?? []).map((r) => ({
          name: r.name,
          type: (r.type === "directory" ? "folder" : "file") as "file" | "folder",
          size: r.size,
          modified: r.modified,
        }));

    return [...raw].sort((a, b) => {
      if (a.type !== b.type) return a.type === "folder" ? -1 : 1;
      switch (sortField) {
        case "name": return a.name.localeCompare(b.name);
        case "size": return (a.size ?? 0) - (b.size ?? 0);
        case "modified": return (a.modified ?? 0) - (b.modified ?? 0);
        case "type": {
          const extA = a.name.split(".").pop() ?? "";
          const extB = b.name.split(".").pop() ?? "";
          return extA.localeCompare(extB);
        }
        default: return 0;
      }
    });
  }, [data, searchResult.data, searchQuery, sortField]);

  const handleDoubleClick = useCallback(
    (name: string, type: "file" | "folder", size?: number) => {
      const path = entryPath(currentPath, name);
      if (type === "folder") {
        onNavigate(path);
      } else {
        onOpenFile(path, name, size ?? 0);
      }
    },
    [currentPath, onNavigate, onOpenFile]
  );

  const handleItemClick = useCallback(
    (name: string) => onSelect(entryPath(currentPath, name)),
    [currentPath, onSelect]
  );

  const handleItemContextMenu = useCallback(
    (e: React.MouseEvent, name: string, isFolder: boolean) => {
      onContextMenu(e, entryPath(currentPath, name), isFolder);
    },
    [currentPath, onContextMenu]
  );

  const handleUpload = useCallback(
    async (files: File[]) => {
      if (!rootId) return;
      for (const file of files) {
        const path = entryPath(currentPath, file.name);
        try {
          await uploadMutation.mutateAsync({ rootId, path, file });
          toast("success", "Uploaded", file.name);
        } catch (err) {
          toast("error", "Upload failed", err instanceof Error ? err.message : file.name);
        }
      }
    },
    [uploadMutation, rootId, currentPath, toast]
  );

  if (!rootId) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2 p-8" data-testid="folder-view">
        <p className="text-[var(--vp-text-tertiary)] text-[13px]">Select a storage root to browse files</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full" data-testid="folder-view">
        <p className="text-[var(--vp-text-tertiary)] text-[13px]">Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full" data-testid="folder-view">
        <p className="text-[var(--vp-status-error)] text-[13px]">
          Failed to load directory
        </p>
      </div>
    );
  }

  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 p-8" data-testid="folder-view">
        <VpathDropZone onFiles={handleUpload} label="This folder is empty" sublabel="Drop files here to upload" />
      </div>
    );
  }

  return (
    <div data-testid="folder-view">
      <div className="px-3 pt-2">
        <VpathDropZone onFiles={handleUpload} compact label="Drop files to upload" />
      </div>
      <div className="p-3">
        {viewMode === "grid" ? (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(140px,1fr))] gap-2">
            {entries.map((entry) => (
              <FileCard
                key={entry.name}
                name={entry.name}
                type={entry.type}
                size={entry.size}
                selected={selectedItem === entryPath(currentPath, entry.name)}
                onClick={() => handleItemClick(entry.name)}
                onDoubleClick={() => handleDoubleClick(entry.name, entry.type, entry.size)}
                onContextMenu={(e) => handleItemContextMenu(e, entry.name, entry.type === "folder")}
              />
            ))}
          </div>
        ) : (
          <table className="w-full text-[13px]" data-testid="folder-view-list">
            <thead>
              <tr className="text-left text-[var(--vp-text-tertiary)] text-[11px] uppercase tracking-wider border-b border-[var(--vp-border-subtle)]">
                <th className="px-3 py-2 font-medium">Name</th>
                <th className="px-3 py-2 font-medium w-24">Size</th>
                <th className="px-3 py-2 font-medium w-28">Modified</th>
                <th className="px-3 py-2 font-medium w-20">Type</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => {
                const fullPath = entryPath(currentPath, entry.name);
                const ext = entry.type === "folder" ? "Folder" : (entry.name.split(".").pop()?.toUpperCase() ?? "FILE");
                return (
                  <tr
                    key={entry.name}
                    className={`border-b border-[var(--vp-border-subtle)] cursor-pointer hover:bg-[var(--vp-bg-hover)] ${
                      selectedItem === fullPath ? "bg-[var(--vp-bg-active)]" : ""
                    }`}
                    onClick={() => handleItemClick(entry.name)}
                    onDoubleClick={() => handleDoubleClick(entry.name, entry.type, entry.size)}
                    onContextMenu={(e) => handleItemContextMenu(e, entry.name, entry.type === "folder")}
                    data-testid={`file-card-${entry.name}`}
                  >
                    <td className="px-3 py-2 text-[var(--vp-text-primary)]">{entry.name}</td>
                    <td className="px-3 py-2 text-[var(--vp-text-tertiary)] tabular-nums">{formatSize(entry.size)}</td>
                    <td className="px-3 py-2 text-[var(--vp-text-tertiary)]">{formatDate(entry.modified)}</td>
                    <td className="px-3 py-2 text-[var(--vp-text-tertiary)]">{ext}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
