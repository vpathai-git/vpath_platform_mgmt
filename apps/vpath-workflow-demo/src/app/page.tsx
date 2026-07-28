import { getRequiredEnv } from "@vpath/sdk";
import { WorkflowDemo } from "@/components/workflow-demo";

export const dynamic = "force-dynamic";

export default function WorkflowDemoPage() {
  const runtime = getRequiredEnv("VPATH_RUNTIME", process.env.VPATH_RUNTIME);
  if (runtime !== "platform" && runtime !== "standalone") {
    throw new Error(`VPATH_RUNTIME must be "platform" or "standalone", got "${runtime}"`);
  }

  return <WorkflowDemo executionAvailable={runtime === "platform"} />;
}
