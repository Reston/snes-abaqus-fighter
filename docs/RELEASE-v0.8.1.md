# v0.8.1 - Reston's short-hair likeness

This native SNES development snapshot gives Reston a fuller, very short dark
buzz cut across all 64 poses and his selection portraits. The mature high
forehead, beard, face, costume and cartoon style remain consistent. Human
likeness feedback and the other [public-release gates](PUBLIC-RELEASE.md)
remain open.

- Cartridge: 4,194,304 bytes, NTSC FastROM LoROM; header checksum `A358`.
- ROM SHA256: `76b456d1ac75471a8b9710c61b0ce4c6ab9ca344b1b8a1f17e38f36e52904466`.
- Cartridge source commit: `fe05e5fd1391a1db20f1b66f1e9f6e699445e77a`.
- Source tree: `46e1af160ffb8ab6cb768e3d9deec1352d77ae83`.

## Art preservation

Four versioned built-in imagegen atlases cover the legacy, motion, action and
airborne/throw/recovery frames. Original masters remain in the source tree.
Adjacent provenance records retain the full prompts, references, output hashes
and extraction checks.

An immutable v0.8 roster baseline and one pinned Reston revision contract
protect the change. All eleven other fighters retain identical native bank
bytes across their 64 frames. Reston's existing fifteen-color palette, physical
scale, source-normalization factors, 96x80 canvas and floor baseline are locked.
The generated replacement must match all 64 reviewed indexed-frame hashes.
Generation validates the complete roster before publishing its preview images
and manifest; a rejected revision cannot become its own baseline.

The native C/65816 engine, combat profiles, controls, stage and audio assets are
unchanged. Selection backgrounds and portraits are regenerated from the revised
art. The native transfer and memory contracts remain those of v0.8.0.

## Verification

The isolated committed-source rebuild reproduces the exact cartridge, manifest,
214 generated assets and normalized symbols in 76.344 seconds. It removes an
intentionally invalid SDK override and uses the freshly extracted source-local
toolchain.

`Test.cmd` exits 0 with all six canonical reports on this exact ROM: 2,595
gameplay, 18,081 roster, 215 presentation, 997 focused input, 8,131 stage and
622 Training checks, totaling **30,641**. The roster suite checks the native
frame payloads, geometry and controller-driven motion in both player slots;
presentation checks each selected portrait's actual VRAM content.

The same cartridge passes the expanded technical gates:

| Gate | Result |
| --- | --- |
| Native matchups | 288 ordered cases under two policies, 600 live frames each, all three stages, four deterministic replay digests |
| Independent engine | Pinned bsnes2014 Accuracy smoke plus 48 bounded combat cases / 28,800 frames, unit video/TRACE cadence and healthy captured PCM |
| Native endurance | 216,356 live frames per mode at 60.0988118623 FPS; one uninterrupted boot/unload each in Arcade, Local Versus and Training |
| Isolated rebuild | Exact ROM, manifest, 214 generated assets and normalized symbols from the committed source export |

The three native sessions wrap the frame counter 4/4/3 times. Required
coverage is complete, all five failure arrays are empty, stable-fight lag is
zero, and resident audio peaks at six queued bytes and drains. These are
accelerated emulated live hours. The independent combat run remains bounded;
it is not a second-engine full ordered-pair matrix or hour-per-mode run.

The shared release evidence validator passes. The offline Windows archive
contains the cartridge, Snes9x, player manual, license notices and exact-ROM
evidence bundle. Its technical audit passes **7,471 checks**, including archive
and source report byte identity; `public_release_certified` remains false.

Native-size review accepted the full 64-frame replacement for integration.
Actual PPU captures confirm Reston renders in both player slots; this is
technical art review, not team likeness approval, human balance testing,
listening approval, controller or real-console certification.
