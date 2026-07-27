# Issue: `CHECKOUT` trägt zwei Rollen — Auslieferungsziel und Gradle-CWD

Status: draft · Herkunft: mars12-Install 2026-07-28 (setupRegistry-Rot,
Ursache identisch mit venus10 Round-2 Attempt 2; Server-DECISION D1)

**Befund:** `docs/INSTANCES.md:64` definiert `CHECKOUT` als „delivery target
**and** Gradle cwd". Auf einer From-within-NUC sind das zwei verschiedene
Dinge: Die Pipeline erzeugt Artefakte über Loopback-SSH mit Workdir
`/workspace` (`lib/vm.sh:694-696` im Server), kopiert aber CWD-relativ aus dem
Gradle-CWD — die beiden decken sich nur, wenn der Gradle-CWD `/workspace`
IST. Server-DECISION D1 (venus10 Round-2-Report:192) hat genau das
entschieden; das Register kennt die Unterscheidung nicht.

**Pain, real eingetreten:** `MARS12_CHECKOUT` nach venus10-Muster
(`/home/nuc/vpath_server_dev`) ließ `deployPipeline` in `setupRegistry`
sterben (scp: registry.crt nicht gefunden — lag in `/workspace`).
`VENUS10_CHECKOUT` führt den Selector heute in denselben bekannten Fehl-CWD
(Warnkommentar im Register gesetzt, 2026-07-28). Behelf: mercury8/mars12
setzen `CHECKOUT=/workspace` — dann ist die Delivery-Ziel-Rolle mit der
CWD-Rolle zusammengelegt, um den Preis zweier Bäume pro Box (Regel-8-Zustand,
kein Ziel).

**Ziel:** Ein Feld je Rolle — z. B. `<NAME>_CHECKOUT` (Delivery-Ziel) +
`<NAME>_GRADLE_CWD` (Install-CWD, Default = CHECKOUT), Schema in
`docs/INSTANCES.md`, Validierung in `registry.py`, Selector nutzt für
`gradle` den CWD, für `deliver` das Ziel. venus10 wird damit ohne
Routen-Änderung D1-konform fahrbar. Kleiner Bauauftrag mit Tests; gehört in
den nächsten platform_mgmt-Zyklus.
