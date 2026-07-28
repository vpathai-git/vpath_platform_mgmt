# Issue: Die Install-Pipeline schreibt Plattform-Passwörter im Klartext auf stdout

Status: draft (Server-Strom-Spur; Tragweite über mars12 hinaus) · Herkunft:
mars12-Install 2026-07-28, Pre-Commit-Secret-Scan der Lauf-Logs

**Befund:** Der Deploy-Lauf druckt vier Zugangsdaten-Werte im Klartext
(betroffene Nutzer: `admin_alain`, `kelly`, `usain`, `vpath-user`); einen
markiert die Pipeline selbst als „SECURITY WARNING: Creating/updating default
dev user with KNOWN PASSWORD" — und druckt ihn trotzdem. Konsequenz: **jedes
Install-Log dieser Pipeline trägt diese Passwörter**, einschließlich bereits
im Server-Repo committeter Logs früherer Läufe.

**Behandlung hier (2026-07-28):** Die vier Werte in den Strang-Logs durch
`<redacted-credential>` ersetzt, Nutzernamen und Zeilenstruktur erhalten,
sichtbare Redaktionsnotiz in jedem betroffenen Log — redigiert, nicht
stillschweigend gelöscht.

**Offen (Entscheidung Andre / Server-Strom):**
1. Pipeline-Fix: Zugangsdaten nie auf stdout — maskieren an der Quelle.
2. Bestandsaufnahme: welche committeten Logs im Server-Repo (und wo sonst)
   tragen die Werte heute?
3. Rotationsfrage für die vier betroffenen Konten (dev-User, LAN-only — die
   Einstufung ist eine Entscheidung, keine Messung).

**Methodennotiz aus demselben Scan:** Ein Substring-Match auf eine
vierstellige Zahl ist als Secret-Check untauglich (26 Falsch-Treffer in
sha256-Digests) — künftige Log-Scans brauchen wertgenaue Muster.
