# Mesen-S compatibility supplement

This optional, silent check exercises the frozen v0.8.1 cartridge in a third
SNES engine: the official Libretro **Mesen-S 0.4.0** Windows x64 core. It does
not change the game, its six canonical reports or the packaged Windows ZIP.

ROM SHA256:
`76b456d1ac75471a8b9710c61b0ce4c6ab9ca344b1b8a1f17e38f36e52904466`.

The [machine-readable report](mesen-test-report.json) **passes** on that exact
ROM: 48 combat cases / 28,800 measured fight frames, 16 cases per stage, zero
non-unit native/video deltas, and 55 successful cold boots. The complete run
took 260.45 seconds. All three stage plates agree with their native masters
within seven channel levels; all twelve ambient phases render distinctly.
The synchronized low-wave probe records 600/600 unit deltas, 37 frames with
both waves active and clear STAT77 range/time overflow bits. All 55 hosts
produce healthy captured PCM, with zero empty runs or exact full-scale samples;
the maximum absolute sample is 24,995. These are technical results, not a
listening or gameplay-quality approval.

## Scope

| Probe | Coverage |
| --- | --- |
| Scene and controller smoke | Arcade, Local Versus and Training; actual loaded selections, movement, jump/landing, pause/resume and all three pause cards |
| Training | Paused dummy selection, repeated Jump takeoffs, live reset with restored health and preserved dummy choice |
| Stage rendering | All three native stage plates, four actual PPU ambient phases per stage, and pause/hitstop/round-end freezes |
| OBJ stress | Synchronized low waves, shadows and actors; 600 callbacks with unit native cadence and clear range/time overflow bits |
| Combat | 48 cases of 600 live frames: all twelve fighters on both sides, both existing controller policies, and all three stages |
| Callback health | One non-null video callback per run, nonempty captured PCM, AV-duration bound, nonzero energy and no exact full-scale samples |

The bounded combat cases reuse the existing independent-core trace bounds and
controller policies. They are not a full ordered-pair matrix or an hour-per-mode
soak. This is **Mesen-S 0.4.0 Libretro** evidence, not a test of the modern Mesen
desktop frontend or physical SNES hardware. Human play, listening and release
approval remain separate.

## Reproduce

From the repository root on Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/setup-mesen.ps1
.tools/python/python.exe tools/test_mesen.py
```

The setup verifies the archive and its sole DLL member before installation.
The test verifies both again and requires the frozen ROM hash, independently
of the mutable build manifest. The report also hashes the host and reused
helpers. The rolling official download can change; a different archive fails
closed instead of silently replacing the pin. A matching cached archive works
offline. Neither the core nor its archive is committed or added to the game ZIP.

| Input | SHA256 |
| --- | --- |
| Core archive | `3bc041ce07f5645602aac9cf6682df12ff8941e6231aa621c5b2332fab96d754` |
| DLL | `87a90f31c331313c4f499d6dfafb59f7911bc60dbb9e10b5d96f959040441abd` |

Overclocking and video filters are disabled, SNES timing is automatic, Gaussian
audio interpolation is retained, and power-on RAM uses the core's random-value
mode. Input comes only through the two standard joypad callbacks. The host
reads WRAM telemetry; it does not write emulated memory, use savestates, open a
window or play captured audio through a device.

Mesen-S supplies a 256x239 picture with seven black rows above and eight below
the game's 256x224 viewport. PNG captures retain the full callback; native
pixel checks use rectangle `(0, 7, 256, 231)`. Black-padding checks and independent
stage-master comparisons validate this alignment. The first SPC buffer is
shorter than steady-state output; total PCM duration allows at most one video
frame of startup difference while every callback run must still supply audio.

Selected full-output captures:
[Reston selection](screenshots/mesen/reston-select.png),
[Training controls](screenshots/mesen/mode2-pause1.png),
[Training specials](screenshots/mesen/mode2-pause2.png),
[Las Condes](screenshots/mesen/stage0-ambient-phase0.png),
[El Castillo](screenshots/mesen/stage1-ambient-phase0.png),
[La Oficina](screenshots/mesen/stage2-ambient-phase0.png).

Primary references:
[official core download](https://buildbot.libretro.com/nightly/windows/x86_64/latest/mesen-s_libretro.dll.zip),
[Mesen-S core source and GPL-3.0 license](https://github.com/libretro/Mesen-S),
[Libretro Mesen-S geometry and options](https://docs.libretro.com/library/mesen-s/),
[Libretro callback definitions](https://github.com/libretro/libretro-common/blob/master/include/libretro.h).
