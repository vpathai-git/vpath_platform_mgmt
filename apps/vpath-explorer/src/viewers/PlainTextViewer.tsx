"use client";

import { useState, useEffect } from "react";
import { WrapText } from "lucide-react";
import type { ViewerProps } from "./ViewerProps";

export default function PlainTextViewer({ contentUrl }: ViewerProps) {
  const [content, setContent] = useState<string | null>(null);
  const [error, setError] = useState(false);
  const [wordWrap, setWordWrap] = useState(true);

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
      <div className="p-6 text-[var(--vp-status-error)] text-[13px]">
        Failed to load text content.
      </div>
    );
  }

  if (content === null) {
    return (
      <div className="p-6 text-[var(--vp-text-tertiary)] text-[13px]">Loading...</div>
    );
  }

  const lines = content.split("\n");

  return (
    <div className="flex flex-col h-full" data-testid="plaintext-viewer">
      <div className="flex items-center justify-end px-3 py-1 border-b border-[var(--vp-border-subtle)] shrink-0">
        <button
          type="button"
          onClick={() => setWordWrap(!wordWrap)}
          className={`p-1 rounded ${
            wordWrap
              ? "text-[var(--vp-accent)] bg-[var(--vp-bg-active)]"
              : "text-[var(--vp-text-tertiary)] hover:text-[var(--vp-text-primary)]"
          }`}
          title="Toggle word wrap"
        >
          <WrapText size={14} />
        </button>
      </div>
      <div className="flex-1 overflow-auto p-4">
        <pre
          className={`text-[13px] font-mono leading-6 text-[var(--vp-text-primary)] ${
            wordWrap ? "whitespace-pre-wrap break-words" : "whitespace-pre"
          }`}
        >
          {lines.map((line, idx) => (
            <div key={idx} className="flex">
              <span className="inline-block w-12 text-right pr-4 text-[var(--vp-text-tertiary)] select-none text-[11px] shrink-0">
                {idx + 1}
              </span>
              <span className="flex-1">{line}</span>
            </div>
          ))}
        </pre>
      </div>
    </div>
  );
}
