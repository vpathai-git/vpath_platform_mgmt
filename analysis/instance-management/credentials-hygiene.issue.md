# Issue: Ablageform für Zugangsmaterial — und ein Gate dagegen

**Status:** draft (Sofortmaßnahme erledigt) · **Priorität:** P2
**Herkunft:** Befund beim Aufnehmen des Requests, 2026-07-26

## Der Vorfall

Die mitgelieferte `platform-admin-credentials.zip` lag im Repo-Root von
`vpath_platform_mgmt` — **untracked und nicht git-ignoriert**. `git status` führte
sie als `??`. Ein `git add -A` hätte sie eingecheckt, samt enthaltenem
SSH-Private-Key (`vpath-ai-vm5-win_key.pem`).

Keine Historie betroffen: `git log --all -- '*.zip' '*credential*'` ist leer, die
Datei war nie eingecheckt.

## Sofortmaßnahme (erledigt)

`.gitignore:88-94` ergänzt:

```
platform-admin-credentials*.zip
*.pem
*_key
*_key.*
instances.local.*
```

Verifiziert:
`git check-ignore -v platform-admin-credentials.zip` → `.gitignore:91`.

## Warum das trotzdem offen bleibt

Ein `.gitignore`-Eintrag ist ein Zaun, kein Gate. Er verhindert das Einchecken
dieser einen Datei, nicht das der nächsten. Nach der Hausregel — *eine Prüfung, die
nur warnt, ist keine Prüfung* — braucht es einen Pre-Commit-Check, der hart
fehlschlägt, wenn Schlüsselmaterial oder ein Instanzregister im Commit landet.

Das Serverprojekt hat dieses Muster bereits gelernt: `.env.nucs` lag am 24.07.
ebenfalls zuerst untracked im Repo-Root und wurde nachträglich ignoriert
(`vpath_server_dev/analysis/nuc-fleet-access/summary.md:32-34`).
**Derselbe Fehler zum zweiten Mal, in einem zweiten Repo** — das ist ein Muster,
kein Einzelfall, und rechtfertigt ein Gate statt einer weiteren Zeile in einer
Ignore-Datei.

## Erfolgskriterium

1. Festgelegte Ablage für Zugangsmaterial — im Repo (git-ignoriert) oder außerhalb
   (z. B. `~/.vpath/`) — und begründet, warum.
2. Ein Pre-Commit-Gate, das bei Schlüsselmaterial oder Registerdateien hart
   fehlschlägt. Kein Warn-und-weiter.
3. Der ausgepackte Inhalt der ZIP liegt nirgends unabsichtlich im Arbeitsbaum.

## Randnotiz, keine Aufgabe

Die Admin-Notiz in der ZIP verweist für ihre Herkunft auf
`platform_infra/config/demo_users.yaml` und bezeichnet die Zugangsdaten
ausdrücklich als stabile, absichtliche **Demo**-Credentials, nicht als rotiertes
Geheimnis. Dieselben Demo-Passwörter stehen im Klartext in
`vpath_server_dev/README.md:20`. Das ist offenbar bewusst so — hier nur festgehalten,
damit es niemand später als Leck neu „entdeckt".
