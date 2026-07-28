import { createVersionProxyRoute } from "@vpath/sdk";
export const dynamic = "force-dynamic";
export const { GET } = createVersionProxyRoute({
  target: () => process.env.VPATH_API_BASE_URL,
});
