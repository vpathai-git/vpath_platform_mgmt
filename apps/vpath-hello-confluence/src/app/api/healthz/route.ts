// Web liveness/readiness probe (manifest spec.health → /hello-confluence/api/healthz).
import { createHealthRoute } from "@vpath/sdk";

export const { GET } = createHealthRoute();
