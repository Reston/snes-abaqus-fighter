# Expansion 01: animation weight

The native presentation now holds planted poses longer, stages strong attacks
through anticipation and recoil, and releases landing compression through a
short return to guard. It reuses the approved 64 frames for every fighter.
Combat timing, damage, reach, movement, jump physics and input eligibility are
unchanged. The integration base is `610537d3da8f7005c28ea31d0a45a7c17f8f7ba8`.

The feature ROM is SHA256
`07f3f6d589f905c58b2e72b499245e5538d365790319990a7fbb18193c4e5d68`,
header checksum `2776`, built with the pinned PVSnesLib 4.6.0 toolchain.
The local cartridge/symbol/manifest outputs are intentionally excluded from
the feature commit. Version 0.22.0 and the combined release remain parent-owned.

## Native sequencing

- Idle uses a 96-tick breathing cycle: guard 32, inhale 12, exhale 16, return
  12, guard 24. Returning from another state begins at the return pose. The
  initial roster phase remains staggered by fighter ID.
- Forward/backward steps still follow travelled distance, with the original
  32/16-pixel cycle lengths. Contact and opposite-foot holds last five phase
  units each; passing and under-body poses last three each. No screen-space
  bob, translation, rescaling or separate gait timer is added.
- Strong punches and kicks briefly gather in ready pose 32 before windup.
  Active art stays aligned to the existing native active interval. A strong
  extension holds for two early recovery ticks, retracts, then returns to
  ready during the final four ticks. Jab and light kick recover more directly.
  Sweeps gather through 28/38, extend as 8, then recover through 39/28.
- Rush startup now uses anticipation until its real active interval. Other
  specials retain their family art, with the grounded cast returning to guard
  late in recovery. Air normals reclaim apex guard 55 late in recovery.
- Jump descent uses bent-knee air recovery 54 near the floor, reserving landing
  compression 31 for physical contact. After the existing three landing ticks,
  visual state 15 shows 28 for three ticks and 19 for three ticks. A new punch,
  step, jump, crouch or guard takes priority immediately. This visual release
  adds no control lock or landing delay.
- Throw ascent keeps lifted victim 58; ordinary knockdown ascent uses recoil
  60. Both switch to fall 61 at the physical apex. Ground impact holds 59 for
  five ticks before settling on prone 14. Get-up plants 62 for six ticks and
  reaches upright guard 63 for the final four, then retains the ordinary wake
  state. A standing KO falls through 47/59/14. No downed-state duration changes.

`src/game.c` replaces only the old `animateFighter` definition with the include
of [animation_weight.h](../src/animation_weight.h). `poseFor`, gameplay, OAM,
DMA, sound, CPU, stages and all art-generation code are untouched. The module
adds no globals or data tables. Fighter64, Wave16 and TRACE 0..122 remain exact;
only the existing private animation clock and requested frame fields change.
Animation advance still belongs to the original pause/hitstop gate.

## Focused native proof

[expansion-01-report.json](expansion-01-report.json) records **471 focused checks
over 17,299 native callbacks**, all twelve mirror matchups and both physical
controller ports. Menus, movement, attacks, specials, jumps, both throw roles,
sweep knockdowns, pause/resume and landing-release interruption use actual pad
inputs. Four representatives also run a 600-callback transition stress segment.
The harness neither writes WRAM nor uses save states; the libretro host opens
no window or audio device.

Every callback compares both padded actor pages against the complete approved
native 64-frame payload set, and checks all thirty OAM entries per actor for
the original 96x80 geometry, floor pivot, size and palette. No torn or unknown
payloads, two-page replacements, out-of-range requests, OBJ overflow flags or
geometry failures occurred. SDK counters record zero lag increments and exactly
one vblank per callback, including simultaneous two-actor transitions, impacts,
pause and round-end presentation.

The same physical controller routes were run against a native build of the
integration base, SHA256
`50332438739f93808ece5c192c06ab85288d964158faa58db69378c9559d204b`.
Every non-animation Fighter byte and every non-animation public combat-trace
field match frame by frame, including action/tick/endpoints, position, health,
energy, buffers, throws, knockdown, wake and round outcomes. Only Fighter bytes
44..47 (`animFrame`, `oldFrame`, `animState`, `animTick`) are excluded from that
comparison. Each route's digest is retained in the report.

All 219 tracked generated assets match the base Git blobs. This preserves all
768 encoded frames, palettes, physical scales, approved Damian v5 and all other
art/audio/stage pins. All 1,276 RAM/direct-page symbols retain their names and
addresses. The animation function grows from 4,790 to 7,253 bytes (+2,463),
within one LoROM bank at `$E3:E2A0`. Its bank has 267 unoccupied bytes; linker
section accounting leaves 24 wholly unoccupied banks. No ROM section crosses
a 32 KiB bank boundary. Combined placement must be checked again after merges.

Twenty-four callback-captured GIFs and labelled native strips cover Damian,
Reston and Lars idle, forward/back steps, landing, strong punch/kick, throw and
sweep sequences in [screenshots/expansion-01](screenshots/expansion-01/).
Representative strips:

- [Damian landing](screenshots/expansion-01/fighter00-jump.png)
- [Damian strong punch](screenshots/expansion-01/fighter00-normal-x.png)
- [Reston landing](screenshots/expansion-01/fighter09-jump.png)
- [Lars strong kick](screenshots/expansion-01/fighter11-normal-a.png)
- [Lars knockdown/get-up](screenshots/expansion-01/fighter11-sweep.png)

Strip labels describe the requested trace frames; the alternating actor DMA
can trail by one picture. GIF centisecond holds use cumulative 10/20ms rounding
to approximate 60.0988 Hz. The screenshots are actual native PPU pictures.

Run from this checkout with the shared ignored `.tools` junction:

```powershell
& 'D:\snes-abaqus-fighter\.tools\python\python.exe' tools/build.py
& 'D:\snes-abaqus-fighter\.tools\python\python.exe' tools/test_expansion_01_animation_weight.py
```

To reproduce the unchanged-gameplay comparison, first build `610537d` separately
and retain its ROM and symbols, then record those controller routes:

```powershell
& 'D:\snes-abaqus-fighter\.tools\python\python.exe' tools/test_expansion_01_animation_weight.py --record-base --base-rom build/expansion-01-base.sfc --base-symbols build/expansion-01-base.sym
& 'D:\snes-abaqus-fighter\.tools\python\python.exe' tools/test_expansion_01_animation_weight.py
```

The base recording is ignored under `build/`. Without it the visual/controller
checks still run and the report explicitly records `base_comparison: false`.
`--skip-preservation` permits parent-owned combined assets and added RAM globals;
the combined candidate should not be compared to this feature-only gameplay
digest after other authorized gameplay features are merged.

## Integration hooks and limits

Feature 04 owns personality intros and winner sequences. The `roundEnd` winner
selection and state-8 animation assignment remain the original behavior, marked
in the module. Add the personality winner override there; an intro-only pose
override can be made before ordinary locomotion selection. Keep that ownership
when resolving a game.c conflict instead of restoring the obsolete function.

Parent-owned roster expectations should observe a complete 96-tick idle cycle
(currently `verify_p1_fighter` observes 64). The logical-pose whitelist should
accept new visual transitions: grounded neutral can release through 28; jump
can use 54; strong kick recovery can use 32; sweep recovery can use 28;
knockdown/hurt can settle on 14 and rise through 63; cast recovery can use 32.
Anticipation remains a visual transition even while the logical pose is neutral.
Existing startup tests that require cross windup 34 on the first buffered tick
should also allow ready 32. Do not relax contact timing, physics, active-frame,
native payload, geometry or transfer assertions.

The six shared suites, compatibility smoke and combined release evidence are
left to the parent. No six-suite, full endurance, hardware or release-readiness
claim is made here. The visible result remains bounded by the approved frame
art; no new in-between drawings or likeness edits were introduced.
