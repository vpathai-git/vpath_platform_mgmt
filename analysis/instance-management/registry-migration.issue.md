# Issue: Instanzregister aus dem Serverprojekt herauslösen

> **ERLEDIGT 2026-07-27** (`aed0003` hier, `84607af10` im Server). Das Register
> liegt als git-ignoriertes `instances.local.env` in diesem Projekt und trägt
> alle fünf Instanzen, `KIND`-getragen. Migriert wurden **beide** Vorgänger —
> `vpath_server_dev/.env.nucs` *und* das am 27.07. entstandene
> `claas_demo/.env.instances`. Im Server zeigt jede eingecheckte Referenz auf
> das neue Haus (`analysis/nuc-fleet-access/registry-retired.md`); das
> Ignore-Muster bleibt dort stehen, damit eine liegengebliebene lokale Kopie
> nicht doch noch eingecheckt wird. Der Zeiger-Inhalt für die lokale Datei
> steht wörtlich in jener Datei — ein einmaliger Operator-Schritt, weil eine
> git-ignorierte Datei nicht per Commit entfernt werden kann.
> Erfolgskriterium 4 (`nuc-fleet-access` verweist hierher und ist auf seinen
> Restumfang reduziert) ist erfüllt.


**Status:** draft · **Priorität:** P1
**Herkunft:** `raw/2026-07-26_2007_instanzverwaltung-signaletik.md`
(„die sind bisher im Serverprojekt selbst koordiniert worden. Die müssen da raus.")

## Ausgangslage — belegt

- Register: `/Volumes/T7/vpath/vpath_server_dev/.env.nucs`, git-ignoriert über
  `vpath_server_dev/.gitignore:31` („NUC fleet access registry … NEVER commit").
- Konvention pro Box: `NUC<n>_NAME / _HOST / _USER / _SSH_KEY / _SSH_ALIAS`
  (Kopfkommentar der Datei).
- Begleitmaterial: `vpath_server_dev/analysis/nuc-fleet-access/` — Spec Sheet,
  Switching-Issue, Installationspläne, `raw/`.
- Zusätzlicher Zugangspfad außerhalb des Repos: Fleet-Block in `~/.ssh/config`
  (`nuc-fleet-access/summary.md:46,108`).

## Schmerz

Die Flotte wird dort verwaltet, wo das Produkt gebaut wird. Das Serverprojekt soll
stabil bleiben — genau deshalb existiert `vpath_platform_mgmt`
(`vpath_platform_mgmt/README.md:16-17`). Wer heute eine Instanz hinzufügt, fasst das
Serverprojekt an.

## Erfolgskriterium

1. Das Register liegt in `vpath_platform_mgmt`, git-ignoriert, mit eingechecktem
   Schema und eingecheckter Vorlage.
2. Es trägt **alle fünf** Instanzen, nicht nur die NUCs — also `kind`-getragen statt
   `NUC<n>`-präfixiert.
3. `.env.nucs` im Serverprojekt ist **entfernt**, nicht dupliziert
   (`claas_demo/AGENTS.md` Regel 8: keine zwei Varianten desselben Dings).
4. Der Strang `nuc-fleet-access` im Server verweist hierher und wird geschlossen
   oder auf seinen Rest-Scope reduziert.

## Reihenfolge — wichtig

Erst hier tragfähig machen, **dann** in einem Schnitt umstellen und dort entfernen.
Nicht: hier anlegen und dort liegen lassen — das erzeugt genau die zwei Varianten,
die Regel 8 verbietet.

## Zu beachten

- Der Serverstrang ist **in laufender Arbeit** (venus10-Erstinstall, offene
  Operator-Entscheidungen zum ArgoCD-Gap, `nuc-fleet-access/summary.md:86-89`).
  Ein Zug am Register trifft laufende Arbeit — Zeitpunkt abstimmen.
- Der Kopf von `.env.nucs` enthält Wissen, das nicht verloren gehen darf: die
  Uniform-Access-Regel (User `nuc`, `~/.ssh/id_ed25519`, NOPASSWD sudo, keine
  weiteren Human-User) und den Hinweis, dass die Pipeline die Datei **nicht** liest.
- Blockiert durch: [naming-collision-terra](naming-collision-terra.issue.md).
