"use client";

import type { ViewerProps } from "./ViewerProps";

export default function PdfViewer({ contentUrl, filename }: ViewerProps) {
  return (
    <div className="w-full h-full" data-testid="pdf-viewer">
      <iframe
        src={contentUrl}
        className="w-full h-full border-0"
        title={filename}
      />
    </div>
  );
}
