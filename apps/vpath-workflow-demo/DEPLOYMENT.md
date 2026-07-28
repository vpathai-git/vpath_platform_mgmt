# Deployment

The app is web-only. It has no app-owned API backend. Its same-origin
`/api/proxy/*` route forwards authenticated workflow requests to the VPATH
platform API, and `/api/version` proxies the strict platform deploy identity.

## Cluster

1. Keep `vpath-app.yaml` and `vpath-workflow.yaml` together in the app directory.
2. Build and deploy the web app through the normal platform app pipeline.
3. Publish the authored workflow definition through the platform workflow
   template pipeline. The platform generates Argo YAML from it and discovers the
   resulting template through `vpath.io/workflow-template=true`.
4. Confirm that the `agent-provider` requirement can satisfy `gpt-5-mini` before
   provisioning the app project.
5. Open the app from the platform sidebar. `WorkflowApp` asks the platform API to
   provision the pipeline declared by `spec.workflow` and fails visibly if the
   stored manifest configuration or required resource is missing.

Do not add generated Argo resources to this directory. Do not add
`provisioning.azure_secret` or blanket credential `envFrom`; the agent channel is
declared on the agentic step.

## Standalone

Standalone has no Argo workflow engine. Registration is useful only for the real
render/catalog/empty-state path and must not be presented as run support.

Until standalone boot discovery is complete, add one isolated entry to
`NEXT_APPS` in the platform checkout's `standalone/src/main/index.ts`:

```ts
"vpath-workflow-demo": {
  appName: "vpath-workflow-demo",
  basePath: "/workflow-demo",
  sourceDirRel: path.join("apps_infra", "apps", "vpath-workflow-demo"),
  clientId: "vpath-workflow-demo",
  windowTitle: "Workflow Demo (standalone)",
  catalog: {
    id: "workflow-demo",
    label: "Workflow Demo",
    description: "Inspect an agentic workflow definition",
    icon: "workflow",
  },
},
```

The standalone supervisor already injects `VPATH_RUNTIME=standalone` and the
platform API route used by the version proxy. If that checkout contains a
`PICKED_NEXT_APPS` allowlist, add `vpath-workflow-demo` to it as a separate,
additive edit; otherwise the registered app will not boot. No Python spawn entry
is needed because this example has no backend.

Then run the integrated Electron shell and execute the scenario named
`standalone-workflow-demo`. The expected proof is limited to sidebar catalog
visibility plus the rendered configuration and empty-state strings.

## Verification status

- Source, manifest, TypeScript, and Book gates: mechanically verifiable here.
- Standalone user-visible path: scenario-authored; only verified after a real
  integrated-shell run.
- Cluster provisioning and Argo execution: unverified in this environment.
