# v0.24 contact alignment

## Contact and dedicated-super composition follow-up

The follow-up starts from committed integration `413b222`, with contact PR15
and dedicated-super PR17 already merged. A fresh `Build.cmd --assets` reproduces
the interim cartridge `62b39ea0971d5e80ab28eef2b579cc4ef97dd0fa6d206261bb2390ca524da58c`.
This composition still precedes attack/jump art and combined pacing. The parent
owns the final six-feature gates and human playtest.

The scoped production change is two conservative distance branches inside the
eligible, non-volley direct-super block of `canHit`: actor canvases separated by
at least96 pixels cannot contain overlapping strike/hurt rectangles. This skips
active-pose selection and far-ROM reads for impossible remote pulses. Volley,
startup, ordinary-strike and throw paths retain their original gates. Existing12.4 coordinates,
strict edges, facing/cross-up gates, throws, profile clocks/damage and geometry
remain unchanged. There are no new locals, mutable state or ROM tables.

The fresh per-case repro binds TRACE to direct `frame`, `snes_vblank_count`,
`lag_frame_counter` and `vblank_flag`. On the original interim ROM, only Roxana's
simultaneous remote-super case repeats at1332 and1360. Both are real runtime
misses: direct frame delta0, vblank delta1 and lag delta1. The other four
recorded simultaneous sequences have empty failure arrays. The Accuracy core
reproduces the same observations.

David's legacy target28 fixture actually settles at26.5 pixels. On both ports
it deals8,8 and misses the18 finisher. The neutral22-pixel fixture deals8,8,18.
Cristian and Roxana complete all their pulses at both spacings. The original
legacy super driver's assertions remain unchanged. The composition driver
requires David's specific target28 miss as a negative boundary case and requires
the complete tuned pulse sequence in the closer fixture; it does not accept
arbitrary missing pulses.

`tools/test_contact_super_composition.py` records each pulse's physical input,
native clocks, selected/uploaded poses, positions and native-derived regions.
Collision runs before animation; the offline body uses the prior selected pose.
The snapshot undoes the immediate post-contact16/32-unit displacement and
finisher knockdown facing/y writes. Observed post-contact positions are retained
separately. Its offline overlays add no runtime drawing or collision state.

The final interim candidate is
`00ede52d7b44725a4967afaad319757d622394149dc4bcebe96f505ed7d0d57b`,
runtime source `8ea3f1b448eeea82fdf358e1d5319312602a0f38`. Its49 composition
cases include simultaneous dedicated supers for all12 fighters on both ports,
all three rising families at both spacings with neutral/timed standing guard,
remote whiffs, startup interruptions and recovery punishment. Every measured
direct-frame/vblank/lag, TRACE, OBJ, transfer, audio and phase failure array is
empty. The recorded Roxana workload also passes on pinned Accuracy.

The report retains a separate **failed** Accuracy five-case attempt: David's
single-callback Start pulse was absent from actual native `rawKeys`, while
frame/vblank/lag cadence remained healthy. A three-callback Start probe observes
the real Start on callback2, pauses once and freezes both clocks. No controller
code or old immediate-pause assertion is changed. Parent must reassess that
fixture against actual sampled input on its final combined ROM; this note does
not certify the failed attempt.

The earlier broader rejection before the super eligibility block is rejected
history (`712b32d4...`): it also changed the volley/startup observation boundary.
The final runtime change confines the optimization to eligible direct pulses.
Both intermediate failed attempts and the final results remain under ignored
`build/`; the feature report identifies their exact hashes and commands.

The final focused report records108 all-roster/both-port native sessions and
52,083 callbacks. Their complete input/state trajectory hashes are compared to
the reproduced62b39 interim ROM, rather than the older baseline-art proof.
The219 generated outputs and geometry digest remain exact across this fix;
their25 differences from approved v0.23.1 belong exclusively to merged super art.
All1,318 prior RAM labels remain exact, with no additional state or geometry.

`rising-super-pulses.png` uses the actual HP-event snapshot for each connection,
or the first active snapshot for an entirely missed pulse. The exact per-tick
rows retain later active ticks, observed/reconstructed positions and VRAM poses.
In particular, Cristian's target28 finisher connects on tick30 after its tick29
near miss; the diagram does not assign that hit to the earlier pose position.

Parent has cherry-picked the runtime changes into `9bd9acc` after all-six
source `88f6edd`. This child never builds that final art/pacing workload. Its
source-only parent rebuild must refresh geometry and regenerate all final gates.
The interim `--expect-legacy-david-miss` switch must not be used as a final
pacing expectation: the merged recoil owner intentionally improves early-pulse
linking without increasing reach. Parent also composes the focused RAM check
with its independently audited eight-byte pacing allowance; contact remains0.

## Historical baseline-art isolated feature

This workstream replaces the shared feet-relative attack bands and fixed body
rectangle with stable, pose-specific ROM rectangles. Its measurements use the
approved v0.23.1 art on contract commit `3f51120`. Final attack, jump and super
art and the combined pacing are **not** certified by this isolated result.
`combat-24-contact-report.json` identifies the exact tested candidate, source,
host/core, commands, coverage and failure arrays. No shared six-suite report or
release identity is replaced.

The isolated proof passes on ROM
`c2cefc9bc385c88e728c7b2845607c465d765ec6250d0085f35efe5d6915feac`,
runtime/driver source `d29cfe489dd224eef89c8d8acb830ff96e20c6d8`:
108 native sessions and 52,083 measured live callbacks cover all12 fighters on
both ports. Cadence, native timing, ambient, OBJ-overflow and SPC failure arrays
are empty. All1,318 prior RAM/direct-page labels and all219 generated assets
remain exact. The later all64 diagnostic appendix changes only offline drawing;
its `--check` confirms the existing cartridge geometry header is still exact.

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
For dedicated super slot2, the generator reads the frozen twelve-super family
inventory: David, Cristian and Roxana use the raised-fist region; the other
families use their grounded cast/strike region. The profile source hash is
part of the geometry digest. This composes the super artwork with collision;
it does not change pulse timing, damage or energy.
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
The twelve `NN-all64-regions.png` appendices include every pose on both facings,
so future super1/2/4 and jump/landing revisions also receive automatic overlays.
Their orange rectangles are stored strike candidates: action, phase and pulse
eligibility still apply; an orange outline never grants an idle/startup attack.
The two before/after GIFs use controller-only native captures of baseline main
and the isolated candidate. GIF frame durations approximate native cadence;
the cartridge and recorded native counters remain authoritative.

Integration requirements: regenerate after final art, review the new diagnostic
regions, rerun this focused driver on combined timings, then regenerate the
parent's six suites, pinned Accuracy smoke and all final exact-ROM evidence.
The all-roster proof here uses baseline mirrors; the parent still owns combined
mixed-roster matchup/balance coverage and human playtest. No main merge,
combined pass count, physical hardware or public-use approval is claimed.
