"use client";

// One factory call wires auth, query client, activity bar (P2). Zero per-app
// auth files; the header/title come from the activity, not app chrome.
import { createVpathApp } from "@vpath/sdk";

export const { Providers, useAuthContext, useVpathQuery, useVpathMutation } =
  createVpathApp({
    appId: "hello-confluence",
    basePath: "/hello-confluence",
  });
