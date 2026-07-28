"use client";

import { useAuthContext } from "@/components/providers";
import { ExplorerLayout } from "@/components/ExplorerLayout";

export default function ExplorerPage() {
  const ctx = useAuthContext();

  if (ctx.status !== "authenticated") {
    return (
      <div className="h-full bg-[var(--vp-bg-base)] flex items-center justify-center">
        <p className="text-[var(--vp-text-tertiary)]">Authenticating...</p>
      </div>
    );
  }

  return <ExplorerLayout />;
}
