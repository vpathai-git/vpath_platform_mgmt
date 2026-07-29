# Modell-Landschaft für lokales Coding-Serving auf jupiter11

Recherche-Paket A. Abrufdatum aller Quellen: **2026-07-30**. Reine Web-/Doku-Recherche,
die Box wurde nicht angefasst. Hardware-Budget als gegeben angenommen: RTX 3090 24 GB
(Ampere SM86, eGPU über Thunderbolt 3), RTX 2060 Mobile 6 GB (Turing SM75, intern),
64 GB DDR4, i7-1165G7 (4C/8T).

Einheiten: HuggingFace zeigt Dateigrößen in dezimalen **GB**; GPU-VRAM wird in **GiB**
gemessen. Beide Werte werden getrennt genannt (Umrechnung 1 GiB = 1,074 GB, als
Umrechnung markiert). Nutzbares VRAM real: ~23,5 GiB + ~5,5 GiB = **~29 GiB**.

## 0. Evidenzlage — was das offizielle Leaderboard hergibt und was nicht

Wichtige Einschränkung vorab: `swebench.com` rankt **Agent-Scaffold-Einreichungen**, nicht
Basismodelle. Die Leaderboard-Daten (`data/leaderboards.json` im Site-Repo) enthalten
Einträge wie „Claude 4.5 Opus (high reasoning), 76,8 %, 2026-02-17"; die Seite ist
clientseitig gerendert und war per Fetch nicht vollständig auslesbar — die Verified-Liste
konnte **nicht** direkt im Original gelesen werden (offen).
Sekundärquelle bestätigt: die Spitze der offiziellen Liste besteht aus Closed-Weights-Systemen
(Claude Mythos Preview, GPT-5.3 Codex, Claude Opus), und Anbieter können ihr Scaffold auf
den Benchmark tunen ([codeant.ai](https://codeant.ai/blogs/swe-bench-scores), publ. 2026-07-29).

Konsequenz für dieses Paket: Scores für Open-Weights-Modelle der 20–40B-Klasse stammen aus
**Herstellerkarten (self-reported, eigenes Scaffold)** plus dem Aggregator
[llm-stats.com](https://llm-stats.com/benchmarks/swe-bench-verified). Sie sind untereinander
nur eingeschränkt vergleichbar. Der Open-Weights-Marker bei llm-stats ist erkennbar
unzuverlässig (Qwen3.6-27B ist dort „No", ist aber Apache-2.0 auf HF) — nicht darauf stützen.

## 1. Beste Open-Weights-Modelle auf SWE-bench Verified (heute)

| Modell | Params (aktiv) | SWE-bench Verified | Quelle | Im 30-GB-Budget? |
|---|---|---|---|---|
| DeepSeek-V4-Pro-Max | offen | 80,6 % | [llm-stats](https://llm-stats.com/benchmarks/swe-bench-verified) | nein |
| MiniMax M2.5 | 230B (10B) | 80,2 % | [llm-stats](https://llm-stats.com/benchmarks/swe-bench-verified) | nein |
| DeepSeek-V4-Flash-Max | offen | 79,0 % | [llm-stats](https://llm-stats.com/benchmarks/swe-bench-verified) | nein |
| Mistral Medium 3.5 | 128B dense | 77,6 % | [aimadetools](https://www.aimadetools.com/blog/mistral-medium-3-5-complete-guide/) | nein |
| **Qwen3.6-27B** | **27B dense** | **77,2 %** | [Modellkarte](https://huggingface.co/Qwen/Qwen3.6-27B) + [llm-stats](https://llm-stats.com/benchmarks/swe-bench-verified) | **ja** |
| GLM-4.7 | ~360B MoE | 73,8–74,2 % | [z.ai docs](https://docs.z.ai/guides/llm/glm-4.7) | nein |
| **Qwen3.6-35B-A3B** | **35B (3B)** | **73,4 %** | [Modellkarte](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | **ja, mit Offload** |
| Devstral 2 | 123B dense | 72,2 % | [mistral.ai](https://mistral.ai/news/devstral-2-vibe-cli/) | nein |
| Qwen3-Coder-Next | 80B (3B) | 70,6 % (SWE-Agent) | [arXiv 2603.00729](https://arxiv.org/html/2603.00729v1) | nur Q4 + RAM |
| Devstral Small 2 | 24B dense | 68,0 % | [mistral.ai](https://mistral.ai/news/devstral-2-vibe-cli/) | knapp |
| GLM-4.7-Flash | 30B (3B) | 59,2 % | [Modellkarte](https://huggingface.co/zai-org/GLM-4.7-Flash) | ja |
| Nemotron 3 Nano 30B-A3B | 30B (3B) | 38,8 % | [Review](https://medium.com/@leucopsis/a-technical-review-of-nvidias-nemotron-3-nano-30b-a3b-e91673f22df4) | ja |

**Kernbefund:** Das beste Open-Weights-Modell, das in dieses Budget passt, ist
**Qwen3.6-27B** mit 77,2 % — nur ~3,4 Punkte unter dem besten Open-Weights-Modell der Welt
und über GLM-4.7 (360B) und Devstral 2 (123B). Die 27B-Dense-Klasse hat 2026 aufgeholt.

## 2. Dekodierung „Gven 3.6 36b"

Die Vermutung war richtig, und es gibt eine erstaunlich exakte Entsprechung:

- **Qwen3.5** (Feb/März 2026): 397B-A17B, 122B-A10B, 35B-A3B, 27B, 9B, 4B, 2B, 0,8B
  ([codersera](https://codersera.com/blog/qwen-3-5-complete-guide-2026/))
- **Qwen3.6** (April 2026, zwei Wellen): **Qwen3.6-35B-A3B** (16.04.) und
  **Qwen3.6-27B** dense (22.04.) ([GitHub QwenLM/Qwen3.6](https://github.com/QwenLM/Qwen3.6))
- **Qwen3-Coder**: 480B-A35B, 30B-A3B, Qwen3-Coder-Next (80B-A3B, Feb 2026).
  Eine 3.6- oder 3.7-Coder-Variante ist **nicht** erschienen (Stand 12.07.2026).
- Qwen3.7 Max / Plus existieren nur als API-Modelle, nicht als Open Weights.

→ **„Gven 3.6 36b" = Qwen3.6-35B-A3B.** „3.6" ist die Version, „36b" die auf-/verhörte
Größe 35B. Der Wunsch ist also ein real existierendes Modell.

→ **Aber:** die *schwächere* der beiden Qwen3.6-Varianten fürs Coding. Die dense
**Qwen3.6-27B** liegt bei 77,2 % gegen 73,4 %, ist kleiner und schlägt laut Qwen sogar das
eigene 397B-A17B-Flaggschiff von Qwen3.5 (76,2 %). Das ist die relevante Korrektur.

## 3. Kandidaten im VRAM-Budget

Alle Qwen3.6-Modelle: **Apache 2.0**, **262.144 Token nativ** (bis 1.010.000 mit YaRN),
hybride Architektur Gated DeltaNet + Gated Attention, multimodal (Bild/Video).

### Qwen3.6-27B — dense, 77,2 %

GGUF-Größen ([unsloth](https://huggingface.co/unsloth/Qwen3.6-27B-GGUF)) mit gemessenem
VRAM-Bedarf ([llama-bench auf RTX 3090](https://ahelpme.com/ai/llamacpp-ai/llama-bench-the-qwen3-6-27b-and-nvidia-rtx-3090/)):

| Quant | GB (HF) | GiB gemessen | Passt | Gemessen t/s |
|---|---|---|---|---|
| Q8_0 | 28,6 | 26,62 | nur 3090+2060 zusammen | 26,8 (auf 2×3090) |
| Q6_K | 22,5 | 20,97 | 3090 allein | 31,6 |
| Q5_K_M | 19,5 | 18,16 | 3090 allein | 35,9 |
| Q4_K_M | 16,8 | 15,65 | 3090 allein | 39,9 |
| BF16 | 53,8 | 50,10 | nein | 15,5 (3×3090) |

Offizielle 8-bit-Alternativen zu GGUF: [Qwen/Qwen3.6-27B-FP8](https://huggingface.co/Qwen/Qwen3.6-27B-FP8)
(feingranular FP8, Blockgröße 128, vLLM/SGLang/Transformers). **Achtung Hardware:** die 3090
(SM86) hat **kein natives FP8** — vLLM fährt FP8-Gewichte auf Ampere als **W8A16 über
FP8-Marlin**, also Dequantisierung nach BF16 zur Laufzeit
([vLLM-Doku](https://docs.vllm.ai/en/v0.8.1/features/quantization/fp8.html),
[PR #5975](https://github.com/vllm-project/vllm/pull/5975)). Qualitativ ok, aber kein
FP8-Tensor-Core-Speedup. Zusätzlich [AWQ](https://huggingface.co/QuantTrio/Qwen3.6-27B-AWQ)
und AWQ-6Bit von QuantTrio (Community).

### Qwen3.6-35B-A3B — MoE, 3B aktiv, 73,4 %

GGUF-Größen ([unsloth](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF)):
Q8_0 36,9 GB (34,4 GiB, Umrechnung) · UD-Q6_K 29,3 GB (27,3 GiB) · UD-Q4_K_XL 22,4 GB
(20,9 GiB) · BF16 69,4 GB.

Gemessen auf **einer** RTX 3090, llama.cpp CUDA, UD-IQ4_NL_XL (19,5 GiB)
([Giles Thomas, Juli 2026](https://www.gilesthomas.com/2026/07/benchmarking-qwen-3-6-35b-moe-rtx-3090)):

- alles auf GPU: **3.360 t/s Prompt, 139,6 t/s Generierung**, 89.600 Token Kontext, ~19 GiB VRAM
- 10 Layer MoE-Offload (`-ncmoe 10`): **1.154 t/s Prompt, 89,1 t/s Generierung**, volle
  262.144 Token Kontext
- Flags: `-ngl all -fa on -sm none -ncmoe N`. CUDA deutlich schneller als Vulkan.

### Weitere geprüfte Kandidaten

- **Devstral Small 2** — 24B dense, Apache 2.0, 256K Kontext, 68,0 %
  ([mistral.ai](https://mistral.ai/news/devstral-2-vibe-cli/)). Q8_0 **~25–26 GB
  (Schätzung**, keine GGUF-Dateigröße geprüft — offen). Fällt gegen Qwen3.6-27B um 9 Punkte
  zurück, ohne Vorteil bei Größe oder Lizenz.
- **GLM-4.7-Flash** — 30B-A3B MoE, **MIT**, 131K Kontext, **59,2 %**
  ([Karte](https://huggingface.co/zai-org/GLM-4.7-Flash)). GGUF Q8_0 31,8 GB / Q6_K 24,7 GB
  ([unsloth](https://huggingface.co/unsloth/GLM-4.7-Flash-GGUF)). Passt, aber 18 Punkte
  unter Qwen3.6-27B → kein Grund.
- **Qwen3-Coder-Next** — 80B-A3B, 70,6 % mit SWE-Agent-Scaffold
  ([arXiv 2603.00729](https://arxiv.org/html/2603.00729v1)). In 8 bit ~85 GB → sprengt
  VRAM+RAM. Nur Q4 mit massivem RAM-Offload; verletzt den 8-bit-Anker und liegt trotzdem
  unter der 27B.
- **gpt-oss-20b / 120b** — Apache 2.0, MoE, **nativ MXFP4** (20,9B/3,6B aktiv in ~16 GB;
  116,8B/5,1B in ~63 GB) ([OpenAI](https://openai.com/index/introducing-gpt-oss/)).
  Einordnung: MXFP4 ist hier die **Trainingspräzision der MoE-Gewichte**, keine
  nachträgliche Verlustquantisierung — der „lieber 8 bit"-Anker greift nicht direkt.
  Praktisch aber Generation August 2025; ein SWE-bench-Verified-Wert von 60,7 % für 20b
  kursiert sekundär ([IntuitionLabs](https://intuitionlabs.ai/articles/openai-gpt-oss-open-weight-models)),
  wurde hier **nicht gegen die OpenAI-Karte verifiziert → offen**. Klar hinter Qwen3.6.
- **Seed-OSS-36B-Instruct** — 36B dense, 512K Kontext, aber Artificial-Analysis-Index nur
  18 (geschätzt) ([AA](https://artificialanalysis.ai/models/comparisons/seed-oss-36b-instruct-vs-qwen3-32b-instruct-reasoning));
  kein aktueller SWE-bench-Verified-Wert gefunden (offen). In 8 bit ~38 GB → passt nicht.
- **Nemotron 3 Nano 30B-A3B** — 38,8 % SWE-bench. Schnell (3,3× Throughput vs.
  Qwen3-30B-A3B auf H200), aber Qualität nicht konkurrenzfähig.
- **Out of budget, nur zur Referenz:** DeepSeek-V4-Pro-Max (80,6 %), MiniMax M2.5 (230B),
  Mistral Medium 3.5 (128B), Devstral 2 (123B), GLM-4.7 (~360B).

## 4. KV-Cache: eigene Rechnung aus den config.json

Der entscheidende Hebel für „maximalen Kontext" ist die hybride Architektur: nur jeder
**4. Layer** ist volle Attention (`full_attention_interval: 4`), der Rest ist Gated DeltaNet
mit **kontextlängen-unabhängigem** Zustand. Werte aus
[config.json 27B](https://huggingface.co/Qwen/Qwen3.6-27B/raw/main/config.json) und
[config.json 35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/raw/main/config.json).
**Die folgenden Zahlen sind meine Rechnung, nicht gemessen:**

| | Qwen3.6-27B | Qwen3.6-35B-A3B |
|---|---|---|
| Layer total / volle Attention | 64 / **16** | 40 / **10** |
| num_key_value_heads × head_dim | 4 × 256 | 2 × 256 |
| KV pro Token, FP16 | **64 KiB** | **20 KiB** |
| KV pro Token, 8-bit | **32 KiB** | **10 KiB** |
| KV @ 64K Kontext, 8-bit | 2,0 GiB | 0,6 GiB |
| KV @ 128K Kontext, 8-bit | 4,0 GiB | 1,25 GiB |
| KV @ 262K Kontext, 8-bit | 8,0 GiB | 2,5 GiB |
| DeltaNet-Zustand (konstant) | ~75 MB | ~31 MB |

Plausibilitätsprüfung: 19,5 GiB Gewichte + 262K FP16-KV (5,0 GiB) = 24,5 GiB > 24 GB —
genau deshalb brauchte die gemessene Referenz für den vollen Kontext 10 offengeladene
Layer. Rechnung und Messung passen zusammen.

**Folge:** Bei der MoE-Variante kostet voller 262K-Kontext in 8-bit-KV nur 2,5 GiB. Bei der
dense 27B sind es 8,0 GiB — dort ist Kontext teuer.

## 5. Ranking und drei Empfehlungen

Ranking im Budget, nach SWE-bench Verified: **Qwen3.6-27B (77,2) > Qwen3.6-35B-A3B (73,4)
> Devstral Small 2 (68,0) > GLM-4.7-Flash (59,2) > Nemotron 3 Nano (38,8)**. Es gibt keinen
Kandidaten außerhalb der Qwen3.6-Familie, der hier Sinn ergibt.

### (a) Beste Qualität GPU-only — Qwen3.6-27B, Q8_0, über beide Karten

26,62 GiB Gewichte auf 3090 + 2060 verteilt, ~2,4 GiB bleiben für KV und Puffer.
**Kontext bei 8-bit-KV: ~64K** (Rechnung, 32 KiB/Token). Erfüllt den 8-bit-Anker exakt und
liefert die höchste erreichbare Qualität ohne RAM.
Geschwindigkeit: Referenz 26,8 t/s auf 2×3090; auf 3090+2060 **Schätzung 15–22 t/s**, weil
die 2060 (Turing, 336 GB/s statt 936 GB/s) auf ihren Layern zum Bremsklotz wird.
Risiko: kaum Puffer — jeder OOM kostet Kontext.

### (b) Beste Qualität mit CPU-Expert-Offload — Qwen3.6-35B-A3B, Q8_0

34,4 GiB Gewichte: Attention, Shared-Expert und ein Teil der Experten auf die 3090, der
Rest über `--n-cpu-moe` in die 64 GB RAM (~12–14 GiB dort, Schätzung). Nur 3B aktive
Parameter → CPU-Anteil pro Token klein.
**Kontext: die vollen 262.144 Token** bei 8-bit-KV (2,5 GiB, Rechnung) — das ist der
„maximaler Kontext"-Wunsch, und zwar in echtem 8-bit.
Geschwindigkeit: die Referenzmessung erreichte mit 10 CPU-Layern 89,1 t/s — **aber** auf
einem Desktop. jupiter11 hat einen i7-1165G7 (4C/8T, Dual-Channel DDR4) und die 3090 hängt
an Thunderbolt 3. **Schätzung: 15–35 t/s**, deutlich unter der Referenz. Prompt-Processing
bleibt GPU-seitig schnell.
Zusatzbefund: auf **Speculative Decoding nicht hoffen** — eine 3090-Messung über 19
Konfigurationen mit Qwen3.6-35B-A3B fand *keinen* Netto-Speedup auf Ampere + A3B-MoE
([thc1006, 2026-04-19](https://github.com/thc1006/qwen3.6-speculative-decoding-rtx3090)).
Für die dense 27B mit MTP-Gewichten ([unsloth MTP-GGUF](https://huggingface.co/unsloth/Qwen3.6-27B-MTP-GGUF))
ist das ungetestet → offen.

### (c) Pragmatischer Alltags-Sweet-Spot — Qwen3.6-27B, Q6_K, 3090 allein

20,97 GiB gemessen, läuft komplett auf der 3090; die 2060 bleibt frei für KV-Überlauf,
Embeddings oder ein zweites kleines Modell. **31,6 t/s gemessen** auf genau dieser Karte.
Mit ~2,5 GiB Rest plus 2060 sind bei 8-bit-KV **~64–96K Kontext** realistisch (Rechnung).
Das ist die einzige Variante mit gemessenen Zahlen für exakt unsere GPU, ohne RAM-Offload
und ohne heterogenen Split.
Abwägung gegen den 8-bit-Anker: Q6_K ist ein Schritt tiefer. Der Gegenwert ist +50 %
Geschwindigkeit gegenüber (a), doppelter Kontext und ein robuster Ein-Karten-Aufbau. Aus
meiner Sicht ist das die „Not", die der Anker zulässt — die Entscheidung liegt bei Dir.

**Empfehlung:** (c) als Arbeitspferd aufsetzen, (b) parallel als „großer Kontext"-Profil
danebenstellen. Beide sind dasselbe Ökosystem (Apache 2.0, llama.cpp, GGUF), also ein
Setup mit zwei Profilen statt zwei Stacks. (a) nur, wenn 8-bit hart gesetzt ist.

## 6. Konsequenzen für die Engine (Vorgriff auf Paket B)

- **llama.cpp/GGUF** ist der praktikable Weg: heterogener Split 3090 (SM86) + 2060 (SM75)
  wird unterstützt, MoE-CPU-Offload via `--n-cpu-moe` ist der gemessene Pfad. Hinweis der
  Modellkarten: **neueste llama.cpp-Version** nötig, die Gated-DeltaNet-Operatoren sind neu.
- **vLLM/SGLang** wären für die 27B-FP8-Variante attraktiv (Empfehlung der Karte:
  `vllm>=0.19.0`, `sglang>=0.5.10`), aber Tensor-Parallelismus über zwei ungleiche GPUs mit
  6 GB auf der zweiten ist nicht sinnvoll → dann nur 3090 allein, und dort passt FP8 (~27 GB)
  nicht hinein.
- Der Wunsch **„KV-Cache auf der 2060, Modell auf der 3090"** ist so nicht umsetzbar: KV
  wird pro Layer auf dem Gerät dieses Layers alloziert. Die realisierbare Näherung ist, die
  letzten Layer auf die 2060 zu legen — deren KV liegt dann dort. Detailprüfung: Paket B.
- **„turboquant"** ließ sich keinem existierenden Produkt zuordnen (offen). Nächstliegende
  reale Kandidaten bleiben TurboMind/LMDeploy und die Marlin-Kernels; gehört in Paket B.

## 7. Offene Punkte

1. Offizielle SWE-bench-Verified-Liste nicht im Original auslesbar (JS-gerendert) — alle
   Open-Weights-Scores sind Herstellerangaben plus Aggregator.
2. Devstral Small 2: GGUF-Q8_0-Dateigröße nicht belegt (nur Schätzung).
3. gpt-oss SWE-bench-Verified-Werte nicht gegen die OpenAI-Karte verifiziert.
4. DeepSeek-V4-Pro-Max: Parametergröße nicht verifiziert (nur „weit über Budget" gesichert).
5. Alle t/s-Angaben für jupiter11 sind Schätzungen; Referenzmessungen liefen auf Desktop-CPUs
   ohne Thunderbolt-eGPU. Eigene `llama-bench`-Läufe auf der Box sind der einzige harte Beleg.
6. MTP/Speculative Decoding für die dense 27B auf Ampere: ungetestet.
