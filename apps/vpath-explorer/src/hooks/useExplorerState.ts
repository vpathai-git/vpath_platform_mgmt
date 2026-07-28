"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { storageState } from "@vpath/sdk";

export type ViewMode = "grid" | "list";
export type SortField = "name" | "size" | "modified" | "type";

export type ExplorerPersistedState = {
  rootId: string | null;
  path: string;
  viewMode: ViewMode;
  sortField: SortField;
  expandedNodes: string[];
};

const DEFAULT_STATE: ExplorerPersistedState = {
  rootId: null,
  path: "",
  viewMode: "grid",
  sortField: "name",
  expandedNodes: [],
};

async function loadState(): Promise<ExplorerPersistedState> {
  try {
    const text = await storageState.load();
    if (!text || text === "null") return DEFAULT_STATE;
    const parsed = JSON.parse(text);
    return { ...DEFAULT_STATE, ...parsed };
  } catch {
    return DEFAULT_STATE;
  }
}

async function saveState(state: ExplorerPersistedState): Promise<void> {
  try {
    await storageState.save(JSON.stringify(state));
  } catch {
    // Non-critical — UI still works without persistence
  }
}

export function useExplorerState() {
  const [rootId, setRootId] = useState<string | null>(DEFAULT_STATE.rootId);
  const [path, setPath] = useState<string>(DEFAULT_STATE.path);
  const [viewMode, setViewMode] = useState<ViewMode>(DEFAULT_STATE.viewMode);
  const [sortField, setSortField] = useState<SortField>(DEFAULT_STATE.sortField);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [loaded, setLoaded] = useState(false);

  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load on mount — use functional updates to avoid overwriting user interactions
  // that happened while the async GET request was in flight.
  useEffect(() => {
    loadState().then((s) => {
      setRootId((prev) => (prev === DEFAULT_STATE.rootId ? s.rootId : prev));
      setPath((prev) => (prev === DEFAULT_STATE.path ? s.path : prev));
      setViewMode((prev) => (prev === DEFAULT_STATE.viewMode ? s.viewMode : prev));
      setSortField((prev) => (prev === DEFAULT_STATE.sortField ? s.sortField : prev));
      setExpandedNodes((prev) => (prev.size === 0 ? new Set(s.expandedNodes) : prev));
      setLoaded(true);
    });
  }, []);

  // Debounced save whenever state changes (after initial load)
  const scheduleSave = useCallback(
    (next: ExplorerPersistedState) => {
      if (!loaded) return;
      if (saveTimer.current) clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(() => saveState(next), 800);
    },
    [loaded]
  );

  const handleSetRootId = useCallback(
    (id: string | null) => {
      setRootId(id);
    },
    []
  );

  const handleSetPath = useCallback(
    (p: string) => {
      setPath(p);
    },
    []
  );

  const handleSetViewMode = useCallback(
    (m: ViewMode) => {
      setViewMode(m);
    },
    []
  );

  const handleSetSortField = useCallback(
    (f: SortField) => {
      setSortField(f);
    },
    []
  );

  const handleToggleExpanded = useCallback(
    (key: string) => {
      setExpandedNodes((prev) => {
        const next = new Set(prev);
        if (next.has(key)) {
          next.delete(key);
        } else {
          next.add(key);
        }
        return next;
      });
    },
    []
  );

  // Save on any state change (after load)
  useEffect(() => {
    if (!loaded) return;
    scheduleSave({
      rootId,
      path,
      viewMode,
      sortField,
      expandedNodes: Array.from(expandedNodes),
    });
  }, [rootId, path, viewMode, sortField, expandedNodes, loaded, scheduleSave]);

  return {
    rootId,
    path,
    viewMode,
    sortField,
    expandedNodes,
    loaded,
    setRootId: handleSetRootId,
    setPath: handleSetPath,
    setViewMode: handleSetViewMode,
    setSortField: handleSetSortField,
    toggleExpanded: handleToggleExpanded,
  };
}
