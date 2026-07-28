"use client";

import {
  Folder,
  FolderOpen,
  AlertCircle,
  Loader2,
  ChevronRight,
} from "lucide-react";
import { useStorageRoots, useStorageListing, type StorageRoot } from "@/hooks/useFileSystem";

export function nodeKey(rootId: string, path: string): string {
  return `${rootId}:::${path}`;
}

type TreePaneProps = {
  currentRootId: string | null;
  currentPath: string;
  expandedNodes: Set<string>;
  onToggleExpanded: (key: string) => void;
  onRootSelect: (rootId: string) => void;
  onPathSelect: (rootId: string, path: string) => void;
  onContextMenu?: (
    e: React.MouseEvent,
    rootId: string,
    path: string,
    isFolder: boolean
  ) => void;
};

type TreeNodeProps = {
  rootId: string;
  path: string;
  label: string;
  depth: number;
  currentRootId: string | null;
  currentPath: string;
  expandedNodes: Set<string>;
  onToggleExpanded: (key: string) => void;
  onPathSelect: (rootId: string, path: string) => void;
  onContextMenu?: (
    e: React.MouseEvent,
    rootId: string,
    path: string,
    isFolder: boolean
  ) => void;
};

function TreeNode({
  rootId,
  path,
  label,
  depth,
  currentRootId,
  currentPath,
  expandedNodes,
  onToggleExpanded,
  onPathSelect,
  onContextMenu,
}: TreeNodeProps) {
  const key = nodeKey(rootId, path);
  const expanded = expandedNodes.has(key);
  const { data, isLoading } = useStorageListing(expanded ? rootId : null, path);
  const subFolders = (data ?? []).filter((e) => e.type === "directory");

  const isSelected = currentRootId === rootId && currentPath === path;
  const Icon = isSelected ? FolderOpen : Folder;

  const handleClick = () => {
    onPathSelect(rootId, path);
    onToggleExpanded(key);
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onContextMenu?.(e, rootId, path, true);
  };

  return (
    <div>
      <button
        type="button"
        onClick={handleClick}
        onContextMenu={handleContextMenu}
        data-testid={path === "" ? `root-item-${rootId}` : `tree-node-${rootId}-${path}`}
        style={{ paddingLeft: `${8 + depth * 16}px` }}
        className={`w-full flex items-center gap-1.5 pr-2 py-1 text-left text-[13px] rounded-md transition-colors ${
          isSelected
            ? "bg-[var(--vp-bg-active)] text-[var(--vp-text-primary)] border-l-2 border-[var(--vp-accent)]"
            : "text-[var(--vp-text-secondary)] hover:bg-[var(--vp-bg-hover)] hover:text-[var(--vp-text-primary)]"
        }`}
        title={label}
      >
        {/* Expand/collapse arrow */}
        <span className="shrink-0 w-3 flex items-center justify-center">
          {isLoading ? (
            <Loader2 size={10} className="animate-spin text-[var(--vp-text-tertiary)]" />
          ) : (
            <ChevronRight
              size={11}
              className={`text-[var(--vp-text-tertiary)] transition-transform ${
                expanded ? "rotate-90" : ""
              }`}
            />
          )}
        </span>

        <Icon size={13} className="shrink-0" />

        <div className="min-w-0 flex-1">
          <div className="truncate font-medium">{label}</div>
          {depth === 0 && (
            <div className="truncate text-[11px] text-[var(--vp-text-tertiary)]">
              {rootId.replace("vpath-", "").split("/")[0]}
            </div>
          )}
        </div>
      </button>

      {expanded && (
        <div>
          {subFolders.map((child) => (
            <TreeNode
              key={child.name}
              rootId={rootId}
              path={path ? `${path}/${child.name}` : child.name}
              label={child.name}
              depth={depth + 1}
              currentRootId={currentRootId}
              currentPath={currentPath}
              expandedNodes={expandedNodes}
              onToggleExpanded={onToggleExpanded}
              onPathSelect={onPathSelect}
              onContextMenu={onContextMenu}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function RootNode({
  root,
  currentRootId,
  currentPath,
  expandedNodes,
  onToggleExpanded,
  onPathSelect,
  onContextMenu,
}: {
  root: StorageRoot;
  currentRootId: string | null;
  currentPath: string;
  expandedNodes: Set<string>;
  onToggleExpanded: (key: string) => void;
  onPathSelect: (rootId: string, path: string) => void;
  onContextMenu?: (
    e: React.MouseEvent,
    rootId: string,
    path: string,
    isFolder: boolean
  ) => void;
}) {
  return (
    <TreeNode
      rootId={root.id}
      path=""
      label={root.label}
      depth={0}
      currentRootId={currentRootId}
      currentPath={currentPath}
      expandedNodes={expandedNodes}
      onToggleExpanded={onToggleExpanded}
      onPathSelect={onPathSelect}
      onContextMenu={onContextMenu}
    />
  );
}

export function TreePane({
  currentRootId,
  currentPath,
  expandedNodes,
  onToggleExpanded,
  onRootSelect,
  onPathSelect,
  onContextMenu,
}: TreePaneProps) {
  const { data: roots, isLoading, error } = useStorageRoots();

  const handlePathSelect = (rootId: string, path: string) => {
    if (path === "") {
      onRootSelect(rootId);
    } else {
      onPathSelect(rootId, path);
    }
  };

  return (
    <div className="flex flex-col h-full" data-testid="tree-pane">
      <div className="px-4 border-b border-[var(--vp-border-subtle)] flex items-center h-[41px] shrink-0">
        <span className="text-[11px] font-medium uppercase tracking-wider text-[var(--vp-text-tertiary)]">
          File Systems
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-1 space-y-0.5">
        {isLoading && (
          <div className="flex items-center gap-2 px-3 py-4 text-[13px] text-[var(--vp-text-tertiary)]">
            <Loader2 size={13} className="animate-spin" />
            Loading…
          </div>
        )}
        {error && (
          <div className="flex items-center gap-2 px-3 py-4 text-[13px] text-[var(--vp-status-error)]">
            <AlertCircle size={13} />
            Failed to load storage roots
          </div>
        )}
        {roots?.map((root) => (
          <RootNode
            key={root.id}
            root={root}
            currentRootId={currentRootId}
            currentPath={currentPath}
            expandedNodes={expandedNodes}
            onToggleExpanded={onToggleExpanded}
            onPathSelect={handlePathSelect}
            onContextMenu={onContextMenu}
          />
        ))}
        {roots?.length === 0 && (
          <div className="px-3 py-4 text-[13px] text-[var(--vp-text-tertiary)]">
            No storage roots available
          </div>
        )}
      </div>
    </div>
  );
}
