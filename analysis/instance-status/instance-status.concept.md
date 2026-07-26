# Konzept: Instanzstatus — Ermittlung, Lücke, Oberfläche

**Status:** Entwurf zur Diskussion · 2026-07-26
Herkunft: `raw/2026-07-26_2045_instanzstatus-und-konsole.md`

---

## 1 · Die Frage

Der Request stellt sie selbst, und zwar als Bedingung:

> „Das wäre gut, wenn das irgendwie halt mechanisch geht … Falls sich das gar nicht
> ermitteln lässt, dann brauchen wir ein, wenn man so will, Health Endpoint."

Also: **Was lässt sich heute schon mechanisch ermitteln, und wo genau hört das auf?**
Alles andere folgt daraus. Wer diese Frage überspringt, baut Endpoints, die es nicht
gebraucht hätte — in einem fremden Repo, koordiniert, mit allem Aufwand, den das
kostet.

---

## 2 · Herleitung

### 2.1 Die drei Angaben sind nicht gleich schwer

Der Request nennt drei: **läuft sie**, **letzter Installiervorgang**, **Version**.
Sie haben unterschiedliche Wahrheitsquellen und unterschiedliche Reichweite.

| Angabe | Server (NUC, Azure) | Standalone (Electron) |
|---|---|---|
| läuft / gesund | `health-check-platform-ready.sh` (Keycloak, OpenFGA, Dapr, Ingress) — existiert, Exit-Code, cluster-lokal | nichts |
| letzter Install | `build/phase-gates/platformReady.marker` — Datei mit Zeitpunkt | nichts |
| Version | Image-Labels `vpath.git.sha` / `vpath.git.repo` / `vpath.src.hash` | nichts |

Belege: `vpath_server_dev/build.gradle.kts:215-238`,
`lib/pipeline/build-from-gitea.sh:61`, `lib/pipeline/build-docker-image.sh:62`.

### 2.2 Die Lücke ist der Transport, nicht der Inhalt

Für die Server ist die Information **vorhanden, aber ortsgebunden**. Sie steht im
Cluster, im Build-Verzeichnis, in der lokalen Registry. Ein Skript im
Platform-Management-Projekt erreicht sie über den Weg, der ohnehin im Register steht:
SSH.

Das ist die entscheidende Umdeutung des Requests: **erst die Ferne herstellen, dann
über Endpoints nachdenken.** Ein Health-Endpoint auf dem Server ergänzt eine
Information, die schon da ist — er ist Komfort, nicht Notwendigkeit.

Gegenargument, das ernst zu nehmen ist: Ein Endpoint ist stabiler als das Abgreifen
interner Artefakte. Ein Marker im `build/`-Verzeichnis ist ein Implementierungsdetail
des Serverprojekts; wer es ausliest, koppelt sich daran. Das ist genau die Sorte
undeklarierter Kopplung, die `AGENTS.md` Regel 9 als Defekt bezeichnet.

**Auflösung:** Nicht die Artefakte direkt lesen, sondern das Serverprojekt seine
eigenen Mittel ausführen lassen — über SSH `health-check-platform-ready.sh` aufrufen
und dessen Exit-Code nehmen. Das ist eine **deklarierte** Nutzung einer vorhandenen
Schnittstelle, kein Griff in fremde Innereien.

### 2.3 Wo der Fallback wirklich fällig ist

Bei den Standalones. Kein Cluster, kein `kubectl`, kein Marker, kein SSH. Von den
drei Angaben ist heute **keine einzige** ermittelbar.

Der Request verlangt den Endpoint „sowohl für jeden Server als auch für jede
Standalone" — der Befund kehrt das um: **für die Standalones zwingend, für die
Server voraussichtlich verzichtbar.**

Und dort ist es die schwierigere Aufgabe. Eine Electron-App ist ein lokaler Prozess.
„Läuft sie" kann heißen: Prozess vorhanden, Fenster offen, oder eingebettetes Backend
antwortet — drei Zustände, die auseinanderfallen. Das ist eine Definitionsfrage vor
der Implementierungsfrage.

### 2.4 Das UI ist keine neue Anforderung

`pyproject.toml:10` und `README.md:3,8` beauftragen für dieses Projekt eine
**Admin-Konsole** für drei Rollen, Bauform offen („graphical or chatbot-assisted,
TBD"). Der Request beschreibt deren ersten Bildschirm: Liste links, Detail bei Klick,
Uptime.

Zwei Konsequenzen:

1. Es wird **kein separates Statusfenster** gebaut, sondern der erste Screen der
   beauftragten Konsole. Sonst stehen später zwei Oberflächen nebeneinander — Regel 8.
2. Die Bauformentscheidung fällt damit faktisch auf *grafisch*. Das ist ein Stück
   EIP-222 und gehört dort vermerkt, nicht nur hier.

### 2.5 Der Zuschnitt, der daraus folgt

```
[ Register ]  →  [ Status-Probe ]  →  [ Konsole ]
 (Strang 1)      dieses Projekt        dieses Projekt
                       ↓
              [ Endpoint für Standalones ]
               App-Template / Serverprojekt — koordiniert
```

Die Reihenfolge ist nicht willkürlich: Die Probe beweist, wo der Endpoint gebraucht
wird. Andersherum baut man ihn auf Verdacht.

---

## 3 · Vorschlag

1. **Probe zuerst, für die Server, über SSH.** Sie liefert nach kurzer Zeit einen
   belastbaren Befund darüber, was tatsächlich fehlt.
2. **Ergebnis der Probe entscheidet über den Endpoint** — voraussichtlich nur für
   die Standalones, und dann als eigener, koordinierter Auftrag ins App-Template.
3. **Konsole zuletzt**, auf einer Statusquelle, die schon funktioniert. Ein UI über
   einer unfertigen Probe zeigt Platzhalter und verdeckt genau die Lücken, die der
   Request sichtbar machen soll.
4. **Machart vom Pin-Tool übernehmen**: abhängigkeitsfrei, Test in derselben
   Größenordnung, gestufte Exit-Codes — insbesondere ein eigener Ausgang für „nicht
   feststellbar".

---

## 4 · Offene Punkte

| # | Frage | Warum sie zählt |
|---|---|---|
| **S1** | Erst SSH-Weg versuchen, bevor im Serverprojekt gebaut wird? | Entscheidet über einen ganzen koordinierten Cross-Repo-Auftrag. |
| **S2** | Was heißt „läuft" bei einer Electron-Standalone? | Drei mögliche Definitionen, die auseinanderfallen. |
| **S3** | Bauform der Konsole — grafisch? | Legt eine offene EIP-222-Entscheidung fest. |
| **S4** | Uptime wovon — Box, Cluster, Plattformdienste, Apps? | Vier Zahlen; bei einer NUC laufen sie auseinander. |
| **S5** | Darf die Probe `health-check-platform-ready.sh` über SSH ausführen — oder ist das eine undeklarierte Kopplung? | Regel 9. Ausführen einer vorhandenen Schnittstelle ist etwas anderes als Auslesen interner Artefakte; die Grenze gehört festgelegt. |
| **S6** | Wie oft läuft die Probe — auf Abruf, periodisch, beim Öffnen der Konsole? | Bestimmt, ob Zustand gecacht wird, und damit die halbe Architektur. |
