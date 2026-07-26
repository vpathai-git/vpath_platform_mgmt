# Konzept: Instanzregister und Verwaltungsgrenze

**Status:** Entwurf zur Diskussion · 2026-07-26
Herkunft: `raw/2026-07-26_2007_instanzverwaltung-signaletik.md`

---

## 1 · Kontext

`vpath_platform_mgmt` ist heute ein leerer Template-Stempel — ein Commit
(`0390b41`), kein Fachcode. Sein Auftrag laut eigenem README: die
Build/Deploy/Health-Check/Uninstall-Pipeline aus dem Serverprojekt herauslösen,
plus Konsole für App-Entwickler, Administratoren und Server-Entwickler
(`README.md:3-17`; Wahrheitsquelle laut README ist Jira **EIP-222**).

Der Request ist der erste konkrete Inhalt für dieses Projekt: **die Flotte.**

Er passt exakt auf die Grenze, die im Workspace am 26.07. gezogen wurde —
Werkzeuge, die *etwas tun*, gehören nach `platform_mgmt`; Werkzeuge, die *etwas
zeigen*, dürfen im Workspace beginnen (`claas_demo/AGENTS.md:38`). Instanzen
ansprechen, deployen, redeployen ist unzweideutig *tun*. Der Request landet am
richtigen Ort.

---

## 2 · Die Frage

Wie verwaltet ein eingechecktes Projekt eine Flotte, deren Daten nicht eingecheckt
werden dürfen?

Das ist die eigentliche Konstruktionsfrage. Alles andere folgt daraus.

---

## 3 · Herleitung

### 3.1 Die Zweiteilung ist die Antwort

Der Request formuliert sie bereits, ohne sie zu benennen:

| Eingecheckt (Repo) | Nicht eingecheckt (lokal, git-ignoriert) |
|---|---|
| Das **Schema** — welche Felder eine Instanz hat | Die **Werte** — Adressen, Nutzer, Schlüsselpfade |
| Der **Mechanismus** — auswählen, verbinden, deployen | Der **Bestand** — wer welche Instanzen hat |
| Die **Vorlage** (`instances.example.*`) | Die **eigene Tabelle** jedes Nutzers |
| Ein **Gate**, das prüft, dass nichts Geheimes eingecheckt wurde | — |

Jeder, der das Projekt auszieht, hat sofort den Mechanismus und trägt seine eigenen
Instanzen ein. Das ist der Kern der Formulierung *„jeder, der das Plattform
Management-Projekt startet, seine Zugänge zu seinen Systemen pflegen kann und dann
davon profitiert, dass es Convenience gibt"*.

### 3.2 Das Muster ist erprobt — nur am falschen Ort

`vpath_server_dev/.env.nucs` macht genau das seit dem 24.07.: git-ignoriert
(`vpath_server_dev/.gitignore:31`), Konvention pro Box
`NUC<n>_NAME / _HOST / _USER / _SSH_KEY / _SSH_ALIAS`, dazu ein Fleet-Block in
`~/.ssh/config` und ein Spec Sheet im Strang `analysis/nuc-fleet-access/`.

Wir erfinden also nichts. Wir **verlagern etwas Bewährtes und erweitern es** von
zwei NUCs auf fünf heterogene Instanzen.

Zwei Dinge ändern sich dabei substanziell:

1. **Heterogenität.** `NUC<n>_*` trägt die Bauart im Feldnamen. Eine Azure-VM und
   eine Electron-Standalone passen nicht in dieses Präfix. Das Schema braucht ein
   Feld `kind` (`nuc` | `cloud-vm` | `standalone`) statt einer Nummer im Namen —
   sonst entstehen drei Registerformate statt eines.
2. **Zugangsvielfalt.** NUCs: direkter SSH im LAN mit `id_ed25519`. Azure: SSH über
   sekundäre öffentliche IP mit eigenem `.pem`, App nur über SOCKS-Tunnel auf einer
   privaten Adresse erreichbar. Standalone: gar kein Netzzugang, ein lokaler
   Prozess. **Ein Feld „Host" reicht nicht.** Das Register muss einen *Zugangsweg*
   beschreiben, nicht eine Adresse.

### 3.3 Die Lücke, die den Nutzen erst herstellt

Das heutige Register ist **Dokumentation, kein Steuerinstrument**: Die
Installationspipeline liest `.env.nucs` nicht, sondern `NUC_HOST/_USER/_SSH_KEY` aus
`config/dot_env/.env.nuc` (`vpath_server_dev/lib/vm.sh:404`). Umschalten heißt heute:
von Hand kopieren.

Solange das so bleibt, ist ein verlagertes Register nur eine verschobene Textdatei.
**Der Selektor ist der Punkt, an dem der Request seinen Wert bekommt** — nicht die
Migration. Ein Entwurf existiert (`nuc-fleet-access/nuc-switching.issue.md`,
P1, ungebaut): `-Pnuc=<name>` mappt `NUC<n>_*` → `NUC_HOST/_USER/_SSH_KEY`,
fail-hard, kein Fallback.

Für fünf heterogene Instanzen wird daraus ein `--instance <name>`, das je nach
`kind` einen anderen Weg wählt.

### 3.4 Wo die Grenze zum Serverprojekt läuft

Die Pipeline selbst — Gradle-Tasks, Airgap-Gates, Image-Transfer — bleibt im Server.
Sie herauszulösen ist der große Auftrag aus EIP-222 und **nicht Teil dieses
Requests**.

Was hierher kommt, ist die Schicht darüber:

```
platform_mgmt:   [ Register ] → [ Selektor ] → ruft auf →
vpath_server:                                   [ bestehende Pipeline ]
```

Der Vorschlag ist damit **additiv, nicht invasiv**: `06` wird der Ort, an dem man
sagt *wohin*, das Serverprojekt bleibt der Ort, der weiß *wie*. Das ist zugleich der
erste ehrliche Schritt in Richtung EIP-222 — die Pipeline wandert später, die
Zieladressierung wandert jetzt.

Ein zweiter Grund, es so zu schneiden: Andernfalls hinge dieser Request an der
Herauslösung der gesamten Pipeline und würde monatelang nicht liefern.

### 3.5 Was das für den Serverstrang bedeutet

`vpath_server_dev/analysis/nuc-fleet-access/` ist mitten in einer laufenden
Operation (venus10-Erstinstall, offene Operator-Entscheidungen zum ArgoCD-Gap).
Ein Zug am Register jetzt trifft laufende Arbeit.

Regel 8 aus `claas_demo/AGENTS.md` verbietet zwei Varianten desselben Dings — aber
sie verlangt keine sofortige Umschaltung. Sauber ist: **erst das neue Register hier
tragfähig machen, dann in einem Schnitt umstellen und `.env.nucs` im Server
ersatzlos entfernen.** Nicht: hier anlegen und dort liegen lassen.

---

## 4 · Vorschlag

1. **Terra-Konflikt zuerst entscheiden** — er blockiert jede Zeile Register.
2. Schema entwerfen: `kind`-getragen, ein Datensatz je Instanz, Zugangsweg statt
   Adresse. Eingecheckt: Vorlage + Schema. Nicht eingecheckt: die Tabelle.
3. Selektor bauen, der die bestehende Serverpipeline aufruft — fail-hard, kein
   Fallback auf eine Default-Instanz.
4. Erst danach Azure und die Standalones aufnehmen: beide brauchen einen eigenen
   Weg, den es heute nicht gibt.
5. Am Ende `.env.nucs` im Server entfernen und den dortigen Strang auf diesen hier
   verweisen lassen.

---

## 5 · Offene Punkte

| # | Frage | Warum sie zählt |
|---|---|---|
| **I1** | Wem gehört der Name **Terra**? | Dreifach belegt; blockiert das Register. |
| **I2** | Zwei Namensklassen (Planeten/NATO) — bewusst so? | Kippt sonst eine Entscheidung vom 24.07. |
| **I3** | Welche Installation **ist** Alpha? | Nicht verifizierbar; ohne Antwort kein Eintrag. |
| **I4** | Register-Format: `.env`-Stil wie bisher, oder YAML? | `.env` ist erprobt und shell-nah; YAML trägt Heterogenität besser. |
| **I5** | Gehört **Zustand** dazu (Version, Health, letzter Deploy)? | Entscheidet, ob es eine Tabelle oder ein Werkzeug wird. |
| **I6** | Wie wird die Azure-VM überhaupt deployt? | Heute ist nur der *Zugang* dokumentiert, kein Deploy-Weg. Möglicherweise der größte verdeckte Aufwand im ganzen Request. |
| **I7** | Wann wird `.env.nucs` im Server abgeschaltet? | Trifft laufende Arbeit im Strang `nuc-fleet-access`. |
