# Strang: instance-status

**Einstiegspunkt.** Wer nur diese Datei liest, ist auf Stand.

Sprache: Deutsch (Dateinamen, Code, Bezeichner Englisch) · Angelegt: 2026-07-26 20:45
Projekt: `/Users/drnorden/projects/vpath/vpath_platform_mgmt` (Workspace-Ordner `06`)
Status: **Anforderung aufgenommen, Belege erhoben — noch nicht diskutiert, keine Umsetzung**

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
[`instance-management`](../instance-management/summary.md) — dort beantragt, dort
noch nicht gebaut, dort am Terra-Namenskonflikt blockiert. Dieser Strang kann ohne
das Register nicht liefern.

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

### Das UI ist bereits beauftragt — als Admin-Konsole

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
- **[status-probe](status-probe.issue.md)** — das Skript. Liest das Register, fragt
  jede Instanz ab, urteilt hart und unterscheidet „ungesund" von „nicht feststellbar".

### P1 — cross-repo, braucht Koordination
- **[health-endpoint-gap](health-endpoint-gap.issue.md)** — wo die drei Quellen
  fehlen (Standalones), muss die Instanz selbst Auskunft geben. Umsetzung im
  Serverprojekt bzw. im App-Template. **Erst entscheiden, ob und für wen.**

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
4. **Uptime wovon** — der Box, des k3s-Clusters, der Plattformdienste oder der Apps?
   Vier verschiedene Zahlen, und bei einer NUC laufen sie auseinander.

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
