# Native OBJ scanline budget

This note records the measured baseline for the stage-polish renderer. It is
an engineering diagnostic, not a release report. The probe was silent and
headless and did not write the normal test reports.

## Baseline observation

The instrumented baseline ROM was SHA-256
`868f7dc5357c4eb1114c9ed1e3811c90859547070dce326d2ced98758c1b8d55`.
`TRACE[114]` contains a read-only sample of PPU register `$213E` (`STAT77`),
captured after `WaitForVBlank()` and before the normal DMA work. The low nibble
is the PPU version (`1`); bit 7 is OBJ time overflow and bit 6 is OBJ range
overflow.

The controller-only reproduction was:

1. Boot Local Versus.
2. Select fighter 4 (Negger) for P1. Select fighter 6 for P2. Both profiles
   use the groundwave special family.
3. Select the first stage and wait for the intro to finish, then wait three
   quiet frames.
4. Hold `DOWN` on both controllers for four frames.
5. Hold `DOWN+X` on both controllers for 28 frames.

Both waves were active together at trace frames 536 through 548. The baseline
sample was `0x81` at frames 538 through 548: bit 7 was set and bit 6 stayed
clear. Other frames in the same run reported `0x01`. This proves a reachable
OBJ time-overflow transient with two actors and two low waves; it does not
indicate a range-overflow condition.

The probe reads `$213E` without writing any PPU state. `STAT77` is sticky for
the active display and its overflow flags clear at the end of VBlank, so the
post-`WaitForVBlank()` sample observes the preceding active frame. A single
sample is a frame-level latch, not a scanline number; the vertical overlap
calculation below identifies the contributing scanlines.

## Worst-case arithmetic

The actor renderer emits thirty 16x16 OBJ entries per fighter: six columns
per actor row. With both fighters grounded, one actor contributes
`6 * 16 = 96` OBJ pixels to each body scanline, or `192` pixels for both.

The baseline shadow entries are four 16x16 sprites at OAM Y `FLOOR-5 = 196`.
They add `4 * 16 = 64` pixels on scanlines 196 through 200. A low wave is a
16x16 sprite at Y 183 and ends at 198; two simultaneous waves add `32` pixels.
Therefore scanlines 196 through 198 reach `192 + 64 + 32 = 288` OBJ pixels,
above the SNES limit of `8 * 34 = 272`.

The floor-impact effect occupies OAM Y 189 through 204. If it coincides with
that overlap it adds another 16 pixels, for a conservative `304`-pixel
worst case. The range count remains at most 19 sprites (12 actor pieces, 4
shadows, 2 waves and 1 effect), below the 32-OBJ range limit.

## Bounded fix

The baseline shadow ink sits six pixels inside the selected 16x16 effects
tile. The fix moves the source ellipse from source Y 22..27 to Y 16..21 and both
shadow OAM entries from Y 196 to Y 202. The visible ink remains at Y 202..207,
while the hardware fetch range moves below the actor and low-wave bottoms
(actors end at Y 200 and low waves at Y 198). This removes the 288/304-pixel
overlap without adding sprites or changing the visible footprint.

`oamSet`'s priority argument is also material: actor pieces use priority 2,
while the baseline shadows use priority 0. In Mode 1 the priority-0 shadows
sit behind the opaque stage BG1. The revised shadow entries use priority 2
like the actors so the intended floor contact is visible; their later OAM
slots leave the actors in front where their pixels overlap. This priority
change has no OBJ-budget cost.

## Fixed-cartridge evidence

The stage suite passes against ROM SHA-256
`e44a739488bd549cfcffbe35bbb32bb5e71d9d2dce12bea6562ebd3dd0c15b84`.
Its controller-only two-wave fixture repeats in all three arenas. Both waves
are observed, every sampled `STAT77` value is `0x01`, and full 128-entry OAM
accounting reaches at most 28 fetched tiles and 14 sprites on one scanline.
The original instrumented reproduction also runs without overflow on this
cartridge: both waves coexist for 13 frames, with all 28 status samples clear.

Each arena also has a 600-frame motion/attack stress probe with zero overflow
and strict one-step cadence. The exact-ROM results, native contact captures
and GIFs are in [stage-test-report.json](stage-test-report.json) and
`docs/screenshots/stages/`.

The allocation bound is separate from that observed peak: at most 24 actor
tiles, four wave tiles and two impact tiles can overlap above the shadow
region, for 30 fetched tiles. At Y 202 and below, actors and waves have ended;
the four shadow sprites and one impact need at most ten tiles. This leaves
headroom under 34 in either region, without depending on transparent pixels
being skipped. The background ambient layer consumes no OBJ entries.

## References

- SNES PPU register reference, including `$213E` bits and OBJ limits:
  [SNESdev PPU registers](https://snes.nesdev.org/wiki/PPU_registers)
- PVSnesLib 4.6.0 definitions and flag timing:
  `.tools/sdk/pvsneslib/pvsneslib/include/snes/video.h` (`REG_STAT77`)
- Project OAM layout and transfer constraints: `docs/DEVELOPMENT.md`
