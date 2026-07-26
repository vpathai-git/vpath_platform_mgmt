# User Request — 2026-07-26 20:07

Kanal: Diktat (Sprach-Übersetzer), an den Hilfs-Agenten im Koordinations-Workspace.
Mitgeliefertes Artefakt: `platform-admin-credentials.zip`
(liegt bei Eingang bereits unter `vpath_platform_mgmt/platform-admin-credentials.zip`).

---

## Wortlaut (unverändert)

> in 06 platform management
>
> platform-admin-credentials.zip
>
> Also, in Plattformmanagement wollen wir alle Instanzen, die wir nutzen können,
> verwalten. Wir haben bereits zwei NUC Instanzen, NUC-Instanzen, die sind bisher im
> Serverprojekt selbst koordiniert worden. Die müssen da raus. Das heißt, die wollen
> wir von hier aus koordinieren. Das ist aktuell in 01 Server Backbone. Das geht da
> raus. Dann haben wir eine Azure Instanz, die ist im Zip-Pfeil beschrieben, wo die
> liegt. Und diese drei Serverinstanzen sollen hier in dem in dem Plattform
> Management Projekt in 06 ansprechbar, verwaltbar, redeploybar und so weiter sein.
> Das wollen wir immer von hier aus tun. Und die Nomenklatur ist Signaletik, das
> heißt. Die erste Instanz der Nook 1 ist Merkur, der Nook 2 ist Venus, das
> übernehmen wir. Und die Azure Instanz heißt Terra. Und dann bauen wir noch zwei
> lokale Elektron Based Standalone Instanzen auf. Eine gibt's schon, und eine weitere
> müssen wir noch dazu machen. Und die nennen wir entsprechend dem Naturalphabet
> Alpha Alpha in Bravo. Und werden, wenn wir weitere haben, auch so weiter aufbauen.
> Diese konkreten Instanzen, die fünf, über die wir gerade sprechen, die werden zwar
> im Plattform Management-Projekt verwaltet, aber in einem Gitign eigenen, in einer
> Git Git verwalteten, und in Git ignorten eigenen Verwaltungstabelle, wie auch immer
> das aussieht. Also das heißt, wir brauchen einen Weg, wie wir, wie jeder, der das
> Plattform Management-Projekt startet, seine Zugänge zu seinen Systemen pflegen kann
> und dann davon profitiert, dass es Convenience gibt, wie zum Beispiel der Weg, wie
> wir jetzt Sachen installieren, wie wir Deployments und Builds machen. Das soll
> alles von hier aus gehen. Aber auf Basis von einem. Nicht eingecheckten Set an
> Instanzen. Das, was ich jetzt gerade gesagt habe, ist ein User Request, den wir in
> Plattform Management im Analysis Folder als User Request aufplanen. Und dann wollen
> wir aber auch im Workspace Coordination Projekt im Analysis Folder ein Hinweis
> geben, dass diese Arbeit zu koordinieren ist. Das heißt, wir haben also immer einen
> eigentlichen Arbeitsrequest. Und dann einen Zeiger aus dem Analysisfolder auf
> diesen Analysisfolder. Setzt das bitte auf.
>
> Du bist der Hilfsscheriff für den Hauptagent, der die User Requests vorgeneriert,
> sodass ich mit dem Hauptagent direkt da einsteigen kann. Okay? Das heißt, arbeite
> ihm zu, indem du sehr, sehr gründlich alle diese Dinge tust. Wir sollten dir einen
> Skill anlegen. Das heißt, versuch mal dein eigenes Verständnis zu formulieren, wie
> du arbeitest.

---

## Dekodierung der Diktat-Artefakte

Nur Wortkorrekturen, keine Deutung. Die Deutung steht im Konzept.

| Wortlaut | Gemeint |
|---|---|
| „im Zip-Pfeil beschrieben" | im ZIP-**File** beschrieben |
| „der Nook 1" / „der Nook 2" | die **NUC** 1 / NUC 2 (Intel-NUC-Kleinrechner) |
| „die Nomenklatur ist Signaletik" | das **Namensschema**/die Benennungssystematik |
| „Elektron Based Standalone Instanzen" | **Electron**-basierte Standalone-Instanzen |
| „dem Naturalphabet" | dem **NATO-Alphabet** (Alpha, Bravo, …) |
| „Alpha Alpha in Bravo" | **Alpha und Bravo** |
| „in einem Gitign eigenen, in einer Git Git verwalteten, und in Git ignorten eigenen Verwaltungstabelle" | in einer **eigenen, git-ignorierten** Verwaltungstabelle (nicht eingecheckt) |
| „Aber auf Basis von einem. Nicht eingecheckten Set an Instanzen." | auf Basis eines **nicht eingecheckten** Sets an Instanzen |
| „Hilfsscheriff" | zuarbeitende Rolle (Vorbereitung für den Hauptagenten) |

## Ortsangaben aus dem Wortlaut

- „06 platform management" / „in 06" → Workspace-Ordner `06 · platform mgmt`
  = `/Users/drnorden/projects/vpath/vpath_platform_mgmt`
  (`claas_demo.code-workspace:27-30`)
- „01 Server Backbone" → Workspace-Ordner `01 · server (backbone)`
  = `/Volumes/T7/vpath/vpath_server_dev`
  (`claas_demo.code-workspace:7-10`)
- „Workspace Coordination Projekt" → `/Volumes/T7/workspaces/claas_demo`
  (Ordner `00 · workspace (coordination)`)

## Aufträge, die dieser Prompt enthält

1. Diesen Request als Strang in `vpath_platform_mgmt/analysis/` aufsetzen.
2. Im Koordinations-Workspace (`claas_demo/analysis/`) einen **Zeiger** anlegen,
   dass diese Arbeit zu koordinieren ist.
3. Das eigene Arbeitsverständnis der zuarbeitenden Rolle formulieren
   (Vorstufe zu einem Skill).
