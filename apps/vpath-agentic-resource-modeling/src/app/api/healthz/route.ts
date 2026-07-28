// Web liveness/readiness probe (manifest spec.health → /agentic-resource-modeling/api/healthz).
import { createHealthRoute } from "@vpath/sdk";

export const { GET } = createHealthRoute();
