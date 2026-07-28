import { createVersionProxyRoute } from "@vpath/sdk";
export const dynamic = "force-dynamic";
// Same canonical pattern as every app: the imprint's same-origin
// /fortune/api/version proxies to the backend's /api/version.
export const { GET } = createVersionProxyRoute({
  target: () => process.env.VPATH_API_BASE_URL,
});
