# Rohfassung — jupiter11: drei GPUs lokalisieren, beide RTX für AI enablen

Diktat Andre, 2026-07-29 ~23:45 (deutsch diktiert), Continuation des Strangs
(Antwort auf den P2-Befund „zusätzliche RTX 3090" aus dem Onboarding-Report).

> Da hat zwei Grafikkarten angeschlossen. Also eigentlich drei. Eine interne
> Intel Grafikkarte, dann eine RTX 2060 und eine RTX 3090. Versucht die mal
> zu finden. Die sind an unterschiedlichen Stellen zu finden. Die interne
> Grafikkarte ist wahrscheinlich nicht relevant. Ich möchte gerne die
> Grafikkarten für ein AI-Setup nutzen. Und zuerst mal die RTX, die zwei RTX
> Grafikkarten grundsätzlich dafür enablen.

## Diktat-Dekodierung (nur Wortreparaturen)

| Wortlaut | Gemeint |
|---|---|
| „Da hat zwei Grafikkarten angeschlossen" | „Da sind zwei Grafikkarten angeschlossen" — bestätigt den Onboarding-Befund (RTX 2060 + RTX 3090), plus iGPU = drei |
| „an unterschiedlichen Stellen zu finden" | die physische Topologie erheben: wo hängt welche Karte (intern vs. extern) |
| „grundsätzlich dafür enablen" | Grund-Enablement: NVIDIA-Treiber + CUDA-Fähigkeit, beide RTX in `nvidia-smi` sichtbar und nutzbar — noch kein AI-Workload-Stack (ollama, Container-Toolkit o. ä.) |
