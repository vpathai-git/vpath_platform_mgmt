"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";
import { useVpathMutation } from "@/components/providers";

interface Fortune {
  fortune: string;
  sign: string;
}

const primary = { color: "var(--vp-text-primary)" } as const;
const muted = { color: "var(--vp-text-secondary)" } as const;

// The activity-bar header (title/icon) is rendered by the SDK from the manifest
// spec.ui — this page writes ZERO header/nav chrome (CLAUDE.md §2). All colors
// are semantic tokens (var(--vp-*)); no palette literals (CLAUDE.md §4).
export default function FortuneTellerPage() {
  const [question, setQuestion] = useState("");
  const draw = useVpathMutation<Fortune, { question: string }>({
    method: "POST",
    path: "/api/fortune/draw",
  });

  return (
    <div className="mx-auto flex max-w-xl flex-col gap-6">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          draw.mutate({ question });
        }}
        className="flex flex-col gap-3"
      >
        <label htmlFor="oracle-q" className="text-sm font-medium" style={muted}>
          Ask the oracle — a question is optional
        </label>
        <input
          id="oracle-q"
          data-testid="oracle-question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Type a question, or leave it blank…"
          className="rounded-md border px-3 py-2 text-sm"
          style={{
            color: "var(--vp-text-primary)",
            backgroundColor: "var(--vp-bg-input)",
            borderColor: "var(--vp-border-input)",
          }}
        />
        <button
          type="submit"
          data-testid="oracle-reveal"
          disabled={draw.isPending}
          className="rounded-md px-4 py-2 text-sm font-semibold"
          style={{
            color: "var(--vp-on-accent)",
            backgroundColor: "var(--vp-accent)",
          }}
        >
          Reveal my fortune
        </button>
      </form>

      {draw.isPending ? (
        <Card testid="oracle-loading">
          <p className="text-sm" style={muted}>
            Consulting the oracle…
          </p>
        </Card>
      ) : draw.isError ? (
        <Card testid="oracle-error" tone="danger">
          <h2
            className="text-base font-semibold"
            style={{ color: "var(--vp-danger)" }}
          >
            The oracle is silent
          </h2>
          <p className="mt-2 text-sm" style={muted}>
            {draw.error?.message ?? "The fortune service could not be reached."}
          </p>
        </Card>
      ) : draw.data ? (
        <Card testid="fortune-card">
          <div className="flex items-center gap-2">
            <Sparkles size={16} style={muted} />
            <span
              data-testid="fortune-sign"
              className="text-xs font-semibold uppercase tracking-wide"
              style={muted}
            >
              {draw.data.sign}
            </span>
          </div>
          <p data-testid="fortune-text" className="mt-3 text-lg" style={primary}>
            {draw.data.fortune}
          </p>
        </Card>
      ) : (
        <Card testid="oracle-empty">
          <h1 className="text-base font-semibold" style={primary}>
            Ask the oracle a question…
          </h1>
          <p className="mt-2 text-sm" style={muted}>
            Type a question above — or none at all — and reveal your fortune. The
            same question always draws the same card.
          </p>
        </Card>
      )}
    </div>
  );
}

function Card({
  children,
  testid,
  tone = "subtle",
}: {
  children: React.ReactNode;
  testid: string;
  tone?: "subtle" | "danger";
}) {
  const borderColor =
    tone === "danger" ? "var(--vp-danger-border)" : "var(--vp-border-subtle)";
  return (
    <section
      data-testid={testid}
      className="rounded-lg border px-6 py-8"
      style={{ borderColor }}
    >
      {children}
    </section>
  );
}
