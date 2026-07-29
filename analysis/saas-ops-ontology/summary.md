# Strang: SaaS-Betriebsökosystem in Standardsprache (NIST + Cloud-Ontologie)

**Angelegt:** 2026-07-28 · **Sprache:** Deutsch (Fachbegriffe Englisch) ·
**Status:** Stakeholder-Diskussion läuft — kein Implementierungsauftrag
**Ort:** seit 2026-07-29 hier in `vpath_platform_mgmt` (Betriebs-/Plattform-
thema; ursprünglich in `vpath_llm_wikis/analysis/` abgelegt, per
Nutzerentscheid verschoben — das Raw dort dokumentiert die Herkunft verbatim)

## Scope

Das Betriebsökosystem einer modernen SaaS-Plattform als Gesamtbild in
Standardterminologie auslegen — NIST als Definitionsrahmen plus die konsolidierte
DevOps-Sprache der Cloud-Anbieter — und diese Ontologie dann auf die VPATH-Welt
mappen (Server/Standalone, Apps mit Frontend/Backend/Workflow-Containern,
Buildpipelines; alles jeweils als Repo → Binary → laufende Instanz).
Leitstern: Plattform ändert sich selten, Apps bauen beliebig. Nichts erfinden,
alles übertragen.

## Kernergebnis (Stand heute)

- Die eine „NIST-DevOps-Ökosystem-Beschreibung" existiert nicht als
  Einzeldokument; die stärkste Blaupause ist ein **Komposit**: NIST 800-145 /
  500-292 / 800-190 / 800-218 (SSDF) / 800-53-CM als normativer Rahmen, dazu
  OCI, Twelve-Factor, SemVer, SLSA/SBOM, CNCF Platform Engineering, GitOps,
  DORA, SRE/ITIL als konsolidierte Betriebs-Sprache.
- Grundgesetz des Bildes: **drei Existenzformen** (Source → Artifact →
  Instance) für jedes Ding — Plattform, Pipeline, App. Andres
  Repo/Binary/Instanz-Beobachtung ist exakt Twelve-Factor V + OCI.
- Der Zielzustand „Plattform selten, Apps beliebig" hat einen benannten
  Standardmechanismus: versionierter Platform Contract + Deprecation Policy +
  Version-Skew-Fenster.
- Das Mapping macht fünf Spannungen sichtbar (Kopplung über Source statt
  Registry; impliziter Contract via Lockstep; build-on-deploy statt
  build-once-promote; Multi-Arch ohne Image Index; Provenance als Label statt
  Attestation) — jede mit benanntem Standardmechanismus als Auflösung.

## Backlog

- **P0 (jetzt):** Bild diskutieren — Konzept + discussion.html liegen vor;
  Andres Lesart und Einwände einarbeiten.
- **P1 (als Nächstes):** Aus der Diskussion ggf. Zielbild-Entscheidungen
  ableiten (Registry-Kopplung, Contract-Fenster) — erst nach Andres Votum.
- **P2 (Idee, geparkt):** Wiki-Kapitel/Vault-Inhalt aus dem Konzept machen;
  Tenancy-Modell der Server-Variante; FinOps-Dimension.

## Dateien

- `raw/2026-07-28_1951_saas-ops-ontology.md` — Prompt verbatim + Dekodierung.
- `nist-devops-ecosystem.concept.md` — das Konzept: Blaupause, Kern-Ontologie,
  Matrix, VPATH-Mapping, Spannungen. **Einstieg für Inhalt.**
- `discussion.html` — visuelle Diskussionsseite (Wegwerf-Artefakt, wird pro
  Iteration überschrieben).
- `discussion_color.html` — abgeleitete Variante (Andre 2026-07-28): dasselbe
  Strukturbild zweimal, eingefärbt nach Herkunfts-Repo (Lila = Platform-Repo,
  Grün = App-Repo, Blau = Pipeline-Repo, Grau = kein Repo-Erzeugnis); oben
  Standard-Beschriftung, unten dieselben Knoten in VPATH-Sprache.

## Entscheidungslog

- 2026-07-28 — Strang eröffnet auf Andres Anfrage (verbatim in `raw/`). Noch
  keine Entscheidungen; reine Auslege-Phase.
- 2026-07-29 — **Karte 3 entschieden (Option A):** Bauen über OCI, Multi-Arch
  unter einem Image Index — als neuer Demand auf dem Serverprojekt; Vorgehen
  Worktree-Linie → absichern → Big-Bang-Einführung. Wortlaut verbatim und
  Aufnahme: `vpath_server_dev/todo/oci-multiarch-build/demand.md`;
  Koordination: claas_demo Track 82. Chips in beiden Diskussionsseiten
  geflippt. Karten 1 (Registry-Kopplung) und 2 (Contract) bleiben offen.
