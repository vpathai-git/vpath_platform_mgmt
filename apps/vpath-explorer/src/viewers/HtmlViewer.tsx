"use client";

import { useState, useEffect } from "react";
import type { ViewerProps } from "./ViewerProps";

export default function HtmlViewer({ contentUrl }: ViewerProps) {
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
      <div className="p-6 text-[var(--vp-status-error)] text-[13px]">
        Failed to load HTML content.
      </div>
    );
  }

  if (content === null) {
    return (
      <div className="p-6 text-[var(--vp-text-tertiary)] text-[13px]">Loading...</div>
    );
  }

  return (
    <div className="w-full h-full" data-testid="html-viewer">
      <iframe
        srcDoc={content}
        sandbox="allow-same-origin"
        className="w-full h-full border-0 bg-[var(--vp-bg-base)]"
        title="HTML Preview"
      />
    </div>
  );
}
