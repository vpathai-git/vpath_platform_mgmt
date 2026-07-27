# Issue: Health-Auskunft dort, wo heute keine existiert

> **BEWIESEN 2026-07-27 — und die Empfehlung steht.** Die Probe hat geliefert,
> was dieses Issue als Voraussetzung verlangt: der Beweis, für welche
> Instanzarten die Ermittlung wirklich scheitert.
>
> **Server: die Bedingung ist NICHT erfüllt** — für alle drei
> Server-Umgebungen sind Zustand, letzter Installiervorgang und Version über
> SSH ermittelbar, ohne im Serverprojekt irgendetwas zu bauen. Damit ist ein
> Health-Endpoint für Server **nicht zu bauen.**
>
> **Standalones: die Bedingung ist erfüllt, und der Grund ist strukturell.**
> Nicht „es gibt kein kubectl", sondern: **eine laufende Standalone hat keine
> Adresse, die von außen bekannt sein kann.** Die Shell vergibt jeden Port über
> `allocatePort()` → `srv.listen(0, "127.0.0.1")`
> (`vpath_server/standalone/src/main/supervisor.ts:420-431`); die Ports sind
> ephemer und werden nirgends abgelegt. Ermittelbar ist heute nur: ob ein
> Prozess auf das Home zeigt, wann `runtime/state.db` zuletzt geschrieben wurde,
> und welchen Kit-Stand das App-Repo *gebaut* hat. Gesundheit und die *laufende*
> Version sind es nicht — die Probe meldet das als benannte Lücke.
>
> **Empfehlung zum Ort (die offene Frage dieses Issues): das App-Template.**
> Drei Gründe. (1) Die Electron-Shell wird vom Template getragen, nicht vom
> Serverprojekt — der Supervisor, der die Ports vergibt, ist genau der Ort, der
> sie auch bekanntgeben kann. (2) Es ist kein Endpoint-Problem, sondern ein
> *Adress*-Problem: das Billigste, das die Lücke schließt, ist eine
> Statusdatei an einem verabredeten Pfad **unter dem Home** — Ports, PID,
> gebauter Stand, Startzeit —, geschrieben vom Supervisor beim Start. Dann
> findet die Probe die Instanz über das Home, das im Register ohnehin steht,
> und braucht gar keinen Endpoint. (3) Sie kostet keinen Cross-Repo-Auftrag im
> Serverprojekt zwölf Tage vor der Demo.
> Falls stattdessen doch ein HTTP-Endpoint gewünscht ist, gilt derselbe Ort —
> aber sein Port müsste dann wiederum irgendwo stehen, was auf dieselbe Datei
> hinausläuft.
>
> **Die Definitionsfrage bleibt beim Nutzer:** was „läuft" heißen soll (Prozess
> da / Fenster offen / Backend antwortet). Die Probe verwendet heute die
> billigste Lesart und sagt das auch: „Prozess, der auf dieses Home zeigt".


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
