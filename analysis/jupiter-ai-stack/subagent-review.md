# Subagent-Review: Codex vs. Claude-Wrapper an dieser Recherche

Finaler Schritt der Methoden-Vorgabe (raw, 2026-07-30): beide Delegates an je einem
überschneidungsfreien Paket, kein Doppel-Arbeiten — Beurteilung an der realen Arbeit,
gegen die VOR Eintreffen der Ergebnisse fixierten Kriterien (Summary).

## Rahmen

| | Claude-Wrapper | Codex |
|---|---|---|
| Paket | A — Modell-Landschaft, SWE-bench Verified | B — Serving-Architektur, Dual-GPU-Machbarkeit |
| Konto/Modell | `claude_tb` → `info_vpath`, Opus 5 | Config-Default (gpt-Klasse), ein Thread |
| Aufwand | 38 Turns, 2,64 $ (Subscription-Quota) | ~42 Items, Quota Codex-Abo |
| Brief-Treue | exakt eine Datei, kein Commit, Box unberührt ✓ | exakt eine Datei, kein Commit, Box unberührt ✓ |

## Befund je Kriterium (1–5, an dieser Arbeit gemessen)

| Kriterium | Wrapper | Codex | Beleg |
|---|---|---|---|
| Evidenztreue | **5** | **5** | Beide mit URL je Zahl; meine Stichproben (HF-Karte 27B, GGUF-Größen; LMDeploy-TurboQuant, `--spec-draft-device`) trafen **alle** zu. Beide markieren Unbelegbares explizit als offen. |
| Prämissen-Härte | 4 | **5** | Beide kippen die Wunsch-Topologie „KV auf 2060" unabhängig und begründet. Codex zusätzlich mit Hardware-Präzision (FP8 erst ab Ada; Marlin-SM75-Rückportierung — Korrektur einer VERALTETEN Annahme aus meinem eigenen Briefing; Q8_0 = 1,0625 B/Wert). |
| Rechenwege | **5** | **5** | Wrapper: KV-Herleitung aus config.json, gegen unabhängige Messung plausibilisiert — nachgerechnet, stimmt. Codex: GQA-Formel mit Geometrien aus Originalconfigs — nachgerechnet, stimmt. |
| Aktualität / Discovery | **5** | **2** | **Der entscheidende Unterschied.** Der Wrapper fand die April-2026-Familie (Qwen3.6) und die Hybridarchitektur — der Dreh- und Angelpunkt des Ergebnisses. Codex arbeitete auf dem Modellstand ~Mitte 2025 (Qwen2.5-Coder-14B, Devstral 2507) und hat NICHT nach neueren Familien gesucht; seine konkreten Modell-Empfehlungen waren bei Ankunft überholt. (Fairness: Modelljagd war Paket A — aber Codex hätte für seine eigenen Optionen A/B die Aktualität prüfen können.) |
| Urteilskraft | 4 | 4 | Wrapper: klare Korrektur des Nutzer-Kandidaten (27B > 35B-A3B fürs Coding) + ehrliche Q6-Abwägung. Codex: ehrliches Topologie-Ranking inkl. „Solo-Baseline muss jeder Dual-GPU-Versuch schlagen" und „offen statt geraten" (SGLang). Beide ohne Optionssalat. |

## Charakteristik (für künftige Delegation)

- **Claude-Wrapper: Discovery und Weltstand.** Breite Websuche, findet das Neueste
  (Modellfamilien, unabhängige Messungen, Negativ-Resultate wie „Spec-Decoding bringt auf
  Ampere+A3B nichts"), eigenständige Herleitungen aus Primärdaten (config.json). Teurer
  (Opus-Quota), dafür der richtige Arm für „Was ist HEUTE der Stand der Welt?".
- **Codex: Doku-Präzision und Mechanik.** Flag-genau (`--spec-draft-device`, `-ncmoe`,
  `quant_policy=42`), dekodiert vage Begriffe zu realen Produkten („turboquant" →
  LMDeploy TurboQuant), korrigiert Hardware-Folklore mit Primärquellen, diszipliniertes
  Offen-Markieren. Schwäche: Release-Blindheit — es recherchiert tief in Doku, die es
  kennt, aber jagt nicht nach dem Neuesten. Der richtige Arm für „Was können diese
  Systeme EXAKT?".
- **Konsequenz fürs Schnüren:** Paket-Zuschnitt hat funktioniert (keine Kollision, beide
  brief-treu). Künftig: Discovery-lastige Fragen → Wrapper; Spezifikations-/Machbarkeits-
  fragen → Codex; und Codex' Briefing sollte den aktuellen Modell-/Release-Stand als
  INPUT mitbekommen, statt ihn selbst erheben zu müssen.

## Verdikt

Kein Sieger über alles — ein komplementäres Paar. An dieser Aufgabe war der Wrapper
ergebnisentscheidend (ohne Qwen3.6-Fund wäre das Konzept auf einem 14-Monate-alten
Modell gelandet), Codex qualitätsentscheidend (Topologie-Wahrheit, TurboQuant-Dekodierung,
Hardware-Grenzen). Die Kombination hat sich exakt so gelohnt, wie die Methoden-Vorgabe
es wollte.
