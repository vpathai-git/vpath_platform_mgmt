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

- Startbar (`vpath-platform-mgmt` ist heute ein Console-Script mit Platzhalter,
  `README.md:50-58`)
- Links: Liste aller Instanzen mit **Typ** und **Grobzustand** — läuft / broken /
  sonstiges, auf einen Blick
- Klick öffnet die Detailansicht derselben Instanz
- **Uptime** gehört dazu

## Offene Punkte

- **S4 — Uptime wovon?** Box, k3s-Cluster, Plattformdienste oder Apps. Vier
  verschiedene Zahlen; bei einer NUC laufen sie auseinander (Box läuft seit Wochen,
  Cluster seit dem letzten Install, Apps seit dem letzten Redeploy). Eine davon ist
  gemeint — welche, entscheidet, was gemessen wird.
- **Bauform** — Python-TUI, lokale Weboberfläche, Electron? Das Projekt ist ein
  reines Python-Paket (`src/vpath_platform_mgmt/`, `pyproject.toml`); jede grafische
  Variante bringt eine Technologieentscheidung mit, die es dort noch nicht gibt.
- **Live oder Momentaufnahme?** Hängt an S6 (wie oft die Probe läuft). Eine Liste,
  die bei jedem Öffnen fünf SSH-Verbindungen aufbaut, fühlt sich anders an als eine,
  die einen zwischengespeicherten Stand zeigt — und ein zwischengespeicherter Stand,
  der als aktuell erscheint, ist genau die Sorte stiller Täuschung, die hier
  verboten ist.
- Zeigt die Konsole später auch den **Pin-Status**? Beide Werkzeuge beantworten
  „stimmt hier noch alles" für verschiedene Gegenstände. Nicht jetzt entscheiden,
  aber beim Zuschnitt nicht ausschließen.

## Reihenfolge

**Zuletzt.** Ein UI über einer unfertigen Probe zeigt Platzhalter und verdeckt genau
die Lücken, die dieser Request sichtbar machen soll.

## Blockiert durch

[status-probe](status-probe.issue.md) und mittelbar das Register aus
`../instance-management/`.
