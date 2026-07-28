"use client";

import { useState, useCallback } from "react";
import { useCopyItem, useRenameItem } from "./useFileSystem";
import { useToast } from "./useToast";

type ClipboardAction = "copy" | "cut";

type ClipboardState = {
  action: ClipboardAction;
  rootId: string;
  paths: string[];
} | null;

export function useClipboard() {
  const [clipboard, setClipboard] = useState<ClipboardState>(null);
  const copyMutation = useCopyItem();
  const moveMutation = useRenameItem();
  const { toast } = useToast();

  const copy = useCallback((rootId: string, paths: string[]) => {
    setClipboard({ action: "copy", rootId, paths });
    toast("info", "Copied", `${paths.length} item(s) copied to clipboard`);
  }, [toast]);

  const cut = useCallback((rootId: string, paths: string[]) => {
    setClipboard({ action: "cut", rootId, paths });
    toast("info", "Cut", `${paths.length} item(s) cut to clipboard`);
  }, [toast]);

  const paste = useCallback(
    async (destPath: string) => {
      if (!clipboard) return;
      const { rootId, paths, action } = clipboard;

      for (const fromPath of paths) {
        const name = fromPath.split("/").pop() ?? fromPath;
        const toPath = destPath ? `${destPath}/${name}` : name;

        if (action === "copy") {
          await copyMutation.mutateAsync({ rootId, fromPath, toPath });
        } else {
          await moveMutation.mutateAsync({ rootId, fromPath, toPath });
        }
      }

      const verb = action === "copy" ? "Copied" : "Moved";
      toast("success", verb, `${paths.length} item(s) ${verb.toLowerCase()}`);

      if (action === "cut") {
        setClipboard(null);
      }
    },
    [clipboard, copyMutation, moveMutation, toast]
  );

  const clear = useCallback(() => setClipboard(null), []);

  return { clipboard, copy, cut, paste, clear };
}
