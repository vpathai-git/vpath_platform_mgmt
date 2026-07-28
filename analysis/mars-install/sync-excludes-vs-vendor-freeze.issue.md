# Issue: Full-Tree-Sync wirft Dateien weg, die das Vendor-Freeze-Gate hasht

Status: **Wurzel am HEAD gelöst** (nachgemessen 2026-07-28: 0 getrackte
`settings.local.json` im Vendor-Baum @ Server `origin/main 47d9d23ea` —
`git ls-tree`; Folge des Substrat-Schnitts S55/Masterplan). **Auf dem
Flotten-Pin `1a2c51dc` lebt die Kollision weiter**, bis die Flotte den Stand
hebt — der mars12-Behelf (Restore der zwei Dateien) bleibt bis dahin nötig.
BP11-Schwäche bleibt eigenes Issue. ·
Herkunft: mars12-Install 2026-07-28, `buildWorkflowBase` rot nach 23m 5s

**Befund:** `lib/vm.sh:2638` schließt `.claude/` aus dem From-within-Sync nach
`/workspace` aus. Das Fork-Provenance-Freeze hasht aber den gesamten vendorten
Baum `platform_infra/docker/workflow-base/vendor/vpath_agents/src/vpath_workflows` —
und der gepinnte Commit `1a2c51dc7891` TRACKT dort zwei
`.claude/settings.local.json` (unter `processors/generic_json_etl/` und
`processors/polarion_publisher/`; `git ls-tree` bestätigt). Auf jeder
From-within-NUC fehlen die zwei Dateien in `/workspace`, der actual-Hash weicht
vom declared ab, `buildWorkflowBase` stirbt. Kein Box-Spezifikum.

**Wurzel, eine Ebene tiefer:** Dass `.claude/settings.local.json` überhaupt
getrackt im Vendor-Baum liegt, ist der eigentliche Defekt — lokale
Claude-Session-Dateien gehören nicht ins Repo; der Sync-Exclude existiert
genau deshalb. Zwei legitime Mechanismen kollidieren nur, weil der Vendor-Baum
etwas Illegitimes enthält.

**Nicht-Wege, ausdrücklich:** `fork-provenance.sh --write` würde das Label auf
den verstümmelten Baum umschreiben (Gate-Waschen); die Exclude-Liste zu ändern
wäre ein Pipeline-Eingriff am Symptom. Behelf auf mars12 (2026-07-28,
Koordinator-GO): die zwei getrackten Dateien aus dem Checkout nach
`/workspace` wiederhergestellt, Freeze read-only vorab verifiziert.

**Ziel (Server-Strom):** settings.local.json aus dem Vendor-Baum entfernen und
das Freeze-Label sauber neu schreiben — dann verschwindet die Kollision an der
Wurzel. Zusammen mit [bp11-index-vs-tree](bp11-index-vs-tree.issue.md) und den
übrigen Spur-Punkten aus `REPORT-2026-07-28.md`.
