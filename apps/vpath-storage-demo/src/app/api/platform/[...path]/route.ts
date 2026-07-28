export const dynamic = "force-dynamic";

import { createProxyRoute, getRequiredEnv } from "@vpath/sdk";
import { authOptions } from "@/pages/api/auth/[...nextauth]";

// The storage hooks (useStorageRoots / useStorageListing / …) call the
// same-origin path /api/platform/v1/storage/*. This route forwards those
// authenticated calls to the VPATH platform API. The target is read per
// request from runtime env — never baked into the build (CLAUDE.md §5).
const PLATFORM_API_URL = getRequiredEnv(
  "VPATH_API_BASE_URL",
  process.env.VPATH_API_BASE_URL,
);

export const { GET, POST, PUT, DELETE } = createProxyRoute({
  target: () => PLATFORM_API_URL,
  authOptions,
});
