"use client";

import { createVpathApp } from "@vpath/sdk";

export const { Providers, useAuthContext, useVpathQuery, useVpathMutation } =
  createVpathApp({
    appId: "explorer",
    basePath: "/explorer",
  });
