# Issue: Electron-Standalones Alpha und Bravo

> **TEILWEISE ERLEDIGT 2026-07-27** (`aed0003`). Alpha ist bestimmt und steht
> im Register (`ALPHA_APP_ROOT` = das Blindrun-App-Repo, `ALPHA_HOME` = dessen
> Standalone-Home); Bravo steht als `LIFECYCLE=planned` — deklariert, nicht
> gebaut, und die Probe meldet ihn als `PLANNED` statt als Fehler. Das
> Zwei-Klassen-Schema ist in beiden Strängen dokumentiert (hier und
> `vpath_server_dev/analysis/nuc-fleet-access/registry-retired.md`).
>
> **Offen bleibt Erfolgskriterium 2 und 3:** Bravo aufbauen, und ein
> definiertes Verfahren für „neu bauen / ersetzen". Letzteres hängt an einer
> Erkenntnis der Probe: eine Standalone hat **keine feststehende Adresse** —
> die Shell vergibt jeden Port über `allocatePort()` → `listen(0)`. Solange das
> so ist, kann kein Werkzeug von außen sagen, welche Version dort *läuft*.
> Siehe `../instance-status/health-endpoint-gap.issue.md`.


**Status:** draft · **Priorität:** P2
**Herkunft:** `raw/2026-07-26_2007_instanzverwaltung-signaletik.md`
(„zwei lokale Electron Based Standalone Instanzen … Eine gibt's schon, und eine
weitere müssen wir noch dazu machen … die nennen wir entsprechend dem NATO-Alphabet
Alpha und Bravo.")

## Was belegt ist

- Die Electron-Standalone-Schiene existiert im App-Template: Bauanleitung in
  `vpath_platform_app_template/STANDALONE_STAGING_BRIDGE.md` (Prerequisites für die
  „standalone Electron shell", ausdrücklich als temporäres Gerüst markiert,
  Brücken-Schritte gegen `vpath_server#19` und weitere) sowie
  `HOW_TO_BOOTSTRAP_STANDALONE.md` (dort referenziert).
- **Nicht verifiziert:** welche konkrete, laufende Installation die im Request
  gemeinte „gibt's schon"-Instanz ist. Ich habe eine Bauanleitung gefunden, keine
  benannte Instanz.

## Warum das ein eigenes Issue ist

Eine Standalone ist keine Serverinstanz. Sie hat keine Adresse, keinen SSH-Zugang,
keinen Cluster. „Redeployen" heißt hier etwas anderes als bei mercury8 — vermutlich:
neu bauen und lokal ersetzen.

Das Register muss sie trotzdem tragen, sonst zerfällt die Flotte in zwei Werkzeuge.
Das ist der Grund für das `kind`-Feld im Schema
(`instance-registry.concept.md`, Abschnitt 3.2).

## Namensfrage — bewusst zu entscheiden

Am 24.07. wurde im Serverstrang festgehalten: Namensschema = Planetenpool,
**„Alpha/Beta" verworfen** (`vpath_server_dev/analysis/nuc-fleet-access/summary.md:114`).

Der Request führt Alpha/Bravo jetzt für die Standalones ein. Als **Zwei-Klassen-Schema**
— Planeten für Server, NATO für lokale Standalones — ist das schlüssig und kein
Widerspruch. Es muss nur ausdrücklich so entschieden werden, sonst kippt eine zwei
Tage alte Entscheidung unbemerkt.

## Erfolgskriterium

1. Alpha ist eindeutig bestimmt (welche Installation, auf welchem Rechner, in
   welchem Zustand).
2. Bravo ist aufgebaut.
3. Beide stehen im Register mit `kind: standalone` und einem definierten Verfahren
   für „neu bauen / ersetzen".
4. Das Zwei-Klassen-Namensschema ist in beiden Strängen dokumentiert — hier und im
   Serverstrang.

## Offene Frage an den Nutzer — beantwortet 2026-07-27

**Alpha = die Blindrun-Kit-Standalone** (die im Blindtest aufgebaute
Electron-Shell, `blindrun-legacy-upload/…/kit`). Der Bestand wird benannt;
**Bravo entsteht frisch** nach Anleitung. Damit ist auch das
Zwei-Klassen-Schema faktisch bestätigt: Planeten für Server, NATO-Alphabet für
Standalones. Der erste Registereintrag ist schreibbar.
