# Issue: Probe-Exit für registrierte, noch nicht installierte Boxen

Status: draft · Herkunft: jupiter11-Onboarding 2026-07-29 (Schritt 3,
Verifikation) · Strang: `summary.md`

**Beobachtung (gemessen):** `probe --instance jupiter11` auf der frisch
harmonisierten Box — Verdict-Zeile `jupiter11 [server-nuc] HEALTHY`, alle
sechs Server-Fakten ehrlich `not establishable` (kein Checkout, kein Profil,
kein k3s — wahr, es ist nichts installiert), **Exit-Code 2**.

**Pain:** Exit 2 bedeutet laut `docs/INSTANCES.md` „could not be established".
Eine registrierte-aber-noch-nicht-installierte Box ist damit im Exit-Code
nicht von einer defekten Umgebung unterscheidbar; jeder Skript-Konsument der
Probe (CI, Konsole, Flottenlauf) sieht Rot für einen Zustand, der im
Onboarding-Prozess legitim und gewollt sichtbar ist. Das Schema kennt nur
`live`/`planned` — der Zwischenzustand „harmonisiert, Install ausstehend" hat
keine ehrliche Heimat: `planned` wäre gelogen (die Box existiert und wird per
SSH erreicht — Register-Drift-Meldung wäre die Folge), `live` erzeugt Exit 2.

**Ziel:** Der Zustand „erreichbar, harmonisiert, kein Server installiert" ist
im Register ausdrückbar UND im Probe-Exit von einem Defekt unterscheidbar —
ohne Soft-Pass (die not-establishable-Zeilen bleiben sichtbar, nichts wird
grün gefärbt, das no-fallback-Gebot gilt).

**Lösungsraum (nicht entschieden):**
- (a) Lifecycle-Wert ergänzen (z. B. `provisioned`): Schema + `registry.py` +
  Probe-Semantik in EINEM Zug (docs/INSTANCES.md ist die eine Heimat der
  Werteliste; die mars12-Lektion — erfundene Werte machen das Register
  unlesbar — gilt wörtlich, also nur als echte Schema-Erweiterung).
- (b) Probe-Exit differenzieren (erreichbar + nichts installiert ≠ nicht
  etablierbar), Register unverändert.
- Entscheid gehört zu den Registry-/Schema-Strängen
  (`../instance-management/`, `../instance-status/`), nicht hierher.

**Erfolgskriterium:** Flotten-Probe über alle Instanzen liefert für eine
Onboarding-Box einen eigenen, dokumentierten Zustand; ein Skript kann „warte
auf Install" von „kaputt" unterscheiden. Regressionstest deckt beide Fälle.
