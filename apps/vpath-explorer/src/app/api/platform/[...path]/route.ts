export const dynamic = "force-dynamic";

import { createProxyRoute, getRequiredEnv } from "@vpath/sdk";

const PLATFORM_API = getRequiredEnv("VPATH_API_BASE_URL", process.env.VPATH_API_BASE_URL);

export const { GET, POST, PUT, DELETE } = createProxyRoute({
  target: () => PLATFORM_API,
});
