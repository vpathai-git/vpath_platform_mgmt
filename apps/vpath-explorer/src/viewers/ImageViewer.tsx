"use client";

import { useState } from "react";
import type { ViewerProps } from "./ViewerProps";

export default function ImageViewer({ filename, contentUrl }: ViewerProps) {
  const [zoomed, setZoomed] = useState(false);

  return (
    <div
      className="flex items-center justify-center w-full h-full p-4 overflow-auto"
      data-testid="image-viewer"
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={contentUrl}
        alt={filename}
        onClick={() => setZoomed(!zoomed)}
        className={`transition-transform cursor-pointer ${
          zoomed
            ? "max-w-none max-h-none"
            : "max-w-full max-h-full object-contain"
        }`}
        style={zoomed ? { transform: "scale(1)" } : undefined}
      />
    </div>
  );
}
