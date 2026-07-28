# FINDINGS.md — the pin ledger (gap ↔ pin, both directions)

Brownfield adoption: every inventory gap is pinned below. A pin only
disappears by working the gap off (map + validate + prove), never by
deleting the line — the PIN row reds a pin without a gap AND a gap
without a pin.

## Open pins

- PIN unmapped:src.app.api.healthz.route — inventoried, not yet mapped
- PIN unmapped:src.app.api.platform.[...path].route — inventoried, not yet mapped
- PIN unmapped:src.app.api.version.route — inventoried, not yet mapped
- PIN unmapped:src.app.auth.error.page — inventoried, not yet mapped
- PIN unmapped:src.app.auth.signin.page — inventoried, not yet mapped
- PIN unmapped:src.app.auth.signout.page — inventoried, not yet mapped
- PIN unmapped:src.app.layout — inventoried, not yet mapped
- PIN unmapped:src.app.page — inventoried, not yet mapped
- PIN unmapped:src.components.ConfirmDialog — inventoried, not yet mapped
- PIN unmapped:src.components.ContextMenu — inventoried, not yet mapped
- PIN unmapped:src.components.ExplorerLayout — inventoried, not yet mapped
- PIN unmapped:src.components.FileCard — inventoried, not yet mapped
- PIN unmapped:src.components.FolderView — inventoried, not yet mapped
- PIN unmapped:src.components.NewFolderDialog — inventoried, not yet mapped
- PIN unmapped:src.components.RenameDialog — inventoried, not yet mapped
- PIN unmapped:src.components.Toast — inventoried, not yet mapped
- PIN unmapped:src.components.ToastProvider — inventoried, not yet mapped
- PIN unmapped:src.components.Toolbar — inventoried, not yet mapped
- PIN unmapped:src.components.TreePane — inventoried, not yet mapped
- PIN unmapped:src.components.providers — inventoried, not yet mapped
- PIN unmapped:src.hooks.useClipboard — inventoried, not yet mapped
- PIN unmapped:src.hooks.useExplorerState — inventoried, not yet mapped
- PIN unmapped:src.hooks.useFileSystem — inventoried, not yet mapped
- PIN unmapped:src.hooks.useToast — inventoried, not yet mapped
- PIN unmapped:src.pages.api.auth.[...nextauth] — inventoried, not yet mapped
- PIN unmapped:src.pages.api.sso.clear-nextauth — inventoried, not yet mapped
- PIN unmapped:src.viewers.BinaryViewer — inventoried, not yet mapped
- PIN unmapped:src.viewers.HtmlViewer — inventoried, not yet mapped
- PIN unmapped:src.viewers.ImageViewer — inventoried, not yet mapped
- PIN unmapped:src.viewers.JsonViewer — inventoried, not yet mapped
- PIN unmapped:src.viewers.MarkdownViewer — inventoried, not yet mapped
- PIN unmapped:src.viewers.PdfViewer — inventoried, not yet mapped
- PIN unmapped:src.viewers.PlainTextViewer — inventoried, not yet mapped
- PIN unmapped:src.viewers.ViewerModal — inventoried, not yet mapped
- PIN unmapped:src.viewers.ViewerProps — inventoried, not yet mapped
- PIN unmapped:src.viewers.ViewerRegistry — inventoried, not yet mapped
- PIN unmapped:src.viewers.YamlViewer — inventoried, not yet mapped
- PIN reverse_draft:src.app.api.healthz.route — concept doc is a hypothesis stub
- PIN reverse_draft:src.app.api.platform.[...path].route — concept doc is a hypothesis stub
- PIN reverse_draft:src.app.api.version.route — concept doc is a hypothesis stub
- PIN reverse_draft:src.app.auth.error.page — concept doc is a hypothesis stub
- PIN reverse_draft:src.app.auth.signin.page — concept doc is a hypothesis stub
- PIN reverse_draft:src.app.auth.signout.page — concept doc is a hypothesis stub
- PIN reverse_draft:src.app.layout — concept doc is a hypothesis stub
- PIN reverse_draft:src.app.page — concept doc is a hypothesis stub
- PIN reverse_draft:src.components.ConfirmDialog — concept doc is a hypothesis stub
- PIN reverse_draft:src.components.ContextMenu — concept doc is a hypothesis stub
- PIN reverse_draft:src.components.ExplorerLayout — concept doc is a hypothesis stub
- PIN reverse_draft:src.components.FileCard — concept doc is a hypothesis stub
- PIN reverse_draft:src.components.FolderView — concept doc is a hypothesis stub
- PIN reverse_draft:src.components.NewFolderDialog — concept doc is a hypothesis stub
- PIN reverse_draft:src.components.RenameDialog — concept doc is a hypothesis stub
- PIN reverse_draft:src.components.Toast — concept doc is a hypothesis stub
- PIN reverse_draft:src.components.ToastProvider — concept doc is a hypothesis stub
- PIN reverse_draft:src.components.Toolbar — concept doc is a hypothesis stub
- PIN reverse_draft:src.components.TreePane — concept doc is a hypothesis stub
- PIN reverse_draft:src.components.providers — concept doc is a hypothesis stub
- PIN reverse_draft:src.hooks.useClipboard — concept doc is a hypothesis stub
- PIN reverse_draft:src.hooks.useExplorerState — concept doc is a hypothesis stub
- PIN reverse_draft:src.hooks.useFileSystem — concept doc is a hypothesis stub
- PIN reverse_draft:src.hooks.useToast — concept doc is a hypothesis stub
- PIN reverse_draft:src.pages.api.auth.[...nextauth] — concept doc is a hypothesis stub
- PIN reverse_draft:src.pages.api.sso.clear-nextauth — concept doc is a hypothesis stub
- PIN reverse_draft:src.viewers.BinaryViewer — concept doc is a hypothesis stub
- PIN reverse_draft:src.viewers.HtmlViewer — concept doc is a hypothesis stub
- PIN reverse_draft:src.viewers.ImageViewer — concept doc is a hypothesis stub
- PIN reverse_draft:src.viewers.JsonViewer — concept doc is a hypothesis stub
- PIN reverse_draft:src.viewers.MarkdownViewer — concept doc is a hypothesis stub
- PIN reverse_draft:src.viewers.PdfViewer — concept doc is a hypothesis stub
- PIN reverse_draft:src.viewers.PlainTextViewer — concept doc is a hypothesis stub
- PIN reverse_draft:src.viewers.ViewerModal — concept doc is a hypothesis stub
- PIN reverse_draft:src.viewers.ViewerProps — concept doc is a hypothesis stub
- PIN reverse_draft:src.viewers.ViewerRegistry — concept doc is a hypothesis stub
- PIN reverse_draft:src.viewers.YamlViewer — concept doc is a hypothesis stub
- PIN to_be:K01 — expression backlog twin born red (strict xfail)
- PIN hull_as_is:C-given-storage-hooks — foundation contract fails today (pinned as_is)

## requirement-seam-2026-07-24

Explorer is specified by its manifest (vpath-app.yaml) and its source, not an external requirement catalog; n/a on record — mirrors the monorepo book decision requirement-seam-2026-07-17.

Decided 2026-07-24 by the operator invoking `new_app.py --adopt` — the
--seam-record/--seam-note flags are the decision act, this section
records it. Status `n/a`: this book declares no requirement catalog
of its own. Flip the spine block to `covered` by hand if one ever
exists; the SEAM row reds when this anchor moves or disappears.
