"use client";

/**
 * Storage hooks for the Explorer app — re-exported from @vpath/sdk.
 *
 * All file operations are scoped to the authenticated user (enforced server-side).
 * Root ID format: "{app}/{folder}" e.g. "vpath-explorer/Documents"
 */

export type { StorageRoot, FileEntry } from "@vpath/sdk";
export {
  useStorageRoots,
  useStorageListing,
  useStorageSearch,
  useUploadFile,
  useCreateFolder,
  useRenameItem,
  useCopyItem,
  useDeleteFile,
  useDeleteFolder,
} from "@vpath/sdk";
