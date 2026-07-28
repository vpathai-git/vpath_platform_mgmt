"use client";

import { useState, useEffect, useCallback } from "react";
import { Copy, ChevronRight, ChevronDown } from "lucide-react";
import type { ViewerProps } from "./ViewerProps";

type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };

function JsonNode({ name, value, depth }: { name?: string; value: JsonValue; depth: number }) {
  const [expanded, setExpanded] = useState(depth < 2);

  if (value === null) {
    return (
      <div style={{ paddingLeft: depth * 16 }} className="flex items-center h-6 text-[13px] font-mono">
        {name !== undefined && <span className="text-[var(--vp-text-primary)]">{name}: </span>}
        <span className="text-[var(--vp-text-tertiary)]">null</span>
      </div>
    );
  }

  if (typeof value === "string") {
    return (
      <div style={{ paddingLeft: depth * 16 }} className="flex items-center h-6 text-[13px] font-mono">
        {name !== undefined && <span className="text-[var(--vp-text-primary)]">{name}: </span>}
        <span className="text-[var(--vp-status-success)]">&quot;{value}&quot;</span>
      </div>
    );
  }

  if (typeof value === "number") {
    return (
      <div style={{ paddingLeft: depth * 16 }} className="flex items-center h-6 text-[13px] font-mono">
        {name !== undefined && <span className="text-[var(--vp-text-primary)]">{name}: </span>}
        <span className="text-[var(--vp-status-info)]">{value}</span>
      </div>
    );
  }

  if (typeof value === "boolean") {
    return (
      <div style={{ paddingLeft: depth * 16 }} className="flex items-center h-6 text-[13px] font-mono">
        {name !== undefined && <span className="text-[var(--vp-text-primary)]">{name}: </span>}
        <span className="text-[var(--vp-status-purple)]">{String(value)}</span>
      </div>
    );
  }

  const isArray = Array.isArray(value);
  const entries = isArray ? value.map((v, i) => [String(i), v] as const) : Object.entries(value);
  const bracket = isArray ? ["[", "]"] : ["{", "}"];
  const Arrow = expanded ? ChevronDown : ChevronRight;

  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        style={{ paddingLeft: depth * 16 }}
        className="flex items-center h-6 text-[13px] font-mono w-full text-left hover:bg-[var(--vp-bg-hover)]"
      >
        <Arrow size={12} className="text-[var(--vp-text-tertiary)] mr-1 shrink-0" />
        {name !== undefined && <span className="text-[var(--vp-text-primary)]">{name}: </span>}
        <span className="text-[var(--vp-text-tertiary)]">
          {bracket[0]} {!expanded && `${entries.length} items ${bracket[1]}`}
        </span>
      </button>
      {expanded && (
        <>
          {entries.map(([key, val]) => (
            <JsonNode key={key} name={isArray ? undefined : key} value={val as JsonValue} depth={depth + 1} />
          ))}
          <div style={{ paddingLeft: depth * 16 }} className="h-6 text-[13px] font-mono text-[var(--vp-text-tertiary)]">
            {bracket[1]}
          </div>
        </>
      )}
    </div>
  );
}

export default function JsonViewer({ contentUrl }: ViewerProps) {
  const [data, setData] = useState<JsonValue | undefined>(undefined);
  const [raw, setRaw] = useState("");
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setError(false);
    fetch(contentUrl)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.text();
      })
      .then((text) => {
        if (cancelled) return;
        setRaw(text);
        setData(JSON.parse(text));
      })
      .catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; };
  }, [contentUrl]);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(raw);
  }, [raw]);

  if (error) {
    return (
      <div className="p-6 text-[var(--vp-status-error)] text-[13px]">Failed to load JSON.</div>
    );
  }

  if (data === undefined) {
    return (
      <div className="p-6 text-[var(--vp-text-tertiary)] text-[13px]">Loading...</div>
    );
  }

  return (
    <div className="relative" data-testid="json-viewer">
      <button
        type="button"
        onClick={handleCopy}
        className="absolute top-3 right-3 p-1.5 rounded text-[var(--vp-text-tertiary)] hover:text-[var(--vp-text-primary)] hover:bg-[var(--vp-bg-hover)]"
        title="Copy to clipboard"
      >
        <Copy size={14} />
      </button>
      <div className="p-4 overflow-auto">
        <JsonNode value={data} depth={0} />
      </div>
    </div>
  );
}
