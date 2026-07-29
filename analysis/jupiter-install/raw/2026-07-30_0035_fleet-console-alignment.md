# Rohfassung — Fleet: deutsche Tastatur + Lapdock-Fähigkeit auf allen NUCs

Diktat Andre, 2026-07-30 ~00:35, Continuation (nach dem jupiter11-Lapdock-Setup).

> stelle auch alle anderen Nucs so ein, dass sie deutsche tastatur und
> displaymode alternate mode unterstützen

## Dekodierung

| Wortlaut | Gemeint |
|---|---|
| „alle anderen Nucs" | mercury8, venus10, mars12 (terra ist die Azure-VM, kein NUC, kein physisches Display) |
| „displaymode alternate mode" | DisplayPort Alternate Mode über USB-C — d. h. ein Lapdock an jeder Box muss Konsole zeigen (Alt Mode selbst ist Hardware; konfigurierbar ist der Konsolen-Pfad) |
| Randbedingung (aus dem Bestand) | Produktivboxen: reboot-frei arbeiten — Tastatur wirkt live via setupcon, Guards greifen beim nächsten natürlichen Boot |
