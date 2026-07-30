# Issue: jupiter11 — Serving-Implementierung (P1 Q6_K + P2 Max-Kontext)

Status: done (2026-07-30 — alle 7 Schritte, Abnahme inkl. Reboot-Probe:
/models gemountet, Service-Autostart, beide GPUs re-attached, API antwortet
„REBOOT-OK" nach Kaltstart) · Herkunft: Konzept-Freigabe 2026-07-30 („q6 ist ok" +
Plan-Review; SSD-Bestätigung: „die zweite SSD, die mit 256 GB, da legen wir
die ganzen Modelle ab") · Strang: `summary.md` · Konzept:
`coding-llm-serving.concept.md`

## Plan (freigegeben)

1. **Modell-Platte**: zweite SSD (250-GB-Samsung) → GPT, ext4 `models`,
   Mount `/models` (fstab UUID, `nofail`).
2. **Toolchain**: build-essential, cmake, CUDA-Toolkit (NVIDIA-Network-Repo,
   toolkit-only — Treiber 595 unangetastet).
3. **Downloads** (Hintergrund): `Qwen3.6-27B-Q6_K.gguf` (22,5 GB) +
   `Qwen3.6-35B-A3B-Q8_0.gguf` (36,9 GB), unsloth, via hf-CLI, resume-fähig.
4. **llama.cpp** master bauen (`-DGGML_CUDA=ON`, SM86+SM75), Commit gepinnt.
5. **llama-swap v244** als systemd-Service: LAN-Port 9292 (Router-NAT ⇒
   intranet-only), Backends 127.0.0.1, API-Key nur auf der Box (600).
   Profile: **P1 „coding"** (27B Q6_K solo 3090 via GPU-UUID, q8_0-KV, 64K)
   · **P2 „longctx"** (35B-A3B Q8_0, `--n-cpu-moe` kalibriert, 262144, q8_0-KV).
6. **Abnahme-Messung**: llama-bench + realer API-Test je Profil (Prefill,
   Decode, TTFT, VRAM je GPU) + Reboot-Probe. Kein „fertig" ohne Zahlen.
7. **Doku**: Register-Kommentar, Strang-Ticks, Commits (kein Push).

Bewusst NICHT drin: P3 Draft/Spec-Decoding auf der 2060 (erst nach Baseline),
Docker/k3s.

## Ausführungs-Log (Evidenz je Schritt)

- **Schritt 1 erledigt** (29.07. ~23:30 Boxzeit): /models gemountet, 229 G
  nutzbar, ext4 Label `models`, fstab via UUID+nofail.
  **VORFALL, ehrlich dokumentiert:** Der erste Partitionier-Versuch lief
  gegen `/dev/nvme0n1` — das war beim Onboarding die leere Platte, ist aber
  nach Reboots die **OS-Platte** (NVMe-Namen sind NICHT reboot-stabil; die
  Nummerierung tauschte). **parteds Busy-Schutz verweigerte jede Schreibung**
  („Partition(s) … are being used", Exit 1); `parted print` + laufendes
  System beweisen: Tabelle unverändert, kein Schaden. Konsequenz sofort
  umgesetzt: Schreibzugriffe nur noch über `/dev/disk/by-id/…<serial>` mit
  Guard (Modell+Größe+Leere im selben Befehl geprüft, sonst Abbruch).
  Register-Kommentar entsprechend korrigiert (Serial-basierte Benennung).
- **Schritt 3 gestartet**: beide Downloads laufen als nohup-Jobs auf der Box
  (`/models/.dl-27b.log`, `.dl-35b.log`), Bytes fließen (verifiziert).
  Startrate ~2 MB/s gesamt — Dauer offen, wird gemessen.
- **Schritt 2/4 gestartet**: Toolchain-Job (`/models/.toolchain.log`) —
  apt-Toolchain, CUDA-Keyring, cuda-toolkit, llama.cpp-Clone (Commit wird
  geloggt).
- **Schritt 3 erledigt**: beide GGUFs byte-exakt gegen die HF-API verifiziert
  (22.523.238.624 + 36.903.140.320 Bytes), reale Rate ~80 MB/s.
- **Schritt 2/4 erledigt** (Umweg dokumentiert): erster Toolchain-Job starb
  STILL an einem transienten `wget -q` unter gesättigter Leitung + `set -e`
  ohne sichtbaren Fehler — Lehre: keine stummen Downloads in Jobs, Phasen-
  Marker pro Schritt. Zweiter Lauf grün: cuda-toolkit (NVIDIA-Repo),
  llama.cpp `3018a11`, Build SM86+SM75 in ~20 min.
- **Schritt 5 erledigt**: llama-swap v244, Key in `/etc/llama-swap/api-key`
  (600, nie im Repo/Transkript), Config mit Macros, 3090 per GPU-UUID,
  systemd-Unit enabled.
- **Schritt 6 erledigt — Messprotokoll:**
  - P1 `coding` (27B Q6_K solo): **pp2048 1122 t/s, tg128 31,9 t/s** (Bench);
    realer 20.608-Token-Prompt korrekt beantwortet, Roundtrip 35 s; VRAM
    23,98/24,1 GiB statisch — Härtetest gehalten. Auth: ohne Key 401.
  - P2 `longctx` (35B-A3B Q8_0, 262K): Kalibrierung mit Umweg — ncmoe 17/18
    sterben am pp-Compute-Buffer (CUDA-OOM), und ein erster „UP"-Befund war
    FALSCH (curl exit 0 auch bei 503-loading; Gesundheits-Checks ab jetzt
    als HTTP-200 verifiziert). ncmoe 20+ub256 läuft, drückt aber Prefill auf
    37 t/s; **final ncmoe 22 (ub default): pp2048 57,8 t/s, tg64 44,5 t/s,
    VRAM 21,1 GiB (3 GiB Luft), API-Abnahme „READY" nach 18,5 s Cold-Swap.**
  - LAN-Abnahme vom Dev-Mac: `LAN-OK` über `/v1/chat/completions` inkl.
    automatischem Profil-Rückswap (~25 s).
  - Betriebsfakt: Qwen3.6 ist ein Thinking-Modell (max_tokens großzügig).
  - Ehrliche Grenze: MoE-Prefill ist CPU-gebunden (4C/8T) — Riesen-Prompts
    auf longctx dauern Minuten; gemessen und akzeptiert, kein Workaround.
  - **Reboot-Probe grün**: fstab-Mount hält (Platte kam diesmal wieder als
    anderes nvme-Device — by-UUID trägt), `llama-swap` autostartet, beide
    RTX nach eGPU-Reauth da, `coding` antwortet „REBOOT-OK" nach Kaltstart.

## Sicherheitsregeln

- Zugangsdaten/API-Key nie im Strang; Key nur auf der Box + einmalige
  Nennung an Andre.
- Kein öffentlicher Bind; LAN only. Kein Port-Forwarding einrichten.
- Jede Dual-GPU-/Offload-Variante muss die Solo-Baseline messbar schlagen,
  sonst wird sie nicht Default (No-Fallback).
