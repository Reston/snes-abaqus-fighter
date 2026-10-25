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

- Source/harness freeze: `b7f6181fa36df5d1b4cb9d31334a1fcccfb31ea7`.
- ROM SHA256: `0cee5cf59741dd9b5698ffa58e543209a308ae338d57f3e32483e06057b17b3a`.
- Header checksum: `515D`; 4 MiB NTSC FastROM LoROM, PVSnesLib 4.6.0.
- Runtime header SHA256: `63c129b5c30ac2cbc1fadc97bbcf2aefb7f4e63894ecef35fec51f1ccc682b39`.
- Focused harness SHA256: `ffc231da1981a97bb8c703833c8e8807d27e816690399537c6b5640f2f8673db`.
- [Aggregate report](arena-life29-report.json), [Snes9x report](arena-life29-snes9x.json),
  [pinned Accuracy report](arena-life29-accuracy.json).

Snes9x passes 125,711 focused check executions across all three stages;
Accuracy passes 117,499. The two reports carry identical producer/harness/
dependency hashes and ROM identity. They measure 8,626 and 8,625 native
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

Snes9x replays 8,200 identical controller samples against approved v0.28 ROM
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

## TRACE correction after parent review

The original `677bd914...` candidate had a real publication defect: unchanged
`traceActorsFast` always stored legacy ambient values after the C tick wrote
the new telemetry. Its focused harness checked the reservation and VRAM but
omitted TRACE115..118 equality. A direct controller-only reproduction on that
retained ROM fails at frame 686: actual `[0,0,255,0]`, expected `[0,1,255,0]`.
The old ROM, reports, captures and failing reproduction remain ignored under
`build/arena-life29-history-38489c4/`; those old reports cannot certify the
documented new TRACE semantics.

`arenaLife29Publish()` now explicitly owns the four words immediately after
every `traceActorsFast()` call, after completed DMA, and on scene load. No
assembly or art changed. The new harness checks every fight callback against
the literal reservation formula, including idle/frozen/no-upload samples:
`[state[3], state[1], state[5] if state[4]<6 else 255, state[4] if state[4]<6 else 0]`.
There is no masking or normalization. It also independently retains each
completed chunk to prove the entire 1,536-byte pool on every measured native
callback. When a wholly completed base phase is known, the four TRACE words
directly reconstruct every pool byte. The explicit 255 mixed marker is
checked literally and its actual bytes remain covered by completed-DMA
history.

The corrected full proofs check 8,632 Snes9x and 8,631 Accuracy TRACE samples,
including 1,770 / 1,794 partial-pool samples, 7,269 / 7,262 no-upload native
samples, and 225 / 226 last-chunk completions. Each core additionally earns a
P2 KO in round two, pauses a partially uploaded KO phase, turns background
motion off through real guide controls, and allows the genuine round-end
clock to enter round three. The intro abort publishes `[255,63,255,0]` on
Snes9x and `[255,61,255,0]` on Accuracy without a transfer or clock advance,
remains exact through 208 mixed-pool samples on each core,
and converges after motion resumes. One intro abort per core is required;
all previous cadence, VRAM, actor, OBJ, SPC and unmasked baseline gameplay
assertions remain in place. The initial diagnostic reproduction and this
new abort route are recorded in the aggregate report.

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
All 359 linked ROM sections fit one LoROM bank; the largest remains 30,720
bytes. The feature's six C code sections occupy 2,294 bytes.

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
is written only after the corresponding DMA. The post-assembly publication
hook repeats the exact current reservation on every callback, so frozen and
no-upload samples retain those meanings. Full state-byte definitions are
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
before `main`; resolve a quiet-blank source before the wait; call
`arenaLife29Publish()` immediately after `traceActorsFast()`; and replace the
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
& $taskPython tools/run_background.py --log build/arena-life29-trace-build.log -- $taskPython tools/build.py
& $taskPython tools/run_background.py --log build/arena-life29-snes9x.log -- $taskPython tools/test_arena_life29.py --core snes9x --report docs/arena-life29-snes9x.json
& $taskPython tools/run_background.py --log build/arena-life29-accuracy.log -- $taskPython tools/test_arena_life29.py --core accuracy --report docs/arena-life29-accuracy.json
```

The initial asset build was followed by cached native rebuilds while fixing
telemetry, scene handoff and the retained KO-hitstop scheduling issue. Final
native build and both final proofs exit 0; reports bind the final producer
bytes. The first build's source-change guard correctly refused publication
during development. A final LF canonicalization of art metadata was followed
by both frozen proof runs. No failed diagnostic is represented as passing.

The TRACE correction's native build regenerates metadata and exits 0. Both
full corrected proof commands exit 0 on the same frozen source. Compared with
the historical candidate, every generated art/audio/header payload stays
exact; only `arena-life29.json` adds the C publication-ownership note.

Exact corrected ROM, symbols, manifest, generated assets and fingerprints are
retained under ignored `build/arena-life29-tested/`. Generated assets and dist
are restored to the integration base before the evidence commit; the child
PR intentionally contains source/art/docs/focused media only. Expected output
allowlist: stage0/1/2 `{.png,_tiles.bin,_map.bin}`, `assets.h`, `data.asm`,
`stage-depth.json`; new `arena_life29_stage0/1/2.bin` and `arena-life29.json`.
The parent rebuilds/publishes final combined generated outputs and ROM.
