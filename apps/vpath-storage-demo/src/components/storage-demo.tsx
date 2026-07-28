"use client";

import { useState } from "react";
import {
  useStorageRoots,
  useStorageListing,
  useCreateFolder,
  type StorageRoot,
  type FileEntry,
} from "@vpath/sdk";

// The folders this app DECLARES in vpath-app.yaml (spec.appStorage.folders).
// Authored here only to TEACH the three visibility modes next to the live
// surface — the platform, not this constant, is the source of the real roots
// (which arrive through useStorageRoots below).
const DECLARED_FOLDERS = [
  {
    name: "Notes",
    shared: "private",
    description: "Per-user private scratch space — visible only to its owner.",
  },
  {
    name: "Handbook",
    shared: "read",
    description: "Team-readable reference content the app publishes read-only.",
  },
  {
    name: "Uploads",
    shared: "readwrite",
    description: "Shared drop zone every member of the app can read and write.",
  },
] as const;

const panel = {
  borderColor: "var(--vp-border-subtle)",
} as const;
const primary = { color: "var(--vp-text-primary)" } as const;
const secondary = { color: "var(--vp-text-secondary)" } as const;
const tertiary = { color: "var(--vp-text-tertiary)" } as const;
const errorColor = { color: "var(--vp-status-error)" } as const;

export function StorageDemo() {
  const [rootId, setRootId] = useState<string | null>(null);
  const [newFolder, setNewFolder] = useState("");
  const roots = useStorageRoots();
  const listing = useStorageListing(rootId, "");
  const createFolder = useCreateFolder();

  const selectedRoot = roots.data?.find((r) => r.id === rootId) ?? null;
  const canWrite = selectedRoot?.access === "readwrite";

  return (
    <div className="space-y-6">
      <section
        data-testid="storage-intro"
        className="rounded-lg border p-5"
        style={{ ...panel, backgroundColor: "var(--vp-bg-elevated)" }}
      >
        <h1 className="text-base font-semibold" style={primary}>
          Storage Demo — the Stores citizen
        </h1>
        <p className="mt-2 text-sm" style={secondary}>
          This app declares its storage folders in <code>vpath-app.yaml</code>{" "}
          (<code>spec.appStorage.folders</code>) and turns on{" "}
          <code>spec.capabilities.storageExplorer</code>. The platform
          provisions and serves those folders; the app only declares them and
          reads them through the SDK storage hooks — it never mounts a volume or
          builds a file service itself (CITIZENS.md §3).
        </p>
      </section>

      <section
        data-testid="storage-declared-folders"
        className="rounded-lg border p-5"
        style={panel}
      >
        <h2 className="text-sm font-semibold" style={primary}>
          Declared folders
        </h2>
        <p className="mt-1 text-xs" style={tertiary}>
          One per visibility mode. The platform derives the real storage roots
          below from exactly this declaration.
        </p>
        <ul className="mt-4 grid gap-3 md:grid-cols-3">
          {DECLARED_FOLDERS.map((folder) => (
            <li key={folder.name} className="rounded-md border p-4" style={panel}>
              <p className="text-sm font-medium" style={primary}>
                {folder.name}
              </p>
              <p className="mt-1 text-xs font-mono" style={secondary}>
                shared: {folder.shared}
              </p>
              <p className="mt-2 text-xs" style={tertiary}>
                {folder.description}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <section
        data-testid="storage-explorer"
        className="rounded-lg border p-5"
        style={panel}
      >
        <h2 className="text-sm font-semibold" style={primary}>
          Live storage roots
        </h2>
        <p className="mt-1 text-xs" style={tertiary}>
          Served by the platform storage API through the app&apos;s same-origin{" "}
          <code>/api/platform</code> proxy. No data is faked: if the API is
          unreachable this surface fails closed instead of showing an empty
          store.
        </p>

        <StorageRootsView
          roots={roots}
          rootId={rootId}
          onSelect={(id) => setRootId(id)}
        />

        {rootId ? (
          <ListingView listing={listing} rootId={rootId} />
        ) : null}

        {selectedRoot ? (
          <CreateFolderView
            rootId={selectedRoot.id}
            canWrite={canWrite}
            value={newFolder}
            onChange={setNewFolder}
            createFolder={createFolder}
          />
        ) : null}
      </section>
    </div>
  );
}

function StorageRootsView({
  roots,
  rootId,
  onSelect,
}: {
  roots: ReturnType<typeof useStorageRoots>;
  rootId: string | null;
  onSelect: (id: string) => void;
}) {
  if (roots.isPending) {
    return (
      <p data-testid="storage-loading" className="mt-4 text-sm" style={secondary}>
        Contacting the platform storage API…
      </p>
    );
  }
  if (roots.isError) {
    return (
      <div data-testid="storage-unavailable" className="mt-4 text-sm" style={errorColor}>
        <p className="font-medium">Platform storage API unreachable.</p>
        <p className="mt-1" style={secondary}>
          Fail-closed: no folders can be listed and nothing is invented.{" "}
          {roots.error.message}
        </p>
      </div>
    );
  }
  if (!roots.data.length) {
    return (
      <p data-testid="storage-empty" className="mt-4 text-sm" style={secondary}>
        No storage roots are visible for you yet. Once the platform provisions
        the declared folders they appear here.
      </p>
    );
  }
  return (
    <ul data-testid="storage-roots" className="mt-4 flex flex-wrap gap-2">
      {roots.data.map((root: StorageRoot) => (
        <li key={root.id}>
          <button
            type="button"
            onClick={() => onSelect(root.id)}
            aria-pressed={root.id === rootId}
            className="rounded-full border px-3 py-1 text-xs font-medium"
            style={{
              ...panel,
              color: "var(--vp-text-secondary)",
              backgroundColor:
                root.id === rootId ? "var(--vp-bg-elevated)" : "transparent",
            }}
          >
            {root.label} · {root.access}
          </button>
        </li>
      ))}
    </ul>
  );
}

function ListingView({
  listing,
  rootId,
}: {
  listing: ReturnType<typeof useStorageListing>;
  rootId: string;
}) {
  if (listing.isPending) {
    return (
      <p data-testid="storage-listing-loading" className="mt-4 text-sm" style={secondary}>
        Listing {rootId}…
      </p>
    );
  }
  if (listing.isError) {
    return (
      <p data-testid="storage-listing-error" className="mt-4 text-sm" style={errorColor}>
        Could not list {rootId}: {listing.error.message}
      </p>
    );
  }
  if (!listing.data.length) {
    return (
      <p data-testid="storage-listing-empty" className="mt-4 text-sm" style={secondary}>
        {rootId} is empty.
      </p>
    );
  }
  return (
    <ul data-testid="storage-listing" className="mt-4 space-y-1">
      {listing.data.map((entry: FileEntry) => (
        <li
          key={entry.name}
          className="flex items-center justify-between text-sm"
          style={secondary}
        >
          <span style={primary}>
            {entry.type === "directory" ? "📁" : "📄"} {entry.name}
          </span>
          <span className="text-xs font-mono" style={tertiary}>
            {entry.type === "directory" ? "dir" : `${entry.size} B`}
          </span>
        </li>
      ))}
    </ul>
  );
}

function CreateFolderView({
  rootId,
  canWrite,
  value,
  onChange,
  createFolder,
}: {
  rootId: string;
  canWrite: boolean;
  value: string;
  onChange: (value: string) => void;
  createFolder: ReturnType<typeof useCreateFolder>;
}) {
  if (!canWrite) {
    return (
      <p data-testid="storage-readonly" className="mt-5 text-xs" style={tertiary}>
        This root is read-only, so no folders can be created here.
      </p>
    );
  }
  return (
    <form
      data-testid="storage-create"
      className="mt-5 flex flex-wrap items-center gap-2"
      onSubmit={(event) => {
        event.preventDefault();
        if (value.trim()) {
          createFolder.mutate({ rootId, path: value.trim() });
        }
      }}
    >
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="new-folder"
        className="rounded-md border px-3 py-1 text-sm"
        style={{ ...panel, ...primary, backgroundColor: "var(--vp-bg-elevated)" }}
      />
      <button
        type="submit"
        disabled={!value.trim() || createFolder.isPending}
        className="rounded-md border px-3 py-1 text-sm font-medium disabled:opacity-50"
        style={{ ...panel, color: "var(--vp-accent)" }}
      >
        {createFolder.isPending ? "Creating…" : "Create folder"}
      </button>
      {createFolder.isError ? (
        <span className="text-xs" style={errorColor}>
          {createFolder.error.message}
        </span>
      ) : createFolder.isSuccess ? (
        <span className="text-xs" style={{ color: "var(--vp-status-success)" }}>
          Folder created.
        </span>
      ) : null}
    </form>
  );
}
