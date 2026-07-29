# Issue: jupiter11 — Serving-Implementierung (P1 Q6_K + P2 Max-Kontext)

Status: in progress · Herkunft: Konzept-Freigabe 2026-07-30 („q6 ist ok" +
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

## Sicherheitsregeln

- Zugangsdaten/API-Key nie im Strang; Key nur auf der Box + einmalige
  Nennung an Andre.
- Kein öffentlicher Bind; LAN only. Kein Port-Forwarding einrichten.
- Jede Dual-GPU-/Offload-Variante muss die Solo-Baseline messbar schlagen,
  sonst wird sie nicht Default (No-Fallback).
