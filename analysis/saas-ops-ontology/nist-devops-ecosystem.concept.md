# Das Betriebsökosystem einer SaaS-Plattform in Standardsprache

**Strang:** `analysis/saas-ops-ontology/` · **Stand:** 2026-07-28 · **Status:** Diskussionsgrundlage

## 1. Kontext und Frage

Wir betreiben eine Plattform, die in zwei Geschmacksrichtungen existiert (Server,
Standalone), Apps in Containern hostet (Frontend-, Backend-, Workflow-Anteile),
und deren Bausteine jeweils dreifach leben: als Repository, als baubares Binary,
als laufende Instanz. Dazu Buildpipelines, die selbst wieder dreifach leben.
Zielzustand: Die Plattform ändert sich selten; Apps bauen beliebig, weil die
Plattform alles bereitstellt.

Die Frage: **Wie beschreibt ein NIST-kompatibles SaaS-System all diese Dinge in
Standardterminologie, Standardartefakten und Standardstrategien** — ohne Rücksicht
auf unseren Ist-Zustand? Erst das Standardbild, dann das Mapping auf unsere Welt.

## 2. Die Blaupause — was „NIST-kompatibel" hier konkret heißt

Eine ehrliche Vorbemerkung: **Die eine „NIST-DevOps-Ökosystem-Beschreibung" als
Einzeldokument gibt es nicht.** NIST liefert den normativen Definitions- und
Kontrollrahmen; die operative DevOps-Sprache, die alle Cloud-Anbieter heute
konsolidiert sprechen, ist in Industriestandards kodifiziert, die NIST referenziert
und voraussetzt. Die stärkste Blaupause ist ein Komposit — und jedes Element
unseres Bildes trägt unten seine Quelle:

| Schicht | Standard | Liefert |
|---|---|---|
| Was ist Cloud/SaaS/PaaS | **NIST SP 800-145** (Definition of Cloud Computing) | Service-Modelle (SaaS/PaaS/IaaS), Deployment-Modelle (public/private/hybrid), 5 essenzielle Eigenschaften |
| Wer spielt welche Rolle | **NIST SP 500-292** (Cloud Computing Reference Architecture) | Akteure: Cloud Provider, Cloud Consumer, Auditor, Broker, Carrier; Service-Orchestrierung und Service-Management |
| Container-Stack | **NIST SP 800-190** (Application Container Security Guide) | Die kanonische Container-Ontologie: Image → Registry → Orchestrator → Container → Host OS |
| Der Bau-Apparat | **NIST SP 800-218** (SSDF — Secure Software Development Framework) | Praktiken für die Software-Fabrik: Prepare Organization (PO), Protect Software (PS), Produce Well-Secured Software (PW), Respond to Vulnerabilities (RV) |
| Die installierte Welt | **NIST SP 800-53, CM-Familie** | Baseline Configuration (CM-2), Change Control (CM-3), Component Inventory (CM-8) — Konfigurations- und Bestandsführung laufender Systeme |
| Artefakt-Identität | **OCI** (Open Container Initiative: image-spec, distribution-spec) | Image, Digest, Registry, **Image Index** (Multi-Arch) |
| Existenzformen | **Twelve-Factor App** (Faktor I, III, V) | Ein Codebase, viele Deploys; Config in der Umgebung; **strikte Trennung Build → Release → Run** |
| Versionssemantik | **SemVer** | Verträge versionieren; Breaking Changes sind Major |
| Lieferketten-Integrität | **SLSA / in-toto / SBOM** (SPDX, CycloneDX) | Provenance, Attestation, Stückliste — „was steckt in diesem Artefakt und wer hat es wie gebaut" |
| Plattform ↔ App-Teams | **CNCF Platforms Whitepaper / Platform Engineering** | Internal Developer Platform, Platform as a Product, Golden Paths / Paved Roads, Platform Capabilities |
| Deploy-Steuerung | **OpenGitOps** (4 Prinzipien) | Deklarierter Soll-Zustand in Git, versioniert und unveränderlich, automatisch gezogen, kontinuierlich abgeglichen |
| Liefer-Loop messen | **DORA** (4 Metriken) | Deployment Frequency, Lead Time, Change Failure Rate, MTTR |
| Betrieb | **SRE / ITIL 4** | SLO, Error Budget, Incident/Problem/Change Management |

Der Befund, den Andre vermutet hat, bestätigt sich: **Nichts an unserem Bild muss
erfunden werden.** Jedes Element hat einen etablierten Namen, ein etabliertes
Artefakt und eine etablierte Strategie.

## 3. Die Kern-Ontologie

### 3.1 Das Grundgesetz: drei Existenzformen (Source → Artifact → Instance)

Das, was wir als „Repo / Binary / laufende Instanz" beobachten, ist Twelve-Factor
Faktor V — **Build, Release, Run, strikt getrennt** — kombiniert mit der
OCI-Distribution. Jedes betreibbare Ding existiert in genau drei Formen:

1. **Source** — Repository, Branch, Commit. Zuhause: das SCM.
2. **Artifact** — unveränderlich, versioniert, inhaltsadressiert: Container-Image
   mit Digest, Wheel, Helm-Chart, Installer-Bundle. Zuhause: die **Registry**
   (Artifact Store). Ein Artefakt wird **einmal** gebaut.
3. **Instance** (Deployment) — ein Artefakt, das in einer **Environment** mit
   deren Konfiguration läuft. Zuhause: Infrastruktur.

Die Übergänge sind die Prozesse des Ökosystems:

```
Source ──(CI: Build+Test)──▶ Artifact ──(Release: Set schnüren)──▶ Release
Release ──(CD: Promote/Deploy)──▶ Instance ──(Operate/Observe)──▶ Feedback → Source
```

Zwei abgeleitete Gesetze, beide Standard:

- **Build once, deploy many.** Dasselbe Artefakt (identischer Digest) läuft in
  jeder Environment; nur die Config unterscheidet sich (Faktor III). Ein Rebuild
  pro Umgebung wäre ein Defekt.
- **Ein Release ist kein Deployment.** Release = benanntes, unveränderliches
  **Set aus Artefakten + Metadaten** (Versionsnummer, SBOM, Provenance,
  Release Notes). Deployment = dieses Set in eine Environment gebracht.
  Exposure gegenüber Nutzern ist nochmal getrennt steuerbar (Feature Flags,
  Canary, Blue/Green — „Progressive Delivery").

### 3.2 Akteure (NIST SP 500-292, übersetzt auf eine Plattform-Organisation)

- **Platform Provider** — das Plattform-Team. Betreibt die Plattform als Produkt.
- **Platform Consumer** — die App-Teams. Konsumieren die Plattform als **PaaS**:
  sie liefern Workloads, die Plattform liefert Runtime, Capabilities, Pipeline.
- **End Customer / Tenant** — konsumiert die fertige Anwendung als **SaaS**
  (gehostete Variante) oder betreibt sie selbst (self-managed Variante).
- Auditor/Broker/Carrier existieren im NIST-Modell; für unser Bild relevant ist
  vor allem der **Auditor**-Gedanke: Compliance schaut von außen auf Provenance,
  SBOM und Konfigurationsstand — deshalb sind das erstklassige Artefakte.

Die entscheidende Doppelrolle: **Dieselbe Organisation ist SaaS-Provider nach
außen und PaaS-Provider nach innen.** Das Plattform/App-Verhältnis ist intern
exakt das Cloud-Provider/Cloud-Consumer-Verhältnis — mit Vertrag, Versionierung
und Support-Fenstern, nicht mit Zuruf.

### 3.3 Plattform ↔ App: Vertrag und goldener Weg (Platform Engineering)

Die konsolidierte Sprache dafür ist heute **Platform Engineering** (CNCF):

- **Platform Contract / Platform API** — die versionierte Oberfläche, die die
  Plattform garantiert: SDKs, Base Images, Manifest-Schema, Runtime-Services
  (Auth, Storage, Messaging, Observability). Alles hinter dem Vertrag ist
  Plattform-Interna und darf sich frei ändern.
- **Golden Path (Paved Road)** — der kanonische Weg, eine App zu bauen:
  Scaffold/Template, Base Images, geteilte Pipeline, Standard-Deployment. Wer auf
  dem Weg bleibt, bekommt alles geschenkt; Abweichen ist erlaubt, aber man trägt
  dann selbst.
- **Platform Capabilities** — die Funktionalität, die Apps konsumieren statt
  bauen.
- **„Kanonische App" = Thin App:** eine App, die auf dem Golden Path bleibt und
  nur ihren Business-Logic-Kern besitzt. Genau Andres Formulierung — der Standard
  nennt es „the platform absorbs the undifferentiated heavy lifting".

Der Mechanismus hinter „**die Plattform ändert sich selten, Apps bauen
beliebig**" ist im Standard kein Wunsch, sondern ein Vertragswerk:

1. **Versionierter Plattform-Contract** (SemVer: Breaking = Major).
2. **Deprecation Policy** — nichts verschwindet unangekündigt; Abkündigung mit
   Frist und Migrationspfad (Vorbild: Kubernetes Deprecation Policy).
3. **Kompatibilitätsfenster / Version Skew Policy** — die Plattform unterstützt
   Apps, die gegen die letzten N Minor-Versionen gebaut sind (Vorbild:
   Kubernetes N-2, Browser-Evergreen, Android API Levels).
4. **Stabile Interfaces, instabile Interna** — der Vertrag ist schmal und hart,
   alles dahinter beweglich.

### 3.4 Anatomie einer App: Workloads (CNCF/Kubernetes-Sprache)

Eine „App" ist im Standardbild ein **Set aus Workloads** unter einem gemeinsamen
Lebenszyklus:

| Unser Wort | Standard-Workload | Typische Form |
|---|---|---|
| Frontend-Anteil | **Web workload** (stateless) | Deployment + Service/Ingress; statische Assets ggf. CDN |
| Backend-Anteil | **API service workload** (stateless) | Deployment + Service; horizontal skalierbar |
| Workflow-Anteil | **Batch/Workflow workload** | Jobs bzw. Workflow-Engine (CNCF: Argo Workflows); jeder Step ein Container |

„Weitestgehend gleichartig gebaut" heißt im Standard: **eine goldene Pipeline
stanzt alle drei** — gleiches Base-Image-Regime, gleiche Build-Schritte, gleiche
Attestation, unterschiedliche Workload-Manifeste. Die App deklariert ihre
Workloads in einem **Application Manifest** (deklarativ, versioniert im Repo —
GitOps-Prinzip 1+2).

### 3.5 Die Pipeline ist selbst ein Produkt mit drei Existenzformen

Andres Beobachtung — die Buildpipeline hat selbst Repo, Binary und Installation —
ist im Standard präzise abgebildet, als **drei getrennte Dinge**:

1. **CI/CD-System** (der Dienst): Runner-Infrastruktur, Scheduler, Secrets —
   eine betriebene Plattform-Capability mit eigenen Instanzen (GitHub Actions,
   GitLab CI, Cloud Build, Tekton). Hat selbst Source/Artifact/Instance.
2. **Pipeline-Templates** (das Artefakt): **Pipeline-as-Code**, versioniert
   releast — „reusable workflows" / „CI templates" / „golden pipelines". Die
   Plattform besitzt sie; Apps **instanziieren** sie nur.
3. **Pipeline-Instanziierung** (die Nutzung): das dünne Pipeline-File im
   App-Repo, das Template + Version referenziert.

Damit gibt es **eine** Server-Pipeline und **eine** App-Pipeline nur als
Template-Familie — nicht als Kopie pro Repo. Pipeline-Updates sind
Template-Releases und rollen über alle Apps aus wie jedes andere
Plattform-Release: versioniert, mit Deprecation-Fenster.

### 3.6 Versionierung, Pinning, Lieferkette (SemVer + SLSA + SSDF)

- **Identität ist der Digest, nicht das Label.** OCI-Images sind
  inhaltsadressiert; Tags sind bewegliche Namen, Digests sind Fakten. (Unsere
  Regel „Compare SHAs, not version numbers" ist exakt dieser Standard.)
- **Abhängigkeiten sind gepinnt und maschinell verifiziert** — Lockfiles,
  Digest-Pins, Version-Manifeste. Der Standard-Kopplungspunkt zwischen
  Produzent und Konsument ist aber die **Registry**: Konsumenten pinnen
  **Artefakt-Versionen/Digests**, nicht Quell-Checkouts.
- **Jedes Artefakt trägt seine Herkunft:** SBOM (was ist drin) + SLSA
  Provenance/Attestation (wer hat es wann aus welchem Commit gebaut). Der
  Digest verbindet Artefakt ↔ Provenance ↔ Source-Commit kryptografisch.
- **Drift ist ein Messwert, kein Schicksal:** „Pin ist alt" ist im Standardbild
  eine Dashboard-Zahl (Dependency-Update-Automation à la Renovate/Dependabot +
  Compliance-Scan über SBOMs), kein stiller Zustand.

### 3.7 Multi-Arch: das ARM/x86-„Thema" ist im Standard gelöst

Die Architektur-Spezifität ist real (Container sind arch-gebunden), aber der
Standard macht sie **unterhalb der Sichtbarkeitslinie** unsichtbar: ein
**OCI Image Index (Manifest List)** fasst die per-Arch-Manifeste unter **einem**
Tag/Digest zusammen; die Runtime zieht automatisch die passende Variante.
Gebaut wird per Multi-Platform-Build (native Runner pro Architektur oder
Emulation). Konsequenz für die Ontologie: **Arch ist eine Dimension des
Artefakts, nie der App.** Kein Konsument — weder Deployment noch Pin — spricht
je über Architektur.

Zur Kostenfrage (Diskussion 2026-07-29): Multi-Arch verdoppelt **nicht** die
ausgelieferte Größe — die Runtime zieht über den Index genau eine Variante;
Pull, Platte und Startzeit bleiben unverändert. Verdoppelt wird nur
Registry-Speicher, und dort nur der arch-spezifische Anteil (Base-OS,
Binaries, native Wheels): Layer sind digest-adressiert, byte-identische
neutrale Layer (Frontend-Bundles, reine Python-Logik, Assets) werden geteilt —
allerdings nur bei deterministischem Build; wer sparen will, trennt neutrale
und arch-spezifische Layer bewusst im Dockerfile. Die Multi-Arch-Kosten
(Build-Zeit ×Architekturen, Registry-Platz) liegen damit vollständig auf der
Produzenten-/Bauengine-Seite.

### 3.8 Environments, Promotion, GitOps

- **Environments** sind erstklassige Objekte: dev → staging → prod (+ ephemere
  Preview-Environments). Unterschied zwischen ihnen ist **nur Config**.
- **Promotion:** dasselbe unveränderliche Release wandert durch die
  Environments; jede Stufe ist ein Quality Gate. Nie ein Rebuild.
- **GitOps:** Der Soll-Zustand jeder Environment (welche Releases, welche
  Config) steht deklarativ in Git; ein Reconciler gleicht kontinuierlich ab.
  Damit ist „was läuft wo" eine **Abfrage, kein Gerücht** — und Rollback ist
  ein Revert.
- **Release-Kanäle** für die Außenwelt: stable / beta / LTS — die Strategie, mit
  der ein Anbieter „selten und verlässlich" nach außen ändert, obwohl er innen
  täglich baut.

### 3.9 Betrieb und Wartung (Day-2): SRE + ITIL + SSDF-RV

Der laufende Apparat, in Standardbegriffen:

- **Observability** — Metrics, Logs, Traces als Plattform-Capability; Apps
  bekommen sie geschenkt (Golden Path), bauen sie nie selbst.
- **SLO / Error Budget** — der Vertrag über Zuverlässigkeit; das Error Budget
  steuert das Tempo von Änderungen (SRE).
- **Incident / Problem / Change Management** — der ITIL-Anteil; Incidents
  füttern den Loop zurück in Source (Postmortem → Issue → Fix → Release).
- **Vulnerability Response (SSDF RV)** — CVE-Triage über SBOMs („welche
  Artefakte enthalten libX 1.2?" ist eine Registry-Abfrage), Patch-SLAs,
  **Base-Image-Refresh-Kadenz**: Plattform patcht Base Images, die goldene
  Pipeline rebuildet die Welt, Apps merken es nicht.
- **Configuration Management (NIST CM)** — CM-2 Baseline pro Environment, CM-3
  Change Control (im GitOps-Bild: der PR-Review auf das Environment-Repo),
  CM-8 Inventory (im Container-Bild: Registry + Cluster-Ist = Inventar).
- **Lifecycle der installierten Basis** (self-managed Variante): Support-Matrix
  pro Version, Upgrade-Pfade („durch N.x hindurch"), Migrationsskripte als Teil
  des Releases.

### 3.10 Die zwei Geschmacksrichtungen sind Deployment-Modelle, kein Fork

NIST SP 800-145 nennt es Deployment-Modelle; die Industrie hat dafür ein
konsolidiertes Muster (GitLab, Grafana, Sentry …):

- **Hosted/SaaS** („Server"): der Anbieter betreibt; Multi- oder Single-Tenant;
  kontinuierliche Deployments möglich.
- **Self-managed/Standalone**: der Kunde (oder Entwickler lokal) betreibt; die
  Auslieferung ist ein **Distribution-Artefakt** (Installer-Bundle, Airgap-OCI-
  Bundle, Chart, Desktop-Verpackung) desselben Releases.

Das Gesetz dazu: **Ein Codebase, ein Artefakt-Set, zwei Distributionskanäle.**
Die Geschmacksrichtung ist eine Verpackungs- und Betriebsfrage am Ende der
Pipeline — niemals eine zweite Quelle, niemals ein zweites Build-Regime. (Genau
das ist die „one source, two runtimes"-These unseres App-Templates, als
Standardprinzip.)

## 4. Das Gesamtbild als Matrix

Ding-Arten × Existenzformen — jede Zelle mit ihrem Standardnamen:

| | **Source** (SCM) | **Artifact** (Registry) | **Instance** (Environment) |
|---|---|---|---|
| **Plattform** | Platform-Repo(s) | Release-Set: Images (Digest), Charts, SDKs, Distribution-Bundles — je Kanal verpackt | SaaS-Instanz(en) **und** self-managed Installationen; GitOps-verwaltet bzw. Support-Matrix |
| **Buildpipeline** | Pipeline-as-Code-Repo (Template-Familie) | Versionierte Pipeline-Templates + Runner-/Builder-Images | CI/CD-Dienst (Runner-Flotte) als betriebene Capability |
| **App** (FE/BE/WF gleichermaßen) | App-Repo (Scaffold vom Golden Path; enthält Manifest + dünne Pipeline-Instanziierung) | OCI-Images unter **einem** Multi-Arch Image Index pro Workload, + SBOM/Provenance | Workloads in Environments (web/API: Deployments; Workflow: Jobs/Workflow-Engine) |

Quer darüber liegen die drei verbindenden Schichten:

1. **Der Plattform-Contract** (versioniert, Deprecation-Policy, Skew-Fenster) —
   verbindet Plattform-Zeile und App-Zeile.
2. **Die Lieferkette** (CI → Registry → Release → Promotion → GitOps) —
   verbindet die Spalten.
3. **Der Betriebs-Loop** (Observability → SLO → Incident → Fix → Release) —
   führt von rechts nach links zurück.

## 5. Mapping: Standard-Ontologie → VPATH

| VPATH-Begriff/-Ding | Standardbegriff | Quelle |
|---|---|---|
| Die Plattform (vpath_server) | Internal Developer Platform; nach innen PaaS, nach außen SaaS | CNCF Platforms, NIST 800-145 |
| Server-Variante | Hosted/SaaS deployment model | NIST 800-145 |
| Standalone-Variante | Self-managed distribution desselben Releases (eigener Kanal, z. B. Electron-Verpackung, Airgap-OCI-Bundle) | Industriemuster (GitLab et al.) |
| App = Frontend + Backend + Workflow | Workload-Set: web / API service / batch-workflow | CNCF/K8s |
| „Gleichartig gebaut" | Eine goldene Pipeline für alle Workload-Arten | Platform Engineering |
| Kanonischer Anteil | Golden Path + Platform Capabilities | CNCF Platforms |
| „App ist kanonisch, wenn sie nichts selbst baut" | Thin App auf dem Paved Road | Platform Engineering |
| App-individueller Business-Logic-Anteil | Der Workload-Code — das Einzige, was die App besitzt | Twelve-Factor |
| ARM vs. x86 erzwingt arch-spezifische Builds | Multi-Platform-Build unter einem OCI Image Index; Arch ist Artefakt-Dimension, nicht App-Dimension | OCI image-spec |
| Repo / Binary / Instanz (bei allem) | Source / Artifact / Instance; Build→Release→Run strikt getrennt | Twelve-Factor V, OCI |
| Buildpipeline für Server bzw. Apps | Golden-Pipeline-Template-Familie (Pipeline-as-Code) + CI/CD-Dienst | konsolidierte CI/CD-Sprache |
| App-Template / Kit | Golden-Path-Scaffold (App Development Kit) | Platform Engineering |
| Gepinnte SHAs zwischen Repos | Dependency Pinning; Standard-Kopplungspunkt ist die Registry (Artefakt-Digest), Verifikation im Build; SBOM + SLSA Provenance | SLSA, SSDF PS/PW |
| preBuild-Pin-Verifikation, check_lockstep.py | Build-time dependency verification / lockstep gate | SSDF PW |
| Image-Labels mit Pin-Ständen | Provenance-Attestation (Standardform: signierte Attestation statt Label) | SLSA, in-toto |
| „Plattform ändert sich selten, Apps beliebig" | Stable platform contract: SemVer + Deprecation Policy + Version-Skew-Fenster (N-2) | K8s-Vorbild, SemVer |
| Release der Plattform | Release-Set + Kanäle (stable/beta/LTS) | Release Management |
| Installation (irgendwo läuft sie) | Deployment in Environment; Baseline + Inventory | NIST 800-53 CM |
| Drift („Pin ist alt, baut aber grün") | Messbarer Skew: Dependency-Update-Automation + SBOM-Abfrage statt stillem Altern | SLSA/Renovate-Muster |

## 6. Spannungen, die das Mapping sichtbar macht

Kein Entscheidungsteil — aber die Stellen, an denen unser Ist vom Standardbild
abweicht, benennt das Mapping von selbst. Das ist der Diskussionsstoff:

1. **Kopplungspunkt Source statt Registry.** Wir pinnen Quell-Commits
   (git-SHA-Pins, Vendoring, In-Tree-Kopien); der Standard koppelt über die
   Registry mit Artefakt-Digests. Konsequenz des Ist: Jeder Konsument baut den
   Produzenten mit; „no PyPI publish" macht die Registry-Rolle unbesetzt. Der
   Standardmechanismus (Registry + Digest-Pin + Provenance) würde die
   Pin-Arithmetik dieses Workspaces zu einer Registry-Abfrage machen.
2. **Der Plattform-Contract ist implizit.** Lockstep (Kit ↔ Server auf
   demselben SHA) erzwingt Gleichzeitigkeit statt Kompatibilität — das
   Standardbild hat stattdessen einen versionierten Contract mit Skew-Fenster,
   damit Apps *nicht* im Gleichschritt mit der Plattform laufen müssen. Genau
   dieses Fenster ist der Mechanismus hinter dem Zielzustand „Plattform ändert
   sich selten, Apps bauen beliebig".
3. **Release und Deployment fallen zusammen.** Install-Skripte bauen und
   deployen in einem Zug (build-on-deploy); Standard ist build-once-promote —
   ein Release-Artefakt, das durch Environments wandert.
4. **Multi-Arch liegt heute auf der App-Seite der Linie.** Arch-spezifische
   Builds sind sichtbar; der Image Index würde sie unter einen Digest schieben.
5. **Provenance als Label statt Attestation.** Image-Labels mit Pin-Ständen
   sind der richtige Gedanke in schwacher Form; der Standard signiert
   Attestations, die maschinell verifiziert werden (die
   verify-vendor-provenance-Schwäche — Stringvergleich statt Inhalt — ist
   genau die Lücke zwischen beiden Formen).

Alle fünf sind Übertragungen, keine Erfindungen — jede Spannung hat einen
benannten Standardmechanismus als Auflösung.

## 7. Offene Punkte

- Tenancy-Modell der Server-Variante (Single- vs. Multi-Tenant) ist im Bild
  offen gelassen — für die Ontologie egal, für den Betrieb später nicht.
- Ob aus diesem Strang ein Wiki-Kapitel (Vault-Inhalt) wird — offen. Der
  Strang liegt seit 2026-07-29 in vpath_platform_mgmt (Betriebs-/
  Plattformthema; ursprünglich in vpath_llm_wikis abgelegt, per
  Nutzerentscheid hierher verschoben).
- Kosten-/FinOps-Dimension bewusst ausgeklammert.
