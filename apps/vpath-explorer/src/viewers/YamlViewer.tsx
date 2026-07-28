"use client";

import { useState, useEffect } from "react";
import type { ViewerProps } from "./ViewerProps";

function highlightYaml(line: string): React.ReactNode {
  // Comment lines
  if (line.trimStart().startsWith("#")) {
    return <span className="text-[var(--vp-text-tertiary)] italic">{line}</span>;
  }

  // Key-value lines
  const kvMatch = line.match(/^(\s*)([\w.-]+)(\s*:\s*)(.*)/);
  if (kvMatch) {
    const [, indent, key, colon, value] = kvMatch;
    let valueNode: React.ReactNode;

    if (value.startsWith('"') || value.startsWith("'")) {
      valueNode = <span className="text-[var(--vp-status-success)]">{value}</span>;
    } else if (/^-?\d+(\.\d+)?$/.test(value)) {
      valueNode = <span className="text-[var(--vp-status-info)]">{value}</span>;
    } else if (value === "true" || value === "false") {
      valueNode = <span className="text-[var(--vp-status-purple)]">{value}</span>;
    } else if (value === "null" || value === "~") {
      valueNode = <span className="text-[var(--vp-text-tertiary)]">{value}</span>;
    } else {
      valueNode = <span className="text-[var(--vp-text-primary)]">{value}</span>;
    }

    return (
      <>
        {indent}
        <span className="text-[var(--vp-accent)]">{key}</span>
        <span className="text-[var(--vp-text-tertiary)]">{colon}</span>
        {valueNode}
      </>
    );
  }

  // List items
  if (line.trimStart().startsWith("- ")) {
    const idx = line.indexOf("- ");
    return (
      <>
        {line.slice(0, idx)}
        <span className="text-[var(--vp-text-tertiary)]">- </span>
        <span className="text-[var(--vp-text-primary)]">{line.slice(idx + 2)}</span>
      </>
    );
  }

  return <span className="text-[var(--vp-text-primary)]">{line}</span>;
}

export default function YamlViewer({ contentUrl }: ViewerProps) {
  const [content, setContent] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setContent(null);
    setError(false);
    fetch(contentUrl)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.text();
      })
      .then((text) => { if (!cancelled) setContent(text); })
      .catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; };
  }, [contentUrl]);

  if (error) {
    return (
      <div className="p-6 text-[var(--vp-status-error)] text-[13px]">Failed to load YAML.</div>
    );
  }

  if (content === null) {
    return (
      <div className="p-6 text-[var(--vp-text-tertiary)] text-[13px]">Loading...</div>
    );
  }

  const lines = content.split("\n");

  return (
    <div className="p-4 overflow-auto" data-testid="yaml-viewer">
      <pre className="text-[13px] font-mono leading-6">
        {lines.map((line, idx) => (
          <div key={idx} className="flex">
            <span className="inline-block w-10 text-right pr-3 text-[var(--vp-text-tertiary)] select-none text-[11px]">
              {idx + 1}
            </span>
            <span className="flex-1 whitespace-pre-wrap">{highlightYaml(line)}</span>
          </div>
        ))}
      </pre>
    </div>
  );
}
