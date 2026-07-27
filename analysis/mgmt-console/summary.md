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

## Offene Punkte

| # | Frage |
|---|---|
| M1 | Typ-Template-Format: dasselbe Schema wie das Register (`kind`-getragen) oder eigenes Artefakt je Typ? |
| M2 | `remote`/win-claas: Zugangsweg und Deploy-Pfad sind unerhoben — vor der Template-Definition erheben. |
| M3 | OntoGate-Viewer-Link: setzt `.ontogate/`-Adoption der Ziele voraus — auch dieses Repo hat noch keine. Reihenfolge? |
| M4 | Achse-3-Iteration-1 (Explorer isoliert) berührt die laufende Explorer-Extraktion ins eigene Repo — derselbe Gegenstand aus zwei Richtungen; Zuschnitt gehört koordiniert. |

---

## Dateien

- `raw/2026-07-27_1252_three-axes.md` — Wortlaut + Dekodierung
- README-Abschnitt „Primary goals — the three axes" — der verbindliche Zieltext
- Vorgänger: `../instance-management/`, `../instance-status/`

## Entscheidungslog

- 27.07.: Strang angelegt; die drei Achsen als Primärziele im README verankert
  (self-contained). Keine Umsetzungsentscheidung getroffen.
