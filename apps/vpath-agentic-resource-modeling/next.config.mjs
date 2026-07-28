import path from "node:path";
const appDir = path.dirname(new URL(import.meta.url).pathname);

/** @type {import('next').NextConfig} */
// PLAIN JS (CLAUDE.md §5) — never import the TS createNextConfig helper here; it
// breaks the cluster Docker build (ERR_UNKNOWN_FILE_EXTENSION).
const nextConfig = {
  output: "standalone",
  basePath: "/agentic-resource-modeling",
  experimental: {
    externalDir: true, // compile the vendored @vpath/sdk source from outside this dir
  },
  // The vendored SDK lives outside this app, so its bare imports (next-auth,
  // react, …) must still resolve to THIS app's node_modules. The platform
  // monorepo hoists via workspaces; the kit vendors the SDK standalone, so we
  // add the app's node_modules to webpack's resolution explicitly.
  webpack(config) {
    config.resolve.modules = [
      path.join(appDir, "node_modules"),
      ...(config.resolve.modules ?? ["node_modules"]),
    ];
    return config;
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Cache-Control", value: "no-store, must-revalidate" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-DNS-Prefetch-Control", value: "off" },
          { key: "Content-Security-Policy", value: "frame-ancestors 'self'" },
        ],
      },
      {
        source: "/_next/static/:path*",
        headers: [
          { key: "Cache-Control", value: "public, max-age=31536000, immutable" },
        ],
      },
    ];
  },
};

export default nextConfig;
