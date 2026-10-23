# Fighter personality: native intro and victory gestures

Feature 04 for the reserved v0.22 integration, based on `610537d`.
Implementation: `src/fighter_personality.h`, with four small render hooks in
`src/game.c`. No narrative, progression, source version or shared release
evidence changes belong to this feature.

The twelve fighters now perform different introductory gestures and seven-beat
victory sequences, using their existing approved 64-frame art. Each signature
accent has its own native path. Gesture titles below name fictional presentation
choreography; they add no dialogue or claims about the pictured people.

## Individual designs

| Fighter | Gesture title | Intro choreography | Victory choreography | Signature accent |
| --- | --- | --- | --- | --- |
| Damian | Kernel salute | Gather at the waist, extend a palm, retract, ready | Palm, gather, raised fist, shoulders up, full salute, shoulder beat, hold salute | Cyan kernel travels from wrist to palm |
| Ivo | Capital guard | Shield, deliberate low bow, shield, open palm | Shield, bow, gather, palm, shoulders, salute, held shoulders | Hollow cyan arc held beside the guard |
| Cristobal | Atomic one-two | Wind back, cross, retract, ready | Wind back, cross, retract, raise fist, salute, shoulder beat, salute | Gold split spark moves straight forward |
| Cote | Balance check | Lower center, coil, lift fist, retract | Low stance, coil, raised fist, reset, shoulders, salute, held shoulders | Hollow arc rises from the waist |
| Negger | Macro brace | Broad windup, brace, close guard, ready | Windup, brace, extend palm, close guard, shoulders, salute, hold | Amber crest pulses at the lead heel |
| David | Audit rise | Coil, rise to fist, shoulders up, ready | Coil, raised fist, uppercut silhouette, fist reset, shoulders, salute, hold shoulders | Gold glint climbs vertically beside the fist |
| Fernando | Legacy seal | Shield, gather, seal with palm, retract | Shield, gather, palm, retract, lift fist, shoulders, salute | Amber crest passes from rear heel toward center |
| Cristian | Risk reversal | Shield, wind back, retract, ready | Shield, windup, cross, retract, raised fist, salute, held shoulders | Gold spark travels diagonally outward and up |
| Mamariaga | Merge pulse | Lower stance, gather, push palm, ready | Low stance, gather, palm, retract, shoulders, salute, held shoulders | Alternating amber double-beat at the forward foot |
| Reston | Cloud horizon | Gather, open palm, raise fist, ready | Gather, palm, retract, lift fist, shoulders, salute, hold | Cyan orb breathes in reverse beside the palm |
| Roxana | Close-out flourish | Retract, raise fist, shoulders up, ready | Retract, lift fist, shoulders, salute, shoulder beat, fist, final salute | Cyan arc climbs above the raised hand |
| Lars | Nordic stamp | Coil, settle low, gather, retract | Coil, low stance, gather, palm, fist, shoulders, salute | Amber crest travels forward with reversed phase |

All twelve intro frame orders differ, and all twelve victory frame orders
differ. The sequences have visible pose differences, including lower-body
changes, palm extensions, guard changes and raised-arm silhouettes. They are
not one shared animation with different labels.

## Timing and ownership

The existing `intro` countdown remains 110 ticks. It holds native neutral frame
16 for eight ticks, then four individual twelve-tick beats. At elapsed tick 56,
both fighters settle into ready frame 32, ahead of the ordinary FIGHT cue at
elapsed tick 60. Nothing moves either fighter or enables an attack. The existing
Training Select reset still skips directly to live practice.

The existing `roundEnd` countdown remains 180 ticks. Only the actual living
winner receives the individual victory sequence. Its beat boundaries are
elapsed ticks 0, 20, 40, 64, 88, 116 and 144; the final pose holds until the
ordinary next-round/result transition. KO losers keep the original fall/floor
frames. A healthy timeout DRAW keeps the existing non-winner poses and has no
signature accent.

Both sequences derive their beat from those countdowns. There is no new mutable
clock or fighter state. Pausing freezes the exact pose and accent, including
when a guide page is open. The normal Start/B/A/Select priority, both ports'
pause actions, four face-button combat layout and L/R CPU Training levels stay
in their existing paths.

The accent borrows only `OAM_EFFECT_BASE` (byte 276, object 69). Existing impact
`fxLife` always owns that slot first. P1 gets intro ticks 20..31 and P2 gets
36..47; the winner gets result ticks 32..63 and 108..139. It uses only existing
spark, orb, hollow-arc and heel-crest tiles and existing OBJ palette 2. Positions
mirror with actual facing and clamp to the native screen. No gameplay wave,
damage, sound, new palette upload or new effect slot is created.

## Hardware and preservation

The candidate is the native 4 MiB NTSC FastROM LoROM cartridge, built directly
with PVSnesLib 4.6.0. ROM SHA256:

`ce70e32e9fddd712459cd6f7d807399fa3621e4a71b370e7e680d18853837dd6`

Header checksum: `F836`.

- Fighter64, Wave16 and `TRACE[0..122]` are unchanged. Actor origins, scale,
  physical positions and facing are unchanged by presentation.
- All 219 generated assets remain byte-for-byte identical to `610537d`,
  including approved Damian v5, every fighter bank/palette/portrait, stages,
  effects and audio. No source art was edited or generated.
- The compiler places the two `const` sequence tables in 132 initialized WRAM
  bytes, appended at `$7F:0448..04CB`. There is no new mutable state.
  All 1,274 pre-existing RAM/direct-page symbols other than two allocation-end
  markers retain their exact addresses. `SECTIONEND_globram.data` and
  `RAM_USAGE_SLOT_3_BANK_127_END` advance by those 132 bytes.
- New functions occupy 335 bytes at `$9B:FDD9`, 382 at `$9B:F988`, and 1,827 at
  `$8B:F800`. Every function fits its 32 KiB LoROM bank. The verbose linker
  audit reproduces the identical ROM and reports 931,321 bytes free (22.20%),
  including all 24 banks 104..127 completely free.
- The existing queue remains the only actor DMA producer. Observed actor-page
  changes never exceed one per video frame. Each upload still uses 3,840 bytes.
  The existing 320-byte HUD and staged guide paths are untouched.
- Native measurements across the twelve controller cases observe at most 65
  visible objects, 16 objects on a scanline and 32 fetched tiles on a scanline
  (hardware limits 32 objects / 34 tiles). Native STAT77 overflow arrays are
  empty. There are no new OBJ entries, palette banks or SPC commands.

## Focused evidence

Run silently and headlessly after building:

```powershell
D:\snes-abaqus-fighter\.tools\python\python.exe tools/build.py
D:\snes-abaqus-fighter\.tools\python\python.exe tools/test_expansion_04_fighter_personality.py
```

Optional comparison with an independently built base ROM:

```powershell
D:\snes-abaqus-fighter\.tools\python\python.exe tools/test_expansion_04_fighter_personality.py --baseline-rom build/personality-baseline.sfc
```

`docs/expansion-04-report.json` records the exact ROM/core, assertions, image
hashes, symbol audit, per-fighter measurements and linker allocations. This
candidate passes **400 focused checks**. The official Snes9x 1.63 libretro core
hash is `f00db5bd97bbe0e80761e590449eb14716bd9ab5785a1b50725c55e10505c343`.

The proof uses real menu/controller routes, ordinary A-kick damage for every
KO, actual emulated actor VRAM and native PPU images. It uses no emulated memory
writes or save states and opens no audio device or GUI. All twelve intros are
checked on both mirrored player sides; winners alternate P1/P2 across the
roster and cover all three stages. Each sampled beat must match the exact
approved 3,840-byte native pose, not just an animation trace value.

The twelve runs measure 10,972 native frames, including 4,752 strict cadence
samples across intro, victory and neutral live combat. Each strict sample has
one native tick per video frame and no new SDK lag. The separate 1,000-tick
controller replay matches the baseline's health, energy, positions, actions,
intro/result countdowns, score, clock, hitstop and round outcomes exactly.
That baseline is SHA256
`50332438739f93808ece5c192c06ab85288d964158faa58db69378c9559d204b`.

Additional controller probes cover intro/victory pause freezing, simultaneous
Start+Select priority, Controls-guide publication, B+A roster return, live
Training reset, both ports' L/R CPU level controls and opposite cancellation,
healthy DRAW, a complete two-round win, effect cleanup at the result screen and
the normal A rematch path.

- [All twelve intro sequences](screenshots/expansion-04/intro-all12.png)
- [All twelve victory sequences](screenshots/expansion-04/victory-all12.png)
- `docs/screenshots/expansion-04/` also contains 24 full native screenshots,
  one intro and one victory for each fighter. Contact sheets use actual native
  PPU crops at 1:1 scale in chronological order.

These are focused feature results. The parent owns all six combined native
suites, independent compatibility smoke and final integration testing. No
offline package or full release evidence was generated here.

## Integration notes

Feature 01 should retain the state-8 winner dispatch and the intro override in
`drawFighter`; all active-combat animation remains its area. Features 02/08
should retain impact priority over the borrowed single effect slot. Feature 09
can change surrounding text/progression while keeping the existing 110/180
countdowns, which are this module's presentation clocks. If those durations
are intentionally changed later, update the two elapsed-time calculations and
the focused timing oracle together.

The focused preservation assertion pins fighter/portrait assets; other features
may legitimately change their own generated effects/audio assets. The report
also records every generated change from the integration base for review.
