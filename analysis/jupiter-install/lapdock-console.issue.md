# Issue: jupiter11 — Konsole auf das Lapdock (USB-C DP Alt Mode) umleiten

Status: done (2026-07-30, remote verifiziert; Sichtprüfung am Panel steht
Andre zu) · Herkunft: Diktat 2026-07-30
(`raw/2026-07-30_0005_lapdock-console.md`) · Strang: `summary.md`

**Auftrag:** Die Bildschirmausgabe der Box über USB-C auf das angeschlossene
Lapdock legen (lokaler Schirm + Tastatur für die Server-Box).

## Befund (gemessen)

- Lapdock = **HP Elite x3 Lap Dock** (`lsusb`: 03f0:0c56 + RTS5411-Hub +
  ITE-Tastatur/Touch) — USB-Seite funktionierte sofort.
- **DP Alt Mode war bereits ausgehandelt** (Andres Zwischenruf „wir brauchen
  displayport alternate mode" war damit schon erfüllt): iGPU-Connector
  `card1-DP-2` connected, EDID des Panels gelesen (1920×1080) — aber
  `disabled`, Panel schwarz.
- Ursache: zwei fbdevs (`fb0 = nvidia-drmdrmfb`, `fb1 = i915drmfb`); fbcon
  bindet fb0 — die Konsole lag auf den display-losen RTX-Karten.

## Lösung (minimal, deterministisch, reboot-fest)

`/etc/modprobe.d/nvidia-drm-no-fbdev.conf` → `options nvidia-drm fbdev=0`
(+ `update-initramfs -u`). Die RTX-GPUs sind im AI-Setup reine
Compute-Devices; ohne NVIDIA-fbdev wird der i915-Framebuffer immer `fb0`
und fbcon landet von selbst auf der iGPU → Lapdock. Kein `fbcon=map:`-Hack
(fb-Nummern sind bootreihenfolgeabhängig — der wäre fragil), kein
Paket-Zukauf (`con2fbmap` existiert in 24.04 nicht).

## Verifiziert nach Reboot (2026-07-30)

- `/proc/fb` = `0 i915drmfb` (einziger fbdev) · `card1-DP-2` **enabled** ·
  `getty@tty1` active → Login-Prompt am Lapdock.
- CUDA-Regression ausgeschlossen: `nvidia-smi -L` listet weiterhin beide RTX.
- Nicht remote beweisbar: dass das Panel physisch leuchtet — Sichtprüfung
  durch Andre ausstehend.
