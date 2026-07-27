# Issue: mars12 onboarding — Zugang harmonisieren, Install vorbereiten

Status: open (dispatchbar) · Herkunft: Diktat 2026-07-27
(`raw/2026-07-27_2222_mars12-onboarding.md`) · Strang: `summary.md` · Track 43

**Constraint des Nutzers:** Alles läuft über **einen** Agenten aus
`vpath_platform_mgmt`. Kein zweiter Akteur, keine Aufteilung.

**Ziel:** `mars12` (NUC 3) von „online im Auslieferungszustand" auf „harmonisiert,
registriert, installationsbereit" — der Server-Install selbst ist NICHT Teil
dieses Issues.

**Quellen, in dieser Reihenfolge zu lesen:** Register-Block `mars12` in
`instances.local.env` (Zugangsdaten NUR dort) · `docs/INSTANCES.md`
(Schema + Boundary) · die Register-Kommentare zu mercury8/venus10 (Uniform-Regel
und das venus10-Onboarding vom 2026-07-24 — das Playbook).

## Schritt 1 — Zugang harmonisieren (venus10-Playbook)

a) Erstzugang mit dem Auslieferungs-User. Das Passwort steht **nur im
   Register** (der mars12-Block verweist auf die dokumentierte Zeile). Es darf
   von dort in die Prozess-Umgebung gelesen werden (`sshpass -e`), erscheint
   aber nie in einer Befehlszeile, einem Log, einer Datei oder einem Report.
   **Maximal zwei Anmeldeversuche** (Lockout-Gefahr) — schlägt es fehl:
   harter Stopp, Eskalation an den Dispatcher. *(Präzisiert 2026-07-28 vom
   Koordinator: die frühere Fassung verlangte interaktive Nutzereingabe und
   schloss sshpass aus; mit der delegierten Durchführung ist Register-Env der
   Weg, der nichts Neues ablegt.)*
b) User `nuc` anlegen, NOPASSWD-sudo (`/etc/sudoers.d/90-nuc-nopasswd`,
   Muster der anderen Boxen), den gemeinsamen Public Key
   (`*_SSH_KEY` des Registers, `.pub`) in `~nuc/.ssh/authorized_keys`.
c) Hostname auf `mars12` setzen — **vor** jedem k3s-Install (venus10-Lehre:
   Hostname wird der k3s-Node-Name).
d) Auslieferungs-User löschen (Uniform-Regel: „no other human users") —
   erst NACH verifiziertem Key-Login als `nuc`. Offene Frage M1 der Summary;
   Default: löschen.
e) Grundzustand erheben und im Register-Kommentarblock nachtragen (Muster
   mercury8/venus10): CPU, RAM, Disk (+ freier Platz!), OS-Stand, ggf.
   MSDM/OEM-Hinweis.

## Schritt 2 — Registereintrag von `onboarding` heben

`instances.local.env`: `MARS12_SSH_USER` → `nuc`, `MARS12_LIFECYCLE` →
entfernen oder auf aktiv, `MARS12_CHECKOUT` setzen (Frage M2; Default:
venus10-Muster `/home/nuc/vpath_server_dev`). Danach:
`python -m vpath_platform_mgmt.instances.probe` — mars12 muss ehrlich
erscheinen (erreichbar, kein Server installiert ist ein zulässiger Zustand,
kein Fehler).

## Schritt 3 — Install vorbereiten, dann triggern und managen

*(Scope erweitert 2026-07-28 auf Nutzeranweisung: der frühere harte Stopp vor
dem Install fällt — der Install wird getriggert und gemanagt durchgeführt.)*

a) Voraussetzungen prüfen wie beim venus10-Onboarding: Plattenplatz/LV-Layout
   (venus10-Falle: Ubuntu-Installer-Default ließ das Root-LV klein), Netz.
b) Den Delivery-Weg der Server-Pipeline vorbereiten: Checkout-Ziel anlegen,
   `deliver`-Route des Selectors gegen mars12 trocken prüfen (die Pipeline
   liest ihr WIE aus `config/dot_env/.env.nuc` — nichts davon ins Register
   kopieren).
c) **Install triggern — über den Selector** (die Server-Pipeline, nie eine
   nachgebaute Route) — und **gemanagt** begleiten: Fortschritt beobachten,
   Fehler dokumentiert an den Dispatcher, KEINE Workarounds an der Pipeline
   (No-Fallback: ein roter Install wird gemeldet, nicht kaschiert).
d) Abschluss: Probe-Verdict für mars12 (`probe`), Deployments-Zustand wie bei
   den Schwester-NUCs gemessen, Register-Kommentarblock nachgetragen.

## Evidenzvertrag

Jede Aussage mit dem erzeugenden Befehl (Host-Angaben nur als `mars12`/Alias,
nie als Adresse in Reports). Was nicht verifizierbar ist: „nicht verifiziert".
Report als Datei an den vom Dispatcher benannten Pfad **und** Meldung an den
Dispatcher; Wortlimit 350.

## Sicherheitsregeln (gelten wörtlich)

- Zugangsdaten existieren nur im gitignorierten Register. Reports, Commits
  und dieser Strang bleiben frei davon.
- Nichts in diesem Repo committen außer dem eigenen Strang-/Report-Anteil,
  und nie das Register (es ist gitignored — `git check-ignore -v` vor jedem
  Commit, falls Zweifel).
- Kein Install-Lauf, kein k3s, keine Softwareinstallation über das
  Harmonisieren hinaus.
