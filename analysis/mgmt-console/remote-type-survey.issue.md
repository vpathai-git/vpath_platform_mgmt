# Issue: Erhebung des Instanztyps `remote` (win-claas)

**Status:** **erhoben 2026-07-28** — Struktur belegt, eine Frage bleibt offen
(und zwar die, die kein Repository beantworten kann)
**Priorität:** P2 · **Herkunft:** Interview-Entscheidung M2, 2026-07-27

## Auftrag (unverändert)

Das `remote`-Template wurde mit den bekannten Feldern strukturiert und als
**declared, unproven** markiert. Dieses Issue war die Erhebung, die es beweist:
Zugangsweg und Deploy-Pfad des kundenseitigen Windows-Clusters (CLAAS-Linie).

## Quellenlage

Erhoben gegen das Serverprojekt `vpathai-git/vpath_server` @ `889a6939` (main),
wie im Auftrag vorgesehen: „Primär das Serverprojekt (Target-Tabelle im README,
Playbook-Installationswege)". Jede Zeile unten trägt ihren Beleg. Was dort
nicht steht, steht hier als **offen** — nicht als plausible Annahme.

**Werte bleiben draußen.** Die Erhebung ist dabei auf reale Zugangsdaten
gestoßen (Host **und Admin-Kontoname**, `.claude/skills/reinstall/SKILL.md:33`).
Die stehen bewusst **nicht** in diesem Repository — weder hier noch im Template.
Belegt wird über Datei:Zeile, deklariert wird im gitignorten Register.

## Frage 1 — Zugang

| Punkt | Befund | Beleg (`vpath_server`) |
|---|---|---|
| Protokoll | **SSH**, schlüsselbasiert, keine Passwörter | `lib/vm.sh:503-505`, `.claude/skills/reinstall/SKILL.md:29-37` |
| Adressierung | `REMOTE_DEPLOY_HOST` / `REMOTE_DEPLOY_USER` aus dem gitignorten `config/dot_env/.env` | `lib/vm.sh:412-413`, `SKILL.md:411` |
| Schlüssel | Default-Keypair des Operators; der Callsite übergibt **kein** `-i` — anders als der NUC-Pfad, der `NUC_SSH_KEY` mitgibt | `lib/vm.sh:503` vs. `639-643`, `SKILL.md:33-37` |
| Sprunghost | **keiner konfiguriert** — direkte Verbindung | Abwesenheit in `lib/vm.sh:503-505`; kein Bastion in der Topologie-Tabelle |
| Wozu | alle `run_kubectl`-Aufrufe werden über diese SSH-Verbindung geroutet | `SKILL.md:411` |

## Frage 2 — Deploy-Pfad

**Dieselbe Gradle-Pipeline wie jedes andere Ziel.** Das ist der wichtigste
Befund, weil er die Sonderbehandlung kleiner macht als erwartet: „Both targets
run the **same** Gradle pipeline" (`README.md:18`), und „The pipeline is
identical from `provisionBuildVM` onward — only the VM lifecycle management
differs" (`SKILL.md`, Abschnitt *Windows Variant*).

### Die vier Ortsfragen, remote gegen nuc

| # | Frage | nuc | remote (win-claas) | Beleg |
|---|---|---|---|---|
| 1 | Host + Filesystem | die NUC selbst | entfernter Enterprise-Host beim Kunden | `README.md:16` |
| 2 | Build-Prozess | **auf der Box** — Build- und Deploy-Host sind dieselbe Maschine | **auf der Maschine des Operators** (QEMU-Build-VM), nur der Deploy-Host ist entfernt → **weicht ab** | `lib/vm.sh:387-392` vs. `SKILL.md:29-34` |
| 3 | Quell-Repos | Server-Monorepo | dieselben — es ist dieselbe Pipeline | `README.md:18` |
| 4 | Container-Images | (NUC: lokaler Docker-Daemon, s. Probe) | **In-Cluster-Registry auf dem Deploy-Host**, befüllt per `skopeo copy docker-daemon: docker://` → **weicht ab** | `README.md:18`, `analysis/app-ify/08-airgap-packaging.md:123-124` |

**Airgap ist Pflicht, nicht Stil:** Der Deploy-Host darf das Internet nie
erreichen; die Phase-Gate `verifyAirgap` erzwingt das (`README.md:18`). Gebaut
wird dort, wo es Internet gibt — beim Operator.

## Frage 3 — Grenzen · **OFFEN, und das ist ein Befund**

Im gesamten Serverprojekt ist **kein** Freigabeweg, kein Wartungsfenster und
keine Kundenzustimmung für Installationen dokumentiert. Gesucht wurde nach
`customer approval|consent|sign-off`, `change window`, `maintenance window`,
`production install` — die einzigen Treffer betreffen Backup-CronJobs und ein
Keycloak-Upgrade, nichts davon ein Freigabeprozess.

Das ist **keine Lücke in der Erhebung, sondern die richtige Antwort**: Was die
Konsole auf einem Kundensystem tun darf, ist eine Betreiber- und
Kundenentscheidung, kein Code-Fakt. Kein Repository kann sie liefern.

**Konsequenz im Code, statt einer Annahme:**
- `CONSOLE_PERMITTED` bleibt ausdrücklich als **offen** markiert.
- Die Transportschicht **verweigert** diesen Instanztyp weiterhin vollständig
  (`transport.require_ssh`) — mit geänderter Begründung: nicht mehr „wir wissen
  nicht wie", sondern „wir dürfen nicht". Den Weg zu kennen ist keine Erlaubnis,
  ihn zu fahren.
- Die Probe meldet weiterhin `UNPROVEN` und misst nichts; der Zugangsweg ist
  jetzt eine gemessene Tatsache, die Lücke heißt jetzt `clearance`.

## Erfolgskriterium — erfüllt

> „Das `remote`-Template verliert die Markierung *unproven* — jede Feldangabe
> ist belegt …, oder das Feld ist ausdrücklich als offen markiert. Kein
> geratenes Feld."

Erfüllt: `remote.json` ist auf `template_version: 1`, `proven: true`. Jedes Feld
trägt seinen Beleg im Kommentar; `CONSOLE_PERMITTED` ist ausdrücklich offen.
Kein Feld ist geraten.

**Was das ausdrücklich nicht behauptet:** Niemand hat sich von dieser Konsole
aus mit dem Cluster verbunden. `proven` heißt „die Struktur ist belegt", nicht
„es wurde erprobt".

## Nebenbefund — Sicherheit, im Serverprojekt

`lib/vm.sh:532-535` erklärt, der Kunden-Host behalte „full host-key tracking",
und begründet damit, warum er den ephemeren SSH-Wrapper nicht benutzt. Die
tatsächlichen Callsites verwenden aber `StrictHostKeyChecking=no`
(`lib/vm.sh:503`, `778`, `960`). `no` verweigert bei **geändertem** Hostkey
nicht — es ist gerade nicht das, was der Kommentar beschreibt.

Auf einem Kunden-Produktionssystem ist das eine MITM-Exposition. `accept-new`
träfe die im Kommentar formulierte Absicht (erste Verbindung akzeptieren, bei
Wechsel abbrechen) — so, wie es der NUC-Pfad bereits macht (`lib/vm.sh:641`).

**Gehört nicht in dieses Repository.** Weitergabe ans Serverprojekt nötig; hier
nur festgehalten, damit der Befund nicht verloren geht.

## Was jetzt noch fehlt

1. **Betreiberauskunft zu Frage 3** — die einzige echte Restfrage. Bis dahin
   fährt die Konsole dort nichts.
2. **Ein Verbindungsnachweis** — die Struktur ist belegt, erprobt ist sie nicht.
3. **Weitergabe des Sicherheitsbefunds** ans Serverprojekt.

## Entscheidungslog

- 27.07.: Angelegt aus M2 — Struktur jetzt, Erhebung als Auftrag.
- 28.07.: **Erhoben gegen `vpath_server@889a6939`.** Zugang (SSH, keine
  Sprunghost, Default-Keypair) und Deploy-Pfad (dieselbe Pipeline, Build beim
  Operator, In-Cluster-Registry) belegt. Zwei der vier Ortsfragen weichen vom
  NUC ab (Build-Prozess, Container-Images). Frage 3 bleibt offen und ist als
  Betreiberentscheidung erkannt, nicht als Erhebungslücke. Template auf v1,
  `proven: true`. Sicherheits-Nebenbefund aufgenommen.
