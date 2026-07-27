# Issue: Ein invalider Registereintrag legt die Flotten-Werkzeuge — Gate fehlt

Status: draft · Herkunft: mars12-Onboarding 2026-07-28 (Z1-Befund des
Stream-Agenten, unabhängig verifiziert)

**Befund:** `registry.load()` validiert alle Instanzen bei jedem Lauf — ein
einziger schemafremder Wert (hier: ein Lifecycle außerhalb
`registry.py:59-61`) macht das gesamte Register unlesbar: `selector` und
`probe` beenden mit Exit 2 für die GANZE Flotte, nicht nur für die eine
Instanz. Der Fehlerfall trat real ein (Draft-Eintrag `mars12`, 2026-07-27).

**Pain:** Wer eine neue Instanz anlegt, kann mit einem Tippfehler die
Werkzeuge für alle bestehenden lahmlegen — und merkt es erst beim nächsten
Flotten-Kommando.

**Ziel:** Ein Gate, das einen kaputten Eintrag findet, bevor er wirkt —
Optionen: (a) `selector validate` als expliziter Vorab-Check nach
Register-Edits, (b) fehlertolerantes Laden mit hartem, benanntem Fehler NUR
für die betroffene Instanz (kein Soft-Pass: die kaputte Instanz bleibt Fehler,
die Flotte bleibt bedienbar). Entscheidung offen.
