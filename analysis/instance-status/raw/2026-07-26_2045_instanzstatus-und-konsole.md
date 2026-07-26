# User Request — 2026-07-26 20:45

Kanal: Diktat (Sprach-Übersetzer), an den zuarbeitenden Agenten
(Rolle: `platform-coordination-deputy`).
Vorgänger-Request derselben Sitzung: `../instance-management/raw/2026-07-26_2007_instanzverwaltung-signaletik.md`

---

## Wortlaut (unverändert)

> Und du guckst dich einfach weiter Requests. Der nächste Request ist, dass diese
> Instanzen, die wir gerade aufgeschrieben haben, dass wir die im Status überprüfen
> können. Das heißt, es muss ein zentrales Skript geben, dass die get ignorierte
> Definition von Serverinstanzen ausliest und dann prüft. Für die großen Server, aber
> auch für die lokalen Instanzen, auf welchen Versionen laufen die und was ist der
> Status. Das wäre gut, wenn das irgendwie halt mechanisch geht. Das heißt, ich stelle
> mir das so vor, dass man ein Skript hat, das durchläuft und für alle Instanzen prüft.
> Ob sie gerade laufen und was der letzte Installiervorgang war. Und was die aktuelle
> Version ist. Falls sich das gar nicht ermitteln lässt, dann brauchen wir ein, wenn
> man so will, Health Endpoint. Sowohl für jeden Server als auch für jede Standalone
> Instanz und müssen das koordiniert umsetzen im Serverprojekt. Also, der zweite
> Request, den du aufschreibst, für dieses Management Plattform Management Projekt ist
> ein am besten ein UI, das wir aufstarten und indem jede Instanz von Server, die wir
> zur Verfügung haben, inklusive Uptime und so, einfach gelistet wird. Also ich sehe so
> ein klassisches Links sind die Instanzen und deren Typ, und wenn man draufklickt,
> sieht man den Status.Also wenn man draufklickt, sieht man den Status im Detail, aber
> links sieht man auch schon mal, ob die Instanzen laufen oder broken sind oder was mit
> denen ist.

---

## Dekodierung der Diktat-Artefakte

Nur Wortkorrekturen, keine Deutung.

| Wortlaut | Gemeint |
|---|---|
| „Und du guckst dich einfach weiter Requests" | Du nimmst einfach weiter Requests auf |
| „die get ignorierte Definition von Serverinstanzen" | die **git-ignorierte** Definition der Serverinstanzen (das Register aus Request 1) |
| „was der letzte Installiervorgang war" | wann/was zuletzt installiert wurde — letzter Deploy-/Install-Vorgang |
| „ein, wenn man so will, Health Endpoint" | ein Health-Endpoint (Bezeichnung vom Nutzer selbst als behelfsmäßig markiert) |
| „müssen das koordiniert umsetzen im Serverprojekt" | die Health-Endpoints entstehen **im Serverprojekt**, koordiniert |
| „ein am besten ein UI, das wir aufstarten" | eine startbare Oberfläche |
| „inklusive Uptime und so" | inkl. Laufzeit seit Start |

## Die drei Gegenstände in diesem Prompt

Der Nutzer nennt zwei Requests; sachlich sind es drei Bauteile.

1. **Status-Skript** — liest das git-ignorierte Register, läuft über **alle** Instanzen
   (große Server *und* lokale Standalones) und ermittelt mechanisch je Instanz:
   läuft sie · letzter Installiervorgang · aktuelle Version.
2. **Health-Endpoint** — *nur falls sich das nicht ermitteln lässt.* Ausdrücklich als
   Bedingung formuliert, nicht als gesetzt. Für **jeden** Server und **jede**
   Standalone. Umsetzung **im Serverprojekt**, koordiniert.
3. **UI** — startbare Oberfläche im Platform-Management-Projekt. Links die Liste der
   Instanzen mit Typ und Grobzustand (läuft / broken / sonstiges), Klick öffnet den
   Detailstatus. Uptime gehört dazu.

Reihenfolgeaussage des Nutzers: (2) ist der **Fallback** von (1), nicht dessen
Ergänzung. Die Ermittlungsfrage geht der Endpoint-Frage voraus.

## Abhängigkeit, die im Prompt steht

„diese Instanzen, die wir gerade aufgeschrieben haben" und „die git-ignorierte
Definition" verweisen beide auf den Vorgänger-Request. Dieser Request **setzt das
Register voraus**, das dort erst beantragt ist.
