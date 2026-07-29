# Rohfassung — jupiter11: Bildschirmausgabe auf das Lapdock (USB-C) umleiten

Diktat Andre, 2026-07-30 ~00:05, Continuation des Strangs (direkt nach dem
GPU-Enablement).

> ich hab ein lapdock angeschlossen, kannst du die bildschirmausgabe über
> usb-c an das lapdock umleiten?

Zwischenruf während der Ausführung:

> wir brauchen displayport alternate mode

## Dekodierung / Befundlage

| Wortlaut | Gemeint / gemessen |
|---|---|
| „Lapdock" | HP Elite x3 Lap Dock (per `lsusb` identifiziert: Hub RTS5411 + HP ITE Tastatur/Touch + Dock-Gerät 03f0:0c56) |
| „über usb-c umleiten" | Video via USB-C DP Alt Mode; gemessen: Alt Mode war bereits ausgehandelt — iGPU-Connector `card1-DP-2` connected, EDID 1920×1080 gelesen, aber `disabled` |
| „wir brauchen displayport alternate mode" | war schon aktiv — das fehlende Stück war der Modeset: fbcon klebte am NVIDIA-Framebuffer (fb0), an dem kein Display hängt |
