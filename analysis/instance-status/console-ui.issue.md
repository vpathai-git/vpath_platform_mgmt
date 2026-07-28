# Issue: Konsolen-UI — Instanzliste mit Detailansicht

**Status:** draft · **Priorität:** P2 (hängt an Probe und Register)
**Herkunft:** `raw/2026-07-26_2045_instanzstatus-und-konsole.md`
(„am besten ein UI, das wir aufstarten und in dem jede Instanz … inklusive Uptime
und so, einfach gelistet wird … links sind die Instanzen und deren Typ, und wenn man
draufklickt, sieht man den Status im Detail")

## Der Befund, der dieses Issue prägt

**Dieses UI ist bereits beauftragt.** `vpath_platform_mgmt/pyproject.toml:10` und
`README.md:3` beschreiben das Projekt wörtlich als *„App build/deploy/health-check/
uninstall pipeline **and admin console** for VPath server instances"*, mit einer
Konsole für drei Rollen — App-Entwickler, Administratoren, Server-Entwickler
(`README.md:8-14`). Wahrheitsquelle laut README: **EIP-222**.

Der Request beschreibt damit **nicht ein neues Werkzeug, sondern den ersten
Bildschirm dieser Konsole.** Wer ihn als eigenständiges Statusfenster baut, stellt
zwei Oberflächen in ein Projekt, das eine beauftragt hat — Regel 8.

## Zweite Folge: eine offene EIP-222-Entscheidung fällt

`README.md:8` lässt die Bauform ausdrücklich offen: *„graphical or chatbot-assisted,
TBD"*. Der Request beschreibt eine grafische Oberfläche mit Master-Detail-Layout.
Das legt die Entscheidung faktisch fest.

Das ist in Ordnung — aber es ist eine Festlegung in einem Jira-Ticket, das Alex
führt, und sie gehört dort vermerkt, nicht nur hier.

## Anforderung, wie beschrieben

- Startbar — **erfüllt:** `vpath-console` bzw. `npm start` in
  `src/vpath_platform_mgmt/console/electron/`
- Links: Liste aller Instanzen mit **Typ** und **Grobzustand** — **erfüllt**
  (Name, Kind, Status-Badge)
- Klick öffnet die Detailansicht derselben Instanz — **erfüllt**
- **Uptime** gehört dazu — **offen, und als offen sichtbar.** Die Detailsicht
  führt die Zeile, sagt aber „not measured": die entschiedene Hauptzahl
  („Plattformdienste gesund seit") berechnet heute keine Probe. Der
  Install-Marker wird bewusst **nicht** als Uptime umetikettiert — er wäre eine
  plausible und falsche Zahl. Umsetzung gehört zu
  [status-probe](status-probe.issue.md).

## Offene Punkte

- ~~**S4 — Uptime wovon?**~~ **Entschieden 2026-07-27:** Hauptzahl =
  Plattformdienste (gesund seit); Detailansicht zeigt alle vier Uhren (Box, k3s,
  Plattform, Apps).
- ~~**Bauform** — Python-TUI, lokale Weboberfläche, Electron?~~ **Entschieden
  2026-07-28 (Nutzer): Electron.** Umgesetzt in
  `src/vpath_platform_mgmt/console/electron/`. Die Node-Kette in einem reinen
  Python-Repo ist der bewusst gezahlte Preis; eingegrenzt durch die Regel, dass
  die Shell ausschließlich rendert — jede Aussage kommt aus
  `python -m vpath_platform_mgmt.console.api --json`, damit das Fenster nichts
  behaupten kann, was `make check` nicht geprüft hat.
- ~~**Live oder Momentaufnahme?**~~ **Gelöst 2026-07-28 durch Trennung statt
  Wahl:** Das Öffnen liest nur das Register und zeigt jede Instanz als
  `NOT PROBED`; Messen ist ein eigener Knopf („Probe now"), und nur dann trägt
  die Sicht einen Zeitstempel (`probed_at`). Ein zwischengespeicherter Stand
  kann sich damit nicht als aktueller ausgeben.
- Zeigt die Konsole später auch den **Pin-Status**? Beide Werkzeuge beantworten
  „stimmt hier noch alles" für verschiedene Gegenstände. Nicht jetzt entscheiden,
  aber beim Zuschnitt nicht ausschließen.

## Reihenfolge

**Zuletzt.** Ein UI über einer unfertigen Probe zeigt Platzhalter und verdeckt genau
die Lücken, die dieser Request sichtbar machen soll.

## Blockiert durch

[status-probe](status-probe.issue.md) und mittelbar das Register aus
`../instance-management/`.
