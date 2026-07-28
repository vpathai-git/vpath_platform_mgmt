# Issue: BP11 behauptet Baum-Identität, prüft aber nur den Index

Status: draft (Server-Strom-Spur) · Herkunft: mars12-Install 2026-07-28

**Befund:** Das BP11-Gate („Full-tree identity verified: /workspace is a
complete git checkout at <sha>") vergleicht `git ls-files | wc -l` — die Zahl
der im INDEX getrackten Dateien — plus die `extra/*.py`-Zählung. Es prüft
nicht, ob jede getrackte Datei im Arbeitsbaum tatsächlich liegt. Im
mars12-Lauf meldete es deshalb zweimal grün, während zwei getrackte Dateien
fehlten (vom Sync ausgeschlossen) — der Fehler flog erst 23 Minuten später im
Vendor-Freeze auf.

**Pain:** Ein Identitäts-Gate, das den Index zählt statt den Baum zu prüfen,
kann Baum-Identität nicht behaupten — es ist grün genau dann, wenn die
Buchhaltung stimmt, nicht wenn die Lieferung stimmt. Klasse: „im
Ableitungs-Pfad geprüft, nicht im Lauf-Pfad".

**Ziel (Server-Strom):** BP11 auf echte Baum-Prüfung heben — z. B.
`git status --porcelain` muss leer sein für getrackte Pfade (Deletions zählen
als Verletzung), oder `git ls-files -d` explizit leer. Red-Drill dazu: eine
getrackte Datei entfernen und zeigen, dass das Gate rot wird.
