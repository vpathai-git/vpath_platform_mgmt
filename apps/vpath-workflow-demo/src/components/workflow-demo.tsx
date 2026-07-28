"use client";

import { createAllWorkflowHooks, WorkflowApp } from "@vpath/sdk/workflow";
import { useVpathMutation, useVpathQuery } from "@/components/providers";

const TEMPLATE_NAME = "vpath-workflow-demo-text-insight";
const workflowHooks = createAllWorkflowHooks({
  useQuery: useVpathQuery,
  useMutation: useVpathMutation,
});

const steps = [
  { name: "Extract text", detail: "PDF processing" },
  { name: "Normalize text", detail: "Document flattening" },
  { name: "Structure text", detail: "Agentic · gpt-5-mini" },
];

export function WorkflowDemo({ executionAvailable }: { executionAvailable: boolean }) {
  return (
    <div className="space-y-6">
      <section
        data-testid="workflow-boundary"
        className="rounded-lg border p-5"
        style={{
          borderColor: "var(--vp-border-subtle)",
          backgroundColor: "var(--vp-bg-elevated)",
        }}
      >
        <p className="text-sm font-semibold" style={{ color: "var(--vp-text-primary)" }}>
          Cluster execution required
        </p>
        <p className="mt-2 text-sm" style={{ color: "var(--vp-text-secondary)" }}>
          This workflow runs on Argo in the VPATH cluster. Standalone shows the authored
          configuration only and does not simulate runs.
        </p>
      </section>

      <section
        data-testid="workflow-configuration"
        className="rounded-lg border p-5"
        style={{ borderColor: "var(--vp-border-subtle)" }}
      >
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-base font-semibold" style={{ color: "var(--vp-text-primary)" }}>
              Text insight demo
            </h1>
            <p className="mt-1 text-sm" style={{ color: "var(--vp-text-secondary)" }}>
              Template: {TEMPLATE_NAME}
            </p>
          </div>
          <span
            className="rounded-full border px-3 py-1 text-xs font-medium"
            style={{
              borderColor: "var(--vp-border-subtle)",
              color: "var(--vp-text-secondary)",
            }}
          >
            {executionAvailable ? "Platform API connected" : "Configuration only"}
          </span>
        </div>

        <ol className="mt-5 grid gap-3 md:grid-cols-3">
          {steps.map((step, index) => (
            <li
              key={step.name}
              className="rounded-md border p-4"
              style={{ borderColor: "var(--vp-border-subtle)" }}
            >
              <p className="text-xs" style={{ color: "var(--vp-text-tertiary)" }}>
                Step {index + 1}
              </p>
              <p className="mt-1 text-sm font-medium" style={{ color: "var(--vp-text-primary)" }}>
                {step.name}
              </p>
              <p className="mt-1 text-xs" style={{ color: "var(--vp-text-secondary)" }}>
                {step.detail}
              </p>
            </li>
          ))}
        </ol>
      </section>

      {executionAvailable ? (
        <ClusterWorkflowExperience />
      ) : (
        <section
          data-testid="workflow-empty-state"
          className="rounded-lg border border-dashed p-8 text-center"
          style={{ borderColor: "var(--vp-border-subtle)" }}
        >
          <h2 className="text-sm font-semibold" style={{ color: "var(--vp-text-primary)" }}>
            No standalone workflow engine
          </h2>
          <p className="mx-auto mt-2 max-w-xl text-sm" style={{ color: "var(--vp-text-secondary)" }}>
            Open this app on a VPATH cluster to upload a PDF, configure the workflow,
            and start a real Argo run.
          </p>
        </section>
      )}
    </div>
  );
}

function ClusterWorkflowExperience() {
  const template = workflowHooks.useTemplateDetail(TEMPLATE_NAME);

  return (
    <section data-testid="workflow-cluster-controls">
      {template.isError ? (
        <p className="mb-3 text-sm" style={{ color: "var(--vp-status-error)" }}>
          The workflow template catalog could not be loaded: {template.error.message}
        </p>
      ) : null}
      <WorkflowApp
        useQuery={useVpathQuery}
        useMutation={useVpathMutation}
        appName="vpath-workflow-demo"
        upload={{ accept: [".pdf"], maxSizeMb: 10, multiple: false }}
        settings={["detail_level"]}
        actionLabel="Run text insight workflow"
      />
    </section>
  );
}
