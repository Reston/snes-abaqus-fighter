# Dedicated super artwork: isolated v0.24 feature

All twelve full-gauge supers now select individual, newly authored whole-body
charge, contact/cast/peak and recovery drawings. The only production C change
is `superFrame()` in `src/super_moves.h`. Every super profile, command check,
clock, energy payment, projectile, damage and state transition is unchanged.
This feature targets `integration/readable-combat-v024` for the parent's
combined human playtest. It does not approve a main merge or claim combined
verification.

## Drawing selection

Native slot **1** holds the charge, slot **2** the contact/cast/rising peak,
and slot **4** the recovery. Startup uses1; an actual pulse's existing contact
window uses2; gaps between serialized pulses return to1; the existing recovery
clock uses4. A held cast is no longer displayed during an occupied-Wave wait.
These are drawing choices only: none extend an active window or change a hit.
The retained `SuperProfile` frame fields and all gameplay values remain exact.

| Fighter | Signature | Drawing cues |
| --- | --- | --- |
| Damian | Kernel Overdrive | Rear-hip hand gather, planted double-palm release, open-hand recovery |
| Ivo | Compound Interest | Sternum palm gather, staggered high/low palms, measured weight-back guard |
| Cristobal | Atomic Cascade | Coiled boxer, driving cross and turned support heel, compact brake |
| Cote | Final Balance | Crossed forearms, broad planted driving punch, squared guard return |
| Negger | Macro Collapse | Deep central gather, heavy low palm release, broad crouched recovery |
| David | Final Audit | Low rear-fist chamber, rotating raised uppercut, compressed guard return |
| Fernando | Legacy Rollout | Low rear-thigh gather, sweeping low release, sturdy bent-knee return |
| Cristian | Zero Risk | Closed crossed-arm guard, compact rising fist, tall collected recovery |
| Mamariaga | Merge Storm | Shoulder gather, asymmetric palm snap, narrow springy guard |
| Reston | Cloud Nine | Broad rear-shoulder gather, heavy high release, open-hand reset |
| Roxana | Closing Bell | Low balanced coil, rising uppercut and coordinated hair/hips, centered return |
| Lars | Absolute Zero | Narrow palm wedge, long planted release, upright collected recovery |

## Art and preservation

`assets/art/super-v1.json` indexes twelve adjacent `super-v1.json` provenance
records and twelve unmodified built-in-imagegen `super-v1.png` raw outputs.
Each record retains the exact prompt, selected/raw SHA256, reference SHA256,
original palette SHA256, source/frame mapping and neutral anchor. Damian was
prototyped first against his approved v5 motion sheet; the other eleven use
their approved walking-v2 sheets as appearance references. The reference art
is never modified or pasted into the new drawings.

Each source contains eight separate complete connected figures. Its first
upright neutral is an unmapped scale anchor; poses1/2/3 map to native1/2/4;
the other five mappings are null. The common `tools/pose_revision_assets.py`
importer uses one isotropic conversion per fighter, anchored to the exact
approved `HEIGHTS` value. No per-pose fitting, body-part splice or palette
replacement is used. Native figures fit the safe94x77 bounds on96x80, with
the existing sole baseline78.

The focused audit compares every native pose against approved main f75005d:
only1/2/4 may change. Walking20–27, idle16–19, legacy0/portrait anchor,
intro/victory11/46 and every other unowned pose remain exact, as do every
portrait, OBJ palette and pre-existing source master/provenance file.
Generation changes only the twelve first fighter banks, twelve native preview
PNGs and character-manifest metadata:25 of219 tracked generated outputs.
Generated assets and dist files are local proof outputs and are not committed
in this feature PR.

## Native proof and integration

The authoritative isolated record is [combat-24-super-report.json](combat-24-super-report.json).
Source freeze `22c0d98f190403b3e7a570c63d4146d8f6520889` builds cartridge
`320c26fc8f9a41d788f4b2213b16e73fa2c3e9e14d93e262786ad2f4285ab531`,
header checksum `CEEA`. The asset build and focused driver both exit0.
The focused run passes4,657 counted checks and36,774 monitored candidate
native ticks in355.501 seconds. Its2,424 dedicated-sequence ticks are a
subset, not an additional total. All cadence, OBJ, transfer, PCM/FIFO and
phase failure arrays are empty. It observes143/146 complete actor changes,
never more than one3,840-byte actor payload per callback; peak sampled SPC
backlog is0. All1,318 baseline WRAM/direct-page symbols retain their addresses;
329 linked sections fit their banks, with a largest section of30,720 bytes.
Baseline clip timing and legacy fixture checks are separately identified in
the report and excluded from candidate timing/fixture totals. The counted
checks also include baseline identity and before/after comparison assertions.

The focused command is:

```powershell
.tools/python/python.exe tools/run_background.py --log build/v024-super-focused.log -- D:/snes-abaqus-fighter/.tools/python/python.exe tools/test_combat24_super.py --baseline-rom build/v024-super-baseline/abaqus-after-hours.sfc
```

The optional baseline ROM is the exact approved v0.23.1 cartridge and must have
its matching `.sym` beside it. It supplies before/after PPU clips for volley,
rush and rising families; omit the argument for a current-ROM-only rerun.
The driver reuses the retained gameplay fixtures without changing their
assertions or writing their shared reports. It verifies full96-energy fresh
neutral Y+B, all twelve fighters/both ports, hit/block/whiff/recovery,
interruption, hurt/down/wake/KO rejection, pause/reset and ordinary specials.
It independently observes phase-specific frame selection and complete VRAM
uploads for both actors, consecutive native ticks,30-OBJ actor geometry,
one3840-byte actor payload update per vblank, capture-only PCM and SPC FIFO.

No mutable RAM, OBJ entries, sound slots, palettes, VRAM regions, DMA paths or
pose banks are added. Fighter64/Wave16/TRACE0..122 and all prior RAM symbols
remain exact. The linked cartridge remains4MiB NTSC FastROM LoROM with32KiB
bank-local sections. Automation is headless, muted, below-normal priority and
limited to two logical processors; it does not change user focus.

Conflict boundary: only `superFrame()` is owned here. Pacing/contact owners
may change super gameplay elsewhere; retain this selection against their
final `start`, `actionActiveEnd` and `superContactEnd` clocks. Parent owns the
generic importer, final preservation policy, version and shared suites. Merge
the source, rebuild with `--assets`, refresh final contact geometry against
the resulting drawings, and regenerate every exact combined-ROM gate. The
historical shared preservation policy still pins pre-v0.24 art and must be
updated by the parent; this child does not weaken it.

Human animation/likeness/readability/balance, physical-controller and
consent/public-use review remain open. Original SNES hardware is unverified.

## Review captures

- [Native roster: anchor / charge / contact / recovery](screenshots/combat24-super/roster-native.png)
- Damian volley: [before](screenshots/combat24-super/00-before.gif) / [after](screenshots/combat24-super/00-after.gif)
- Cristobal rush: [before](screenshots/combat24-super/02-before.gif) / [after](screenshots/combat24-super/02-after.gif)
- David rising: [before](screenshots/combat24-super/05-before.gif) / [after](screenshots/combat24-super/05-after.gif)

GIFs sample native PPU callbacks every three ticks at50ms playback; they are
inspection aids, not a substitute for cartridge timing measurements.
