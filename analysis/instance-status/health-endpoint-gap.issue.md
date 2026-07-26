# Issue: Health-Auskunft dort, wo heute keine existiert

**Status:** draft · **Priorität:** P1, aber **erst nach der Probe**
**Herkunft:** `raw/2026-07-26_2045_instanzstatus-und-konsole.md`
(„Falls sich das gar nicht ermitteln lässt, dann brauchen wir ein, wenn man so will,
Health Endpoint. Sowohl für jeden Server als auch für jede Standalone Instanz und
müssen das koordiniert umsetzen im Serverprojekt.")

## Die Bedingung im Request ist ernst zu nehmen

Der Endpoint ist ausdrücklich an *„falls sich das gar nicht ermitteln lässt"*
geknüpft. Für die **Server** ist diese Bedingung nach heutigem Befund **nicht
erfüllt**: Zustand, letzter Install und Version sind auf der Instanz vorhanden
(Belege in [status-probe](status-probe.issue.md)). Was fehlt, ist der Weg dorthin —
und den liefert SSH aus dem Register.

Für die **Standalones** ist sie erfüllt, und zwar vollständig: kein Cluster, kein
`kubectl`, kein `platformReady.marker`, kein SSH-Zugang. Von den drei Angaben ist
heute **keine** ermittelbar.

**Damit kehrt sich der Zuschnitt des Requests um:** der Endpoint ist für die
Standalones zwingend und für die Server voraussichtlich verzichtbar.

## Warum das zählt

„Koordiniert umsetzen im Serverprojekt" heißt: ein Cross-Repo-Auftrag, ein
Stream-Koordinator, ein Worktree, Reviews, Merge-Entscheidung. Das ist der teuerste
Bauteil dieses Requests. Ihn auf Verdacht auszulösen, bevor die Probe gezeigt hat,
was wirklich fehlt, ist vermeidbarer Aufwand in einem fremden Repository — zwölf
Tage vor der Demo.

## Die schwierige Frage steckt bei den Standalones

Was heißt „läuft" bei einer Electron-Instanz? Drei Antworten, die auseinanderfallen:

1. **Prozess vorhanden** — billig zu prüfen, sagt am wenigsten aus.
2. **Fenster offen / UI reagiert** — was der Nutzer meint, am schwersten mechanisch
   zu prüfen.
3. **Eingebettetes Backend antwortet** — mechanisch prüfbar, aber die App kann
   backend-seitig gesund und im UI hängengeblieben sein.

Das ist eine Definitionsfrage, keine Implementierungsfrage. Sie gehört beantwortet,
bevor jemand einen Endpoint schreibt.

Zweiter Punkt: Eine Standalone hat keine feste Adresse. Ein Endpoint braucht einen
lokalen Port oder eine Statusdatei an einem verabredeten Pfad — beides muss ins
Registerschema, sonst findet die Probe sie nicht.

## Ort der Umsetzung — zu klären

Der Request sagt „im Serverprojekt". Die Standalone-Schiene wird aber vom
**App-Template** getragen (`vpath_platform_app_template/STANDALONE_STAGING_BRIDGE.md`
beschreibt die Electron-Shell). Welches Repo den Endpoint trägt, ist damit offen und
gehört vor dem Zuschnitt geklärt — es entscheidet, wer koordiniert.

## Erfolgskriterium

1. Die Probe hat belegt, für welche Instanzarten die Ermittlung tatsächlich scheitert.
2. Für genau diese ist eine Auskunftsschnittstelle definiert — mit einer
   entschiedenen Bedeutung von „läuft".
3. Das Register trägt den Weg dorthin (Port oder Pfad).
4. Kein Endpoint entsteht dort, wo die Information bereits abrufbar ist.

## Reihenfolge

**Nicht vor [status-probe](status-probe.issue.md).** Die Probe ist der Beweis, der
diesen Auftrag begründet oder überflüssig macht.
