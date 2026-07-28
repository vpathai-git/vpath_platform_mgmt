import { lazy, type ComponentType } from "react";
import type { ViewerProps } from "./ViewerProps";

type ViewerComponent = ComponentType<ViewerProps>;

const registry: Record<string, React.LazyExoticComponent<ViewerComponent>> = {
  md: lazy(() => import("./MarkdownViewer")),
  txt: lazy(() => import("./PlainTextViewer")),
  log: lazy(() => import("./PlainTextViewer")),
  json: lazy(() => import("./JsonViewer")),
  yaml: lazy(() => import("./YamlViewer")),
  yml: lazy(() => import("./YamlViewer")),
  html: lazy(() => import("./HtmlViewer")),
  htm: lazy(() => import("./HtmlViewer")),
  jpg: lazy(() => import("./ImageViewer")),
  jpeg: lazy(() => import("./ImageViewer")),
  png: lazy(() => import("./ImageViewer")),
  gif: lazy(() => import("./ImageViewer")),
  svg: lazy(() => import("./ImageViewer")),
  webp: lazy(() => import("./ImageViewer")),
  pdf: lazy(() => import("./PdfViewer")),
};

export function getViewer(filename: string): React.LazyExoticComponent<ViewerComponent> | null {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  return registry[ext] ?? null;
}
