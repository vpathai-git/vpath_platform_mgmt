# VPATH Workflow Demo

`vpath-workflow-demo` is the kit's first workflow application example. It is a
web-only Next.js wrapper around a small, app-owned `VpathWorkflow` definition.
The manifest declares a single-user, auto-provisioned pipeline and the page uses
the published workflow SDK surface to expose the real platform controls.

## Demo pipeline

The authored DAG in `vpath-workflow.yaml` has three steps:

1. extract PDF text;
2. normalize the extracted document;
3. structure the text with an agentic step using `gpt-5-mini`.

The source workflow carries `vpath.io/workflow-template=true`. The platform
discovers that source and generates the executable Argo YAML server-side.
Generated Argo YAML is not part of this app and must never be hand-edited.

## Runtime boundary and maturity

Workflow execution is **cluster-only** because Argo is the only shipped workflow
engine. Standalone renders the application, its catalog entry, the declared DAG,
and an honest empty state; it does not expose a run button or simulate workflow
progress. Upload, provisioning, configuration updates, and runs require the
platform API on a VPATH cluster.

Maturity: **code-complete / cluster execution unverified**. This environment has
no cluster, so no claim is made that a real Argo run has succeeded. The
standalone render/catalog/empty-state path is covered by
`tests/scenarios/standalone-workflow-demo.ts` and remains a verification target
until that scenario is run in the integrated Electron shell.

## Local mechanical checks

From the kit root:

```sh
npm ci
npm run build --workspace vpath-workflow-demo
python3 examples/vpath-workflow-demo/.ontogate/check.py
make check
```

The dynamic page requires `VPATH_RUNTIME=platform` or
`VPATH_RUNTIME=standalone`. Cluster and standalone supervisors inject it; local
Next.js development must set it explicitly. `VPATH_API_BASE_URL` is also
required when the cluster workflow controls or the version proxy are used.

See `DEPLOYMENT.md` for cluster and standalone integration.
