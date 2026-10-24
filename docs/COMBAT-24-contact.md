# v0.24 contact alignment (isolated feature)

This workstream replaces the shared feet-relative attack bands and fixed body
rectangle with stable, pose-specific ROM rectangles. Its measurements use the
approved v0.23.1 art on contract commit `3f51120`. Final attack, jump and super
art and the combined pacing are **not** certified by this isolated result.
`combat-24-contact-report.json` identifies the exact tested candidate, source,
host/core, commands, coverage and failure arrays. No shared six-suite report or
release identity is replaced.

## Behavior

Each of the 768 native poses has two compact hurt bands, one distal forward
strike and an optional rear strike. Hurt bands follow the illustrated body
mass rather than an extended glove or boot. A deterministic extraction trims
the outer fifth of horizontal pixel mass in each band and limits core width
to 29 pixels. Distal fist/boot regions receive at most two pixels of forgiveness.
These are deliberately stable rectangles; runtime never tests individual pixels.
The offline roster sheet exposes the complete result for review, both facings.

The action's active pose selects its strike; startup and recovery remain
ineligible. Standing/crouch/air, guards, leaning attacks and hurt poses retain
their own illustrated hurt geometry. Facing reflects canvas **edges** about
x48, matching the renderer's x -> 95-x pixel reflection. All coordinates use
the existing feet baseline78 and 12.4 actor positions. Touching edges miss;
one fixed-point unit of overlap is sufficient.

Forward reach now follows the visible pose rather than a profile-sized invisible
rectangle. Thus isolated baseline-art reach can differ from the old reach
table; profile data, timing and damage are unmodified. The old `attackReach`
function and `superCanHit` remain as unused legacy helpers for conflict-free
integration; live `canHit` owns eligibility and dispatches the new geometry.
Direct supers retain the existing pulse/connected/volley/facing gates.

Air A alone can reach behind locked takeoff facing, and retains the strict
26-pixel center cap (16 rear plus the existing ten-pixel body allowance).
Other rear strikes remain rejected. Throws retain the original strict
`abs(dx) < throwRange*16`, grounded/healthy eligibility and mutual tech logic;
their range does not inherit strike or hurt padding. Both normal candidates
are still evaluated before either damage resolution, preserving trades.

Projectiles now use their actual single 16x16 OBJ at `(wave.x-8,wave.y)`.
The previous vertical test was centered above this drawing and its horizontal
profile halo could hit without visible contact. Ordinary and super waves use
the same two-band hurt geometry and existing lifetime, damage and one-wave
ownership. Wave-to-wave clashes are unchanged.

## Refresh and parent build hook

The feature owns `src/contact_geometry.h`, the bounded contact block in
`src/game.c`, `tools/contact_geometry.py`, its focused driver, this note and
owned diagnostics. There is no source-art or `characters.h` edit.

Parent must add this exact call in `tools/build.py`, **after** optional
`make_assets.py` and generated-text canonicalization, **before** 816-tcc:

```python
run(sys.executable, ROOT/'tools/contact_geometry.py')
```

The existing `-I build` resolves `build/contact_geometry_data.h`; no generated
asset inventory entry is needed. Always refresh on reuse builds too. A clean
build without this prerequisite fails on its missing include. The generator
does not invoke or modify the shared art pipeline. It reads the final native
preview PNGs, all 96 encoded fighter banks and character manifest. Every pose's
decoded native index hash must match the manifest, and preview alpha must match
the bank silhouette. Its digest includes these inputs and all evaluated boxes.
`--check` rejects stale header bytes after any art/manifest change.

The small `contactActionFrame` function mirrors the ACTIVE selections in
`animation_weight.h`, calling the super owner's `superFrame` for supers.
Parent must keep the selectors coordinated if attack/jump animation mappings
change. The focused native driver checks the ordinary active selections, and
the generator refreshes all64 poses so new super mappings need no table edits.
The native upload scheduler is preserved: collision uses the logical current
active pose; the existing one-actor upload queue may publish it one vblank later.
No new rendering or controller delay is introduced.

## Native resources and conflict boundaries

The flat `const ContactPose[768]` occupies 12,288 ROM bytes and its input digest
another32. Flat storage is essential: this compiler puts multidimensional
const aggregates in initialized WRAM. The focused proof checks the actual
cartridge table bytes, bank containment, every prior RAM/direct-page symbol and
zero added mutable symbols. Runtime overlap transforms each incoming rectangle
once into defender-local coordinates, avoiding repeated far-pointer calls in
the simultaneous-trade hot path.

Fighter64/Wave16, TRACE0..122, 30 OBJ/actor, one3840-byte actor upload/vblank,
VRAM/CGRAM, HDMA, sound, controller commands and physical scale are unchanged.
No assembly, debug OBJ, new UI or mutable cache is introduced. All219 tracked
generated assets remain identical in the isolated build. The parent owns
shared pipeline changes, preservation policy, version and final exact-ROM gates.

`game.c` conflict boundaries: the include and `verticalContact`/`canHit` block
immediately after `updateFighter`, plus the wave-to-defender condition in
`combat`. Do not replace pacing/recoil changes in `updateFighter`,
`hurtWithRecoil`, damage resolution, or jump/attack/super animation ownership.

## Reproduction and evidence

Use the canonical local Python through the silent background runner:

```text
.tools/python/python.exe tools/run_background.py --log build/contact-generate.log -- D:/snes-abaqus-fighter/.tools/python/python.exe tools/contact_geometry.py --overlays docs/screenshots/combat-24-contact
.tools/python/python.exe tools/run_background.py --log build/contact-build.log -- D:/snes-abaqus-fighter/.tools/python/python.exe tools/build.py
.tools/python/python.exe tools/run_background.py --log build/contact-final.log -- D:/snes-abaqus-fighter/.tools/python/python.exe tools/test_combat_24_contact.py --captures
```

The focused proof drives all12 fighters on both native ports, near/far distal
boundaries, standing and low contacts/guards, descending front air punch/kick,
jumping over a low attack, locked-facing rear A and rear-X rejection, symmetric
trades, strict throw range/tech/delayed damage, ordinary specials and supers.
It reads WRAM, OAM, VRAM and captured PCM without writing emulated memory or
using save states. The unchanged endurance inspector checks consecutive native
cadence, real vblank/lag counters, ambient, OBJ overflow and SPC health. A
separate per-callback VRAM comparison enforces at most one changed actor and
3840 changed actor bytes. No GUI or speaker device is opened.

`screenshots/combat-24-contact/roster-pose-regions.png` overlays the evaluated
regions on native pixels. `exact-contact-boundaries.png` and `boundaries.json`
show exact edge-touch misses beside one-pixel overlaps across the roster.
The two before/after GIFs use controller-only native captures of baseline main
and the isolated candidate. GIF frame durations approximate native cadence;
the cartridge and recorded native counters remain authoritative.

Integration requirements: regenerate after final art, review the new diagnostic
regions, rerun this focused driver on combined timings, then regenerate the
parent's six suites, pinned Accuracy smoke and all final exact-ROM evidence.
The all-roster proof here uses baseline mirrors; the parent still owns combined
mixed-roster matchup/balance coverage and human playtest. No main merge,
combined pass count, physical hardware or public-use approval is claimed.
