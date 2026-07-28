"use client";

// One factory call wires auth, query client, and the activity bar (P2). Zero
// per-app auth files; the header/title come from the manifest spec.ui via the
// activity, not app chrome. Canonical form — no inline `activity` (CLAUDE.md §2).
import { createVpathApp } from "@vpath/sdk";

export const { Providers, useAuthContext, useVpathQuery, useVpathMutation } =
  createVpathApp({
    appId: "fortune-teller",
    basePath: "/fortune",
  });
