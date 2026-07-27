# Issue: Erhebung des Instanztyps `remote` (win-claas)

**Status:** draft · **Priorität:** P2 (blockiert nur das remote-Template, nicht Achse 2)
**Herkunft:** Interview-Entscheidung M2, 2026-07-27

## Auftrag

Das `remote`-Template wird jetzt mit den bekannten Feldern strukturiert und als
**declared, unproven** markiert. Dieses Issue ist die Erhebung, die es beweist:
Zugangsweg und Deploy-Pfad des kundenseitigen Windows-Clusters (CLAAS-Linie).

## Was zu erheben ist

1. **Zugang:** Wie erreicht man den Cluster (das Serverprojekt führt ihn als
   Customer-Cluster-Target, z. B. `dehwllvpath01.claas.local`)? Protokoll,
   Sprunghost, Credentials-Modell — nur die *Struktur* ins Template, Werte
   bleiben gitignorte Payload.
2. **Deploy-Pfad:** Wie wird dort heute installiert/aktualisiert (das
   Server-README beschreibt den Install-Host ohne Internet)? Welche der vier
   Ortsfragen (Host+FS, Build-Prozess, Quell-Repos, Container-Images) haben
   dort andere Antworten als bei NUCs?
3. **Grenzen:** Was darf die Konsole dort überhaupt (Kundensystem!) — Health ja,
   Redeploy nur nach welchem Freigabeweg?

## Erfolgskriterium

Das `remote`-Template verliert die Markierung *unproven* — jede Feldangabe ist
belegt (Quelle im Serverprojekt oder Auskunft der Kundenseite), oder das Feld
ist ausdrücklich als offen markiert. Kein geratenes Feld.

## Quelle des Wissens

Primär das Serverprojekt (Target-Tabelle im README, Playbook-Installationswege);
sekundär Rückfrage an die Betreiberseite. Cross-repo — Koordination nötig.
