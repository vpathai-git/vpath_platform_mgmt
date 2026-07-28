# ONTOLOGY.md — vpath-explorer concept catalog (the app domain Spine)

The human-form home of the app's CONCEPT PLANE (five rules R-A..R-E, kit
flavor of the baseline starter seed). The machine form lives in `spine.yaml`
(`entities:` / `concept_pins:`, source of truth) → `ontology.json` (generated
— never hand-edit). The hull plane (27 foundation contracts) is documented in
`README.md`; both planes are gated by the SAME `check.py`.

**The Spine IS the index** (R-C): every entity links its concept doc at a
fixed place — topic → kind → entity, no separate index file that could drift.

## Catalog

| entity | kind | path | concept doc |
|---|---|---|---|
| src.app.api.healthz.route | frontend | src/app/api/healthz/route.ts | [docs/concepts/frontend/src.app.api.healthz.route.md](../docs/concepts/frontend/src.app.api.healthz.route.md) |
| src.app.api.platform.[...path].route | frontend | src/app/api/platform/[...path]/route.ts | [docs/concepts/frontend/src.app.api.platform.[...path].route.md](../docs/concepts/frontend/src.app.api.platform.[...path].route.md) |
| src.app.api.version.route | frontend | src/app/api/version/route.ts | [docs/concepts/frontend/src.app.api.version.route.md](../docs/concepts/frontend/src.app.api.version.route.md) |
| src.app.auth.error.page | frontend | src/app/auth/error/page.tsx | [docs/concepts/frontend/src.app.auth.error.page.md](../docs/concepts/frontend/src.app.auth.error.page.md) |
| src.app.auth.signin.page | frontend | src/app/auth/signin/page.tsx | [docs/concepts/frontend/src.app.auth.signin.page.md](../docs/concepts/frontend/src.app.auth.signin.page.md) |
| src.app.auth.signout.page | frontend | src/app/auth/signout/page.tsx | [docs/concepts/frontend/src.app.auth.signout.page.md](../docs/concepts/frontend/src.app.auth.signout.page.md) |
| src.app.layout | frontend | src/app/layout.tsx | [docs/concepts/frontend/src.app.layout.md](../docs/concepts/frontend/src.app.layout.md) |
| src.app.page | frontend | src/app/page.tsx | [docs/concepts/frontend/src.app.page.md](../docs/concepts/frontend/src.app.page.md) |
| src.components.ConfirmDialog | frontend | src/components/ConfirmDialog.tsx | [docs/concepts/frontend/src.components.ConfirmDialog.md](../docs/concepts/frontend/src.components.ConfirmDialog.md) |
| src.components.ContextMenu | frontend | src/components/ContextMenu.tsx | [docs/concepts/frontend/src.components.ContextMenu.md](../docs/concepts/frontend/src.components.ContextMenu.md) |
| src.components.ExplorerLayout | frontend | src/components/ExplorerLayout.tsx | [docs/concepts/frontend/src.components.ExplorerLayout.md](../docs/concepts/frontend/src.components.ExplorerLayout.md) |
| src.components.FileCard | frontend | src/components/FileCard.tsx | [docs/concepts/frontend/src.components.FileCard.md](../docs/concepts/frontend/src.components.FileCard.md) |
| src.components.FolderView | frontend | src/components/FolderView.tsx | [docs/concepts/frontend/src.components.FolderView.md](../docs/concepts/frontend/src.components.FolderView.md) |
| src.components.NewFolderDialog | frontend | src/components/NewFolderDialog.tsx | [docs/concepts/frontend/src.components.NewFolderDialog.md](../docs/concepts/frontend/src.components.NewFolderDialog.md) |
| src.components.RenameDialog | frontend | src/components/RenameDialog.tsx | [docs/concepts/frontend/src.components.RenameDialog.md](../docs/concepts/frontend/src.components.RenameDialog.md) |
| src.components.Toast | frontend | src/components/Toast.tsx | [docs/concepts/frontend/src.components.Toast.md](../docs/concepts/frontend/src.components.Toast.md) |
| src.components.ToastProvider | frontend | src/components/ToastProvider.tsx | [docs/concepts/frontend/src.components.ToastProvider.md](../docs/concepts/frontend/src.components.ToastProvider.md) |
| src.components.Toolbar | frontend | src/components/Toolbar.tsx | [docs/concepts/frontend/src.components.Toolbar.md](../docs/concepts/frontend/src.components.Toolbar.md) |
| src.components.TreePane | frontend | src/components/TreePane.tsx | [docs/concepts/frontend/src.components.TreePane.md](../docs/concepts/frontend/src.components.TreePane.md) |
| src.components.providers | frontend | src/components/providers.tsx | [docs/concepts/frontend/src.components.providers.md](../docs/concepts/frontend/src.components.providers.md) |
| src.hooks.useClipboard | frontend | src/hooks/useClipboard.ts | [docs/concepts/frontend/src.hooks.useClipboard.md](../docs/concepts/frontend/src.hooks.useClipboard.md) |
| src.hooks.useExplorerState | frontend | src/hooks/useExplorerState.ts | [docs/concepts/frontend/src.hooks.useExplorerState.md](../docs/concepts/frontend/src.hooks.useExplorerState.md) |
| src.hooks.useFileSystem | frontend | src/hooks/useFileSystem.ts | [docs/concepts/frontend/src.hooks.useFileSystem.md](../docs/concepts/frontend/src.hooks.useFileSystem.md) |
| src.hooks.useToast | frontend | src/hooks/useToast.ts | [docs/concepts/frontend/src.hooks.useToast.md](../docs/concepts/frontend/src.hooks.useToast.md) |
| src.pages.api.auth.[...nextauth] | frontend | src/pages/api/auth/[...nextauth].ts | [docs/concepts/frontend/src.pages.api.auth.[...nextauth].md](../docs/concepts/frontend/src.pages.api.auth.[...nextauth].md) |
| src.pages.api.sso.clear-nextauth | frontend | src/pages/api/sso/clear-nextauth.ts | [docs/concepts/frontend/src.pages.api.sso.clear-nextauth.md](../docs/concepts/frontend/src.pages.api.sso.clear-nextauth.md) |
| src.viewers.BinaryViewer | frontend | src/viewers/BinaryViewer.tsx | [docs/concepts/frontend/src.viewers.BinaryViewer.md](../docs/concepts/frontend/src.viewers.BinaryViewer.md) |
| src.viewers.HtmlViewer | frontend | src/viewers/HtmlViewer.tsx | [docs/concepts/frontend/src.viewers.HtmlViewer.md](../docs/concepts/frontend/src.viewers.HtmlViewer.md) |
| src.viewers.ImageViewer | frontend | src/viewers/ImageViewer.tsx | [docs/concepts/frontend/src.viewers.ImageViewer.md](../docs/concepts/frontend/src.viewers.ImageViewer.md) |
| src.viewers.JsonViewer | frontend | src/viewers/JsonViewer.tsx | [docs/concepts/frontend/src.viewers.JsonViewer.md](../docs/concepts/frontend/src.viewers.JsonViewer.md) |
| src.viewers.MarkdownViewer | frontend | src/viewers/MarkdownViewer.tsx | [docs/concepts/frontend/src.viewers.MarkdownViewer.md](../docs/concepts/frontend/src.viewers.MarkdownViewer.md) |
| src.viewers.PdfViewer | frontend | src/viewers/PdfViewer.tsx | [docs/concepts/frontend/src.viewers.PdfViewer.md](../docs/concepts/frontend/src.viewers.PdfViewer.md) |
| src.viewers.PlainTextViewer | frontend | src/viewers/PlainTextViewer.tsx | [docs/concepts/frontend/src.viewers.PlainTextViewer.md](../docs/concepts/frontend/src.viewers.PlainTextViewer.md) |
| src.viewers.ViewerModal | frontend | src/viewers/ViewerModal.tsx | [docs/concepts/frontend/src.viewers.ViewerModal.md](../docs/concepts/frontend/src.viewers.ViewerModal.md) |
| src.viewers.ViewerProps | frontend | src/viewers/ViewerProps.ts | [docs/concepts/frontend/src.viewers.ViewerProps.md](../docs/concepts/frontend/src.viewers.ViewerProps.md) |
| src.viewers.ViewerRegistry | frontend | src/viewers/ViewerRegistry.ts | [docs/concepts/frontend/src.viewers.ViewerRegistry.md](../docs/concepts/frontend/src.viewers.ViewerRegistry.md) |
| src.viewers.YamlViewer | frontend | src/viewers/YamlViewer.tsx | [docs/concepts/frontend/src.viewers.YamlViewer.md](../docs/concepts/frontend/src.viewers.YamlViewer.md) |

Dependency edges (R-B checks declared == observed imports): none.

## Extension records (R-D — the permission ledger)

Editing a validated concept doc requires a re-pin in `spine.yaml` PLUS a dated
record line here naming the entity — the recorded, conscious act IS the
permission. Records:

(none yet — every concept doc is still a reverse_draft hypothesis)
