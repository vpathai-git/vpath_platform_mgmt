# Strang: mgmt-console — die drei Achsen als Primärziele

**Einstiegspunkt.** Wer nur diese Datei liest, ist auf Stand.

Sprache: Deutsch (Dateinamen, Code, Bezeichner Englisch) · Angelegt: 2026-07-27 12:52
Projekt: `vpath_platform_mgmt` (dieses Repository)
Status: **Zielbild verankert (README) — Umsetzung nicht begonnen**

Vorbereitet vom zuarbeitenden Agenten. Selbst-Containment ist hier Anforderung:
Dieser Strang und der README-Abschnitt müssen ohne den Koordinations-Workspace
verständlich sein.

---

## Die drei Achsen (Kurzform — Volltext im README, Abschnitt „Primary goals")

1. **Dualismus** — eine generische Sicht über Server- und Standalone-Plattformen
   (Status, Apps, State, Operationen) + typspezifische Panels (Server: Stack-
   Status, Load …; Standalone: Login, Size-on-Disk …) + OntoGate-Viewer-Link.
2. **Instanzen: CRUD + Health** — Anlage aus **versionierten Typ-Templates**
   (`nuc` | `standalone` | `remote`/win-claas), Instanz-Daten bleiben gitignored;
   Fehlerlogs, Uptime, State, History. Vier Ortsfragen je Instanz: Host +
   Filesystem? Build-Prozess? Quell-Repos des App-Builds? Container-Images?
3. **Apps: CRUD + Health** — build/deploy/undeploy/update (forceful), koexistente
   Versionen; Iteration 1: eine Bestands-App (Explorer) isoliert managen;
   Manifest-Inspektion; Sichtbarkeit Frontend/Backend/Workflow-Templates/Bundles.

---

## Was schon existiert und worauf aufgebaut wird (alles in diesem Repo)

- `src/vpath_platform_mgmt/instances/` — Register, Selektor, Transport, Probe
  (gemergt 2026-07-27, `aed0003`/`5e0cebe`; Tests in `tests/instances/`). Das
  ist der Unterbau von Achse 2: Health und Register laufen; **Templates, CRUD
  der Typen, Logs/History fehlen.**
- `analysis/instance-management/` + `analysis/instance-status/` — die beiden
  abgeschlossenen Vorgänger-Stränge (Registerumzug, Namensschema, Probe,
  Uptime-Definition: Plattformdienste als Hauptzahl, Detail alle vier Uhren).
- Entschieden und hier dokumentiert: Signaletik (Planeten für Server ab
  `mercury8`, NATO ab `alpha` für Standalones), UI-Bauform grafisch
  (Master-Detail: Liste links, Detail bei Klick).

## Was die Achsen NEU verlangen (Delta, je Achse)

| Achse | Neu gegenüber Bestand |
|---|---|
| 1 | Die generische Abstraktion über beide Typen — bisher kennt die Probe Typen, aber es gibt keine vereinheitlichte Sicht; OntoGate-Viewer-Anbindung (dieses Repo hat selbst noch kein `.ontogate/`) |
| 2 | **Typ-Templates** als versionierte Anlagevorlagen; dritter Typ `remote` (win-claas); Fehlerlogs + History (bisher nur Momentaufnahme); die vier Ortsfragen als Registerfelder |
| 3 | Der gesamte App-Teil — das ist die Herauslösung der Build/Deploy-Pipeline aus dem Serverprojekt (der Kernauftrag dieses Repos, Jira EIP-222). Iteration 1 bewusst klein: Explorer isoliert |

## Leitplanken

- **Self-Containment** (Nutzeranforderung, wörtlich): Repo- und Jira-Texte müssen
  für Leser ohne globalen Kontext tragen. Verweise auf Repos + Commits, nie auf
  lokale Verzeichnisse fremder Arbeitsplätze.
- Instanz-**Daten** gitignored (Payload), Typ-**Templates** versioniert — die
  Trennung ist Achsen-Definition, nicht Implementierungsdetail.
- Iteration-1-Schnitt für Achse 3 ist verbindlich klein: **eine** Bestands-App
  (Explorer) isoliert managebar; nicht die ganze Pipeline auf einmal.

## Jira-Vorlage (kopierfertig für EIP-222, self-contained, englisch)

> **Primary goals — the three axes of the management console**
> (1) *Dualism*: manage server AND standalone platform instances through one
> generic view (status, apps, state, operations) plus type-specific panels
> (server: stack status, load; standalone: login, size on disk) and an OntoGate
> viewer link. (2) *Instances — CRUD + health*: instances are created from
> versioned type templates (`nuc`, `standalone`, `remote`/win-claas) while
> instance data stays a gitignored local register; error logs, uptime, state,
> history; the register answers where each instance lives (host + filesystem),
> where its build process lives, which source repositories the build pulls apps
> from, and where the container images live. (3) *Apps — CRUD + health*: build,
> deploy, undeploy, update (forceful if needed); coexisting versions; iteration 1:
> one existing in-server app (Explorer) manageable as an isolated app; manifest
> inspection; visibility for frontend part, backend part, workflow templates,
> and bundles (app + workflow templates as one package).
> Foundation already merged: the instance layer (registry, selector, transport,
> probe) in `vpathai-git/vpath_platform_mgmt` @ `5e0cebe`.

Die Übertragung nach Jira läuft über den zweistufigen Sync (Vorschau → Freigabe);
dieser Block ist die vorbereitete Karte dafür.

## Die vier Zuschnittsfragen — **alle entschieden 2026-07-27 (Interview)**

| # | Entscheidung |
|---|---|
| **M1** | **Deklarativ + kind-Hooks.** Ein versioniertes Template-YAML je Typ im Register-Schema (Pflichtfelder, Defaults); typspezifische Logik in den vorhandenen kind-Hooks (`transport.py`, `probe.py`). Anlage = Vorlage kopieren, Payload füllen, validieren. |
| **M2** | **Struktur jetzt, Erhebung als Auftrag.** Das `remote`-Template (win-claas) wird mit den bekannten Feldern strukturiert und als **declared, unproven** markiert; die Feld-Erhebung ist ein eigener Auftrag → [remote-type-survey](remote-type-survey.issue.md). Kein Raten. |
| **M3** | **Link auf den OntoGate-UI-Server.** Der Link je Instanz/App zeigt auf den OntoGate-UI-Server, der die OntoGate-Sicht **aus dem jeweiligen Projekt** liefert (Server-, Standalone-, App-/Workflow-spezifisch) — *wenn vorhanden*; fehlende Sicht wird ehrlich als fehlend gezeigt. **Nicht verifiziert:** ob ein solcher UI-Server heute existiert oder Teil des Bauauftrags wird — zu erheben (vpath_ontogate). |
| **M4** | **Eigene Quick-Extraktion zuerst.** Arsany arbeitet parallel an seiner Extraktion (Quick-Solution). Iteration 1: **wir extrahieren die Explorer-App selbst und demonstrieren die Deploybarkeit** über die Konsole; **später Umzug auf Arsanys App-Repo als Quelle** → [explorer-quick-extraction](explorer-quick-extraction.issue.md). Die zeitweise zweite Variante ist eine **bewusste, befristete Ausnahme von Regel „keine zwei Varianten"** — vom Nutzer angeordnet, mit definiertem Ablauf (Umzug auf Arsanys Basis). |

---

## Backlog — validiert, bewusst post-MVP (Entscheidung 2026-07-27)

Fünf Dimensionen des klassischen Serverbetriebs, in der Lückenanalyse benannt,
vom Nutzer **alle als valide bestätigt** und in den Backlog gestellt — nicht im
MVP (drei Achsen, Ziel Ende der Woche):

| # | Dimension | Kernpunkt · Beleg |
|---|---|---|
| B1 | **Plattform-Lebenszyklus** | Der Stack zwischen Box und Apps (k3s, Keycloak, OpenFGA, Dapr) hat keinen CRUD: install/upgrade/rollback/uninstall/backup-restore. Projektauftrag nennt uninstall (README:3); Server hat `deploy-backup-jobs.sh`. |
| B2 | **Katalog & Kompatibilität** | „Apps raussuchen" braucht einen Katalog + Kompatibilitätswahrheit (Pin-Kette: App↔SDK↔Server) + Transportweg auf airgapped Boxen. Katalogkonzept existiert plattformseitig (Standalone-Arming). |
| B3 | **Nutzer-/Zugangsverwaltung** | Keycloak-User, SSH-Keys, Rollen — der häufigste Wartungsvorgang; heute manueller Admin-Handgriff (vm5-Manual). |
| B4 | **Daten-Lebenszyklus** | Undeploy/Update ohne Datenkonzept; Box-Wiederherstellung. Empfindlichkeit belegt durch den Run-ID-Überschreib-Fund (workflow-citizen-Strang). |
| B5 | **Sicherheits-Wartungstakt** | CVE-Wellen (gelebt: Next-15-Migration, Trivy-Gates), Zertifikats-/Secret-Rotation. Der reale Grund, warum „über die Zeit" Arbeit anfällt. |

## Dateien

- `raw/2026-07-27_1252_three-axes.md` — Wortlaut + Dekodierung
- README-Abschnitt „Primary goals — the three axes" — der verbindliche Zieltext
- `explorer-quick-extraction.issue.md` — Iteration 1 von Achse 3, dispatchbar
- `remote-type-survey.issue.md` — Erhebung des win-claas-Typs
- Vorgänger: `../instance-management/`, `../instance-status/`

## Entscheidungslog

- 27.07.: Strang angelegt; die drei Achsen als Primärziele im README verankert
  (self-contained). Keine Umsetzungsentscheidung getroffen.
- 27.07. (Interview): **M1–M4 entschieden** — Templates deklarativ + kind-Hooks;
  remote strukturiert als *declared, unproven* mit Erhebungsauftrag; OntoGate-
  Link zeigt auf den OntoGate-**UI-Server** (projektspezifische Sicht, ehrliches
  Fehlen); Iteration 1 = **eigene Quick-Extraktion des Explorers + Deploy-Demo**,
  später Umzug auf Arsanys App-Repo (befristete, angeordnete Regel-8-Ausnahme).
  Namensschreibweise bestätigt: **Arsany** (frühere Diktat-Form „Arsene").
- 27.07. (13:29): **Fünf Betriebs-Dimensionen validiert und in den Backlog
  gestellt** (B1–B5, s. o.) — MVP bleiben die drei Achsen, Ziel Ende der Woche.
- 27.07. (14:15): **Nach Jira gespiegelt** (Sync-Lauf 2, freigegebene Vorschau):
  Zielbild als Block „Stand 27.07.2026" in der Beschreibung von **EIP-222**;
  Umsetzungs-To-do als **EIP-248** („Management-Konsole MVP", unter EIP-163,
  Andre); der Run-Folder-Fund als **EIP-249** (unter EIP-134).
