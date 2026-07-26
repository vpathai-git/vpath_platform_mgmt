# Issue: Namenskonflikt „Terra"

**Status:** draft · **Priorität:** P0 — blockiert das Register
**Herkunft:** `raw/2026-07-26_2007_instanzverwaltung-signaletik.md` („Und die Azure Instanz heißt Terra.")

## Das Problem

Der Name **Terra** ist dreifach belegt:

1. **Der Request** weist ihn der **Azure-VM** zu.
2. Das Serverprojekt hat **`terra12` für die nächste NUC-Box reserviert** —
   Entscheidung vom 24.07., protokolliert in
   `vpath_server_dev/analysis/nuc-fleet-access/summary.md:114`
   („Pool mercury8 / venus10 / terra12 (reserviert) / mars / jupiter / …"),
   eingetragen im Fleet-Block von `~/.ssh/config` und im Kopf von `.env.nucs`.
3. **venus10 *ist* physisch ein „TERRA Micro-PC"** von Wortmann
   (`vpath_server_dev/analysis/nuc-fleet-access/nuc-spec-sheet.md`, Zeile
   „Bauform": *Wortmann AG TERRA Micro-PC … auf Intel-NUC10-Board*). Der
   Herstellername kollidiert mit dem Signaletik-Namen.

Punkt 3 ist der unangenehmste: Wer künftig „Terra" in einem Log oder Spec Sheet
liest, kann nicht wissen, ob die Azure-VM, die reservierte dritte NUC oder das
Fabrikat von venus10 gemeint ist.

## Warum das jetzt zählt

Das Namensschema ist **Signaletik** — es soll Eindeutigkeit herstellen. Ein dreifach
belegter Name tut das Gegenteil. Und solange offen ist, welche Instanz wie heißt,
kann das Register nicht geschrieben werden: der Name ist sein Primärschlüssel.

## Zusatzspannung: die Bahnreihenfolge

Das Schema ist „Planet in **Bahnreihenfolge = Anschaffungsreihenfolge**"
(`nuc-spec-sheet.md`, Abschnitt Signaletik-Namensschema). Terra ist der dritte
Planet — der Request vergibt ihn folgerichtig an die dritte Instanz. Die Reihenfolge
wird also eingehalten; kollidiert wird nur mit einer **Reservierung**, die annahm,
die dritte Instanz sei wieder eine NUC.

Das relativiert den Konflikt: Der Request ist schemakonform. Zu klären ist, ob das
Schema **Instanzen** durchzählt (dann ist Azure = Terra korrekt) oder **NUCs**
(dann braucht Azure einen Namen außerhalb des Pools).

## Erfolgskriterium

Ein entschiedener, dokumentierter Name je Instanz; `terra12` im Serverprojekt
entweder freigegeben oder bestätigt; die Doppeldeutigkeit zum Fabrikat von venus10
in `nuc-spec-sheet.md` ausdrücklich vermerkt.

## Lösungsansätze

| Option | Konsequenz |
|---|---|
| **A** — Schema zählt **Instanzen**: Azure = `terra`, `terra12` im NUC-Pool freigeben, nächste NUC wird `mars` | Request unverändert umgesetzt; eine Reservierung fällt; Fabrikatskollision bleibt und muss dokumentiert werden |
| **B** — Schema zählt **NUCs**: Azure bekommt einen Namen außerhalb des Planetenpools (z. B. eigene Klasse für Cloud) | Reservierung bleibt; widerspricht dem Request und braucht eine dritte Namensklasse neben Planeten und NATO |
| **C** — Generationssuffix wie bei NUCs auch für Cloud (`terra-az`) | Eindeutig gegen beide Kollisionen; weicht die Reinheit des Schemas auf |

**Ohne Empfehlung** — das ist eine Nutzerentscheidung, keine technische.
