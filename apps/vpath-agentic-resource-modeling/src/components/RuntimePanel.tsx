"use client";

import { useState } from "react";
import { Play, Radio, ShieldAlert } from "lucide-react";
import { useVpathMutation, useVpathQuery } from "@/components/providers";

// The RUNTIME panel: it exercises the canonical get_agent_factory() path through
// the same proxy the editor uses. Offerings are the bound contract projected
// verbatim; invoke constructs one agent inside the contract and sends a message.
// All colors are semantic tokens (var(--vp-*)) — no palette literals (CLAUDE §4);
// zero header/nav chrome (CLAUDE §2). When nothing is bound, offerings fails
// closed (422 resource_not_bound) and this renders the honest unbound state —
// the real first-use path, never a fabricated "ready".

interface Offerings {
  agents: string[];
  models: string[];
  llm_providers: string[];
  regions?: string[] | null;
  capabilities?: string[] | null;
}
interface InvokeResult {
  conversation_id: string;
  agent: string;
  model: string;
  streamed: boolean;
  answer: string;
}

const primary = { color: "var(--vp-text-primary)" } as const;
const muted = { color: "var(--vp-text-secondary)" } as const;
const inputStyle = {
  color: "var(--vp-text-primary)",
  backgroundColor: "var(--vp-bg-input)",
  borderColor: "var(--vp-border-input)",
} as const;

export function RuntimePanel() {
  const offerings = useVpathQuery<Offerings>("/api/modeling/runtime/offerings");
  const invoke = useVpathMutation<InvokeResult, unknown>({
    method: "POST",
    path: "/api/modeling/runtime/invoke",
  });

  if (offerings.isPending) {
    return (
      <Card testid="runtime-loading">
        <PanelTitle />
        <p className="mt-2 text-sm" style={muted}>
          Reading the bound agent-provider contract…
        </p>
      </Card>
    );
  }

  if (offerings.isError || !offerings.data) {
    // Fail-closed: no bound contract -> the runtime refuses (422). This is the
    // truthful first-use state (the NEED is declared but unbound), not an error
    // to paper over.
    return (
      <Card testid="runtime-unbound">
        <PanelTitle />
        <div className="mt-3 flex items-center gap-2">
          <ShieldAlert size={16} style={{ color: "var(--vp-danger)" }} />
          <span className="text-sm font-semibold" style={primary}>
            Runtime unavailable — no agent-provider bound (fail-closed)
          </span>
        </div>
        <p className="mt-1 text-sm" style={muted}>
          {offerings.error?.message ??
            "get_agent_factory() found no bound contract; nothing is invented."}
        </p>
      </Card>
    );
  }

  return (
    <BoundRuntime offerings={offerings.data} invoke={invoke} />
  );
}

function BoundRuntime({
  offerings,
  invoke,
}: {
  offerings: Offerings;
  invoke: ReturnType<typeof useVpathMutation<InvokeResult, unknown>>;
}) {
  const [agent, setAgent] = useState(offerings.agents[0] ?? "");
  const [model, setModel] = useState(offerings.models[0] ?? "");
  const [message, setMessage] = useState("");

  const canSubmit = agent && model && message.trim() && !invoke.isPending;

  return (
    <Card testid="runtime-offerings">
      <PanelTitle />
      <p className="mt-2 text-sm" style={muted}>
        Bound contract — agents{" "}
        <strong style={primary}>{offerings.agents.join(", ")}</strong>; models{" "}
        <strong style={primary}>{offerings.models.join(", ")}</strong>; providers{" "}
        <strong style={primary}>{offerings.llm_providers.join(", ")}</strong>.
      </p>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field label="Agent" htmlFor="runtime-agent">
          <select
            id="runtime-agent"
            data-testid="runtime-agent"
            value={agent}
            className="rounded-md border px-3 py-2 text-sm"
            style={inputStyle}
            onChange={(e) => {
              setAgent(e.target.value);
              invoke.reset();
            }}
          >
            {offerings.agents.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Model" htmlFor="runtime-model">
          <select
            id="runtime-model"
            data-testid="runtime-model"
            value={model}
            className="rounded-md border px-3 py-2 text-sm"
            style={inputStyle}
            onChange={(e) => {
              setModel(e.target.value);
              invoke.reset();
            }}
          >
            {offerings.models.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </Field>
      </div>

      <Field label="Message" htmlFor="runtime-message">
        <textarea
          id="runtime-message"
          data-testid="runtime-message"
          value={message}
          rows={2}
          placeholder="Send one message to the bound agent…"
          className="mt-1 rounded-md border px-3 py-2 text-sm"
          style={inputStyle}
          onChange={(e) => {
            setMessage(e.target.value);
            invoke.reset();
          }}
        />
      </Field>

      <button
        type="button"
        data-testid="runtime-invoke-button"
        disabled={!canSubmit}
        onClick={() => invoke.mutate({ agent, model, message })}
        className="mt-4 inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-semibold"
        style={{ color: "var(--vp-on-accent)", backgroundColor: "var(--vp-accent)" }}
      >
        <Play size={14} />
        {invoke.isPending ? "Invoking…" : "Invoke agent"}
      </button>

      <RuntimeResult invoke={invoke} />
    </Card>
  );
}

function RuntimeResult({
  invoke,
}: {
  invoke: ReturnType<typeof useVpathMutation<InvokeResult, unknown>>;
}) {
  if (invoke.isError) {
    return (
      <div data-testid="runtime-error" className="mt-4 rounded-md border p-3"
        style={{ borderColor: "var(--vp-danger-border)" }}>
        <p className="text-sm font-semibold" style={{ color: "var(--vp-danger)" }}>
          Invocation refused
        </p>
        <p className="mt-1 text-sm" style={muted}>
          {invoke.error?.message ?? "The agent invocation was refused."}
        </p>
      </div>
    );
  }
  if (invoke.data) {
    return (
      <div data-testid="runtime-result" className="mt-4 rounded-md border p-3"
        style={{ borderColor: "var(--vp-border-subtle)" }}>
        <p className="text-xs uppercase tracking-wide" style={muted}>
          answer ({invoke.data.agent} · {invoke.data.model})
        </p>
        <p className="mt-1 text-sm" style={primary}>
          {invoke.data.answer}
        </p>
      </div>
    );
  }
  return null;
}

function PanelTitle() {
  return (
    <div className="flex items-center gap-2">
      <Radio size={16} style={muted} />
      <span
        className="text-xs font-semibold uppercase tracking-wide"
        style={muted}
      >
        Agent runtime (get_agent_factory)
      </span>
    </div>
  );
}

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mt-3 flex flex-col gap-1">
      <label htmlFor={htmlFor} className="text-sm font-medium" style={muted}>
        {label}
      </label>
      {children}
    </div>
  );
}

function Card({
  children,
  testid,
}: {
  children: React.ReactNode;
  testid: string;
}) {
  return (
    <section
      data-testid={testid}
      className="rounded-lg border px-6 py-5"
      style={{ borderColor: "var(--vp-border-subtle)" }}
    >
      {children}
    </section>
  );
}
