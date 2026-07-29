# Issue: jupiter11 onboarding — Zugang harmonisieren, als NUC 4 registrieren

Status: done (2026-07-29 — alle drei Schritte verifiziert; Probe-Exit-Befund
als eigenes Draft-Issue `probe-preinstall-exit.issue.md`) · Herkunft: Prompt 2026-07-29
(`raw/2026-07-29_2158_jupiter11-onboarding.md`) · Strang: `summary.md`

**Auftrag des Nutzers:** Die Box auf die Fleet-Regel heben („only login via the
common ssh user") und sie als weiteren verwalteten NUC in dieses Repository
aufnehmen. Der Server-Install ist NICHT Teil dieses Issues (anders als beim
mars12-Issue, dessen Scope nachträglich erweitert wurde).

**Ziel:** `jupiter11` (NUC 4, ein NUC11 Enthusiast) von „online im
Auslieferungszustand" auf „harmonisiert, registriert, ehrlich in der Probe".

**Quellen, in dieser Reihenfolge:** Register-Block `jupiter11` in
`instances.local.env` (Zugangsdaten NUR dort) · `docs/INSTANCES.md`
(Schema + Boundary) · Register-Kommentare mercury8/venus10/mars12
(Uniform-Regel + Playbook + die mars12-Lektionen).

## Schritt 1 — Zugang harmonisieren (venus10-Playbook, mars12-Fassung)

a) Erstzugang mit dem Auslieferungs-User. Passwort steht **nur im Register**
   (Fleet-Wert, dokumentiert im venus10-Block); Übergabe via `sshpass -e` aus
   der Prozess-Umgebung — nie in Befehlszeile, Log, Datei oder Report.
   **Maximal zwei Anmeldeversuche**, dann harter Stopp.
b) User `nuc` anlegen (venus10-Gruppenset `adm,cdrom,dip,plugdev,sudo`),
   gemeinsamen Fleet-Key (`~/.ssh/id_ed25519.pub`, Fingerprint
   `SHA256:IytnV6O+REo8dnhEttYQE8RjNccyZnlCsQfVahrKfKY`) nach
   `~nuc/.ssh/authorized_keys` (700/600), NOPASSWD-sudo via
   `/etc/sudoers.d/90-nuc-nopasswd` (440 root:root, `visudo -cf` vor Aktivierung).
c) Hostname auf `jupiter11` — **vor** jedem späteren k3s-Install
   (venus10-Lehre: Hostname wird der k3s-Node-Name).
d) Konsolen-Passwort von `nuc` auf den Fleet-Wert (chpasswd aus der
   Prozess-Umgebung, nie in eine Datei).
e) Key-Login als `nuc` verifizieren, DANN Auslieferungs-User `userdel -r`
   (Uniform-Regel: „no other human users"; M1-Default aus mars-install).
f) Grundzustand erheben und im Register-Kommentarblock nachtragen (Muster der
   Schwestern): CPU, RAM, beide SSDs (LV-Falle des Ubuntu-Installers prüfen!),
   OS-Stand, MSDM/OEM-Hinweis, GPU (erste Box mit interner dGPU: RTX 2060).

## Schritt 2 — Registereintrag

`instances.local.env`: Block `JUPITER11_*` (server-nuc, `SSH_USER=nuc`,
gemeinsamer Key, `ENV_PROFILE=nuc`, `CHECKOUT=/workspace` — DECISION D1,
mercury8/mars12-Muster; das venus10-Muster ist als Install-cwd nachweislich
kaputt), `jupiter11` in `VPATH_INSTANCES` aufnehmen. **Kein erfundener
LIFECYCLE-Wert** — das Schema kennt nur `live` und `planned`; der
mars12-Draft mit `onboarding` machte das GESAMTE Register unlesbar.
Dazu ~/.ssh/config-Block nach mars12-Muster (Alias `jupiter11`, nuc4, UND die
Adresse im Host-Pattern; Keepalives für lange Läufe).

## Schritt 3 — Verifikation

`python -m vpath_platform_mgmt.instances.selector list` und
`… .instances.probe --instance jupiter11` — die Box muss ehrlich erscheinen:
erreichbar, kein Server installiert ist ein zulässiger Zustand, kein Fehler.
Passwort-Login für den gelöschten Auslieferungs-User tot, Key-Login als `nuc`
grün.

## Sicherheitsregeln (gelten wörtlich, aus mars-install übernommen)

- Zugangsdaten existieren nur im gitignorierten Register. Reports, Commits
  und dieser Strang bleiben frei davon (Adresse nur als `jupiter11`/Alias).
- Das Register wird nie committet (`git check-ignore -v` bei Zweifel).
- Keine Softwareinstallation über das Harmonisieren hinaus; kein k3s, kein
  Install-Lauf.
