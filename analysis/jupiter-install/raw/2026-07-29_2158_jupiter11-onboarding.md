# Rohfassung — jupiter11: Aufnahme als weiterer NUC, Zugang harmonisieren

Diktat/Prompt Andre, 2026-07-29 ~21:58 (englisch diktiert). **Redaktion:** Die
Zeilen mit Adresse, Nutzername und Passwort-Verweis sind hier bewusst ersetzt —
Zugangsdaten stehen ausschließlich im gitignorierten Register
(`instances.local.env`, Block `jupiter11`). Kein stiller Drop: die Auslassung
ist markiert.

> /Users/drnorden/projects/vpath/vpath_platform_mgmt
>
> there is a new remote nuc host [REDAKTIERT: Adresse → Register `jupiter11`]
> jupiter11
>
> it is a nuc enthusiast with two ssds 1x 512gb and 1x 256gb and an rtx2060
> and 64gb ram
>
> [REDAKTIERT: Nutzername, Passwort-Verweis → Register `jupiter11`]
>
> make them aligned with the rest => only login via the common ssh user etc..
>
> work in /Users/drnorden/projects/vpath/vpath_platform_mgmt and file a
> request and setup this specifc host as jet another nuc we manage there

## Diktat-Dekodierung (nur Wortreparaturen)

| Wortlaut | Gemeint |
|---|---|
| „a nuc enthusiast" | Intel **NUC 11 Enthusiast** (Phantom Canyon — die Baureihe mit integrierter RTX 2060); daher Suffix 11 im Namen |
| „jupiter11" | Signaletik-konform: `jupiter` ist der nächste Planet nach `mars` (Reihenfolge der Anschaffung), Suffix 11 = NUC-Generation (`docs/INSTANCES.md`, Entscheidung 2026-07-27) |
| „aligned with the rest / only login via the common ssh user" | die Uniform-NUC-Zugangsregel des Registers: User `nuc`, gemeinsamer Fleet-Key, NOPASSWD-sudo, Auslieferungs-User entfernen (venus10-Playbook 2026-07-24, zuletzt mars12 2026-07-28) |
| „file a request" | dieses Verfahren: Strang `analysis/jupiter-install/` mit raw → summary → issue |
| „setup this specifc host as jet another nuc we manage there" | „set up … as yet another NUC we manage there": harmonisieren + in `instances.local.env` registrieren + Probe. Der Server-Install ist NICHT Teil des Requests |
