# Strang: mars-install — NUC 3 (`mars12`) aufnehmen, harmonisieren, Install vorbereiten

**Einstiegspunkt.** Wer nur diese Datei liest, ist auf Stand.

Sprache: Deutsch (Dateinamen, Code, Bezeichner Englisch) · Angelegt: 2026-07-27 22:22
Projekt: `vpath_platform_mgmt` (dieses Repository) · Zeiger:
`claas_demo/analysis/mars-install/summary.md` (Track 43)
Status: **in Ausführung** (Track 43, ein Opus-5-Stream-Agent, seit 2026-07-28) —
Stand: Box harmonisiert + registriert (verifiziert); erster Install-Lauf
fail-fast rot an einem **Upstream-403 von deb.nodesource.com** (nicht
boxspezifisch — vom Mac identisch gemessen; HEAD wäre identisch gestorben,
0 Commits seit dem Pin berühren die Stelle). Entscheidung des Koordinators
2026-07-28: node manuell vom offiziellen nodejs.org-Kanal bereitstellen
(stellt den realen Schwestern-Zustand her, kein Pipeline-Eingriff), Kette
fortsetzen; der Pipeline-Defekt (Live-Abhängigkeit + Airgap-Widerspruch)
bleibt offene Spur für den Server-Strom. Details:
[REPORT-2026-07-28](REPORT-2026-07-28.md)

---

## Der Request (Kurzform — Wortlaut in `raw/`, redigiert)

Ein weiterer NUC ist aufgesetzt und online: **`mars12`** (NUC12-Board → Suffix
12; `mars` war der reservierte nächste Name). Drei Teile, alle durch einen
Agenten aus diesem Repository:

1. **In die Instanzliste aufnehmen** — erledigt als Draft: Register-Eintrag
   `mars12` mit `LIFECYCLE=onboarding` in `instances.local.env` (gitignored;
   Zugangsdaten NUR dort).
2. **Zugang harmonisieren** — den gemeinsamen NUC-Key installieren und die Box
   auf die Uniform-NUC-Regel heben (User `nuc`, NOPASSWD-sudo, Hostname —
   das dokumentierte venus10-Playbook im Register-Kommentar).
3. **Install vorbereiten** — bis vor den Server-Install, nicht ausführen.

→ [mars12-onboarding](mars12-onboarding.issue.md) (open, dispatchbar)

## Verifiziert bei Aufnahme (2026-07-27 ~22:20, vom Dev-Mac)

- Box **online**: Ping 81 ms, **Port 22 offen** (`nc -z` succeeded).
- `mars` ist der beschlossene nächste NUC-Name: `docs/INSTANCES.md:75`
  („venus10, terra, then mars, …; the numeric suffix is the NUC generation")
  und `analysis/instance-management/naming-collision-terra.issue.md`
  (Option A entschieden). **`mars12` ist schemakonform — keine Kollision.**
- Register existiert und ist gitignored (`git check-ignore` →
  `.gitignore:97`); Schema `docs/INSTANCES.md`; Konsumenten: `selector` und
  `probe` (nicht die Install-Pipeline — Boundary-Regel des Registers).
- **Abweichung vom Soll:** Der Box-User ist der Auslieferungs-User (nicht
  `nuc`) — exakt der Zustand, den venus10 am 2026-07-24 hatte
  (Register-Kommentar: „user `nuc` created, `afischn10` deleted, hostname set
  BEFORE the first k3s install"). Das Harmonisieren ist also Schritt 1, nicht
  Kür.

## Leitplanken (aus dem Bestand, nicht neu)

- **Zugangsdaten nie in Strang-Dateien** — Adresse/User/Passwort-Verweis
  stehen im Register-Block `mars12`, sonst nirgends. Das Passwort wird genau
  einmal interaktiv gebraucht (Key-Installation) und kommt zur Laufzeit vom
  Nutzer — es wird nirgends abgelegt.
- **Register sagt WO, nie WIE** (docs/INSTANCES.md): Ports, Workspace-Pfade,
  Build-Ziele bleiben in den Server-Profilen (`config/dot_env/.env.nuc`).
- Hostname/User-Harmonisierung **vor** dem ersten k3s-Install (venus10-Lehre).
- `CHECKOUT` bleibt bewusst leer, bis die Install-Vorbereitung ihn festlegt
  (venus10: `/home/nuc/vpath_server_dev`, mercury8: `/workspace` — Wahl ist
  Teil der Vorbereitung, kein Ratefeld).

## Offene Fragen (gebündelt — keine blockiert die Harmonisierung)

| # | Frage | Kontext |
|---|---|---|
| M1 | Soll der Auslieferungs-User nach der Harmonisierung **gelöscht** werden (venus10-Muster: ja — „no other human users exist on the boxes")? | Empfehlung: ja, Uniform-Regel wörtlich nehmen |
| M2 | Welchen `CHECKOUT`-Pfad bekommt mars12 — venus10-Muster (`/home/nuc/vpath_server_dev`) oder mercury8-Muster (`/workspace`)? | Entscheidet die Install-Vorbereitung; Empfehlung: venus10-Muster (jüngeres Onboarding) |

## Dateien

- `raw/2026-07-27_2222_mars12-onboarding.md` — Wortlaut (redigiert) + Dekodierung
- `mars12-onboarding.issue.md` — das dispatchbare Onboarding (drei Schritte)
- Register-Eintrag: `instances.local.env` Block `mars12` (gitignored, nicht Teil
  dieses Strangs)
- Vorgänger: `../instance-management/` (Register, Signaletik),
  `../instance-status/` (Probe)

## Entscheidungslog

- 27.07. 22:22: Strang angelegt (Deputy). Box-Erreichbarkeit verifiziert,
  Namenskonformität gegen die Signaletik-Entscheidung geprüft (keine
  Kollision), Register-Eintrag `mars12` als `onboarding` angelegt
  (Sofortmaßnahme: Zugangsdaten aus dem Diktat an den einen sicheren Ort;
  reversibel). Keine Ausführung — das Onboarding läuft als **ein** Agent aus
  diesem Repo, Dispatch über den Koordinator.
