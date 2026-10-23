# Expansion 06: CPU personalities

> Combined v0.22.0: this note retains the original feature-branch design and
> isolated measurements. The linked focused report and native captures are
> regenerated for the combined cartridge. Use the [combined release note](RELEASE-v0.22.0.md)
> and [verification record](expansion-v0.22.0-verification.json) for current
> identity, coverage and integration contracts.

Feature branch `t3/cpu-personality-policy`, based on integration commit
`610537d3da8f7005c28ea31d0a45a7c17f8f7ba8`.

The native CPU now has individual spacing, pressure, normal preferences,
throw appetite, guard probability and recovery-answer habits. These are
fictional fighting styles, not descriptions of the people in the roster.

- Damian mixes light punches and light-kick checks at medium range.
- Ivo gives ground, guards often and favors longer kicks.
- Cristobal closes rapidly and maintains frequent light pressure.
- Cote seeks close throws and strong punches.
- Negger uses deliberate heavy checks behind a guarded stance.
- David waits for visible recovery and answers with quick punches.
- Fernando gives the most ground and uses kicks to maintain space.
- Cristian baits at medium range and answers recovery with strong punches.
- Mamariaga pushes forward with strong kicks and occasional throws.
- Reston combines mobile light punches with strong-kick checks.
- Roxana applies close kick pressure and quick recovery answers.
- Lars uses deliberate strong punches and light-kick recovery checks.

Easy keeps these habits with a slower normal cadence, reduced recovery-answer
chance and no universal anti-air. Normal and Hard increase commitment cadence
and sampled recovery/anti-air opportunities. Counter specialists differ in
their observed recovery answers as well as their preferred commands; aggressive
and defensive groups differ in observed approach and retreat decisions.

## Native behavior and integration

`src/game.c` replaces only the old `cpuKeys` body with an include of
`src/cpu_personality.h`. The module owns `cpuKeys`, its small normal-key helper
and a 108-byte constant ROM table. It adds **zero mutable bytes**. Existing
Fighter64/Wave16 layouts, all prior WRAM/direct-page symbol addresses and
TRACE 0..122 remain unchanged.

Decisions pass through the ordinary input capture, command recognition,
startup, recovery, energy, hit, block and knockdown paths. Y/X/B/A remain the
only attack buttons; CPU choices never generate shoulders or system buttons.
No profile damage, reach or timing changes are included. Physical P1/P2 input
routing and the paused Training shoulder-level controls are untouched.
Training Stand/Guard High/Guard Low/Jump still use their existing scripted
path; CPU Training uses the selected difficulty and ignores physical P2
gameplay input.

The shared incoming-wave priority and Normal/Hard crouch-low-wave guard remain.
The original family-specific signature-special spacing and fair universal
anti-air height, distance, cadence and probability remain. Current visible
action timing supplies the existing next-simulation-tick guard check; no
opponent pad, buffered command, future position or predicted outcome is read.
Recovery answers inspect only a currently visible recovery state and still
need full ordinary attack startup. Their Hard threshold is capped at 28/32
on five-tick sample opportunities. Empty jumps can draw an uppercut, and a
retreating jump can make it whiff.

The existing single wake-jump edge remains. Dead fighters cause zero CPU input.
No attack is issued during CPU action, air, hurt, down or hitstop unavailability;
guard directions may continue during guard stun. A downed opponent does not
invite an attack. PRNG advancement now occurs on eligible decisions, so old
phase-specific strategic fixtures must be remeasured for this candidate.

Feature 07 has a documented optional insertion point after availability and
wave/ordinary defense, before signature-special selection. The parent can call
its shared legal super-command API there; this feature adds no super engine,
gauge, extra command or placeholder implementation.

All 219 generated assets and all retained art/source/audio are unchanged,
including Damian v5 and all fighter palette/physical-scale pins. No DMA, OAM,
OBJ fetch rectangle, palette, VRAM, audio or transfer code changes are included.

## Build and focused evidence

Candidate ROM SHA256:
`db0cd17d4dcee9d529ac3a2135a8e158e9731750aead914cc26cc128abf86c1c`.
The ROM, symbols and manifest are local build products and are not committed
by this feature. The parent owns the combined ROM and shared suite reports.

Run from the worktree with the ignored `.tools` junction pointing to the
canonical SDK/cache:

```powershell
D:\snes-abaqus-fighter\.tools\python\python.exe tools/build.py
D:\snes-abaqus-fighter\.tools\python\python.exe tools/run_background.py --log build/expansion-06-final.log -- D:\snes-abaqus-fighter\.tools\python\python.exe tools/test_expansion_06_cpu_personality.py
```

The focused driver uses the pinned actual Snes9x core and captures native
video/audio callbacks without a window, playback device, save state or WRAM
write. Controller menus, pause selection, movement and attacks create every
fixture. Read-only native action clocks supplement the unchanged public trace.
Its report is `docs/expansion-06-report.json`.

The evidence covers:

- Twelve CPUs at all three difficulties in 1,800-frame scripted encounters:
  neutral, pressure, guarding, sweeps, jumps and visible recovery baits.
- A second all-roster Hard encounter with injected P2 gameplay/shoulder
  noise, requiring identical decision/state and sampled native-video hashes.
  These runs total 86,400 strictly checked consecutive fight callbacks.
- Per-character command histograms, action starts, neutral approach/retreat,
  available recovery opportunities/answers, real hits, blocked attacks,
  completed normal whiffs, CPU guards and anti-air starts. Interrupted attacks
  are recorded separately from the completed-whiff assertion.
- All twelve at each difficulty facing a controller-created jab whiff, plus
  multiple fixed Hard phases for pressure and counter specialists. The latter
  measure 4 answers over 32 available recovery ticks for Cristobal versus
  12 over 30 for David/Cristian; Hard also has genuine declined opportunities.
- Paired all-roster fresh boots with a newly pressed P1 attack: the CPU's first
  decision remains identical before that attack becomes visible.
- Genuine low-wave guards for all twelve at Normal and Hard, plus the retained
  independent low-wave/wake controller regressions.
- Three native uppercut hit fixtures with ordinary startup and a complete
  eight-active-tick retreat whiff. Controller-created KOs on both sides leave
  subsequent CPU input zero while new player jump/attack input is supplied.
- Native contact screenshots under `docs/screenshots/expansion-06/` with
  content hashes in the report. They are unedited 256x224 callback images.

The bounded fight windows require every native frame delta to equal one and
every sampled STAT77 OBJ overflow mask to be clear. These are native timing
and fetch-budget observations, not host wall-clock FPS estimates. The linker
places `cpuKeys` in a single bank: 4,780 bytes, versus 3,700 before this feature;
the normal-key helper is 84 bytes. A verbose independent link reports 932,793
free ROM bytes (22.24%), including 1,123 free bytes in CPU code bank 102.
The constant table is in ROM bank 10; automatic section placement can relocate
it during combined integration. No single CPU section approaches 32 KiB.

## Limits and parent review

This is focused exact-candidate evidence. It does not certify the six shared
suites, compatibility smoke, endurance, full release evidence or an offline
package. The parent must regenerate combined evidence after all feature merges.
Balance changes can change encounter metrics and fixed reaction phases; review
those against the combined move data instead of reusing these ROM results.
An additional read-only diagnostic ran the legacy CPU helpers: the family/
difficulty matrix and natural-wave-special probes pass, while
`check_cpu_special_spacing` misses its phase-pinned Normal David rising-special
fixture (`CPU d1 fighter 5 manifests its special`). Its fixed launch/spacing
must be retimed for the new policy. Older anti-air/KO phases likewise cannot be
assumed to survive a policy change. Shared helper code and suite reports remain
the parent's integration responsibility; this feature's reaction evidence uses
remeasured actual controller fixtures.
Super selection belongs at the documented API hook. Native live cadence needs
another combined check as the other features add work.

Human gameplay/balance review remains necessary. Original hardware support,
likeness/consent and public-use approval remain outside this feature's proof.
