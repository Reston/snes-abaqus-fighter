# Animated arena life (topic 6)

Four small background people and four environmental details animate in each
of the three existing arenas. Las Condes has business arrivals and onlookers,
El Castillo has party guests, and La Oficina has coworkers behind the desks.
Plants, doors, monitors, a lantern and pennants provide quieter activity.
Conversation alternates slowly. A real damage step of at least eight HP
elicits a flinch/gasp; a newly active paid super elicits excitement; an actual
zero-HP KO elicits celebration. Priority is KO, super, then heavy contact.
The observer only reads combat state. It never calls RNG or writes actors,
waves, inputs, actions, HP, energy, combat timers or audio state.

This is isolated feature evidence for the integration branch, not combined
v0.29 verification or main-merge approval. The parent owns shared native
suite adaptation, all six suites, final freeze/reproduction and integration.

## Exact candidate and evidence

- Source/harness freeze: `0baa6ae32a9329d49c3f3cd5c3c29013eb48a4f0`.
- ROM SHA256: `677bd91476fe92e745a1b072563a33b416d7e2803ea6b7030ebdf80c033a6d60`.
- Header checksum: `C48A`; 4 MiB NTSC FastROM LoROM, PVSnesLib 4.6.0.
- Runtime header SHA256: `808df56809e6e91bc0e3dcfa759ed58e9dc545b1f86f8cc30f1bdf3b6590494d`.
- Focused harness SHA256: `e6f5e11812f6c6db4f7ad37206b68b6e1308faeaabd06d46861daca9ab6f40fc`.
- [Aggregate report](arena-life29-report.json), [Snes9x report](arena-life29-snes9x.json),
  [pinned Accuracy report](arena-life29-accuracy.json).

Snes9x passes 68,502 focused check executions across all three stages;
Accuracy passes 61,757. The two reports carry identical producer/harness/
dependency hashes and ROM identity. They measure 7,157 and 7,156 native
fight/intro/round-end callbacks respectively, with zero SDK lag or frame
collapse. Forced-blank menu/scene loads are outside live cadence measurement.
Each stage reaches all six authored phases in actual native VRAM. Controller
tests cover both physical ports, pause/resume, the existing guide's background
motion preference, heavy contact, two simultaneous paid supers, earned KO,
the next round and a different arena handoff. Mirrors 8, 10 and 0 cover fast
volleys, rising sequences and ordinary volleys across stages; this is not a
full roster or 432-case matrix.

Every completed 256-byte upload matches its exact phase source and destination;
every changed actor page matches a complete approved 3,840-byte pose. The
measured maxima are 16 OBJ entries / 32 tile fetches per scanline and three
resident SPC FIFO bytes. PCM advances every measured callback and remains
unclipped. Actual PPU spectator changes match 424, 701 and 452 visible changed
pixels in the three conversation captures on each core. The entire detailed
floor's native bytes are exact; rendered floor error versus decoded SNES
colors is at most two channel levels on Snes9x and one on Accuracy.

Snes9x replays 6,731 identical controller samples against approved v0.28 ROM
`09eaa47ddc12d419e259f1330eb225f1e56f75d42efdd2faf5c27063f8f2357c`.
Every unmasked TRACE word 0..113, full Fighter64/Wave16 bytes, RNG, private
super arrays, fight/CPU/second clocks, winner and effect/shake fields match.
This is gameplay preservation for those routes; Accuracy cross-ROM byte
equivalence and whole-WRAM identity are not claimed.

Actual native captures and sampled clips are under
[screenshots/arena-life29](screenshots/arena-life29/). Each GIF samples every
three native callbacks; GIF playback is an inspection approximation, not a
timing proof. No window or audio device was opened. Human aesthetic review,
listening, physical controllers and real-console/flash-cartridge checks remain
outside this focused proof.

## Native allocation

The generator runs after `stage_depth_assets.install` and before transactional
publication. Existing stage tile prefixes (26,144 / 25,600 / 26,048 bytes), all
stage palettes, all original floor map entries and every map cell outside the
48 declared cells remain exact. The complete current generated inventory has
230 committed-source outputs plus the ignored SDK-generated `soundbank.h`:
214 of the prior 226 outputs are exact, twelve declared outputs change, and
four feature outputs are added. Fighters, all poses/portraits/likenesses,
physical scales, UI, menu and audio payloads stay exact.

| Resource | Allocation |
| --- | --- |
| Mutable state | existing `v29ArenaState[48]`, `$7F:0618..0647` |
| BG1 tile pool | tiles 832..879, VRAM **word** `$3400..36FF`, 1,536 bytes |
| Remaining gfx tail | word `$3700..37FF`, untouched |
| Wide BG1 map | word `$3800..3FFF`, unchanged during live play |
| Per arena phase source | 6 phases x 1,536 = 9,216 ROM bytes, single bank |
| Queued transfer | at most one 256-byte / eight-tile chunk per blank |
| Extra OBJ / CGRAM / HDMA | zero / zero / zero |
| Actor transfer | existing maximum one complete 3,840-byte actor per blank |

Every patch uses one of the existing stage palette banks 2..7, selected once
against all six phases. No new CGRAM writes are introduced. Four person
patches are 16x32 pixels, one complete person per chunk; four props are 16x16,
two complete props per chunk. All rectangles are above the floor seam.
Existing coherent whole-scene camera motion and detailed floors remain.
There are no bands, parallax, extra sprites, stage DMA to `$3C00`, or HDMA.
All 358 linked ROM sections fit one LoROM bank; the largest remains 30,720
bytes. The feature's five C code sections occupy 2,478 bytes.

The integration source already defines the parent's six initialized arrays.
Relative to its still-v0.28 tracked symbols, only those 176 reservation bytes
and two end/size markers append. All 1,321 old variable/data labels retain
their addresses; topic 6 adds no mutable symbol. The hardware and TRACE
assembly bytes remain exact.

## Transfer policy and telemetry for parent integration

`arena_life29Tick()` observes after fight processing and actor queue selection.
It prepares a source and destination before `WaitForVBlank()`. The actual
transfer executes only if both actor and every UI/guide dirty flag were clear,
and rechecks actor/interface ownership inside the existing blank. A busy
fight can defer a queued phase; there is no deadline that takes a blank away
from fighters or UI. No phase preempts an unfinished six-chunk phase.

Intro, pause, live hitstop and background-motion OFF freeze clock and uploads.
A timeout does not celebrate. An actual KO may animate within the original
round-end schedule after actors/UI have priority. The original KO path retains
its contact `hitstop` byte until the next round; round-end is explicitly
allowed to animate despite that retained byte. The observer never clears it.
An unfinished old phase is aborted at a new-round intro and marked mixed
until a complete fresh phase converges after the intro.

`assets/generated/arena-life29.json` is the independent reconstruction contract:
pool addresses/bytes, each map offset and native world rectangle, original map
word, replacement word/palette, chunk index, floor seam, original tile/map
hashes, complete phase-source hashes/offsets and current output hashes. The
`stage-depth.json` static output hashes are updated, while its legacy ambient
flag remains disabled. `stage-depth.json` also names the new manifest. Its
old `live_dma_bytes: 0` describes the disabled legacy path; the new manifest
owns the explicit 256-byte arena path. Parent should consume both contracts.

TRACE retains its exact 0..122 ABI. Slots 115..118 now mean:

| Slot | Completed/queued meaning |
| --- | --- |
| 115 | last wholly completed phase 0..5; 255 after aborting a mixed pool |
| 116 | low byte of eligible animation clock |
| 117 | phase currently queued/in flight; 255 when idle |
| 118 | chunks completed in that phase 0..5; zero when idle |

For a normal in-flight phase, its first `TRACE[118]` chunks come from
`TRACE[117]`; remaining chunks retain the last completed phase. The independent
harness can also retain each completed chunk across an intro abort. In the
reserved array, byte 14 is a wrapping completed-transfer serial; bytes 19/20
record the **last actually uploaded** chunk/phase, independent of any newly
queued phase. This distinction matters when the last chunk finishes and the
next phase is queued during the same host callback. Every completion record
is written only after the corresponding DMA. Full state-byte definitions are
in the header and generated manifest. No legacy `ambient*` variable or unsafe
destination drives this runtime.

Parent compatibility work: replace static-only ambient assertions with the
new contract and partial-pool oracle; continue enforcing immutable original
tile prefixes, entire live map and floor. Parent owns changes to
`stage_test_contract.py`, `test_pacing_floor_25.py`, `test_compatibility.py` and
the shared stage/presentation suites. Existing static-only descriptions are
historical for the new runtime. This child has not edited those suites/reports.

Small shared hooks are: prototype before `commonScreen`; clear ownership in
`commonScreen`; enable the stage after `stageDepthLoad`; include the module
before `main`; resolve a quiet-blank source before the wait; and replace the
disabled legacy upload block with the bounded completion-tracked upload.
Substantial runtime and encoding code remains feature-specific.

## Art and reproduction

Original built-in imagegen atlases, exact prompts, output hashes, compositing
reference hashes and crop/registration notes live in
`assets/art/stages/arena-life-v029/`. The source atlas's cropped final seated
row is retained but unused; the burgundy character's upper-body crop supplies
the fourth coworker. Conversion only alpha-composites authored poses, applies
deterministic BOX reduction and quantizes to unchanged stage palettes. No
commercial assets, synthetic replacement poses or original-master edits.

Run commands from this worktree with the repository Python. All heavy jobs
used a PowerShell wrapper whose `ProcessorAffinity` was **12288** (CPU12/13)
and `PriorityClass` was **BelowNormal**, then `tools/run_background.py` with
an absolute resolved Python executable:

```powershell
$p=[System.Diagnostics.Process]::GetCurrentProcess()
$p.ProcessorAffinity=[IntPtr]12288
$p.PriorityClass='BelowNormal'
$taskPython=(Resolve-Path .tools/python/python.exe).Path
& $taskPython tools/run_background.py --log build/arena-life29-build.log -- $taskPython tools/build.py --assets
& $taskPython tools/run_background.py --log build/arena-life29-snes9x.log -- $taskPython tools/test_arena_life29.py --core snes9x --report docs/arena-life29-snes9x.json
& $taskPython tools/run_background.py --log build/arena-life29-accuracy.log -- $taskPython tools/test_arena_life29.py --core accuracy --report docs/arena-life29-accuracy.json
```

The initial asset build was followed by cached native rebuilds while fixing
telemetry, scene handoff and the retained KO-hitstop scheduling issue. Final
native build and both final proofs exit 0; reports bind the final producer
bytes. The first build's source-change guard correctly refused publication
during development. A final LF canonicalization of art metadata was followed
by both frozen proof runs. No failed diagnostic is represented as passing.

Exact tested ROM, symbols, manifest, generated assets and fingerprints are
retained under ignored `build/arena-life29-tested/`. Generated assets and dist
are restored to the integration base before the evidence commit; the child
PR intentionally contains source/art/docs/focused media only. Expected output
allowlist: stage0/1/2 `{.png,_tiles.bin,_map.bin}`, `assets.h`, `data.asm`,
`stage-depth.json`; new `arena_life29_stage0/1/2.bin` and `arena-life29.json`.
The parent rebuilds/publishes final combined generated outputs and ROM.
