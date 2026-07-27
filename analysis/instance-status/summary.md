# Strang: instance-status

**Einstiegspunkt.** Wer nur diese Datei liest, ist auf Stand.

Sprache: Deutsch (Dateinamen, Code, Bezeichner Englisch) · Angelegt: 2026-07-26 20:45
Projekt: `/Users/drnorden/projects/vpath/vpath_platform_mgmt` (Workspace-Ordner `06`)
Status: **Probe umgesetzt 2026-07-27** (`aed0003`), gegen die echte Flotte
gelaufen. Health-Endpoint: nicht gebaut, Empfehlung steht. Konsolen-UI:
zurückgestellt (Nutzeranweisung „not the ui").

Vorbereitet vom zuarbeitenden Agenten. Jede Aussage belegt oder als *nicht
verifiziert* markiert. Nichts entschieden.

---

## Scope

Der Zustand aller Instanzen wird **mechanisch** ermittelt und angezeigt. Drei
Bauteile, in dieser Reihenfolge:

1. **Status-Skript** — liest das git-ignorierte Register, läuft über alle Instanzen
   und ermittelt je Instanz: läuft sie · letzter Installiervorgang · aktuelle Version.
2. **Health-Endpoint** — *nur wo sich das nicht ermitteln lässt.* Vom Nutzer
   ausdrücklich als Bedingung formuliert, nicht als gesetzt. Umsetzung im
   Serverprojekt, koordiniert.
3. **Konsolen-UI** — startbar, links die Instanzliste mit Typ und Grobzustand,
   Klick öffnet den Detailstatus. Uptime gehört dazu.

**Voraussetzung:** das Register aus dem Strang
[`instance-management`](../instance-management/summary.md) — seit 2026-07-27
gebaut. Die Blockade ist weg; Bauteil 1 steht, Bauteil 2 ist entschieden
(nicht bauen, außer für Standalones), Bauteil 3 ist zurückgestellt.

---

## Was der Lauf ergeben hat (2026-07-27, echte Flotte)

| Instanz | Verdikt | Version | Letzter Install |
|---|---|---|---|
| mercury8 | HEALTHY | `1a2c51dc7891` | 2026-07-26T04:52:25Z |
| venus10 | HEALTHY | `1a2c51dc7891` | 2026-07-26T07:44:00Z |
| terra | HEALTHY | `67598d8a9098` | 2026-07-27T04:28:04Z |
| alpha | STOPPED | Kit `09ede4b209e4` (gebaut, nicht laufend) | — |
| bravo | PLANNED | — | — |

Exit 2 — und zwar **richtig so**: die einzige nicht feststellbare Tatsache im
ganzen Lauf ist die Gesundheit und laufende Version der Standalone. Genau das
ist der Beweis, der `health-endpoint-gap` begründet.

Alle drei Server melden `53/53` Deployments bereit und tragen ein
`vpath.git.sha`-Label, dessen SHA mit dem `build_id` der Box übereinstimmt.
Kein Drift zwischen laufendem Stand und Box-Checkout.

---

## Der zentrale Befund: der Fallback ist größtenteils unnötig

Der Request stellt den Health-Endpoint unter eine Bedingung — *„Falls sich das gar
nicht ermitteln lässt."* Diese Bedingung ist für die Server **nicht erfüllt**. Drei
mechanische Quellen existieren bereits im Serverprojekt:

| Gesuchte Angabe | Existierende Quelle | Beleg |
|---|---|---|
| **läuft sie / gesund?** | `health-check-platform-ready.sh` — prüft Keycloak, OpenFGA, Dapr und Ingress, Exit 0 = gesund | `vpath_server_dev/build.gradle.kts:215-238` (Task `requirePlatformReady`, der die Mechanik beschreibt) |
| **letzter Installiervorgang** | `build/phase-gates/platformReady.marker` — wird von PhaseGate geschrieben, wenn der Health-Check 0 liefert | ebd. |
| **aktuelle Version** | Image-Labels `vpath.git.sha`, `vpath.git.repo`, `vpath.src.hash`, beim Bau gestempelt | `lib/pipeline/build-from-gitea.sh:61`, `lib/pipeline/build-docker-image.sh:62`, `build-base-images-from-gitea.sh:10` |

Damit verschiebt sich die Aufgabe erheblich: **Was fehlt, ist nicht der Health-Check,
sondern seine Abfragbarkeit aus der Ferne.** Alle drei Quellen liegen heute *auf*
der Instanz — im Cluster, im `build/`-Verzeichnis, in der lokalen Registry. Für die
NUCs und Azure ist ein Weg dorthin da: SSH. Für ein Skript im
Platform-Management-Projekt ist das erreichbar, ohne im Serverprojekt irgendetwas
Neues zu bauen.

**Die Ausnahme sind die Standalones.** Eine Electron-Instanz hat keinen Cluster,
kein `kubectl`, keinen Marker und keinen SSH-Zugang. Dort existiert **keine** der
drei Quellen. Der Fallback wird also nicht global gebraucht, sondern **genau dort** —
und der Schnitt verläuft umgekehrt zur Formulierung im Request, der „sowohl für jeden
Server als auch für jede Standalone" verlangt.

Das ist der Punkt, an dem eine Entscheidung fällt und viel Arbeit hängt.

---

## Weitere Befunde

### Das UI ist bereits beauftragt — als Admin-Konsole (zurückgestellt)

`vpath_platform_mgmt/pyproject.toml:10` und `README.md:3` beschreiben das Projekt
wörtlich als *„App build/deploy/health-check/uninstall pipeline **and admin console**
for VPath server instances"*, mit einer Konsole für drei Rollen, Bauform
*„graphical or chatbot-assisted, TBD"* (`README.md:8`).

Das im Request beschriebene UI ist damit **kein neues Ding, sondern der erste
Bildschirm dieser Konsole**. Wer es als eigenständiges Werkzeug baut, erzeugt zwei
Konsolen in einem Projekt, das eine beauftragt hat — Regel 8. Die offene Frage
„grafisch oder Chatbot" ist damit implizit beantwortet (grafisch), was ein Stück
EIP-222 festlegt und dort vermerkt gehört.

### Es gibt eine Machart-Vorlage im Haus

Das Pin-Status-Werkzeug im Workspace ist heute fertig geworden und löst dieselbe
Gattung Aufgabe — Zustand aus verteilten Quellen lesen, vergleichen, hart urteilen:

- `claas_demo/scripts/pin_status.py` (35 KB) mit `test_pin_status.py` (35 KB) —
  Test genauso groß wie Code
- `claas_demo/scripts/miniyaml.py` — eigener YAML-Parser, also **abhängigkeitsfrei**
- gestufte Exit-Codes statt eines Booleschen: 1 = Kette gerissen, 2 = Tatsache nicht
  feststellbar, 3 = Manifest weicht von der Live-Lesung ab (`claas_demo/TODO.md`,
  Track 4)

Besonders Exit-Code **2** ist hier zu übernehmen: „nicht feststellbar" ist ein
eigener Ausgang, nicht „ungesund". Für Instanzen ist genau das der häufigste Fall —
Box aus, Netz weg, Tunnel zu.

### Grenzfrage: gehört das Werkzeug wirklich nach `06`?

`AGENTS.md:38` sagt: Werkzeuge, die *etwas tun*, gehören nach `platform_mgmt`;
Werkzeuge, die *etwas zeigen*, dürfen im Workspace beginnen. Ein Status-Werkzeug
zeigt — und das Pin-Tool liegt folgerichtig im Workspace.

Der Nutzer benennt trotzdem `06`, und das trägt: Das Werkzeug braucht das Register,
das nach `06` gehört, und es ist Teil der dort beauftragten Konsole. Die Regel sagt
„dürfen hier beginnen", nicht „müssen". **Kein Widerspruch — aber die Begründung
gehört ins Entscheidungslog**, sonst wirkt es später wie ein Verstoß.

---

## Backlog

### P1 — der Kern
- ~~**[status-probe](status-probe.issue.md)**~~ — **erledigt.** Liest das
  Register, fragt jede Instanz ab, urteilt hart und unterscheidet „ungesund"
  von „nicht feststellbar".

### P1 — cross-repo, braucht Koordination
- **[health-endpoint-gap](health-endpoint-gap.issue.md)** — **bewiesen, wofür:**
  nur für Standalones, und nicht als Endpoint, sondern als Adressproblem.
  Empfehlung: **App-Template**, Statusdatei unter dem Home statt HTTP.
  Entscheidung beim zentralen Koordinator, nichts gebaut.

### P2 — hängt an beidem
- **[console-ui](console-ui.issue.md)** — die Oberfläche. Der Request beschreibt sie
  präzise (Liste links, Detail rechts, Uptime); die eigentliche Frage ist die
  Bauform und dass sie die beauftragte Admin-Konsole *ist*.

---

## Offene Fragen an den Nutzer

Gebündelt.

1. **Reicht SSH?** Für Server ist der Zustand vermutlich ohne neuen Endpoint
   ermittelbar (SSH → `health-check-platform-ready.sh`, Marker, Image-Labels). Soll
   das zuerst versucht werden, bevor irgendetwas im Serverprojekt gebaut wird?
2. **Standalones** — dort ist der Fallback echt nötig. Was gilt als „läuft" bei einer
   Electron-Instanz: Prozess da? Fenster offen? Backend antwortet?
3. **Bauform der Konsole** — der Request impliziert grafisch. Damit fällt eine
   EIP-222-Entscheidung („graphical or chatbot-assisted, TBD"). Bewusst so?
4. ~~**Uptime wovon**~~ — **entschieden 2026-07-27:** Hauptzahl ist die Uptime der
   **Plattformdienste** (seit wann Keycloak/OpenFGA/Dapr gesund); die
   Detailansicht zeigt alle vier Uhren (Box, k3s, Plattform, Apps).

---

## Dateien

- `raw/2026-07-26_2045_instanzstatus-und-konsole.md` — Wortlaut + Dekodierung
- `instance-status.concept.md` — Herleitung und Schnitt
- drei Issues, siehe Backlog

**Voraussetzungsstrang:** [`../instance-management/summary.md`](../instance-management/summary.md)
**Koordinationszeiger:** `/Volumes/T7/workspaces/claas_demo/analysis/instance-status/summary.md`

---

## Entscheidungslog

- 26.07.: Strang angelegt. Keine inhaltliche Entscheidung getroffen.
- 27.07.: **Uptime entschieden** — Plattformdienste als Hauptzahl, Detail alle
  vier Uhren (S4 geschlossen). Track 17 ist zeitgleich entsperrt (Terra
  entschieden) — die Blockade dieses Strangs reduziert sich auf das noch zu
  bauende Register.
- 27.07.: **Probe gebaut und gelaufen.** S5 entschieden: das Health-Skript wird
  **nicht** ausgeführt, weil es den Phase-Gate-Marker berührt — ein
  Statuswerkzeug darf seinen Messwert nicht verändern.
- 27.07.: **Uptime ist noch nicht implementiert.** Die Probe meldet den letzten
  Installiervorgang, nicht die vier Uhren. Das ist bewusst: die Uhren gehören
  zur Detailansicht, und die Detailansicht ist das zurückgestellte UI. Der
  Zugang dazu ist da (SSH, `uptime`, k3s-Node-Alter, Marker) — es fehlt der
  Ort, an dem sie angezeigt würden.
- 27.07.: **Ein Befund gegen die eigene Annahme:** der Phase-Gate-Marker liegt
  nicht unter `build/`, sondern unter `<CHECKOUT>/<TARGET_DIR>/phase-gates/`,
  und `TARGET_DIR` ist pro Umgebung verschieden. Die Probe leitet den Pfad aus
  dem Env-Profil der Box ab.
