# Issue: Iteration 1 — Explorer selbst extrahieren, Deploybarkeit demonstrieren

**Status:** draft — dispatchbar · **Priorität:** P1 (Iteration 1 von Achse 3)
**Herkunft:** Interview-Entscheidung M4, 2026-07-27
(`../mgmt-console/raw/2026-07-27_1252_three-axes.md` + Interview)

## Auftrag (Nutzerentscheidung, sinngemäß wörtlich)

Arsany extrahiert die Explorer-App gerade in ein eigenes Repo — als
Quick-Solution. Unabhängig davon: **Wir extrahieren die Explorer-App selbst und
demonstrieren die Deploybarkeit** — Explorer als isolierte App, gebaut und über
den Instanz-Selektor auf eine registrierte Instanz deployt. **Später wird auf
Arsanys App-Repo als Quelle umgestellt.**

## Die Regel-8-Ausnahme, explizit

Zeitweise existieren damit zwei Extraktionen (unsere Demo-Extraktion + Arsanys
Repo). Das ist eine **bewusste, befristete Ausnahme** von „keine zwei
Varianten" — vom Nutzer angeordnet, mit definiertem Ende: Sobald Arsanys Repo
trägt, wird es die einzige Quelle; unsere Extraktion ist Wegwerf-Beweis der
Deploybarkeit, kein zweiter Pflegeort. Sie wird entsprechend markiert
(kein eigenes Remote, klarer THROWAWAY-Vermerk im README der Extraktion).

## Quelle heute

Die App lebt im Server-Monorepo: `vpath_server/apps_infra/apps/vpath-explorer`
(Frontend) + zugehöriger Backend-/Manifest-Anteil (`vpath-app.yaml`). Die
frühere Extraktions-Analyse des Workspace (Stream 13) hat die Haltepunkte
vermessen: OntoGate-Parentage, Interpreter-Pin, SDK-Relativpfad — deren
Bericht ist Pflichtlektüre vor dem Schnitt.

## Erfolgskriterium

1. Explorer baut **außerhalb** des Server-Monorepos als isolierte App
   (Frontend + Backend + Manifest).
2. Deploy auf mindestens **eine** registrierte Instanz über den Selektor
   (`instances/`-Paket dieses Repos) — nachgewiesen mit Health-Antwort der
   deployten App.
3. Der Weg ist protokolliert (welche Schritte, welche Haltepunkte aus der
   Stream-13-Analyse real bissen) — das ist der eigentliche Ertrag für Achse 3.
4. Die Demo-Extraktion trägt den THROWAWAY-Vermerk und den Verweis auf Arsanys
   Repo als künftige Quelle.

## Nicht Teil dieses Issues

Der Umzug auf Arsanys Basis (folgt, wenn sein Repo steht) und jede UI-Arbeit.
