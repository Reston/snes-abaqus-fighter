# v0.24 stage08: whole scenery and fixed pavement

Isolated feature for `integration/readable-combat-v024`, based on contract
commit `3f51120`. This is source for the combined human playtest, not approval
to merge main or a combined verification claim.

Las Condes, El Castillo and La Oficina have new versioned built-in imagegen
masters under `assets/art/stages/depth-v1/`. Every exact prompt, input role,
reference hash, raw output/hash and selected source is retained. The rejected
old08 branch was not merged. Original masters, provenance, stage selection
plates, fighters, walking/idle frames, portraits, palettes and audio remain.

The entire building/office illustration is one BG1 plane. A separate BG3
plane holds the quiet pavement under the fighters. There are no scanline
bands, split columns/desks, HDMA or architecture wrapping. The two fighters'
midpoint suggests a bounded scenery look of -8..8 pixels, easing by at most
one pixel per live tick. Sixteen authored pixels at each side cover this look
plus the existing maximum two-pixel impact shake. Collision, actors, feet at
201 and shadows at 200 stay in screen space. Normal motion does not scroll
the pavement. Existing impact shake composes equally on both whole planes.

Camera look freezes in intro, pause, hitstop and round results. Impact shake
retains its existing hitstop animation and pause freeze. Each round resets
the look to center. No winner reaction is added. The pavement joints are at
y184 in Las Condes/La Oficina and y192 in El Castillo, below every connected
architectural object. Source conversion uses one centered 9:7 crop and one
nearest reduction to 288x224. The fully opaque existing HUD covers the first
40 rows, so those stage tiles do not need encoding. The pavement deliberately
uses the existing UI colors available to Mode1's 2bpp BG3; no CGRAM/UI change
is needed. It is quieter and less saturated than the original masters.

## Audited native allocations

All addresses below are VRAM **words**, not bytes.

| Range | Final owner |
| --- | --- |
| `$0000..$2FFF` | BG1 scenery, at most768 4bpp tiles |
| `$3000..$37FF` | BG3 pavement, at most256 2bpp tiles |
| `$3800..$3FFF` | BG1 64x32 map; second screen starts `$3C00` |
| `$4000..$49FF` | Existing BG2 UI/font, unchanged |
| `$4A00..$4EFF` | Existing selected portrait, unchanged |
| `$5000..$57FF` | Existing opaque guide glyphs, unchanged |
| `$5800..$5BFF` | Existing BG2 map, unchanged |
| `$5C00..$5FFF` | BG3 32x32 pavement map, formerly unused |
| `$6000..$69FF` | Actor0 padded page, unchanged |
| `$6A00..$73FF` | Actor1 padded page, unchanged |
| `$7800..$7BFF` | Existing effects/projectiles/shadows, unchanged |

Mode1 remains, with BG3 normal priority behind BG1/BG2/actors. BG1 continues
to use CGRAM32..127 (six new stage-specific 15-color palettes). BG3 reads the
unchanged UI CGRAM0..31; OBJ CGRAM is unchanged. No new OBJ, DMA channel,
HDMA channel or live graphics transfer is added. `$420C` remains zero. The
existing actor queue still permits one3840-byte pose transfer per vblank and
thirty16x16 entries per actor. All screen-off map copies use their actual
4096-byte generated sizes.

The old ambient destination `$3C00` now holds the map's right screen. Therefore
its initial/live upload and clock requests are disabled. The original three
ambient binaries and `stage-dynamics.json` remain byte-identical historical
outputs. TRACE0..122 remains ABI-stable; ambient fields115..118 are
`0,0,255,0` for these static stage planes. No mutable RAM is added. The exact
historical16-byte declaration order is preserved:
`stageDepthTable[10], stageDepthFar, stageDepthNear, stageVictoryTick,
stageVictoryPhase`. Only table byte0 (active flag) and the two signed words
(current/target look) are used; the remaining bytes stay reserved.

## Parent integration hook and generated allowlist

This feature does **not** modify the parent's `tools/make_assets.py`. After
that generator writes `data.asm` and `assets.h`, add these explicit lines:

```python
from stage_depth_assets import install as install_stage_depth
install_stage_depth(ROOT)
```

`install` is deterministic and idempotent. It validates all three versioned
source/provenance/reference hashes, replaces only its declared stage payloads,
updates generated size macros and appends six floor asset declarations. For
isolated development, run `tools/stage_depth_assets.py` after `make_assets.py`
and before `build.py` (do not pass `build.py --assets` afterward without the
parent hook). Run the focused test after all other workstreams are integrated.

Relative to the219-file baseline, exactly14 existing generated files change:
`assets.h`, `data.asm`, and for each stage0/1/2: `.png`, `_tiles.bin`, `_map.bin`,
`_pal.bin`. Seven files are added: each stage's `_floor_tiles.bin` and
`_floor_map.bin`, plus `stage-depth.json`. Inventory becomes226. The other205
outputs, including old ambient, menu plates, all fighter art and audio, remain
exact. No generated or dist output is committed in this feature PR.

| Stage | BG1 tiles / bytes | BG3 tiles / bytes | BG1 / BG3 map bytes |
| --- | --- | --- | --- |
| Las Condes | 639 /20448 | 2 /32 | 4096 /2048 |
| El Castillo | 680 /21760 | 2 /32 | 4096 /2048 |
| La Oficina | 614 /19648 | 2 /32 | 4096 /2048 |

Each stage palette remains192 bytes. The floor's two encoded tiles are a
transparent tile and an opaque tile; local map palette choices retain the
authored broad horizontal tone changes. No architectural pixels are spliced.

`game.c` conflict boundaries: three stage map copy lengths in `loadBackground`,
the initial ambient upload replaced with `stageDepthLoad(which)`, and the old
five-line live ambient clock/request block removed after `stageDepthTrack`.
All other runtime behavior lives in `src/stage_depth.h`. Parent owns shared
preservation/test policies and must adapt the old32x32/animated-stage oracles
to the explicitly changed map/ambient policy. Do not weaken overflow, actor,
cadence, UI or exact asset checks.

## Native evidence

Las Condes was prototyped in the actual Snes9x PPU **before** generating the
other two sources. Prototype ROM SHA256:
`d9a66056a4a30c204e759b8c0c459f9122b1c959685e31cd2af75a73cc42e18d`.
Its controller-only diagnostic drove75 left then150 right frames, observing
225 consecutive one-tick callbacks and signed camera endpoints -8/+8.
`prototype-las-condes-left/right.png` retain the actual PPU output. This
prototype is separate from the final isolated proof.

The focused proof is `tools/test_combat_24_stage08.py`, writing only
`docs/combat-24-stage08-report.json` and this feature's screenshots directory.
It independently decodes hardware bitplanes and both map screens, compares
actual PPU pixels to a single coherent scene/floor displacement, checks both
edges in both directions, contacts/shake/KO, intro/pause/guide/hitstop/results,
both ports, all twelve fighters, simultaneous low waves/jumps, immutable maps,
one actor page per callback, native vblank/lag, SPC FIFO and OBJ limits. It
also captures matching baseline/current movement clips and both pinned cores.
Movement clips are continuous controller sequences; contact clips concatenate
selected contact/hitstop episodes. GIF playback timing is approximate.
All runs are callback-only, silent/headless, below normal priority on two
logical processors. The exact final ROM, source/harness identity, commands,
results and failure arrays are recorded in the report; they are isolated
evidence until the parent regenerates them on its combined source freeze.
