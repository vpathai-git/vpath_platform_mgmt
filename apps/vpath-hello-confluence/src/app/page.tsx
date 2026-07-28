"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, FileText } from "lucide-react";
import { useVpathQuery } from "@/components/providers";

interface Space {
  id: string;
  key: string;
  name: string;
  type: string;
}
interface PageNode {
  id: string;
  title: string;
}

const muted = { color: "var(--vp-text-secondary)" } as const;
const subtle = { borderColor: "var(--vp-border-subtle)" } as const;

export default function HelloConfluencePage() {
  const status = useVpathQuery<{ bound: boolean }>("/api/confluence/resource/status");

  if (status.isLoading) return <Hint testid="loading">Loading…</Hint>;
  // The platform's resource gate rejects proxied calls FAIL-CLOSED with 401
  // (bind_required) while no Confluence credential is bound — cluster and
  // standalone share this contract, so for this app a 401 IS the not-bound
  // state, not an outage (vpath_server#22).
  if (status.error?.message === "Unauthorized") return <NotBound />;
  if (status.error) return <Hint testid="status-error">Couldn’t reach the Confluence service.</Hint>;
  if (!status.data?.bound) return <NotBound />;
  return <Browser />;
}

function NotBound() {
  return (
    <section data-testid="not-bound" className="rounded-lg border px-6 py-8" style={subtle}>
      <h1 className="text-base font-semibold" style={{ color: "var(--vp-text-primary)" }}>
        Confluence isn’t connected yet
      </h1>
      <p className="mt-2 text-sm" style={muted}>
        A platform administrator binds the <strong>Confluence</strong> credential for this app.
        Once bound, the spaces you can access appear here — no token is ever entered in this app.
      </p>
    </section>
  );
}

function Browser() {
  const spaces = useVpathQuery<{ spaces: Space[] }>("/api/confluence/spaces");
  const [selected, setSelected] = useState<Space | null>(null);

  if (spaces.isLoading) return <Hint testid="spaces-loading">Loading spaces…</Hint>;
  if (spaces.error) return <Hint testid="spaces-error">Couldn’t load spaces.</Hint>;

  const list: Space[] = spaces.data?.spaces ?? [];
  return (
    <div className="grid grid-cols-[18rem_1fr] gap-6">
      <nav data-testid="space-list" className="flex flex-col gap-1">
        <h2 className="mb-1 text-xs font-semibold uppercase tracking-wide" style={muted}>
          Spaces ({list.length})
        </h2>
        {list.map((s) => (
          <button
            key={s.id}
            data-testid="space-row"
            onClick={() => setSelected(s)}
            className="rounded-md px-3 py-2 text-left text-sm"
            style={{
              color: "var(--vp-text-primary)",
              backgroundColor:
                selected?.id === s.id ? "var(--vp-bg-hover)" : "transparent",
            }}
          >
            <span className="font-medium">{s.name}</span>
            <span className="ml-2 text-xs" style={muted}>{s.key}</span>
          </button>
        ))}
      </nav>

      <section data-testid="page-tree">
        {selected ? (
          <>
            <h2 className="mb-2 text-sm font-semibold" style={{ color: "var(--vp-text-primary)" }}>
              {selected.name}
            </h2>
            <PageChildren path={`/api/confluence/spaces/${selected.id}/pages`} depth={0} />
          </>
        ) : (
          <Hint testid="tree-empty">Select a space to see its page structure.</Hint>
        )}
      </section>
    </div>
  );
}

function PageChildren({ path, depth }: { path: string; depth: number }) {
  const q = useVpathQuery<{ pages: PageNode[] }>(path);
  if (q.isLoading) return <Hint testid="pages-loading" inset={depth}>Loading…</Hint>;
  if (q.error) return <Hint testid="pages-error" inset={depth}>Couldn’t load pages.</Hint>;
  const pages: PageNode[] = q.data?.pages ?? [];
  if (pages.length === 0)
    return <Hint testid="pages-none" inset={depth}>No pages.</Hint>;
  return (
    <ul>
      {pages.map((p) => (
        <PageRow key={p.id} page={p} depth={depth} />
      ))}
    </ul>
  );
}

function PageRow({ page, depth }: { page: PageNode; depth: number }) {
  const [open, setOpen] = useState(false);
  return (
    <li data-testid="page-node">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-1.5 rounded-md px-2 py-1 text-left text-sm"
        style={{ color: "var(--vp-text-primary)", paddingLeft: `${depth * 1.25 + 0.5}rem` }}
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <FileText size={14} style={muted} />
        <span>{page.title}</span>
      </button>
      {open && <PageChildren path={`/api/confluence/pages/${page.id}/children`} depth={depth + 1} />}
    </li>
  );
}

function Hint({
  children,
  testid,
  inset = 0,
}: {
  children: React.ReactNode;
  testid: string;
  inset?: number;
}) {
  return (
    <p
      data-testid={testid}
      className="px-2 py-1 text-sm"
      style={{ ...muted, paddingLeft: `${inset * 1.25 + 0.5}rem` }}
    >
      {children}
    </p>
  );
}
