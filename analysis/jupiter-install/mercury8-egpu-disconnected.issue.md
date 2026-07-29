# Issue: mercury8 — eGPU disconnected, Register-Versprechen „CUDA" unwahr

Status: draft · Herkunft: Nebenbefund beim jupiter11-GPU-Enablement,
2026-07-29 (Referenzmessung der Fleet-Treiberversion) · Strang: `summary.md`

**Beobachtung (gemessen 2026-07-29, read-only, Box nicht angefasst):**

- `nvidia-smi` auf mercury8: „couldn't communicate with the NVIDIA driver".
- `lspci`: **kein NVIDIA-Gerät am Bus**; 0 geladene nvidia-Module.
- `boltctl`: das Razer Core X ist **disconnected**.

**Deutung:** Die RTX-3060-eGPU ist physisch getrennt (Gehäuse aus/abgesteckt
oder Karte entnommen). Naheliegender Zusammenhang: an jupiter11 hängt seit
2026-07-29 ~19:49 UTC ein Razer Core X mit einer RTX 3090 — vermutlich ist
das Gehäuse gewandert und die Karte getauscht/ersetzt worden. Vermutung,
nicht verifiziert — physische Klärung kann nur Andre liefern.

**Pain:** Der mercury8-Register-Kommentar „carries the CUDA eGPU
(CUDA/ollama)" beschreibt einen Zustand, der nicht mehr besteht. Alles, was
auf mercury8 GPU erwartet (ollama-Workloads, CUDA-Jobs), läuft ins Leere
oder fällt auf CPU zurück — genau die stille Degradation, die wir nicht
dulden.

**Sofortmaßnahme (erledigt im selben Zug):** mercury8-Register-Kommentar um
den gemessenen Ist-Zustand ergänzt (eGPU disconnected seit spätestens
2026-07-29; Zeile als historisch markiert). Keine Änderung an der Box.

**Offen (Nutzerentscheid):**
- Bestätigen, wohin die 3060 und das Gehäuse physisch gewandert sind.
- Entscheiden, ob mercury8 dauerhaft ohne GPU bleibt (dann Registerzeile und
  ggf. GPU-abhängige Workloads auf mercury8 bereinigen) oder eine GPU
  zurückkommt.
- Prüfen, ob auf mercury8 aktuell etwas GPU-Erwartendes deployt ist
  (ollama?) und wie es sich ohne GPU verhält.
