"use client";

import { useMemo, useState } from "react";
import { BrainCircuit, Plug, ShieldCheck } from "lucide-react";
import { useVpathMutation, useVpathQuery } from "@/components/providers";
import { RuntimePanel } from "@/components/RuntimePanel";

// The activity-bar header (title/icon) is rendered by the SDK from the manifest
// spec.ui — this page writes ZERO header/nav chrome (CLAUDE.md §2). All colors
// are semantic tokens (var(--vp-*)); no palette literals (CLAUDE.md §4).

// ---- Shapes mirrored from the backend cognition catalog --------------------
interface ProbeView {
  endpoint_env: string;
  path: string;
}
interface AuthModeView {
  auth_mode: string;
  model_source: string;
  membership_enforced: boolean;
  models: string[];
  example_model: string | null;
  probe: ProbeView | null;
}
interface ProviderView {
  provider: string;
  auth_modes: AuthModeView[];
}
interface VariantView {
  name: string;
  wrapper_class: string;
  supports: { provider: string; auth_mode: string }[];
}
interface Catalog {
  providers: ProviderView[];
  variants: VariantView[];
}
interface MappingRow {
  axis: string;
  value: string;
  target: string;
}
interface Projection {
  resource_json: unknown;
  manifest_snippet: string;
  mapping: MappingRow[];
}
interface Capabilities {
  known: boolean;
  context_window?: number;
  supports_function_calling?: boolean;
  supports_vision?: boolean;
  supports_reasoning?: boolean;
  supports_structured_output?: boolean;
}
interface ValidateResult {
  valid: boolean;
  selection: { provider: string; auth_mode: string; model: string; variant: string };
  model_source: string;
  membership_enforced: boolean;
  capabilities: Capabilities;
  projection: Projection;
}
interface ResourceStatus {
  bound: boolean;
  reason?: string;
  message?: string;
  variant?: string;
  provider?: string;
  model?: string;
}

const primary = { color: "var(--vp-text-primary)" } as const;
const muted = { color: "var(--vp-text-secondary)" } as const;
const inputStyle = {
  color: "var(--vp-text-primary)",
  backgroundColor: "var(--vp-bg-input)",
  borderColor: "var(--vp-border-input)",
} as const;

export default function AgenticResourceModelingPage() {
  const catalog = useVpathQuery<Catalog>("/api/modeling/providers");
  const status = useVpathQuery<ResourceStatus>("/api/modeling/resource/status");

  const [provider, setProvider] = useState("");
  const [authMode, setAuthMode] = useState("");
  const [model, setModel] = useState("");
  const [variant, setVariant] = useState("");
  const [reqs, setReqs] = useState({
    function_calling: false,
    vision: false,
    reasoning: false,
    structured_output: false,
    min_context: 0,
  });

  const validate = useVpathMutation<ValidateResult, unknown>({
    method: "POST",
    path: "/api/modeling/validate",
  });

  const providerView = useMemo(
    () => catalog.data?.providers.find((p) => p.provider === provider),
    [catalog.data, provider],
  );
  const authModeView = useMemo(
    () => providerView?.auth_modes.find((a) => a.auth_mode === authMode),
    [providerView, authMode],
  );
  const compatibleVariants = useMemo(
    () =>
      (catalog.data?.variants ?? []).filter((v) =>
        v.supports.some(
          (s) => s.provider === provider && s.auth_mode === authMode,
        ),
      ),
    [catalog.data, provider, authMode],
  );

  const onValidate = () => {
    validate.mutate({ provider, auth_mode: authMode, model, variant, requirements: reqs });
  };

  const canSubmit = provider && authMode && model && variant && !validate.isPending;

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <header className="flex items-center gap-2">
        <BrainCircuit size={18} style={muted} />
        <p className="text-sm" style={muted}>
          Compose a <strong style={primary}>(provider, auth&nbsp;mode, model)</strong>{" "}
          selection in the cognition shape, validate it (reachability +
          capability), and project it onto the platform&apos;s{" "}
          <strong style={primary}>agent-provider</strong> resource.
        </p>
      </header>

      <BoundPanel status={status} />

      {catalog.isError ? (
        <Card testid="catalog-error" tone="danger">
          <p className="text-sm" style={{ color: "var(--vp-danger)" }}>
            Could not load the provider catalog: {catalog.error?.message}
          </p>
        </Card>
      ) : (
        <Card testid="editor">
          <h2 className="text-base font-semibold" style={primary}>
            Editor
          </h2>

          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Provider" htmlFor="provider-select">
              <select
                id="provider-select"
                data-testid="provider-select"
                value={provider}
                className="rounded-md border px-3 py-2 text-sm"
                style={inputStyle}
                onChange={(e) => {
                  setProvider(e.target.value);
                  setAuthMode("");
                  setModel("");
                  setVariant("");
                  validate.reset();
                }}
              >
                <option value="">Pick a provider…</option>
                {catalog.data?.providers.map((p) => (
                  <option key={p.provider} value={p.provider}>
                    {p.provider}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Auth mode" htmlFor="authmode-select">
              <select
                id="authmode-select"
                data-testid="authmode-select"
                value={authMode}
                disabled={!providerView}
                className="rounded-md border px-3 py-2 text-sm"
                style={inputStyle}
                onChange={(e) => {
                  setAuthMode(e.target.value);
                  setModel("");
                  setVariant("");
                  validate.reset();
                }}
              >
                <option value="">Pick an auth mode…</option>
                {providerView?.auth_modes.map((a) => (
                  <option key={a.auth_mode} value={a.auth_mode}>
                    {a.auth_mode} ({a.model_source})
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Model" htmlFor="model-input">
              <ModelControl
                authModeView={authModeView}
                model={model}
                onChange={(v) => {
                  setModel(v);
                  validate.reset();
                }}
              />
            </Field>

            <Field label="Wrapper / variant" htmlFor="variant-select">
              <select
                id="variant-select"
                data-testid="variant-select"
                value={variant}
                disabled={!authMode}
                className="rounded-md border px-3 py-2 text-sm"
                style={inputStyle}
                onChange={(e) => {
                  setVariant(e.target.value);
                  validate.reset();
                }}
              >
                <option value="">Pick a runtime…</option>
                {compatibleVariants.map((v) => (
                  <option key={v.name} value={v.name}>
                    {v.name} (class {v.wrapper_class})
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <fieldset className="mt-4">
            <legend className="text-sm font-medium" style={muted}>
              Required capabilities (the construction-time gate — optional)
            </legend>
            <div className="mt-2 flex flex-wrap gap-4">
              {(
                [
                  ["function_calling", "function calling"],
                  ["vision", "vision"],
                  ["reasoning", "reasoning"],
                  ["structured_output", "structured output"],
                ] as const
              ).map(([key, label]) => (
                <label key={key} className="flex items-center gap-2 text-sm" style={muted}>
                  <input
                    type="checkbox"
                    data-testid={`req-${key}`}
                    checked={reqs[key] as boolean}
                    onChange={(e) => {
                      setReqs((r) => ({ ...r, [key]: e.target.checked }));
                      validate.reset();
                    }}
                  />
                  {label}
                </label>
              ))}
              <label className="flex items-center gap-2 text-sm" style={muted}>
                min context
                <input
                  type="number"
                  data-testid="req-min_context"
                  min={0}
                  value={reqs.min_context}
                  className="w-24 rounded-md border px-2 py-1 text-sm"
                  style={inputStyle}
                  onChange={(e) => {
                    setReqs((r) => ({ ...r, min_context: Number(e.target.value) || 0 }));
                    validate.reset();
                  }}
                />
              </label>
            </div>
          </fieldset>

          <button
            type="button"
            data-testid="validate-button"
            disabled={!canSubmit}
            onClick={onValidate}
            className="mt-5 rounded-md px-4 py-2 text-sm font-semibold"
            style={{ color: "var(--vp-on-accent)", backgroundColor: "var(--vp-accent)" }}
          >
            {validate.isPending ? "Validating…" : "Validate & project"}
          </button>
        </Card>
      )}

      <ResultPanel validate={validate} />

      <RuntimePanel />
    </div>
  );
}

function ModelControl({
  authModeView,
  model,
  onChange,
}: {
  authModeView: AuthModeView | undefined;
  model: string;
  onChange: (v: string) => void;
}) {
  if (!authModeView) {
    return (
      <select
        id="model-input"
        data-testid="model-input"
        disabled
        className="rounded-md border px-3 py-2 text-sm"
        style={inputStyle}
      >
        <option value="">Pick provider + auth mode first…</option>
      </select>
    );
  }
  if (authModeView.model_source === "probe") {
    // probe (local): the served set is discovered from a live endpoint we can't
    // reach offline — show the ProbeSpec (endpoint env + path); validating will
    // FAIL-HARD with probe_requires_live_endpoint (honest, never a faked list).
    return (
      <>
        <input
          id="model-input"
          data-testid="model-input"
          value={model}
          placeholder="served model (resolved from a live probe)"
          className="rounded-md border px-3 py-2 text-sm"
          style={inputStyle}
          onChange={(e) => onChange(e.target.value)}
        />
        {authModeView.probe ? (
          <span data-testid="probe-spec" className="mt-1 text-xs" style={muted}>
            probe: ${authModeView.probe.endpoint_env}
            {authModeView.probe.path} — needs a live endpoint
          </span>
        ) : null}
      </>
    );
  }
  if (authModeView.membership_enforced) {
    // curated/catalog: the roster IS the gate — offer exactly those.
    return (
      <select
        id="model-input"
        data-testid="model-input"
        value={model}
        className="rounded-md border px-3 py-2 text-sm"
        style={inputStyle}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">Pick a model…</option>
        {authModeView.models.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
    );
  }
  // open: BYO passthrough — free text, with the registry-known models as hints.
  return (
    <>
      <input
        id="model-input"
        data-testid="model-input"
        list="model-suggestions"
        value={model}
        placeholder="open — type any model (BYO key)…"
        className="rounded-md border px-3 py-2 text-sm"
        style={inputStyle}
        onChange={(e) => onChange(e.target.value)}
      />
      <datalist id="model-suggestions">
        {authModeView.models.map((m) => (
          <option key={m} value={m} />
        ))}
      </datalist>
    </>
  );
}

function BoundPanel({
  status,
}: {
  status: ReturnType<typeof useVpathQuery<ResourceStatus>>;
}) {
  if (status.isPending) {
    return (
      <Card testid="modeling-bound-loading">
        <p className="text-sm" style={muted}>
          Checking the live agent-provider binding…
        </p>
      </Card>
    );
  }
  if (status.isError) {
    return (
      <Card testid="modeling-bound-error" tone="danger">
        <p className="text-sm" style={{ color: "var(--vp-danger)" }}>
          Could not read the resource status: {status.error?.message}
        </p>
      </Card>
    );
  }
  const s = status.data;
  if (!s?.bound) {
    return (
      <Card testid="modeling-bound-empty">
        <div className="flex items-center gap-2">
          <Plug size={16} style={muted} />
          <span className="text-xs font-semibold uppercase tracking-wide" style={muted}>
            Currently bound agent-provider
          </span>
        </div>
        <p className="mt-2 text-sm" style={primary}>
          Nothing bound yet.
        </p>
        <p className="mt-1 text-sm" style={muted}>
          {s?.message ?? "Bind an agent-provider instance in the platform shell."}
        </p>
      </Card>
    );
  }
  return (
    <Card testid="modeling-bound">
      <div className="flex items-center gap-2">
        <Plug size={16} style={muted} />
        <span className="text-xs font-semibold uppercase tracking-wide" style={muted}>
          Currently bound agent-provider (read-only)
        </span>
      </div>
      <dl className="mt-3 grid grid-cols-3 gap-2 text-sm">
        <Stat label="variant" value={s.variant} />
        <Stat label="provider" value={s.provider} />
        <Stat label="model" value={s.model} />
      </dl>
    </Card>
  );
}

function ResultPanel({
  validate,
}: {
  validate: ReturnType<typeof useVpathMutation<ValidateResult, unknown>>;
}) {
  if (validate.isError) {
    return (
      <Card testid="validation-error" tone="danger">
        <div className="flex items-center gap-2">
          <ShieldCheck size={16} style={{ color: "var(--vp-danger)" }} />
          <h2 className="text-base font-semibold" style={{ color: "var(--vp-danger)" }}>
            Selection rejected (FAIL-HARD)
          </h2>
        </div>
        <p data-testid="validation-error-text" className="mt-2 text-sm" style={muted}>
          {validate.error?.message ?? "The selection could not be validated."}
        </p>
      </Card>
    );
  }
  if (validate.data) {
    const d = validate.data;
    return (
      <Card testid="validation-ok">
        <div className="flex items-center gap-2">
          <ShieldCheck size={16} style={muted} />
          <h2 className="text-base font-semibold" style={primary}>
            Valid — projected to the agent-provider resource
          </h2>
        </div>
        <p className="mt-1 text-sm" style={muted}>
          model source: <strong style={primary}>{d.model_source}</strong> ·
          membership enforced: <strong style={primary}>{String(d.membership_enforced)}</strong>
        </p>

        <h3 className="mt-4 text-sm font-semibold" style={primary}>
          resource.json (preview — non-secret half only)
        </h3>
        <pre
          data-testid="resource-json"
          className="mt-1 overflow-auto rounded-md border p-3 text-xs"
          style={{ ...inputStyle }}
        >
          {JSON.stringify(d.projection.resource_json, null, 2)}
        </pre>

        <h3 className="mt-4 text-sm font-semibold" style={primary}>
          vpath-app.yaml — resourceRequirements (declared, not hand-built)
        </h3>
        <pre
          data-testid="manifest-snippet"
          className="mt-1 overflow-auto rounded-md border p-3 text-xs"
          style={{ ...inputStyle }}
        >
          {d.projection.manifest_snippet}
        </pre>

        <h3 className="mt-4 text-sm font-semibold" style={primary}>
          cognition ↔ agent-provider mapping
        </h3>
        <table data-testid="mapping-table" className="mt-1 w-full text-left text-xs">
          <thead>
            <tr style={muted}>
              <th className="py-1 pr-3 font-medium">axis</th>
              <th className="py-1 pr-3 font-medium">value</th>
              <th className="py-1 font-medium">target</th>
            </tr>
          </thead>
          <tbody>
            {d.projection.mapping.map((row) => (
              <tr key={row.axis} style={primary}>
                <td className="py-1 pr-3">{row.axis}</td>
                <td className="py-1 pr-3">{row.value}</td>
                <td className="py-1" style={muted}>
                  {row.target}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    );
  }
  return (
    <Card testid="validation-empty">
      <h2 className="text-base font-semibold" style={primary}>
        No projection yet
      </h2>
      <p className="mt-2 text-sm" style={muted}>
        Pick a provider, auth mode, model and runtime above, then
        validate — a cognition-correct selection projects to the
        agent-provider resource shape here.
      </p>
    </Card>
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
    <div className="flex flex-col gap-1">
      <label htmlFor={htmlFor} className="text-sm font-medium" style={muted}>
        {label}
      </label>
      {children}
    </div>
  );
}

function Stat({ label, value }: { label: string; value?: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-xs uppercase tracking-wide" style={muted}>
        {label}
      </span>
      <span style={primary}>{value ?? "—"}</span>
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
      className="rounded-lg border px-6 py-5"
      style={{ borderColor }}
    >
      {children}
    </section>
  );
}
