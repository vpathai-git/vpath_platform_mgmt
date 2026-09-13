# uranus11 as a local LLM host — record of the build on 2026-09-13

**This is a record of one build, not a procedure.** It says what was done on
uranus11 on 2026-09-13, why it was decided that way, and what happened on the
way. The next such host will deliberately be built freehand again — by then
there will be other models and probably better runtimes — so nothing here has to
be followed. The date is in the filename for that reason.

Sources: the strand `vpath_release_management/analysis/uranus11-local-llm/`
(`summary.md`, and the lane reports `URANUS-LLM-BUILD-1` = BUILD,
`URANUS-LLM-MEASURE-1` = MEASURE, `LLM-TRICKS-1`, `LLM-QUANT-1`; for the
afternoon `VLM-PICK-1`, `VLM-FIT-1`, `VLM-FAST-1`, `VLM-ROUTER-1`). Each number
names its report; what is not in the strand is not in this document.

## 1. What was built, and what for

One NUC of the fleet became a local, OpenAI-compatible LLM server:
`llama-server` built from source on the box itself, serving `/v1/models` and
`/v1/chat/completions` over the LAN on port 8080, with tool calling and image
understanding, under a systemd unit that survives a reboot. Explicitly not
Ollama-based, and without an API key — a LAN-internal service, not an exposed one.

Since the same afternoon it carries **four** operating modes and a second, small
model: in the fourth mode the model is chosen **per request** through the `model`
field of the OpenAI API (`summary.md` STATUS 18:05).

## 2. The hardware, as measured

Read-only over ssh, 03:45–03:55 (`summary.md`, "Die Box, gemessen"):

| | measured |
|---|---|
| Model | Intel NUC11PHi7 "Phantom Canyon", Ubuntu 24.04.4, kernel 6.8.0-138 |
| CPU | i7-1165G7, 4 cores / 8 threads, Tiger Lake; avx2, avx512f, avx512_vnni |
| RAM | 2 × 32 GB DDR4-3200, dual channel = 62 GiB usable, 52 GiB free |
| GPU | RTX 2060 Mobile (TU106M), Turing, compute capability 7.5, 6144 MiB — 5738 MiB of it actually allocatable by CUDA (BUILD, smoke test); PCIe 3.0 x4 |
| Disks | 466 GB NVMe system · 477 GB NVMe → `/data` (ext4, empty, 445 GB free) · 27 GB → `/optane` (ext4, empty); the last two are the two halves of an Intel Optane Memory H10 — 3D-XPoint on the small half, QLC NAND on the large |
| Network | WLAN only, wired port down; one antenna is loose — 390 Mbit/s at the router against 780 on the identical sibling box |
| Before | no NVIDIA driver, no CUDA, `nouveau` loaded; Secure Boot disabled |

The identical sibling box was measured too (`summary.md`, 04:07): same hardware,
but **Secure Boot enabled** there. Nothing was mirrored onto it — multi-session
operation worked on one box.

## 3. The decisions, and why

These are the parts that age, so they carry their reasoning.

**llama.cpp, not vLLM.** 6 GB of VRAM cannot hold a 35B MoE, not even in Q4. The
only workable layout is attention, dense layers and KV cache in VRAM with the
expert weights in system RAM — llama.cpp does that (`--n-cpu-moe`), vLLM keeps
weights VRAM-resident and sits at the edge of support on Turing. So the
bottleneck is CPU memory bandwidth (51.2 GB/s theoretical), not the GPU, and the
model choice mattered more than the GPU (`summary.md`, "Die Physik dieser Box").

**Qwen3.6-35B-A3B, MTP variant.** Small active share: 256 experts, 8 routed plus
1 shared active, expert FFN 512 — read out of the GGUF header on the box (BUILD:
41 blocks = 40 layers + 1 MTP layer). It does tool calling and has a vision
projector, and only 10 of its 40 layers are full attention; the other 30 are
Gated DeltaNet with a constant-size recurrent state instead of a growing KV
cache (`LLM-TRICKS-1` §1b) — that is what makes a 6 GB card viable at all.

**UD-Q4_K_XL, deliberately not more aggressive.** Here quantisation is a speed
question, not a space question: experts stream out of RAM per token, so fewer
bits mean fewer bytes mean faster, roughly linearly. The break is inside the IQ
family, between 4 and 3 bits — IQ4 unpacks from a 16-entry lookup in a vector
register, IQ3 and below need a codebook: 7.62 against 16.10 t/s at exactly 4
threads (`LLM-QUANT-1`, findings 3–4). The real floor is tool calling, already
the weakest category at Q8_0 on this model (KL 0.177 against ≤0.010 for code),
with twice the failures in an agent run at lower quantisation (finding 7). Q3
rejected, Q2 never downloaded, UD-IQ4_XS fetched as the single comparison.

**Two configured modes, no automatic switching.** The speed trick and multi-user
operation exclude each other today, so a human picks: `solo` (one slot, 64k
context, self-speculation on, vision off) or `team` (8 slots, shared 32k pool,
vision on, speculation off). `team` is the default, and both were measured, not
just configured (`summary.md`, 04:50 and STATUS 08:57).

**A second, small model — for smoke tests, not for quality.** uranus11 is a test
box. At 16:15 Andre reset the criteria in one sentence: *"Das Ergebnis ist sowieso
egal, es muss nur ungefähr richtig im Schema sein … Das ist wertvoller, dass es
schnell zurückkommt."* (`raw/2026-09-13_1045-…`). The small model exists so a
smoke test of the infrastructure comes back quickly; time decides, not quality.

**The fastest, not the best — and what that costs.** Two gates first (tool calls
≥ 8/10 schema-valid, image subject named in ≥ 3/4), then the cycle time alone
decided — image and tool call back to back, median of three, numbers in section 4.
The winner is the **weakest of the three that passed** on argument content — 0/10
fully correct arguments against 10/10 for both others, from two recurring slips —
which under this purpose is explicitly not a criterion, and its schema held in all
20 measured calls (`VLM-FAST-1`). **If the purpose ever changes to work that depends
on those arguments, Gemma 4 E2B is the switch**: the best all-rounder of the field,
0.17 s per cycle dearer, file already on the box.

**Gemma 3 out, Gemma 4 in its mobile E2B form.** Gemma 3 4B-it failed gate 1 with
**0/10 valid tool calls** in ten runs — measured on this build with `--jinja` on,
as for the others, not inferred from a tracker; images it named 4/4. Of Gemma 4 the
mobile E2B was taken, not E4B: E4B is 8B total, its smallest 4-bit quantisation
4.72 GB of weights alone against the 5738 MiB of usable VRAM (`VLM-PICK-1`), while
E2B's own pre-load arithmetic came to ≈4562 MiB (`VLM-FAST-1`).

**Model choice per request is not the automatism that was ruled out.** In the
morning Andre required the *operating modes* to be switched by hand, and automatic
model swapping was rejected on that ground (`VLM-FIT-1` §2 D). At 17:00 he asked
for the other end himself — *"Kann man die Umschaltung von außen machen … über die
openai api"* — so the fourth mode is a dictated wish, not a mechanism that grew
back; the modes themselves are still switched by a human.

**Secure Boot stays off.** The NVIDIA driver is DKMS-built and the box carries a
WMI-driven skull-lighting module too; off, neither needs a signing enrolment at
the console (BUILD step 2a).

## 4. What was actually done, in the order it happened

1. **03:45–03:55** hardware measured read-only — and at 03:47 three `lspci`
   calls of that very measurement wedged the GPU (section 5). The driver install
   at 04:31 ran into the wedge and never reached dpkg; nothing was damaged.
2. **~05:18** the box was power-cycled by hand at the wall switch: load 0.23,
   **blocked: 0** right after — a single event, not a boot fault. nouveau was
   then disarmed (`modprobe.blacklist=nouveau nouveau.runpm=0`) and proven at
   05:20:08: new boot_id, `lsmod | grep -c nouveau` = 0.
3. **05:22–05:29** driver `nvidia-driver-595-open` 595.84 — the branch this
   box's own `ubuntu-drivers devices` marks `recommended` for its PCI ID — plus
   CUDA 13.4 from NVIDIA's repository. Hard gate: `nvcc --list-gpu-arch` had to
   contain `compute_75` or the lane would stop; it did, as the lowest
   architecture still compiled. **The reboot came back in 37 s** against 23 min
   in the wedged attempt, and the modules load by themselves.
4. **05:31–07:07** download and build in parallel. The transfer measured
   ~26 MB/s sustained (estimate revised from 1.5–2 h to ~16 min); both model
   files verified by size **and** sha256, hard abort on mismatch. The build set
   `-DGGML_CUDA_FA_ALL_QUANTS=ON` and read the switches back out of
   `CMakeCache.txt` — a flag passed is not a flag arrived. Result: `790cf51`.
5. **06:50** first smoke test (`-ngl 99 -ncmoe 40 -fa on -c 4096 -np 1`):
   **30.7 t/s**, VRAM 2578–2592 MiB, thinking on by default and spending 423
   tokens ≈ 14 s on two sentences. The answer carried a factual error, which is
   why a plausibility check went in front of every later speed number. **07:09**
   acceptance outside the building lane: hung tasks 0, nouveau 0, every launch
   parameter present exactly once, models byte-exact.
6. **07:11–08:43** measurement series M0–M9 (MEASURE). M0 first settled an open
   build finding (`CMakeCache.txt` showed only the default FA-quant list) by
   measuring KV pairs: f16 104.8, q8_0/q8_0 104.8, mixed q8_0/q4_0 104.5 t/s
   pp512, against 80.3 t/s and **+20 graph splits** for a deliberately
   untranslated pair — the flag is effective, no rebuild needed. Then both modes
   end to end, accepted through the real start verb, not a typed command line.
7. **08:43–08:48** the service (MEASURE, `## Step S`): both configs moved from
   loopback to `0.0.0.0:8080` with a stable model alias, plus the switch, unit
   and verb of section 6, and a 23 GiB swap file on the Optane half at priority
   10 ahead of the existing 8 GiB at −2. No input firewall was active, so
   nothing was opened.
8. **08:49–08:54** acceptance from the Mac by curl: `/v1/models` →
   `qwen3.6-35b-a3b`; a tool call with a nested object and a list →
   `finish_reason tool_calls` with exactly the expected arguments, 30.1 t/s; a
   256×256 image → *"Blue square in middle."*; 4 parallel sessions all answered,
   12.2–15.2 t/s each; thinking on per request → 981 characters of reasoning;
   `/slots` → 8.
9. **16:18–16:51** four small candidates measured against the two gates, each
   through the same driver, the page cache dropped before every cold load
   (`VLM-FAST-1`): Qwen3-VL-2B 0.55 s · Gemma 4 E2B 0.72 s · Qwen3-VL-4B 1.03 s ·
   Gemma 3 4B **0/10 tool calls, out**. Mode `fast` then installed as a third row of
   the existing table — three literal edits in `llm-serve`/`llm-mode` plus a new
   `fast.env`, **no unit change** — five red drills, and a reboot with the switch
   file on `fast`: back in 37 s, `NRestarts=0`, the mode survived.
10. **17:47–17:58** mode `router` (`VLM-ROUTER-1`): one preset file with four
    entries — the big model in its team and in its solo shape, Qwen3-VL-2B,
    Gemma 4 E2B — `--models-max 1`, no model preloaded. Both its gates green
    (section 6). Reboot with the switch file on `router`: back in 35 s, `NRestarts=0`.
11. **18:03** acceptance from the Mac: `/v1/models` → four names · a wrong name →
    HTTP 400 · small-model cycle 2.09 s including the load, 0.55 s when it is
    already resident · Gemma 4 E2B 5.62 s including the load · switch to the big
    model 3.23 s to the answer *"Copenhagen"* (`summary.md` STATUS 18:05).

## 5. The traps we hit

- **`lspci` wedged the GPU** (03:47; ~90 minutes and a trip to the wall switch).
  On a box with an NVIDIA dGPU on `nouveau`, a PCI scan can leave nouveau's
  runtime-PM transition unfinished; processes pile up unkillable in D-state and
  the only visible symptom is **empty output** (by 04:45: ~19 stuck processes,
  load 20). Rule taken from it — before the proprietary driver is in, never scan
  the PCI bus, read single sysfs files, treat empty output as a hang.
- **A silent build flag worth a factor of 25.** A stock CUDA build compiles
  Flash-Attention kernels for only a few KV type combinations; ask for one it
  did not compile and llama.cpp falls back to CPU attention with no warning
  (`LLM-TRICKS-1` §3). Countered by `FA_ALL_QUANTS`, reading the cache back and
  measuring — the reliable probe being the **graph-split count**, not the token
  rate (MEASURE, finding 1).
- **Two network-bound jobs on one loose-antenna WLAN.** The clone was started
  alongside the 22 GB download on the theory that one was CPU-bound. It is not,
  and it timed out; the retry on an idle link cloned in seconds. ~40 minutes,
  plus 36 more because the watcher looked only for compiler errors.
- **A boot-time race whose first fix was refuted.** After the service went in, a
  reboot came back healthy but with `NRestarts=1`: the start guard had correctly
  refused because `nvidia-smi` saw no GPU yet, the device nodes appearing 0.3 s
  later. The first fix — ordering the unit after `nvidia-persistenced.service` —
  was **disproved by the next reboot**: persistenced fails there itself. The
  device nodes come from a udev rule, so the unit was ordered after
  `sys-bus-pci-drivers-nvidia.device`. Proof reboot 08:54: healthy after 48 s,
  **`NRestarts=0`**, journal `Initialized nvidia-drm` → `Started
  llama-server.service`. One reboot is a sample, but that order shows the start
  now hangs off the device event rather than off luck.
- **Gemma 3 sees images, but its tool calls did not arrive as calls.** 0/10 in ten
  runs on this build: `finish=stop`, `n_calls=0`, prose instead. The literature had
  flagged the risk, the probe settled it — at the cost of a measured candidate and
  of the hypothesis the search started from.
- **Router arguments outrank the per-model settings.** The router passes its own
  command line and environment down to every child, so one stray inference parameter
  in the router config would have silently overwritten all four measured
  configurations; `router.env` therefore carries none at all (`VLM-ROUTER-1`).
- **Router operation is not recognisable by a switch but by the missing `-m`** —
  `tools/server/server.cpp:135`, `is_router_server = params.model.path.empty()`. The
  start verb always passed `-m`, so `router` needed a branch, not a fourth literal.

What the measurements refuted (MEASURE, findings) — the part most worth keeping,
because assumptions age faster than numbers:

- Self-speculation gave **0.99–1.31×**, not 1.4–2.2×: a 3-token verification
  step costs 2.2 single steps, the expert union comes out of RAM (M5).
- UD-IQ4_XS decoded **28 % slower**, not 26 % faster, on this 4-thread CPU; only
  prefill gained (+24 %) (M6).
- 8 parallel requests bought **+44 %** total throughput, each 5.3× slower —
  parallel requests do not share the expert read (M4-C).
- Expert layers back on the GPU: weak (~+1.2 % decode per ~500 MiB); `-ub` was
  the strong lever (+70 % / +182 % prefill) (M7). `mlock` gained nothing (M7e).
- Self-speculation *does* work with several slots and with a vision projector
  here; the opposite premise was outdated (M5-check).
- Thinking, on by default, dominated felt latency: first word 10–30 s with it,
  **0.2–0.5 s without**, while nested tool calls still came back 4/4 with
  thinking off (M8). Hence thinking off by default, switchable per request.

## 6. The end state

Accepted independently 2026-09-13 08:57 (`summary.md` STATUS 08:57; MEASURE
`## Step S`).

- systemd unit `llama-server.service`, enabled, unprivileged service account,
  `Restart=on-failure`, ordered after `network-online.target` and
  `sys-bus-pci-drivers-nvidia.device`. It starts `/data/llama/llm-serve` with
  whatever the switch file `/data/llama/mode` holds; anything but `solo` or
  `team` exits 2, with no default. Switch currently `team`; the verb
  `/data/llama/llm-mode solo|team|status` writes it, restarts, waits for health.
- Both modes bind `0.0.0.0:8080`, model name `qwen3.6-35b-a3b`, **no API key**
  (llama-server warns about CORS `*` without one). No input firewall active.
- `/data/models`: UD-Q4_K_XL 22,853,663,008 · UD-IQ4_XS 18,209,036,576 ·
  mmproj-F16 899,283,584 bytes, sha256-verified. Build `790cf51`. Swap
  `/optane/swapfile` 23 GiB, priority 10, ahead of the older 8 GiB at −2.

Measured behaviour, UD-Q4_K_XL (MEASURE, comparison table):

| | solo | team |
|---|---|---|
| slots | 1, further requests queue | 8 in parallel |
| context | 65536 for the one slot | 32768 shared by all 8 |
| vision | off | on (2048×2048 image 43.4 s, 1280×960 17.0 s) |
| self-speculation | on (n_max 2) | off |
| decode, one user | prose 29.6 · code 40.5 · list 38.3 t/s | 30.3 t/s |
| decode, 8 users | queued, each at full speed in turn | 5.7 t/s each, 40.6 total |
| prefill | 267 t/s at 14k, 244 t/s at 56k | 156 t/s at 14k |
| first word (thinking off) | 0.23–0.51 s | 0.45–0.51 s |
| tool calls · 11-question catalog | 2/2, 4/4 · 11/11 | 2/2, 4/4 · 11/11 |
| VRAM peak (of 5738 MiB) | 5006 MiB | 5090 MiB |
| host RAM (server RSS) | ~23.5 GiB | 22.8–25.7 GiB |

The small models, measured the same way (`VLM-FAST-1`, `VLM-ROUTER-1`):

| | Qwen3-VL-2B (`fast`) | Gemma 4 E2B |
|---|---|---|
| smoke cycle, image + tool call · decode | 0.55 s · 141.1 t/s | 0.72 s · 93.7 t/s |
| tool calls · arguments fully correct | 10/10 · 0/10 | 10/10 · 10/10 |
| VRAM loaded (of 5738 MiB) | 4070 MiB at 32k context | 2958 MiB at 8k |

State after the afternoon, accepted 18:03 (`summary.md` STATUS 18:05;
`VLM-ROUTER-1`): four modes `solo|team|fast|router`, the unit still untouched. In
`router` nothing is preloaded, so the box idles at 4 MiB of VRAM, and `/v1/models`
lists `qwen3.6-35b-a3b`, `qwen3.6-35b-a3b-solo`, `qwen3-vl-2b-instruct`,
`gemma-4-e2b-it`. A switch releases its predecessor's VRAM completely — after each
of eight switches the card held exactly the target's own footprint, and no two of
those fit on it together. Cost of a switch, first answer after it: warm
**1.4–1.5 s** to a small model, **3.1 s** to the big one; cold after a reboot 2.3 s
small and **18.2 s** big (22.85 GB off disk). Red drill: an unknown model name is
answered `HTTP 400 model '…' not found` — no substitution, no default, a name one
character off rejected rather than corrected.

The commands this state was checked with, and that check it again:

```bash
/data/llama/llm-mode status     # mode=team unit=active health=ok slots=8
systemctl is-enabled llama-server.service; systemctl show -p NRestarts llama-server
swapon --show                   # /optane/swapfile 23G prio 10 must be there
curl -s http://<host>:8080/v1/models   # from another machine on the LAN
curl -s http://<host>:8080/v1/chat/completions -d '{"model":"nope"}'   # → HTTP 400
```

Since 08:43 the box has rebooted four times and come back without a hand on it
every time, `nouveau` at 0 — two more in the afternoon (16:43, 17:55), each
carrying the mode the switch file held, `NRestarts=0`.

---

Written 2026-09-13 from the strand named at the top, which stays the source of
truth, and extended the same evening with that afternoon's work. A record of one
day, not maintained against later change.
