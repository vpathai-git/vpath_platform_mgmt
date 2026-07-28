"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { TreePane } from "./TreePane";
import { FolderView } from "./FolderView";
import { Toolbar } from "./Toolbar";
import { ContextMenu, type ContextMenuItem } from "./ContextMenu";
import { ConfirmDialog } from "./ConfirmDialog";
import { RenameDialog } from "./RenameDialog";
import { NewFolderDialog } from "./NewFolderDialog";
import { ViewerModal } from "@/viewers/ViewerModal";
import { getAppBasePath } from "@vpath/sdk";
import { useClipboard } from "@/hooks/useClipboard";
import { useDeleteFile, useDeleteFolder, useUploadFile } from "@/hooks/useFileSystem";
import { useToast } from "@/hooks/useToast";
import { useExplorerState } from "@/hooks/useExplorerState";

type DialogState =
  | { kind: "none" }
  | { kind: "confirm-delete"; path: string; isFolder: boolean }
  | { kind: "rename"; path: string; currentName: string }
  | { kind: "new-folder" }
  | { kind: "viewer"; path: string; filename: string; size: number };

function storageFileUrl(rootId: string, path: string): string {
  const base = typeof window !== "undefined" ? getAppBasePath() : "/explorer";
  return `${base}/api/platform/v1/storage/file?root_id=${encodeURIComponent(rootId)}&path=${encodeURIComponent(path)}`;
}

export function ExplorerLayout() {
  const {
    rootId: currentRootId,
    path: currentPath,
    viewMode,
    sortField,
    expandedNodes,
    setRootId: setCurrentRootId,
    setPath: setCurrentPath,
    setViewMode,
    setSortField,
    toggleExpanded,
  } = useExplorerState();

  const [selectedItem, setSelectedItem] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [dialog, setDialog] = useState<DialogState>({ kind: "none" });
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    path: string;
    isFolder: boolean;
  } | null>(null);
  const [treePaneWidth, setTreePaneWidth] = useState(260);
  const resizing = useRef(false);

  const { clipboard, copy, cut, paste } = useClipboard();
  const deleteMutation = useDeleteFile();
  const deleteFolderMutation = useDeleteFolder();
  const uploadMutation = useUploadFile();
  const { toast } = useToast();

  const handleRootSelect = useCallback((rootId: string) => {
    setCurrentRootId(rootId);
    setCurrentPath("");
    setSelectedItem(null);
    setSearchQuery("");
  }, [setCurrentRootId, setCurrentPath]);

  const handleNavigate = useCallback((path: string) => {
    setCurrentPath(path);
    setSelectedItem(null);
    setSearchQuery("");
  }, [setCurrentPath]);

  const handleSelect = useCallback((path: string) => {
    setSelectedItem(path);
  }, []);

  const handleOpenFile = useCallback((path: string, filename: string, size: number) => {
    setDialog({ kind: "viewer", path, filename, size });
  }, []);

  const handleContextMenu = useCallback(
    (e: React.MouseEvent, path: string, isFolder: boolean) => {
      e.preventDefault();
      setContextMenu({ x: e.clientX, y: e.clientY, path, isFolder });
    },
    []
  );

  const dismissContextMenu = useCallback(() => setContextMenu(null), []);

  const handleDelete = useCallback(
    async (path: string, isFolder: boolean) => {
      if (!currentRootId) return;
      try {
        if (isFolder) {
          await deleteFolderMutation.mutateAsync({ rootId: currentRootId, path });
        } else {
          await deleteMutation.mutateAsync({ rootId: currentRootId, path });
        }
        toast("success", "Deleted", path.split("/").pop() ?? path);
        setSelectedItem(null);
      } catch (err) {
        toast("error", "Delete failed", err instanceof Error ? err.message : "Unknown error");
      }
      setDialog({ kind: "none" });
    },
    [deleteMutation, deleteFolderMutation, toast, currentRootId]
  );

  const handlePaste = useCallback(async () => {
    try {
      await paste(currentPath);
    } catch (err) {
      toast("error", "Paste failed", err instanceof Error ? err.message : "Unknown error");
    }
  }, [paste, currentPath, toast]);

  const handleDownload = useCallback((path: string) => {
    if (!currentRootId) return;
    window.open(storageFileUrl(currentRootId, path), "_blank");
  }, [currentRootId]);

  const handleUpload = useCallback(
    async (files: File[]) => {
      if (!currentRootId) return;
      for (const file of files) {
        const path = currentPath ? `${currentPath}/${file.name}` : file.name;
        try {
          await uploadMutation.mutateAsync({ rootId: currentRootId, path, file });
          toast("success", "Uploaded", file.name);
        } catch (err) {
          toast("error", "Upload failed", err instanceof Error ? err.message : file.name);
        }
      }
    },
    [uploadMutation, currentRootId, currentPath, toast]
  );

  const handlePathSelect = useCallback((rootId: string, path: string) => {
    setCurrentRootId(rootId);
    setCurrentPath(path);
    setSelectedItem(null);
    setSearchQuery("");
  }, [setCurrentRootId, setCurrentPath]);

  const handleTreeContextMenu = useCallback(
    (e: React.MouseEvent, rootId: string, path: string, isFolder: boolean) => {
      e.preventDefault();
      setCurrentRootId(rootId);
      setContextMenu({ x: e.clientX, y: e.clientY, path, isFolder });
    },
    [setCurrentRootId]
  );

  const contextMenuItems: ContextMenuItem[] = contextMenu
    ? [
        { label: "Open", action: () => { dismissContextMenu(); } },
        { label: "Copy", action: () => { if (currentRootId) copy(currentRootId, [contextMenu.path]); dismissContextMenu(); } },
        { label: "Cut", action: () => { if (currentRootId) cut(currentRootId, [contextMenu.path]); dismissContextMenu(); } },
        {
          label: "Paste",
          action: () => { handlePaste(); dismissContextMenu(); },
          disabled: !clipboard,
        },
        { divider: true },
        {
          label: "Rename",
          action: () => {
            const name = contextMenu.path.split("/").pop() ?? "";
            setDialog({ kind: "rename", path: contextMenu.path, currentName: name });
            dismissContextMenu();
          },
        },
        {
          label: "Download",
          action: () => { handleDownload(contextMenu.path); dismissContextMenu(); },
          disabled: contextMenu.isFolder,
        },
        { divider: true },
        {
          label: "Delete",
          action: () => {
            setDialog({
              kind: "confirm-delete",
              path: contextMenu.path,
              isFolder: contextMenu.isFolder,
            });
            dismissContextMenu();
          },
          danger: true,
        },
      ]
    : [];

  const handleMouseDown = useCallback(() => { resizing.current = true; }, []);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!resizing.current) return;
      setTreePaneWidth(Math.max(180, Math.min(480, e.clientX)));
    };
    const onMouseUp = () => { resizing.current = false; };
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    return () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
  }, []);

  return (
    <div className="flex h-full overflow-hidden bg-[var(--vp-bg-base)]" data-testid="explorer-layout">
      <div
        className="shrink-0 border-r border-[var(--vp-border-subtle)] overflow-hidden flex flex-col"
        style={{ width: treePaneWidth }}
      >
        <TreePane
          currentRootId={currentRootId}
          currentPath={currentPath}
          expandedNodes={expandedNodes}
          onToggleExpanded={toggleExpanded}
          onRootSelect={handleRootSelect}
          onPathSelect={handlePathSelect}
          onContextMenu={handleTreeContextMenu}
        />
      </div>

      <div
        className="w-1 cursor-col-resize hover:bg-[var(--vp-accent)] active:bg-[var(--vp-accent)] shrink-0"
        onMouseDown={handleMouseDown}
        data-testid="resize-handle"
      />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Toolbar
          currentPath={currentPath}
          onNavigate={handleNavigate}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          sortField={sortField}
          onSortFieldChange={setSortField}
          searchQuery={searchQuery}
          onSearchQueryChange={setSearchQuery}
          hasClipboard={!!clipboard}
          onPaste={handlePaste}
          onNewFolder={() => setDialog({ kind: "new-folder" })}
          onUpload={handleUpload}
        />
        <div className="flex-1 overflow-auto">
          <FolderView
            rootId={currentRootId}
            currentPath={currentPath}
            viewMode={viewMode}
            sortField={sortField}
            searchQuery={searchQuery}
            selectedItem={selectedItem}
            onSelect={handleSelect}
            onNavigate={handleNavigate}
            onOpenFile={handleOpenFile}
            onContextMenu={handleContextMenu}
          />
        </div>
      </div>

      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          items={contextMenuItems}
          onDismiss={dismissContextMenu}
        />
      )}

      {dialog.kind === "confirm-delete" && (
        <ConfirmDialog
          title="Delete item"
          message={`Are you sure you want to delete "${dialog.path.split("/").pop()}"? This action cannot be undone.`}
          confirmLabel="Delete"
          onConfirm={() => handleDelete(dialog.path, dialog.isFolder)}
          onCancel={() => setDialog({ kind: "none" })}
        />
      )}

      {dialog.kind === "rename" && currentRootId && (
        <RenameDialog
          rootId={currentRootId}
          currentName={dialog.currentName}
          onRename={() => setDialog({ kind: "none" })}
          onCancel={() => setDialog({ kind: "none" })}
          itemPath={dialog.path}
        />
      )}

      {dialog.kind === "new-folder" && currentRootId && (
        <NewFolderDialog
          rootId={currentRootId}
          parentPath={currentPath}
          onCreate={() => setDialog({ kind: "none" })}
          onCancel={() => setDialog({ kind: "none" })}
        />
      )}

      {dialog.kind === "viewer" && currentRootId && (
        <ViewerModal
          filename={dialog.filename}
          contentUrl={storageFileUrl(currentRootId, dialog.path)}
          size={dialog.size}
          onClose={() => setDialog({ kind: "none" })}
          onDownload={() => handleDownload(dialog.path)}
        />
      )}
    </div>
  );
}
