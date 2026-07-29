# Konzept: lokales Coding-LLM-Serving auf jupiter11 (Synthese aus Paket A + B)

Status: Vorschlag zur Entscheidung · 2026-07-30 · Quellen: `research/model-landscape.md`
(Wrapper), `research/serving-architecture.md` (Codex), eigene Stichproben-Verifikation
(HF-Modellkarten, LMDeploy-Doku, llama-server-README — alle tragenden Claims geprüft).

## Urteil über die Nutzer-Idee, Punkt für Punkt

| Idee (Diktat) | Urteil |
|---|---|
| „Qwen 3.6 36B in 8-bit" | **Existiert wirklich**: Qwen3.6-35B-A3B (April 2026). Aber es ist die *Max-Kontext*-Wahl, nicht die *Max-Qualität*-Wahl: die dense Schwester **Qwen3.6-27B** schlägt sie auf SWE-bench Verified deutlich (77,2 % vs. 73,4 %, Herstellerangaben, von mir gegen die Modellkarte verifiziert) und ist das beste Open-Weights-Coding-Modell, das überhaupt ins Budget passt — nur ~3 Punkte hinter dem besten Open-Weights-Modell jeder Größe. |
| „KV-Cache auf der 2060, Modell auf der 3090" | **Wörtlich in keiner gepflegten Engine umsetzbar** (beide Pakete unabhängig, Begründung: Attention braucht den KV am Layer-Device; Remote-KV über TB3 wäre ein Latenz-Desaster). Nächstbeste reale Topologien: Layer-Split (KV folgt den Layern auf die 2060) oder **Draft-Modell auf der 2060** (`--spec-draft-device`, Flag von mir verifiziert). |
| „turboquant" | **Dekodiert**: TurboQuant ist ein reales KV-Kompressionsverfahren (LMDeploy 0.13, `quant_policy=42`, K=4bit/V=2bit — verifiziert). Aber: nur PyTorchEngine, kein Spec-Decoding, LMDeploy-Support für die neue Qwen3.6-Hybridarchitektur fraglich — und vor allem **unnötig**: Qwen3.6 hat nur in jedem 4. Layer volle Attention, der KV ist von Haus aus winzig (27B: 32 KiB/Token @8bit; 35B-A3B: 10 KiB/Token). Das Kontext-Ziel erreicht die Architektur, nicht die KV-Kompression. |
| „maximaler Kontext" | **Realistisch**: 35B-A3B fährt die nativen **262.144 Token** mit nur 2,5 GiB KV (8-bit) — mit MoE-Experten-Offload in die 64 GB RAM (gemessene Referenz auf 3090-Klasse: 89 t/s auf Desktop-CPU; auf unserer 4C/8T-CPU konservativ 15–35 t/s geschätzt). |
| „8-bit, tiefer nicht ohne Not" | Erfüllbar. Der einzige Zielkonflikt: die schnellste robuste Variante (27B Q6_K solo auf der 3090, **31,6 t/s gemessen** auf exakt dieser GPU-Klasse) liegt einen Schritt unter 8-bit → das ist die eine Abwägung, die Andre entscheiden muss. |
| „beide RTX nutzen" | Sinnvoll ja — aber ehrlich: Die 2060 (6 GB, Turing, 336 GB/s) ist als *Mitrechner* oft ein Bremsklotz; ihre besten Rollen sind (a) Träger der letzten Layer im strikten 8-bit-Split, (b) Draft-/Utility-GPU (Autocomplete-Modell, Embeddings), (c) Spec-Decoding-Experiment. Jede Dual-GPU-Variante muss die Solo-Baseline **messbar schlagen**, sonst fliegt sie (No-Fallback). |

## Empfohlene Ziel-Architektur

**Engine:** `llama.cpp`/`llama-server` (neueste Version — Gated-DeltaNet-Operatoren nötig)
hinter **`llama-swap`** als systemd-Service. OpenAI-kompatible API (`/v1/chat/completions`),
Bind an die LAN-Adresse mit API-Key, Backends auf `127.0.0.1`. Niemals öffentlich.
Ein Ökosystem (Apache 2.0, GGUF), **ein Setup mit Profilen statt zwei Stacks**:

| Profil | Modell | Quant | Topologie | Kontext (8-bit-KV) | Speed |
|---|---|---|---|---|---|
| **P1 „Arbeitspferd"** | Qwen3.6-27B | Q6_K (21 GiB) | 3090 solo | ~64–96K | ~31 t/s (gemessen, 3090-Klasse) |
| **P1s „strikt 8-bit"** (Alternative zu P1) | Qwen3.6-27B | Q8_0 (26,6 GiB) | Layer-Split 3090+2060 | ~64K | 15–22 t/s (Schätzung) |
| **P2 „Max-Kontext"** | Qwen3.6-35B-A3B | Q8_0 (34,4 GiB) | Attention+KV auf 3090, MoE-Experten → RAM (`--n-cpu-moe`) | **262K nativ** | 15–35 t/s (Schätzung) |
| P3 (Experiment, später) | P1 + Draft/MTP auf 2060 | — | `--spec-draft-device` | — | nur falls Messung > P1 |

**Messpflicht vor Abnahme** (auf der Box, nicht aus Referenzen): `llama-bench` +
drei reale Coding-Workloads; je Profil Prefill, Decode, TTFT, VRAM je GPU. Achtung
eGPU: Referenzmessung zeigt Decode über TB3 nahezu ungebremst, **Prefill etwa halbiert** —
das trifft Coding-Workloads (große Prompts) und gehört ins Messprotokoll.

## Die eine offene Entscheidung (Andre)

**Q6_K als Arbeitspferd zulassen?** Empfehlung: **ja** — der Gegenwert (+50 % Speed,
~doppelter Kontext, Ein-Karten-Robustheit) ist genau die „Not", die der 8-bit-Anker
zulässt; P1s bleibt als strikte Alternative definiert. Bei „hart ≥8-bit": P1s statt P1,
Rest unverändert.

## Handover (nach Entscheid)

Implementierungs-Issue: llama.cpp bauen (CUDA, neueste Version), Modelle laden
(gitignorierte Ablage auf der Box; die zweite SSD 232,9 GB bietet sich als Modell-Platte
an — Format-/Mount-Entscheid gehört ins Issue), llama-swap + systemd + Firewall-Bind,
Messprotokoll, Register-Kommentar. Die Box wird bis dahin nicht angefasst.

## Offene Punkte (aus den Paketen übernommen)

1. Alle t/s-Werte für jupiter11 sind Schätzungen — einzige Referenzen: 3090-Klasse
   Desktop. Harte Zahlen erst per `llama-bench` auf der Box.
2. Spec-Decoding: auf Ampere + A3B-MoE gemessen wirkungslos; für 27B-MTP ungetestet.
3. Devstral Small 2 Q8-Dateigröße unbelegt (irrelevant fürs Ranking — 9 Punkte hinter 27B).
4. SWE-bench-Verified-Scores der Open-Weights-Klasse sind Herstellerangaben
   (offizielles Leaderboard rankt Scaffolds und war nicht maschinenlesbar).
