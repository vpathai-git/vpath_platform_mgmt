# Strang: jupiter-ai-stack — lokales Coding-LLM auf jupiter11, OpenAI-kompatibel im Intranet

**Einstiegspunkt.** Wer nur diese Datei liest, ist auf Stand.

Sprache: Deutsch (Dateinamen, Code, Bezeichner Englisch) · Angelegt: 2026-07-30 01:00
Projekt: `vpath_platform_mgmt` · Vorgänger-Strang: `../jupiter-install/` (Box-Onboarding,
GPU-Enablement: RTX 2060 6 GB + RTX 3090 24 GB eGPU, Treiber 595.84, CUDA 13.2)
Status: **Stakeholder-Diskussion — Konzept liegt vor, EINE Entscheidung offen**
(Q6_K-Arbeitspferd zulassen oder hart ≥8-bit; Empfehlung: zulassen). Kern:
„Qwen 3.6 36B" existiert (Qwen3.6-35B-A3B) und wird das Max-Kontext-Profil (262K);
die dense **Qwen3.6-27B (77,2 % SWE-bench Verified)** ist der bessere
Coding-Hauptkandidat; KV-auf-2060 ist nicht umsetzbar (Draft-GPU/Layer-Split sind
die realen Näherungen); „turboquant" = LMDeploy TurboQuant, real, aber durch die
Qwen3.6-Hybridarchitektur unnötig. Details: `coding-llm-serving.concept.md`.
Subagent-Review (Methoden-Vorgabe) abgelegt: `subagent-review.md`.

---

## Der Request (Kurzform — Wortlaut in `raw/`)

Auf jupiter11 ein **ambitioniertes** Setup: bestes lokales Open-Weights-**Coding-Modell**
(Referenz: **SWE-bench Verified**), OpenAI-kompatible API **nur ins Intranet/WiFi**.
Beide RTX-Karten nutzen, möglichst schnell; **Gewichte ≥8-bit** (tiefer nur mit Not),
„turboquant"; Wunsch-Topologie: **KV-Cache auf der RTX 2060, Modell auf der RTX 3090**,
maximaler Kontext. Nutzer-Kandidat (Diktat, unscharf): „Qwen 3.6 36B" in 8-bit.
Prüfauftrag: Ist das realistisch und nutzt es das System maximal aus — oder gibt es
offensichtlich bessere Kandidaten?

**Methoden-Vorgabe (wörtlich in `raw/`):** Konzept, Orchestrierung, Review beim
Hauptagenten; delegierbare Pakete **abwechselnd an Codex und den Claude-Wrapper**;
nicht doppelt arbeiten, sondern im Review beobachten, wer sich wo besonders gut
anstellt; Abschluss: **Subagent-Review** als Ablage in diesem Strang.

## Arbeitsteilung (Orchestrierung)

| Paket | Wer | Inhalt | Ablage |
|---|---|---|---|
| A — Modell-Landschaft | Claude-Wrapper (`claude_tb` → `info_vpath`, Opus) | SWE-bench Verified live, „Qwen 3.6 36B" dekodieren, Kandidaten-Tabelle mit VRAM-Mathe bei 8-bit, 3 Empfehlungen; Evidenzvertrag (URL je Zahl) | `research/model-landscape.md` |
| B — Serving-Architektur | Codex (Config-Default-Modell) | Engine-Matrix heterogene Dual-GPU (SM75+SM86), Realisierbarkeit „KV auf 2060", 8-bit-Pfade (Marlin/FP8-Hardware-Grenzen), Kontext-Mathe, TB3-eGPU-Kosten, 2 Architektur-Optionen; Evidenzvertrag | `research/serving-architecture.md` |
| Konzept + Review + Synthese | Hauptagent (diese Session) | Prämissen prüfen, Zahlen stichprobenhaft verifizieren, Empfehlung bauen | `concept` + dieser Summary |
| Subagent-Review | Hauptagent | Vergleich Codex vs. Wrapper: Stärken/Schwächen an DIESER Arbeit | `subagent-review.md` (finaler Schritt) |

## Review-Kriterien (vorab fixiert, damit das Review fair ist)

1. **Evidenztreue**: Zahlen mit echter Quelle vs. erfunden/US-genau („confabulated precision").
2. **Prämissen-Härte**: Wird die Wunsch-Topologie (KV auf 2060) ehrlich geprüft oder
   gefällig durchgewunken? Werden Hardware-Grenzen (SM75/SM86, TB3) korrekt behandelt?
3. **Rechenwege**: KV-/VRAM-Mathe nachvollziehbar und nachrechenbar.
4. **Brief-Treue**: Scope eingehalten (nur die eine Datei, kein Commit, Box unberührt).
5. **Urteilskraft**: klare, begründete Empfehlung statt Optionssalat.

## Leitplanken

- Die Box wird in dieser Phase NICHT verändert (reine Stakeholder-Diskussion);
  Implementierung erst nach Handover-Entscheid.
- API nur ins LAN/WiFi binden — niemals öffentlich; Adressen bleiben aus dem Strang
  (Register-Regel).
- Qualitätsanker des Nutzers: Gewichte ≥8-bit bevorzugt, Abweichung nur begründet
  („Muss man abwägen").

## Backlog

| Prio | Punkt | Stand |
|---|---|---|
| P0 | Recherche-Pakete A+B | **erledigt 30.07.** (beide brief-treu, Stichproben bestanden) |
| P0 | Review + Synthese + Empfehlung | **erledigt 30.07.** → `coding-llm-serving.concept.md` |
| P0 | Subagent-Review (Codex vs. Wrapper) | **erledigt 30.07.** → `subagent-review.md` |
| P0 | Nutzer-Entscheid: Q6_K-Arbeitspferd ja/nein | **entschieden 30.07.: Q6 ok**; SSD-Bestätigung: Modelle auf die 256er-SSD |
| P0 | Umsetzung ([Issue](serving-implementation.issue.md)) | **läuft** — /models steht, Downloads + Toolchain im Hintergrund |

## Dateien

- `raw/2026-07-30_0100_local-coding-model-setup.md` — Wortlaut + Dekodierung
- `research/model-landscape.md` — Paket A (Wrapper): Qwen3.6-Fund, Kandidaten, KV-Mathe
- `research/serving-architecture.md` — Paket B (Codex): Engine-Matrix, Topologien, TurboQuant
- `coding-llm-serving.concept.md` — Synthese: Urteil je Diktat-Punkt, Zielarchitektur, Entscheid
- `subagent-review.md` — Codex vs. Wrapper an dieser Arbeit (Methoden-Vorgabe, finaler Schritt)

## Entscheidungslog

- 30.07. ~01:00: Strang angelegt (neues Thema). Zwei überschneidungsfreie
  Recherche-Pakete geschnürt und parallel delegiert (A → Wrapper via claude_tb,
  Konto info_vpath regulär gewählt — Exclude-Datei vom 23.07. führt es als
  reaktiviert; B → Codex). Review-Kriterien VOR Eintreffen der Ergebnisse fixiert.
- 30.07. ~01:20: Beide Pakete eingetroffen und reviewt. Stichproben-Verifikation
  aller tragenden Claims (HF-Karte Qwen3.6-27B: Existenz, 77,2 %, Apache 2.0,
  262K; GGUF-Größen aufs Zehntel; LMDeploy TurboQuant quant_policy=42 inkl.
  Einschränkungen; llama-server `--spec-draft-device`): alles bestätigt.
  KV-/GQA-Rechnungen beider Pakete nachgerechnet: konsistent. Codex' konkrete
  Modell-Picks als veraltet erkannt (Mitte-2025-Generation) und in der Synthese
  durch den Qwen3.6-Fund ersetzt. Konzept + Subagent-Review abgelegt; Handover
  wartet auf den Q6/Q8-Entscheid.
