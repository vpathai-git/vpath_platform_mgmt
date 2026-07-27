# Issue: Azure-Instanz verwaltbar machen (heute nur erreichbar)

> **ERLEDIGT / ÜBERHOLT 2026-07-27.** Die Kernannahme dieses Issues — *„der
> Deploy-Weg fehlt vollständig"* — ist widerlegt. Der Weg existiert und ist
> erprobt: Env-Overlay `config/dot_env/.env.vm5` (im Server committet),
> `VPATH_INSTALL_MODE=nuc`, Aufruf `-Penv=vm5 deployPipeline` **auf der Box**,
> Auslieferung per Delivery-Push vom Mac, GitOps/ArgoCD.
> Beleg: `claas_demo/analysis/infrastructure-consolidation/reports/deploy-pass.md`.
>
> Die vier offenen Fragen sind damit beantwortet: (1) über den nuc-Modus mit
> eigenem Profil; (2) die VM hat Internet, aber **kein** Git-Credential — der
> Delivery-Push bleibt der einzige Weg; (3) ja, `/workspace` ist die
> Repo-Kopie auf der Box; (4) ja, k3s v1.31.6+k3s1 im gleichen Zuschnitt.
>
> Die Instanz steht als `terra` im Register und ist über denselben Selektor
> ansprechbar wie die NUCs — read-only belegt: der Selektor erreicht dort den
> echten Gradle-Wrapper mit `-Penv=vm5`. **Nicht** über SOCKS: der Tunnel ist
> für Browser; direkter SSH vom Mac funktioniert.
>
> Rest-Punkt, nicht Teil dieses Issues: die Box signiert mit einem fremden
> Schlüsselpaar (Regel-8-Zustand, im Deploy-Pass gemeldet) — Freigabe beim
> zentralen Koordinator.


**Status:** draft · **Priorität:** P1
**Herkunft:** `raw/2026-07-26_2007_instanzverwaltung-signaletik.md`
(„Dann haben wir eine Azure Instanz, die ist im ZIP-File beschrieben, wo die liegt.")

## Was belegt ist

Quelle: `platform-admin-credentials.zip` (git-ignoriert seit 26.07.), darin
`vm5-access-manual.md`, `connect-vm5.ps1`, ein SSH-Private-Key, eine
Admin-Demo-Login-Notiz.

Aus dem Handbuch, ohne Zugangsdaten wiedergegeben:

- Azure-VM mit dem Namen **vm5**. **Nichts ist ins Internet exponiert** — das ist
  Absicht, kein Defekt.
- Zugang ausschließlich über einen **SSH-SOCKS-Tunnel** in das private Netz der VM.
  Ein PowerShell-Skript öffnet den Tunnel und startet ein dediziertes Chrome, das
  darüber routet; beim Schließen fällt der Tunnel.
- Die kanonische Adresse der Plattform ist die **private IP** der VM — off-VNet
  nicht erreichbar. Deshalb SOCKS und nicht ein einfaches `ssh -L`: nur so folgt der
  Browser dem Login-Redirect.
- Selbstsigniertes Zertifikat; Anmeldung über Keycloak.
- Admin-Notiz im Handbuch: Kollegen werden aufgenommen, indem ihr öffentlicher
  SSH-Key auf der VM hinterlegt und ein Keycloak-Nutzer angelegt wird.

**Konkrete Adressen, Nutzernamen, Ports und Schlüssel stehen bewusst nicht in dieser
Datei** — sie gehören ins git-ignorierte Register. Das ist der Punkt des Requests.

## Der Schmerz — und er ist größer, als er aussieht

Das Handbuch beschreibt **Zugang**, nicht **Verwaltung**. Es sagt, wie ein Kollege
sich einloggt und die Oberfläche sieht. Es sagt **nichts** darüber, wie auf dieser VM
gebaut, installiert, deployt oder redeployt wird.

Der Request verlangt aber genau das: *„ansprechbar, verwaltbar, redeploybar"*.

Für die NUCs existiert dieser Weg (Gradle nuc-Mode, `-Penv=nuc`, Delivery per
`git push` auf die Box — `vpath_server_dev/README.md:137-173`). Für Azure ist
**nicht verifiziert, dass es ihn gibt.** Möglicherweise ist das der größte verdeckte
Aufwand im ganzen Request.

## Offene Fragen, vor jeder Schätzung zu klären

1. Wie ist die Plattform auf vm5 überhaupt installiert worden — über welchen Pfad?
2. Gilt für vm5 der Airgap-Zwang wie für die NUCs, oder hat die VM Internetzugang?
   (Das entscheidet, ob Images übertragen werden müssen oder gezogen werden können.)
3. Existiert eine Repo-Kopie auf der VM, wie es der NUC-Delivery-Pfad vorsieht?
4. Läuft dort k3s im gleichen Zuschnitt wie auf den NUCs?

## Erfolgskriterium

Die Azure-Instanz ist im Register geführt und über denselben Selektor wie die NUCs
ansprech- und redeploybar — oder es ist dokumentiert und begründet, warum sie einen
eigenen Pfad braucht.

## Zu beachten

Der Zugangsweg über SOCKS ist für **Menschen** gebaut (Browser öffnet sich). Ein
Deploy-Werkzeug braucht einen nicht-interaktiven Pfad. Das Handbuch selbst nennt
unter „Admin notes" eine mögliche Vereinfachung (Hostname statt roher IP, dann
genügt ein einfacher Port-Forward) — als serverseitige Auth-Umkonfiguration, die
geplant werden müsste.
