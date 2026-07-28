// =============================================================================
// Concept story K01. This integrated-shell scenario verifies only the render /
// empty-state path that standalone honestly provides: catalog discovery,
// application rendering, the manifest-declared folder teaching surface, and a
// TERMINAL honest state for the live storage roots (real data, an honest empty
// store, or a fail-closed "unreachable"). It never fabricates file rows and
// never asserts a specific live-API outcome the environment cannot guarantee.
// =============================================================================
import type { Step } from "../../../kit/uitest/engine/lib/scenario.ts";

const BASE = "/storage-demo";

function storageFrame(page: import("playwright").Page) {
  return page.frames().find((frame) => frame.url().includes(BASE));
}

async function readTestId(
  page: import("playwright").Page,
  testId: string,
  timeoutMs: number,
): Promise<string | null> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const frame = storageFrame(page);
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

// The live roots surface must reach exactly one HONEST terminal state. All
// three are correct depending on the real API — the defect is being stuck on
// the loading state or rendering nothing. Returns [testId, text].
async function readTerminalRootsState(
  page: import("playwright").Page,
  timeoutMs: number,
): Promise<[string, string] | null> {
  const deadline = Date.now() + timeoutMs;
  const terminal = ["storage-roots", "storage-empty", "storage-unavailable"];
  while (Date.now() < deadline) {
    const frame = storageFrame(page);
    if (frame) {
      for (const testId of terminal) {
        const text = await frame
          .locator(`[data-testid="${testId}"]`)
          .first()
          .innerText()
          .catch(() => null);
        if (text?.trim()) return [testId, text.trim()];
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  return null;
}

export const storageDemoSteps: Step[] = [
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
    name: "catalog-has-storage-demo",
    action: async ({ page, log }) => {
      await page
        .locator("text=Storage Demo")
        .first()
        .waitFor({ state: "visible", timeout: 30_000 });
      log("sidebar catalog shows Storage Demo");
    },
  },
  {
    name: "open-storage-demo",
    action: async ({ page, log }) => {
      await page.locator("text=Storage Demo").first().click({ timeout: 10_000 });
      log("opened Storage Demo through the sidebar");
    },
  },
  {
    name: "intro-renders",
    action: async ({ page, log }) => {
      const intro = await readTestId(page, "storage-intro", 60_000);
      if (!intro) {
        throw new Error("DEFECT: storage intro did not render in standalone.");
      }
      if (!intro.includes("Stores citizen") || !intro.includes("spec.appStorage")) {
        throw new Error(
          `DEFECT: intro missing the Stores-citizen boundary text. Got: ${intro.slice(0, 180)}`,
        );
      }
      log("Stores-citizen intro rendered");
    },
  },
  {
    name: "declared-folders-render",
    action: async ({ page, log }) => {
      const folders = await readTestId(page, "storage-declared-folders", 30_000);
      if (!folders) {
        throw new Error("DEFECT: declared-folders surface did not render.");
      }
      for (const needle of [
        "Notes",
        "Handbook",
        "Uploads",
        "private",
        "read",
        "readwrite",
      ]) {
        if (!folders.includes(needle)) {
          throw new Error(
            `DEFECT: declared folders missing '${needle}'. Got: ${folders.slice(0, 200)}`,
          );
        }
      }
      log("manifest-declared folders (private/read/readwrite) rendered");
    },
  },
  {
    name: "live-roots-reach-honest-terminal-state",
    action: async ({ page, log }) => {
      const explorer = await readTestId(page, "storage-explorer", 30_000);
      if (!explorer) {
        throw new Error("DEFECT: live storage-roots surface did not render.");
      }
      const terminal = await readTerminalRootsState(page, 60_000);
      if (!terminal) {
        throw new Error(
          "DEFECT: live roots never left the loading state — no roots, empty, " +
            "or fail-closed unavailable state was reached.",
        );
      }
      const [testId, text] = terminal;
      if (testId === "storage-unavailable" && !text.includes("Fail-closed")) {
        throw new Error(
          `DEFECT: unavailable state is not visibly fail-closed. Got: ${text.slice(0, 180)}`,
        );
      }
      // No root is selected in the render-path scenario, so a file listing must
      // NOT appear — the app must never fabricate folder contents.
      const frame = storageFrame(page);
      if (frame && (await frame.locator('[data-testid="storage-listing"]').count())) {
        throw new Error("DEFECT: a file listing rendered without a selected root.");
      }
      log(`live roots reached honest terminal state: ${testId}`);
    },
  },
];
