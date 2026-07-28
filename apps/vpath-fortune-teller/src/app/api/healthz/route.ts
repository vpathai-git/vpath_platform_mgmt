// Web liveness/readiness probe (manifest spec.health → /fortune/api/healthz).
import { createHealthRoute } from "@vpath/sdk";

export const { GET } = createHealthRoute();
