"use client";

import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ViewerProps } from "./ViewerProps";

export default function MarkdownViewer({ contentUrl }: ViewerProps) {
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
        Failed to load markdown content.
      </div>
    );
  }

  if (content === null) {
    return (
      <div className="p-6 text-[var(--vp-text-tertiary)] text-[13px]">Loading...</div>
    );
  }

  return (
    <div className="p-6 prose prose-invert max-w-none text-[var(--vp-text-primary)]" data-testid="markdown-viewer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-2xl font-bold text-[var(--vp-text-primary)] border-b border-[var(--vp-border-subtle)] pb-2 mb-4">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-xl font-semibold text-[var(--vp-text-primary)] mt-6 mb-3">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-lg font-medium text-[var(--vp-text-primary)] mt-4 mb-2">{children}</h3>
          ),
          p: ({ children }) => (
            <p className="text-[14px] text-[var(--vp-text-secondary)] leading-relaxed mb-3">{children}</p>
          ),
          code: ({ className, children }) => {
            const isBlock = className?.includes("language-");
            if (isBlock) {
              return (
                <pre className="bg-[var(--vp-bg-base)] border border-[var(--vp-border-subtle)] rounded p-3 overflow-auto text-[13px] font-mono text-[var(--vp-text-primary)]">
                  <code>{children}</code>
                </pre>
              );
            }
            return (
              <code className="bg-[var(--vp-bg-base)] px-1 py-0.5 rounded text-[13px] font-mono text-[var(--vp-accent)]">
                {children}
              </code>
            );
          },
          table: ({ children }) => (
            <table className="w-full border border-[var(--vp-border-subtle)] text-[13px] mb-4">{children}</table>
          ),
          th: ({ children }) => (
            <th className="px-3 py-2 text-left bg-[var(--vp-bg-base)] text-[var(--vp-text-secondary)] font-medium border border-[var(--vp-border-subtle)]">{children}</th>
          ),
          td: ({ children }) => (
            <td className="px-3 py-2 border border-[var(--vp-border-subtle)] text-[var(--vp-text-primary)]">{children}</td>
          ),
          a: ({ href, children }) => (
            <a href={href} className="text-[var(--vp-accent)] hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>
          ),
          ul: ({ children }) => (
            <ul className="list-disc pl-5 mb-3 text-[var(--vp-text-secondary)]">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal pl-5 mb-3 text-[var(--vp-text-secondary)]">{children}</ol>
          ),
          li: ({ children }) => (
            <li className="mb-1 text-[14px]">{children}</li>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-3 border-[var(--vp-accent)] pl-4 italic text-[var(--vp-text-tertiary)] my-3">{children}</blockquote>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
