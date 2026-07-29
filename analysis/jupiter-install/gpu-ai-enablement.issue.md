# Issue: jupiter11 — beide RTX-GPUs für AI grundsätzlich enablen

Status: done (2026-07-29 — alle vier Erfolgskriterien gemessen erfüllt:
nvidia-smi listet beide RTX, `nvidia` auf beiden gebunden, eGPU nach Reboot
re-authorized, CUDA 13.2, Register nachgezogen) · Herkunft: Diktat 2026-07-29
(`raw/2026-07-29_2345_gpu-ai-enablement.md`) · Strang: `summary.md`

**Auftrag:** Die drei GPUs der Box lokalisieren (die interne Intel ist
irrelevant) und die beiden RTX-Karten grundsätzlich für ein AI-Setup
enablen — Treiber + CUDA-Fähigkeit, beide in `nvidia-smi`. Noch KEIN
Workload-Stack (kein ollama, kein Container-Toolkit, kein k3s-GPU-Operator —
das ist die nächste Welle, wenn das AI-Setup konkret wird).

## Topologie (gemessen 2026-07-29, `lspci -nnk`/`-tv`, `boltctl`)

| GPU | Ort | Anbindung |
|---|---|---|
| Intel Iris Xe (TigerLake GT2) | im Prozessor (Bus 00:02.0) | i915, bleibt unangetastet |
| RTX 2060 Mobile (TU106M) | fest verbaut im NUC11 Enthusiast (Bus 01, direkt am CPU-PCIe) | vorher nouveau |
| RTX 3090 (GA102, Dell-Karte) | **Razer Core X eGPU-Gehäuse an Thunderbolt 3** (Bus 2f) | 20 Gb/s (2 Lanes), autorisiert, Bolt-Policy `iommu`, stored | 

## Weg (der kanonische Ubuntu-Pfad, keine Fremdquellen)

- Secure Boot ist AUS (gemessen `mokutil --sb-state`) — kein MOK-Enrollment.
- `ubuntu-drivers install` → der von Ubuntu empfohlene Treiber
  `nvidia-driver-595-open` 595.84 (ein Treiber für Turing UND Ampere; die
  open kernel modules sind für Turing+ NVIDIAs empfohlene Variante).
- Reboot, dann Verifikation.

## Erfolgskriterien

1. `nvidia-smi -L` listet BEIDE RTX (2060 Mobile + 3090); kein nouveau mehr
   auf den beiden (`lspci -nnk`: Kernel driver in use = nvidia).
2. eGPU übersteht den Reboot (boltctl: authorized/connected — stored policy).
3. CUDA-Fähigkeit sichtbar (CUDA-Version im nvidia-smi-Header; libcuda kommt
   mit dem Treiber).
4. Register-Kommentarblock `jupiter11` aktualisiert (GPU-Zeile: gefunden →
   enabled, Treiberversion, Razer Core X).

## Nebenbefund (nicht Teil dieses Issues)

mercury8s Register-Zeile „carries the CUDA eGPU" ist gemessen unwahr
geworden: Core X dort disconnected, kein NVIDIA-Gerät am Bus, nvidia-smi
tot → eigenes Draft-Issue `mercury8-egpu-disconnected.issue.md`.
