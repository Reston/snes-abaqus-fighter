# Expansion 08: native stage depth and life

> Combined v0.22.0: this note retains the original feature-branch design and
> isolated measurements. The linked focused report and native captures are
> regenerated for the combined cartridge. Use the [combined release note](RELEASE-v0.22.0.md)
> and [verification record](expansion-v0.22.0-verification.json) for current
> identity, coverage and integration contracts.

Feature branch: `t3/stage-parallax-ambient-reactions`, based on integration
commit `610537d`. This feature keeps the source version unchanged; 0.22.0
belongs to the combined integration candidate.

## Behavior

The two fighters' horizontal midpoint drives a small native BG1 camera focus.
The distant scenery scrolls at one pixel per 32 focus pixels, nearer scenery
at one per 16. The signed thresholds are symmetric. The floor stays at its
original coordinates beneath the unchanged fighters and shadows. Existing
impact shake is added equally to all bands. This is actual scanline-dependent
BG1HOFS, independent of shake; the controller proof requires movement with no
attacks and compares the resulting PPU pixels against the exact translated
neutral image.

The existing background plates are used as horizontal bands. Las Condes has
boundaries at lines 48 and 152, El Castillo at 40 and 144, La Oficina at 32 and
152. The opaque five-row HUD hides the highest band in El Castillo and La
Oficina; their visible scenery still moves relative to the fixed floor. This
does not create additional illustrated layers or change the stage masters.
The existing 32-column map wraps at its edges; the bounded offsets expose at
most six pixels of its ordinary wrap. Native left/right captures are retained.

The same eight ambient cells receive more coherent leaf/glass glints in Las
Condes, party gestures in El Castillo, and lower-screen monitor cursors in La
Oficina. All source masters, static tile/map bytes, stage palettes, monitor
digits, fighter assets, Damian v5 and audio are preserved. The source-identical
phase zero remains exact. The three non-neutral phases change 36/36/36,
26/26/26 and 14/16/16 native pixels respectively.

A real round winner triggers two short four-phase ambient cheers using those
same bytes, followed by a neutral settle. The reaction waits sixteen round-end
samples, cycles every eight samples until sample 80 and stops its clock at 96.
Ordinary ambient time remains frozen during the entire round end. Draws do not
start the reaction. Pause freezes both clocks. Intro and hitstop retain the
ordinary freeze policy. A new round, Training reset and scene change reset the
new presentation state.

## Hardware and integration contract

`src/stage_depth.h` contains the feature. The `game.c` hooks are limited to
scene/round reset, live tracking, round-end reaction, ambient eligibility and
the final vblank scroll publication.

- HDMA channel 3: direct mode 2, destination `$210D` (BG1HOFS, two writes).
  Three non-repeating records cover exactly 224 lines, with a zero terminator.
  The table is ten bytes; the PPU receives six scroll data bytes per picture.
  The table and channel setup are written only after `WaitForVBlank`, after
  the existing actor/interface/ambient transfer decisions. No active-display
  table writes can tear an offset.
- `$420C` is write-only. The module writes mask `$08` while fighting and `$00`
  on scene change. It is the sole HDMA owner in this feature base. If another
  feature adds HDMA, compose its mask in software; do not read/modify `$420C`.
  General DMA remains on existing channel 0.
- BG2 scroll, glyph/portrait/map regions, stage tile/map regions, palette banks,
  OBJ entries, one-actor-per-vblank, SPC and audio are unchanged. The ambient
  stream remains four 256-byte phases, eight tiles at `$3C00..$3C7F`; its actual
  writes continue to yield to actor and interface/guide work.
- Sixteen mutable bytes append after existing game globals: table 10, signed
  far/near scroll 4, victory clock/last phase 2. On this isolated ROM they occupy
  `$7E29AF..$7E29BE`. The HDMA bank is explicitly `$7E`; recheck the link map
  after integration. Fighter64/Wave16 and TRACE0..122 are unchanged.
  Existing game addresses remain; the following eight-byte SDK libc allocator
  buffer moves from `$7E29AF` to `$7E29BF`. No gameplay memory is overlaid.
- The shared stage/compatibility suites' historical unconditional round-end
  ambient-freeze assertion needs the new explicit victory-policy exception.
  Camera-sensitive pixel masks must account for each band's offset. The normal
  ambient TRACE115..118 meanings remain intact; the normal clock freezes while
  the new bounded reaction requests phases through the existing pending slot.

## Reproduce and inspect

The owned generator can rebuild just the ambient outputs without invoking
fighter, menu or audio generation:

```powershell
D:/snes-abaqus-fighter/.tools/python/python.exe tools/stage_cartoon.py --regenerate
D:/snes-abaqus-fighter/.tools/python/python.exe tools/build.py
D:/snes-abaqus-fighter/.tools/python/python.exe tools/run_background.py --log build/expansion-08-test.log -- D:/snes-abaqus-fighter/.tools/python/python.exe tools/test_expansion_08_stage_depth.py
```

The focused driver uses ordinary SNES controller callbacks to enter Local VS,
move both fighters in both directions, pause/open Controls, earn a KO and
advance naturally to the next round. It reads WRAM/VRAM/OAM and actual PPU
callbacks. It never writes gameplay memory, loads a save state, opens a window
or opens an audio device. It also drives two low waves and jumping/moving actors
on each stage, observes DMA arbitration, and checks LoROM section boundaries.
The pinned bsnes2014 Accuracy core independently checks actual parallax pixels,
fixed floor, pause freeze, STAT77 and cadence on all three stages. Its shared
compatibility report is left untouched.

The exact ROM hash, check results, resource sizes, measured cadence and pinned
core identities are in [the focused report](expansion-08-report.json).
The isolated final ROM is SHA256
`2e7c9690b23665db7b529c70becf553b8eac21bba7bef839d7aec5644765ea3c`.
The focused run passes 13,130 checks: 6,036 measured Snes9x frames plus 2,568
measured pinned Accuracy frames, with every native frame delta equal to one.
All three stress runs observe 44 simultaneous two-wave frames; the observed
peak is 16 OBJ / 32 tile fetches per scanline, with no STAT77 overflow.
The five feature code sections total 1,178 bytes and fit within their individual
32 KiB banks. Summed linked ROM sections use 3,259,424 of 4,194,304 bytes;
remaining space is fragmented across banks. Repeating the owned generation
and ordinary native build reproduces the same ambient files and ROM hash.

Screenshots and native callback motion captures are in
[`screenshots/expansion-08`](screenshots/expansion-08/): each stage has left/right,
Controls, four ambient phases, parallax, ambient and victory captures. GIF
timing is an inspection approximation; the trace cadence checks are the timing
evidence. The ambient GIF holds each sampled phase for its sixteen live ticks.

This branch does not claim the combined six-suite run, full release evidence,
offline packaging, physical hardware validation or human gameplay review.
Parent integration owns those checks and cross-feature interactions.
