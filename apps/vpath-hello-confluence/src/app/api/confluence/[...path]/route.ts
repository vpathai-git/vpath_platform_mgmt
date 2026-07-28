export const dynamic = "force-dynamic";

// Runtime proxy to our Confluence api. The target (a Dapr-shape invoke URL) is
// only known at runtime and differs per adapter — read it per request, never
// bake it in (CLAUDE.md §5). createProxyRoute streams the body and forwards the
// platform's X-Vpath-* identity/credential headers to the api automatically.
import { createProxyRoute, getRequiredEnv } from "@vpath/sdk";
import { authOptions } from "@/pages/api/auth/[...nextauth]";

export const { GET, POST, PUT, DELETE } = createProxyRoute({
  target: () =>
    getRequiredEnv("VPATH_HELLO_CONFLUENCE_API_URL", process.env.VPATH_HELLO_CONFLUENCE_API_URL),
  authOptions,
});
