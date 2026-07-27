# Issue: Probe druckt HEALTHY bei Exit 2 — Wort und Exit-Code widersprechen sich

Status: draft · Herkunft: mars12-Onboarding 2026-07-28 (Z1-Nebenbefund des
Stream-Agenten)

**Befund:** Für die frisch harmonisierte, aber uninstallierte Box druckte die
Probe die Instanzzeile `mars12 [server-nuc] HEALTHY`, während der Exit-Code 2
(„nicht feststellbar") lautete und alle Detail-Fakten ehrlich
`not establishable` waren.

**Pain:** Wer nur die Zeile liest, liest grünes Licht — das ist die
Wort-Variante eines Soft-Pass. Der Exit-Code ist ehrlich, das Wort nicht.

**Ziel:** Das gedruckte Verdict muss dem gemessenen Zustand entsprechen
(z. B. `UNKNOWN`/`NOT ESTABLISHABLE` für diesen Fall); Wort und Exit-Code
dürfen nie auseinanderfallen. Uptime-/Verdict-Semantik liegt im
instance-status-Strang — dorthin umhängen, wenn es gebaut wird.
