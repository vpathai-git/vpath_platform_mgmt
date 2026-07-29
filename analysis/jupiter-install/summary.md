# Strang: jupiter-install — NUC 4 (`jupiter11`) aufnehmen und harmonisieren

**Einstiegspunkt.** Wer nur diese Datei liest, ist auf Stand.

Sprache: Deutsch (Dateinamen, Code, Bezeichner Englisch) · Angelegt: 2026-07-29 21:58
Projekt: `vpath_platform_mgmt` (dieses Repository)
Status: **erledigt** (2026-07-29, direkt in der Session, kein Dispatch) —
Box harmonisiert (User `nuc` einziger Human-User, Fleet-Key, NOPASSWD-sudo,
Hostname war schon korrekt, LV auf volle VG gehoben), registriert
(`instances.local.env` Block `jupiter11`, Selector listet die ganze Flotte,
Exit 0), Probe ehrlich (`HEALTHY`, Server-Fakten `not establishable` — es ist
nichts installiert). Ein Befund als Draft-Issue:
[probe-preinstall-exit](probe-preinstall-exit.issue.md). Der Server-Install
bleibt unbeauftragt (P2).

---

## Der Request (Kurzform — Wortlaut in `raw/`, redigiert)

Ein weiterer NUC ist online: **`jupiter11`** — ein Intel **NUC 11 Enthusiast**
(Phantom Canyon: interne RTX 2060, 64 GB RAM, zwei SSDs 512 GB + 256 GB).
Signaletik-konform: `jupiter` ist der nächste Planet nach `mars`
(Anschaffungsreihenfolge), Suffix 11 = NUC-Generation. Zwei Teile:

1. **„aligned with the rest — only login via the common ssh user"** — die
   Uniform-NUC-Zugangsregel: User `nuc`, gemeinsamer Fleet-Key, NOPASSWD-sudo,
   Hostname, Auslieferungs-User löschen (venus10-Playbook, mars12-Fassung).
2. **„yet another nuc we manage there"** — Registereintrag in
   `instances.local.env` + Probe-Verifikation. Der Server-Install ist NICHT
   Teil des Requests.

→ [jupiter11-onboarding](jupiter11-onboarding.issue.md) (in progress)

## Verifiziert bei Aufnahme (2026-07-29 ~21:55, vom Dev-Mac)

- Box **online**: Ping ~90 ms, **Port 22 offen** (`nc -z` succeeded).
- `jupiter` ist der schemakonforme nächste NUC-Name (`docs/INSTANCES.md`:
  „mercury8, venus10, terra, then mars, …"; mars12 ist seit 2026-07-28 live).
  **Keine Kollision.**
- Fleet-Key vorhanden, Fingerprint identisch mit dem Register-Soll
  (`SHA256:IytnV6O+REo8dnhEttYQE8RjNccyZnlCsQfVahrKfKY`); `sshpass` installiert.
- Auslieferungs-User wie bei mars12 (Details nur im Register-Block `jupiter11`).

## Leitplanken (aus dem Bestand — mars-install-Lektionen eingepreist)

- **Zugangsdaten nie in Strang-Dateien** — Adresse/User/Passwort nur im
  Register-Block `jupiter11`; Reports nennen die Box nur beim Namen.
- **Kein erfundener LIFECYCLE-Wert**: Schema kennt nur `live`/`planned` —
  `onboarding` (mars12-Draft) machte das ganze Register unlesbar.
- **`CHECKOUT=/workspace`** von Anfang an (DECISION D1; venus10-Muster als
  Gradle-cwd nachweislich kaputt — mars12-Register-Kommentar).
- **~/.ssh/config-Block mit Adresse im Host-Pattern** (Keepalive-Note im
  Register: der Selector wählt die Adresse, nicht den Alias).
- Hostname-Harmonisierung **vor** dem ersten k3s-Install (venus10-Lehre).
- Register sagt WO, nie WIE (`docs/INSTANCES.md`-Boundary).

## Backlog

| Prio | Punkt | Stand |
|---|---|---|
| P0 | Zugang harmonisieren + registrieren + Probe (das Issue) | **erledigt 2026-07-29** |
| P1 | Probe-Exit für Onboarding-Boxen (Exit 2 trotz ehrlichem HEALTHY) — [Draft](probe-preinstall-exit.issue.md) | draft, gehört zu den Registry-/Probe-Strängen |
| P2 | Server-Install auf jupiter11 (mars12-Kette als Vorlage; node-Upstream-403 und die drei offenen Server-Lanes beachten) | geparkt — nicht beauftragt |
| P2 | Zweck der ZUSÄTZLICH gefundenen RTX 3090 und der zweiten SSD (232,9 G, unpartitioniert) klären — beides unerwähnt im Request | geparkt — Nutzerentscheid |

## Dateien

- `raw/2026-07-29_2158_jupiter11-onboarding.md` — Wortlaut (redigiert) + Dekodierung
- `jupiter11-onboarding.issue.md` — das Onboarding (drei Schritte, erledigt)
- `probe-preinstall-exit.issue.md` — Draft: Onboarding-Zustand im Probe-Exit
- Register-Eintrag: `instances.local.env` Block `jupiter11` (gitignored)
- Vorgänger: `../mars-install/` (Playbook + Lektionen),
  `../instance-management/` (Register, Signaletik), `../instance-status/` (Probe)

## Entscheidungslog

- 29.07. 21:58: Strang angelegt. Nutzerauftrag ist explizit „setup this
  host" → Stakeholder-Diskussion auf Minimum kollabiert, direkte Ausführung
  in der Session (Handover = dieses Issue). Erreichbarkeit, Namenskonformität,
  Key-Fingerprint verifiziert.
- 29.07. ~22:10: Playbook durchgeführt und verifiziert. Jeder Schritt mit
  Messung: Login Auslieferungs-User (1. Versuch), `nuc` uid 1001 +
  Gruppenset, Key-Login + `sudo -n` grün, `passwd -S nuc` → P,
  Auslieferungs-User per `userdel -r` entfernt, `/home` nur noch
  `nuc`. Hostname war ab Werk `jupiter11`. LV-Falle (100 G von 462,7 G)
  behoben wie bei den Schwestern → / 455 G. Befunde: zusätzliche RTX 3090 am
  Bus (nicht im Request), zweite SSD leer, kein MSDM, kein Treiber/Docker/k3s
  (Auslieferungszustand). Register + `~/.ssh/config` (Adresse im
  Host-Pattern, Keepalives) nachgezogen; Selector Exit 0 über die ganze
  Flotte; Probe ehrlich HEALTHY/not-establishable, Exit-2-Semantik als
  Draft-Issue gefiled statt gepatcht.
