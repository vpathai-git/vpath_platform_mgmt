# Issue: Fleet — deutsche Tastatur + Lapdock-Fähigkeit auf allen NUCs

Status: done (2026-07-30, remote verifiziert soweit ohne Gerät möglich) ·
Herkunft: Diktat 2026-07-30
(`raw/2026-07-30_0035_fleet-console-alignment.md`) · Strang: `summary.md`

**Auftrag:** mercury8, venus10, mars12 auf den jupiter11-Stand: deutsches
Konsolen-Layout und ein per USB-C DP Alt Mode angestecktes Lapdock muss die
Konsole zeigen. terra (Azure-VM) ist außen vor — kein NUC, kein Display.

**Randbedingung:** Produktivboxen → reboot-frei. Tastatur wirkt sofort
(`setupcon`); Guards greifen beim nächsten natürlichen Boot.

## Durchgeführt (gemessen, je Box)

| Box | Tastatur | Lapdock-Pfad |
|---|---|---|
| mercury8 | `XKBLAYOUT=de`, setupcon (setfont-Fehler = Folgesymptom des fehlenden fb, Keymap gesetzt) | `/proc/fb` leer = **deferred fbdev setup** (headless-Boot), KEIN Defekt: i915 registriert den fb beim Display-Hotplug. Zusätzlich `nvidia-drm fbdev=0`-Guard gesetzt (595-Userspace liegt auf der Box — eine zurückkehrende eGPU darf der Konsole nicht fb0 stehlen) |
| venus10 | `XKBLAYOUT=de`, setupcon sauber | ready as-is: i915 einzige GPU, besitzt fb0; DP-Alt-Mode-Hotplug → fbcon. Kein nvidia-Stack, kein Guard nötig |
| mars12 | `XKBLAYOUT=de`, setupcon sauber | ready as-is: wie venus10 |

Alle drei: `dpkg-reconfigure -f noninteractive keyboard-configuration`
(Layout bis ins initramfs). jupiter11 war bereits umgestellt
(`lapdock-console.issue.md`).

## Diagnose-Notiz mercury8 (festgehalten, damit es niemand „fixt")

Leeres `/proc/fb` bei geladenem i915, sauberer Cmdline, ohne Blacklist und
mit `CONFIG_DRM_FBDEV_EMULATION=y` ist das dokumentierte deferred-Setup des
DRM-fbdev-Clients: ohne connected Connector beim Probe wird der fb erst beim
Hotplug registriert. venus10/mars12 zeigen `i915drmfb` sofort, weil dort ein
EFI-Framebuffer übernommen wurde. Verhalten ist korrekt — nicht „reparieren".

## Nicht remote beweisbar (ehrlich offen)

Der physische Steck-Test (Lapdock an mercury8/venus10/mars12 → Bild +
deutsche Tasten) braucht das Gerät vor Ort — Sichtprüfung Andre. Alles
Konfigurierbare ist gesetzt und gemessen.
