# Strang: instance-management

**Einstiegspunkt.** Wer nur diese Datei liest, ist auf Stand.

Sprache: Deutsch (Dateinamen, Code, Bezeichner Englisch) · Angelegt: 2026-07-26 20:07
Projekt: `/Users/drnorden/projects/vpath/vpath_platform_mgmt` (Workspace-Ordner `06 · platform mgmt`)
Status: **Anforderung aufgenommen, Belege erhoben — noch nicht diskutiert, keine Umsetzung**

Vorbereitet vom zuarbeitenden Agenten für den Hauptagenten. Was hier steht, ist
belegt oder ausdrücklich als *nicht verifiziert* markiert. Nichts davon ist
entschieden.

---

## Scope

Alle Server- und Standalone-Instanzen der VPATH-Plattform werden **von hier aus**
verwaltet: ansprechbar, verwaltbar, redeploybar. Fünf Instanzen sind heute im Spiel,
weitere folgen dem gleichen Muster.

Die Instanzdaten selbst — Adressen, Nutzer, Schlüssel — bleiben **git-ignoriert**.
Eingecheckt wird nur der Mechanismus, der sie nutzbar macht; jeder, der das Projekt
startet, pflegt seine eigenen Zugänge und bekommt dafür die Convenience: Install,
Build, Deployment, Redeploy über einen Weg.

Abgegrenzt: **wie** installiert und deployt wird, bleibt Sache der Pipeline im
Serverprojekt. Hier geht es darum, **wohin** und **von wo aus** — die Flotte, nicht
das Verfahren.

---

## Die fünf Instanzen

Namensschema („Signaletik"): Server tragen Planetennamen in Bahnreihenfolge,
lokale Standalones NATO-Alphabet.

| Name | Art | Heute | Beleg |
|---|---|---|---|
| **mercury8** | NUC 1 (Intel NUC8i5BEK, 64 GB, RTX-3060-eGPU) | k3s aktiv, aktuelles nuc-Mode-Installationsziel; Hostname noch `cuda-nuc` | `vpath_server_dev/analysis/nuc-fleet-access/summary.md:18-26` |
| **venus10** | NUC 2 (Wortmann TERRA Micro-PC auf NUC10-Board, 64 GB) | provisioniert bis K3s, dann am CVE-Gate blockiert | ebd. `:51-89` |
| **Terra** | Azure-VM (`vm5`) | erreichbar nur über SSH-SOCKS-Tunnel, nichts im Internet exponiert; **kein Deploy-Weg dokumentiert** | `platform-admin-credentials.zip` → `vm5-access-manual.md` |
| **Alpha** | lokale Electron-Standalone | „gibt es schon" — **welche Installation konkret, ist nicht verifiziert** | Bauanleitung: `vpath_platform_app_template/STANDALONE_STAGING_BRIDGE.md` |
| **Bravo** | lokale Electron-Standalone | noch aufzubauen | — |

---

## Die vier Befunde, die den Zuschnitt bestimmen

### 1 · Das Register existiert schon — im falschen Projekt

`vpath_server_dev/.env.nucs` ist genau das, was der Request beschreibt: eine
git-ignorierte Verwaltungstabelle der Flotte, Konvention
`NUC<n>_NAME / _HOST / _USER / _SSH_KEY / _SSH_ALIAS`, ignoriert über
`vpath_server_dev/.gitignore:31`.

Es gehört nach `06`. Aber es wird nicht auf der grünen Wiese gebaut — es wird
**verlagert**. Dazu gehört ein ganzer Vorgänger-Strang mit Spec Sheet, Issues und
Plänen: `vpath_server_dev/analysis/nuc-fleet-access/`. Der ist Vorleistung, kein
Hindernis — aber AGENTS.md Regel 8 gilt: **es darf nicht zwei Register geben.**
→ `registry-migration.issue.md`

### 2 · „Terra" ist dreifach belegt — das ist der harte Konflikt

- Der Request weist **Terra der Azure-VM** zu.
- Das Serverprojekt hat **`terra12` für die nächste NUC-Box reserviert**
  (Entscheidung vom 24.07., `nuc-fleet-access/summary.md:114`).
- Und **venus10 *ist* physisch ein „TERRA Micro-PC"** von Wortmann
  (`nuc-spec-sheet.md`, Zeile Bauform) — der Herstellername kollidiert mit dem
  Signaletik-Namen.

Das ist keine Kosmetik: `terra12` steht bereits im Fleet-Block von `~/.ssh/config`
und in `.env.nucs`. Solange das offen ist, kann kein Register geschrieben werden.
**Diese Entscheidung geht allen anderen voraus.** → `naming-collision-terra.issue.md`

### 3 · Alpha/Bravo wurde am 24.07. schon einmal verworfen

Im Entscheidungslog des Vorgänger-Strangs steht wörtlich: Namensschema =
Planetenpool, **„Alpha/Beta" verworfen** (`nuc-fleet-access/summary.md:114`).

Der Request führt Alpha/Bravo jetzt für die Electron-Standalones ein. Das ist kein
Widerspruch, wenn es als **Zwei-Klassen-Schema** gemeint ist — Planeten für Server,
NATO für lokale Standalones. Aber es muss bewusst so entschieden werden, sonst
kippt es die Entscheidung von vor zwei Tagen unbemerkt. → `standalone-instances.issue.md`

### 4 · Die Pipeline liest das Register gar nicht

`.env.nucs` ist heute **reine Dokumentation**. Die Installation konsumiert
`NUC_HOST` / `NUC_USER` / `NUC_SSH_KEY` aus `config/dot_env/.env.nuc`
(`vpath_server_dev/lib/vm.sh:404`, zitiert in `.env.nucs` Kopfkommentar).
Umschalten zwischen Boxen heißt heute: von Hand kopieren.

Genau das ist die im Request geforderte Convenience. Ein Selektor ist im
Vorgänger-Strang bereits als P1 entworfen (`nuc-switching.issue.md`), aber nicht
gebaut. → `instance-selector.issue.md`

---

## Zusätzlicher Befund: Zugangsmaterial lag ungeschützt

Die mitgelieferte `platform-admin-credentials.zip` lag beim Eingang **untracked und
nicht ignoriert** im Repo-Root von `vpath_platform_mgmt` — ein `git add -A` hätte
sie eingecheckt, samt enthaltenem SSH-Private-Key (`vpath-ai-vm5-win_key.pem`).

**Sofort abgestellt:** `.gitignore:88-94` ergänzt (`platform-admin-credentials*.zip`,
`*.pem`, `*_key`, `*_key.*`, `instances.local.*`); mit `git check-ignore -v`
verifiziert. Keine Historie betroffen — die Datei war nie eingecheckt
(`git log --all -- '*.zip'` leer).

Das ist mehr als Hygiene: es ist der Beleg dafür, warum der Request auf einem
git-ignorierten Set besteht. → `credentials-hygiene.issue.md`

---

## Backlog

### ~~P0~~ — **entsperrt 2026-07-27**
- **[naming-collision-terra](naming-collision-terra.issue.md)** — **decided:**
  Azure = `terra`, `terra12`-Reservierung fällt, nächste NUC = `mars`. Das
  Register kann geschrieben werden.

### P1 — der eigentliche Auftrag
- **[registry-migration](registry-migration.issue.md)** — `.env.nucs` aus dem
  Serverprojekt heraus, hierher, ohne zweite Variante entstehen zu lassen.
- **[instance-selector](instance-selector.issue.md)** — eine Instanz wählen und
  darauf installieren/deployen/redeployen, ohne Dateien zu kopieren.
- **[azure-terra-management](azure-terra-management.issue.md)** — die Azure-VM ist
  heute nur *erreichbar*, nicht *verwaltbar*. Der Deploy-Weg fehlt vollständig.

### P2
- **[standalone-instances](standalone-instances.issue.md)** — Alpha bestimmen,
  Bravo aufbauen, beide ins Register.
- **[credentials-hygiene](credentials-hygiene.issue.md)** — Ablageform für
  Zugangsmaterial festlegen; Gate dagegen.

---

## Offene Fragen an den Nutzer

**Alle vier beantwortet (2026-07-27):**

1. **Terra** → Azure = `terra`; Schema zählt Instanzen, `terra12` fällt, nächste
   NUC = `mars`.
2. **Zwei Klassen** → faktisch bestätigt (Planeten für Server, NATO für
   Standalones) durch die Alpha-Entscheidung.
3. **Alpha** → die Blindrun-Kit-Standalone; Bravo entsteht frisch.
4. **Umfang** → Zustand gehört dazu — als eigener Strang beauftragt
   ([instance-status](../instance-status/summary.md), Track 18; Uptime-Hauptzahl:
   Plattformdienste, Detail alle vier Uhren).

---

## Dateien

- `raw/2026-07-26_2007_instanzverwaltung-signaletik.md` — Wortlaut + Dekodierung
- `instance-registry.concept.md` — Herleitung: was das Register ist und wo die Grenze läuft
- sechs Issues, siehe Backlog

**Vorgänger im Serverprojekt (Pflichtlektüre vor der Umsetzung):**
`/Volumes/T7/vpath/vpath_server_dev/analysis/nuc-fleet-access/summary.md`

**Koordinationszeiger im Workspace:**
`/Volumes/T7/workspaces/claas_demo/analysis/instance-management/summary.md`

---

## Entscheidungslog

- 26.07.: Strang angelegt. Noch keine inhaltliche Entscheidung — der Request ist
  aufgenommen, nicht diskutiert.
- 26.07.: `.gitignore` um Zugangsmaterial ergänzt (Sofortmaßnahme, nicht
  entscheidungspflichtig — es war ein offenes Leck).
- 27.07.: **Alle vier Nutzerfragen entschieden** — Azure = `terra` (Schema zählt
  Instanzen; `terra12` fällt, nächste NUC `mars`), Zwei-Klassen-Schema bestätigt,
  Alpha = Blindrun-Kit-Standalone (Bravo frisch), Zustand gehört zum Umfang.
  **Der Strang ist dispatchbar.** Beim Registerumzug den Serverstrang
  `nuc-fleet-access` nachziehen (terra12-Reservierung dort austragen, Fabrikat
  venus10 dokumentieren).
