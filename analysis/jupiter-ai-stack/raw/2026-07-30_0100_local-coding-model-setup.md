# Rohfassung — jupiter11: lokales Coding-Modell, OpenAI-kompatibel im Intranet

Diktat Andre, 2026-07-30 ~01:00. Neues Thema → neuer Strang `jupiter-ai-stack`.

> Jetzt reden wir nochmal über den NUC. Ich möchte dort gerne also über den
> Jupyter. Ich möchte auf dem Jupiter ein Setup fahren, das ein möglichst
> gutes lokales Coding-Modell oder mehrere Varianten davon, lauffähig hält
> und per OpenAI kompatible Schnittstelle ins Internet, also ins Intranet,
> also in unser WiFi stellt. Meine Idee ist, dass wir so ein Gven 6 zum
> Laufen bringen. Entschuldigung, 3.6 zum Laufen bringen. Schau bitte zuerst
> in SVE Bench Verified, was das beste Open Source Modell ist, dass wir in
> unserem Setup fahren können. Ich möchte ein sehr ambitioniertes Setup
> fahren. Und zwar eins, das meine zwei RTX-Grafikkarten nutzt und
> möglichst schnell ist. 8-Bit-Quantisierung ist gut. Tiefer möchte ich
> nicht ohne Not. Muss man abwägen. Ich möchte gerne... das so halten dass
> dass wir turboquant verwenden und idealerweise ist der kv Cache auf dem
> RTX 2060 und das eigentliche Modell auf der RTX 3090 und mir schweb vor
> dass wir das Gven 3.636b nehmen in so einer 8 bitquantisierung und die
> max die maximalen Kontext aufbauen können Schau dir mal an, ob das
> realistisch ist und ob das ein Setup ist, das wirklich unser lokales
> System maximal gut ausnutzt oder ob es da offensichtliche bessere
> Kandidaten gibt.

Methoden-Anweisung (Auszug, wörtlich):

> Dir gehören Konzept, Orchestrierung und Review. Alles andere, wenn
> geeignet, kannst du delegieren. Nutzt dort Codex und Claude wapper im
> Wechsel und lern dabei, welche Vor- und Nachteile die jeweiligen haben.
> Also machst nicht doppelt, sondern versuch einfach beim Review zu sehen,
> wer stellt sich wo besonders gut an. Und gib mir da hinterher eine
> Summary. Im User Request kannst du einfach was ablegen, wo du sagst, Sub
> Agent Review. Das ist so der finale Schritt. Das ist erstmal die
> Voraussetzung.

## Diktat-Dekodierung (Interpretation, im Konzept zu verifizieren)

| Wortlaut | Gemeint (Lesart) |
|---|---|
| „über den Jupyter / auf dem Jupiter" | jupiter11 (der neue NUC, RTX 2060 6 GB + RTX 3090 24 GB eGPU) |
| „Gven 6 … Entschuldigung, 3.6 … das Gven 3.636b" | Qwen-Familie; vermutlich „Qwen3.x ~30–36B"-Klasse — WELCHES Modell genau existiert (Qwen3-32B? Qwen3-Coder-30B-A3B? ein neueres Qwen3.5/3.6?) ist Teil der Recherche, nicht zu raten |
| „SVE Bench Verified" | SWE-bench Verified (Leaderboard) |
| „turboquant" | unscharf — Kandidaten: TurboMind (LMDeploy), FP8/INT8-Marlin-Kernels, ExLlama; in der Recherche klären, was auf Turing+Ampere real existiert |
| „kv Cache auf dem RTX 2060, Modell auf der RTX 3090" | Wunsch-Topologie; technische Realisierbarkeit ist explizit zu prüfen (Engines koppeln KV üblicherweise an die Layer-GPU) |
| „ins Internet, also ins Intranet" | nur ins LAN/WiFi — NICHT öffentlich exponieren |
| „8-Bit … tiefer nicht ohne Not" | Qualitätsanker: ≥8-bit Gewichte bevorzugt; Abwägung erlaubt, aber begründet |
