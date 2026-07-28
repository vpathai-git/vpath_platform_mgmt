// =============================================================================
// Concept story K01. This integrated-shell scenario verifies only what
// standalone honestly provides: catalog discovery, application rendering, the
// authored pipeline summary, and the cluster-only empty state. It never clicks
// or invents a run because standalone has no Argo engine.
// =============================================================================
import type { Step } from "../../../kit/uitest/engine/lib/scenario.ts";

function workflowFrame(page: import("playwright").Page) {
  return page.frames().find((frame) => frame.url().includes("/workflow-demo"));
}

async function readTestId(
  page: import("playwright").Page,
  testId: string,
  timeoutMs: number,
): Promise<string | null> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const frame = workflowFrame(page);
    if (frame) {
      const rendered = await frame
        .locator(`[data-testid="${testId}"]`)
        .first()
        .innerText()
        .catch(() => null);
      if (rendered?.trim()) return rendered.trim();
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  return null;
}

export const workflowDemoSteps: Step[] = [
  {
    name: "shell-loaded",
    action: async ({ page, log }) => {
      await page
        .locator("text=Applications")
        .first()
        .waitFor({ state: "visible", timeout: 120_000 });
      log("shell rendered (Applications visible)");
    },
  },
  {
    name: "catalog-has-workflow-demo",
    action: async ({ page, log }) => {
      await page
        .locator("text=Workflow Demo")
        .first()
        .waitFor({ state: "visible", timeout: 30_000 });
      log("sidebar catalog shows Workflow Demo");
    },
  },
  {
    name: "open-workflow-demo",
    action: async ({ page, log }) => {
      await page.locator("text=Workflow Demo").first().click({ timeout: 10_000 });
      log("opened Workflow Demo through the sidebar");
    },
  },
  {
    name: "configuration-renders",
    action: async ({ page, log }) => {
      const configuration = await readTestId(page, "workflow-configuration", 60_000);
      if (!configuration) {
        throw new Error("DEFECT: workflow configuration did not render in standalone.");
      }
      if (!configuration.includes("vpath-workflow-demo-text-insight")) {
        throw new Error(
          `DEFECT: authored template name is absent. Got: ${configuration.slice(0, 180)}`,
        );
      }
      if (!configuration.includes("Structure text")) {
        throw new Error(
          `DEFECT: agentic DAG step is absent. Got: ${configuration.slice(0, 180)}`,
        );
      }
      log("authored workflow configuration rendered");
    },
  },
  {
    name: "cluster-only-empty-state",
    action: async ({ page, log }) => {
      const empty = await readTestId(page, "workflow-empty-state", 20_000);
      if (!empty || !empty.includes("No standalone workflow engine")) {
        throw new Error(
          `DEFECT: honest cluster-only empty state missing. Got: ${empty ?? "<none>"}`,
        );
      }
      const frame = workflowFrame(page);
      if (!frame) throw new Error("DEFECT: /workflow-demo iframe not found.");
      if (await frame.locator('[data-testid="start-run-btn"]').count()) {
        throw new Error("DEFECT: standalone exposed a workflow run control without Argo.");
      }
      log("cluster-only boundary rendered and no run control was exposed");
    },
  },
];
