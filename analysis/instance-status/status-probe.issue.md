# Issue: Status-Probe — ein Lauf über alle Instanzen

**Status:** draft · **Priorität:** P1
**Herkunft:** `raw/2026-07-26_2045_instanzstatus-und-konsole.md`
(„es muss ein zentrales Skript geben, dass die git-ignorierte Definition von
Serverinstanzen ausliest und dann prüft")

## Ziel

Ein Aufruf, der das Register liest, jede eingetragene Instanz abfragt und je Instanz
meldet: **Zustand · letzter Installiervorgang · Version**. Für Server und
Standalones, mit je eigenem Weg.

## Was schon da ist — und deshalb nicht neu gebaut wird

| Angabe | Quelle | Beleg |
|---|---|---|
| gesund? | `health-check-platform-ready.sh` — Keycloak, OpenFGA, Dapr, Ingress; Exit 0 = gesund | `vpath_server_dev/build.gradle.kts:215-238` |
| letzter Install | `build/phase-gates/platformReady.marker` | ebd. |
| Version | Image-Labels `vpath.git.sha` / `vpath.git.repo` / `vpath.src.hash` | `lib/pipeline/build-from-gitea.sh:61`, `build-docker-image.sh:62` |

Alle drei liegen **auf** der Instanz. Der Zugangsweg steht im Register (SSH für NUCs
und Azure). Die Probe stellt also die Ferne her; sie erfindet keine Prüfung.

## Erfolgskriterium

1. `<werkzeug> status` läuft über **alle** Registereinträge, ohne dass ein Name im
   Code steht.
2. Je Instanz eine Zeile mit den drei Angaben **und der Quelle**, aus der jede
   stammt — nach dem Vorbild des Pin-Tools, das zu jedem Pin die `file:line` nennt,
   aus der er gelesen wurde.
3. **„Nicht feststellbar" ist ein eigener Ausgang**, nicht „ungesund". Box aus, Netz
   weg, Tunnel zu — das ist der häufigste Fall und darf nicht als Defekt erscheinen.
   Vorbild: gestufte Exit-Codes des Pin-Tools (1 = kaputt, 2 = nicht feststellbar,
   3 = Manifest weicht ab).
4. Kein Fallback: eine Instanz, die nicht antwortet, wird als nicht antwortend
   gemeldet — nie stillschweigend übersprungen und nie mit einem Default gefüllt.

## Machart — Vorlage im Haus

`claas_demo/scripts/pin_status.py` (35 KB) + `test_pin_status.py` (35 KB) +
`miniyaml.py` (eigener YAML-Parser, also abhängigkeitsfrei). Gleiche Gattung Aufgabe,
heute fertig geworden. Test in derselben Größenordnung wie der Code ist dort der
Maßstab, nicht die Ausnahme.

## Offene Punkte

- **S5 (Kopplung):** Darf die Probe `health-check-platform-ready.sh` über SSH
  ausführen? Ein vorhandenes Skript aufzurufen ist etwas anderes, als in
  `build/phase-gates/` hineinzugreifen — Letzteres wäre eine undeklarierte Kopplung
  an ein Implementierungsdetail (Regel 9). Die Grenze gehört festgelegt, bevor
  gebaut wird.
- **S6:** Auf Abruf, periodisch oder beim Öffnen der Konsole? Entscheidet über Caching.
- Parallel oder seriell? Fünf Instanzen über SSH, davon eine hinter einem Tunnel —
  seriell kann spürbar dauern, und ein Timeout je Instanz ist Pflicht.

## Blockiert durch

Das Register aus [`../instance-management/registry-migration.issue.md`](../instance-management/registry-migration.issue.md).
Ohne Registerformat kein Lesen. Jenes wiederum hängt am Terra-Namenskonflikt.
