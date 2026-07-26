# Issue: Instanz-Selektor — die eigentliche Convenience

**Status:** draft · **Priorität:** P1
**Herkunft:** `raw/2026-07-26_2007_instanzverwaltung-signaletik.md`
(„ansprechbar, verwaltbar, redeploybar … der Weg, wie wir jetzt Sachen installieren,
wie wir Deployments und Builds machen. Das soll alles von hier aus gehen.")

## Der Befund, auf dem dieses Issue steht

**Das heutige Register steuert nichts.** Es ist Dokumentation. Die Installation
konsumiert `NUC_HOST` / `NUC_USER` / `NUC_SSH_KEY` aus `config/dot_env/.env.nuc`
(`vpath_server_dev/lib/vm.sh:404`, zitiert im Kopf von `.env.nucs`). Umschalten
zwischen Boxen heißt heute: von Hand aus dem Register in die Env-Datei kopieren.

Deshalb: Eine bloße Verlagerung des Registers liefert **keinen** Nutzen. Der Selektor
ist der Punkt, an dem der Request seinen Wert bekommt.

## Vorleistung, die es schon gibt

`vpath_server_dev/analysis/nuc-fleet-access/nuc-switching.issue.md` — P1, Entwurf,
ungebaut: `-Pnuc=<name>` mappt `NUC<n>_*` → `NUC_HOST/_USER/_SSH_KEY` in `lib/vm.sh`,
**fail-hard, kein Fallback**, dazu Doku (`venus10-completion.plan.md:60`, Zeile W-H,
mit 1–2 h veranschlagt, Codex zugeordnet).

Dieser Entwurf löst zwei NUCs. Gebraucht wird er für fünf heterogene Instanzen.

## Schmerz

Drei Zugangsarten, drei Verfahren:

| Instanzart | Zugang | Deploy heute |
|---|---|---|
| NUC (mercury8, venus10) | SSH im LAN, User `nuc`, `id_ed25519` | Gradle nuc-Mode, `-Penv=nuc` |
| Azure (vm5) | SSH über sekundäre öffentliche IP mit eigenem `.pem`; App nur über SOCKS-Tunnel auf privater Adresse | **kein dokumentierter Weg** → eigenes Issue |
| Electron-Standalone | kein Netzzugang, lokaler Prozess | **kein dokumentierter Weg** |

Ein Feld „Host" trägt das nicht. Das Register muss einen *Zugangsweg* je `kind`
beschreiben, und der Selektor muss danach verzweigen.

## Erfolgskriterium

Ein Aufruf der Form `<werkzeug> --instance <name> <aktion>` wählt die Instanz aus dem
lokalen Register und führt Install / Deploy / Redeploy / Health aus — ohne dass
jemand eine Datei kopiert.

**Fail-hard, kein Fallback:** unbekannter Name → Abbruch mit klarer Meldung. Kein
Default auf „die letzte" oder „die erste" Instanz. Ein stiller Deploy auf die falsche
Box ist der teuerste denkbare Fehler dieses Werkzeugs.

## Abgrenzung

Der Selektor **ruft die bestehende Pipeline im Serverprojekt auf**. Er baut sie nicht
nach. Das Herauslösen der Pipeline selbst ist EIP-222 und nicht Teil dieses Requests
(siehe `instance-registry.concept.md`, Abschnitt 3.4).

## Blockiert durch

[registry-migration](registry-migration.issue.md) — ohne Register kein Selektor.
