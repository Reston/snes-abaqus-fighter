# v0.24 isolated pacing / recoil workstream

This feature targets `integration/readable-combat-v024`, from contract commit
`3f51120`, on approved main `f75005d`. It is an isolated native SNES candidate
for the parent's combined human playtest. The game version remains unchanged;
the parent owns final versioning, shared preservation policy and combined gates.

## Behavior

Walking and retreat use 82% of their previous fixed-point speeds, rounded to
the nearest sixteenth pixel. Ordinary projectile / ground-wave speed uses the
same ratio; longer lifetime preserves nominal speed × lifetime travel within
one slower step. Screen bounds still expire off-screen waves normally.
Direct rush speed is unchanged. Its three added startup ticks are stationary,
so its total travel remains exactly the previous distance.

Ground strong punch, strong kick and sweep gain three startup ticks and four
recovery ticks. Ordinary specials gain three startup and five recovery ticks.
Jabs, light kicks, legacy action 2, active windows, damage, reach, throws and
all roster identities remain. Confirmed Y→X / B→A and ordinary paid-special
cancels retain their existing command and hit-confirm requirements. Blocked
attacks cannot use those confirms; strong attacks remain punishable.

Air heavy startup/recovery and horizontal jump launch keep their previous
values independently of the slower ground movement. All twelve `jumpVy`,
`gravity`, `uppercutVy` and `specialVy` values remain byte-for-byte unchanged.
Super profiles, commands, energy, pulse counts and gameplay are unchanged.
Early direct-super pulses use a short easing profile to retain follow-up
range; the finisher retains strong recoil. Their existing strong presentation
and hitstop remain. Linked guards retain their prior one-pixel impulse until
the finisher so stationary rising sequences keep their full block sequence.
The first roster prototype exposed a missed Cristobal
finisher; it was corrected in recoil classification rather than changing super
damage, reach, movement or pulse timing.

Hit feedback uses an initial two-pixel light / four-pixel strong / one-pixel
guard impulse. Live hurt drift eases in descending steps according to the
existing remaining stun. Strong drift doubles light drift; guard drift is
smaller. Damian's measured isolated sample is:

| Measurement | Approved baseline | Isolated candidate |
| --- | ---: | ---: |
| Walk, pixels/native tick | 1.25 | 1 |
| Retreat, pixels/native tick | 0.875 | 0.6875 |
| Ordinary projectile, pixels/native tick | 2.8125 | 2.3125 |
| Ordinary projectile lifetime, ticks | 100 | 122 |
| Strong-punch startup / recovery | 9 / 18 | 12 / 22 |
| Light hit total recoil, pixels | 9.875 | 10 |
| Strong hit total recoil, pixels | 11.5625 | 26 |
| Guard total recoil, pixels | 1 | 3.875 |

Light live drift descends 16→12→8→4 in 12.4 units; strong uses
32→24→16→8. Guard uses 8→6→4. Damage-dependent stun length remains
`12 + floor(damage / 3)` for all 256 byte inputs. Hitstop stays 4 / 6 / 3
for light / strong / guard. Match/menu/audio/video clocks are not slowed.

Both directions are snapshotted before either contact in a trade resolves.
Coincident centers retain each attack's facing as the symmetric fallback.
Every hit and block latches its contact side, including rear air kicks.
Released projectiles retain their own travel direction if their owner turns;
delayed throw damage uses the victim's launch direction. Reactions clamp at
the ordinary walls, end with existing stun and add no invulnerability or new
stun timer. Repeated corner jabs can be guarded.

CPU new-guard opportunities sample every 12 / 8 / 4 ticks at Easy / Normal /
Hard; an already-held back input can continue guarding a visible threat.
Attack defense reads the current attack clock rather than tick+1. Recovery
counters sample every 18 / 12 / 8 ticks, Normal/Hard anti-air every 12 / 8,
and the individual ordinary attack tempos gain three ticks. Existing fallible
chances, personalities and legal input paths remain. No opponent pad or
future outcome is read.

## Native ownership and integration boundaries

- Production files: `src/characters.h` pacing fields, `src/cpu_personality.h`,
  new `src/pacing_recoil.h` and narrow `src/game.c` hooks only.
- `rearKickRecoil` at `$7E2977` reuses its existing byte. Low nibble is P1,
  high nibble P2; each stores direction 1=left / 2=right in bits0–1 and
  strong=bit2 / direct-super-link=bit3. No mutable bytes are appended. All 1,318 prior RAM labels,
  including metadata/SDK labels, retain addresses. No new RAM symbols exist.
- `fighters=$7E2000`, `waves=$7E2080`; Fighter64 / Wave16 / TRACE0..122,
  `hardware.asm`, `trace.asm`, `knockdown.h`, `super_moves.h` and version stay
  exact. Native `applyHitReaction` and its entire damage→stun lookup are audited
  without assembly changes.
- No generated-asset delta: all 219 files retain exact contract-baseline
  bytes. No fighter frames, walking20–27, idle16–19, portraits, palette, source
  art, stage, audio or masters change. No art generation is needed here.
- No OBJ, CGRAM, HDMA, VRAM, audio or DMA allocation is added. Existing
  30-OBJ actors, one 3,840-byte actor upload per vblank, row padding and
  4 MiB / 128-bank FastROM LoROM mapping remain.
- Contact owner: reconcile `hurtWithRecoil`, `hurt`, `updateFighter` and the
  pre-resolution `rear0/rear1` snapshots in `combat`. Keep the new contact-side
  snapshot and pass only the rear boolean to `trainingMoveContact`; changing
  contact geometry does not require changing recoil masks or ABI.
  Parent coordination: contact PR #15 is already merged into the integration
  branch at `066e7b6`. Preserve its pose-derived `canHit`, `verticalContact`
  and wave-defender contact hooks, plus the root build refresh. This isolated
  proof deliberately remains on contract base `3f51120`; final combined
  contact/pacing behavior must be retested by the parent.
- Jump owner: reconcile `attackStart`'s air-heavy timing restoration and
  `controls`' `pacingAirSpeed` call. The latter deliberately preserves original
  horizontal launch rather than inheriting the reduced walk speed. Any new
  approved arc should replace that call explicitly. Character jump fields
  were not changed by this branch.
  Parent coordination: jump PR #18 at `15f3c58` changes only Ivo1 -84→-96,
  Negger4 -82→-86, Fernando6 -80→-86 and Reston9 -84→-105 for standing
  clearance; gravity / uppercutVy / specialVy remain. Parent merges those
  columns alongside this branch's pacing values. PR #18 uses takeoff velocity
  `walkSpeed+8`, so reconcile the baseline-preserving helper deliberately and
  rerun all twelve cross-arcs and cross-ups with combined slower walking.
  Active airborne drawings remain frames50/53.
- Attack/super art owners retain `animation_weight.h` / `superFrame` ownership.
  Pacing changes no pose selection or super drawing.

## Reproduction and evidence

Use the canonical project-local Python and `tools/run_background.py`. The
native host opens no GUI or audio device, never writes emulated memory, and
uses no save states. The pinned Snes9x DLL must hash to
`f00db5bd97bbe0e80761e590449eb14716bd9ab5785a1b50725c55e10505c343`.

Build with `tools/build.py`, then run:

```powershell
$pacingPython = (Resolve-Path .tools/python/python.exe).Path
& $pacingPython tools/run_background.py --log build/pacing-all.log -- $pacingPython tools/test_combat_24_pacing.py
```

The final measurement runs disjoint roster halves in two independent headless
processes, both bound to the same frozen source, harness, core and exact ROM:
`--fighters 0,1,2,3,4,5 --report build/pacing-a.json` and
`--fighters 6,7,8,9,10,11 --report build/pacing-b.json`, using the same background
launcher with separate logs. The committed report lists both exact commands,
component report hashes and durations. No other feature ROM or shared-suite
results are pooled. The single default command above reproduces all cases
sequentially.

The focused driver owns `docs/combat-24-pacing-report.json` and screenshots
under `docs/screenshots/combat-24-pacing/`. It records exact cartridge/symbol
hashes, source commit and hashes, harness/dependency hashes, command, host,
core, native failure arrays and representative assertions with execution counts.
It checks all twelve fighters and both ports for movement, projectile steps,
special timing/rush range, normal reach/timing, confirms, blocking/punishing,
corner escape, front/rear/trade recoil, KO, super chord eligibility and every
super pulse/block/interrupt. Each CPU runs 1,800 ticks at all three levels;
Hard repeats with noisy P2 input and compares full native trace/video hashes.
Fresh paired boots check no input lookahead. Per-fighter clock/DMA samples
check 120 live ticks and 60 paused ticks, both actor VRAM regions, row padding,
native pose bytes and one actor per vblank. Audio callbacks continue every
observed Rig tick; all combat paths check native cadence and OBJ overflow.

Damian's small samples were prototyped before roster testing; the final after
captures are refreshed on the tested cartridge. The ignored
`build/pacing-before.json` / `build/pacing-after.json` identify each exact ROM
and command; `--sample before --baseline` uses retained baseline ROM/symbols
under `build/pacing-baseline.*`. `--sample after` uses the freshly built ROM.
These GIFs retain native frame order; GIF time quantization is approximate:

- [Before strong contact](screenshots/combat-24-pacing/damian-before-strong.gif)
- [After strong contact](screenshots/combat-24-pacing/damian-after-strong.gif)
- [Before light contact](screenshots/combat-24-pacing/damian-before-light.gif)
- [After light contact](screenshots/combat-24-pacing/damian-after-light.gif)
- [Before guard](screenshots/combat-24-pacing/damian-before-guard.gif)
- [After guard](screenshots/combat-24-pacing/damian-after-guard.gif)

## Parent fixture updates to assess honestly

The shared suites and historical focused drivers are not edited here. Parent
must regenerate them against final combined art and cartridge. Known static
expectations / scheduling assumptions that require reassessment include:

- `tools/test_inputs.py::_cross_up_contact_case`: old 32-unit strong initial
  recoil, constant nine-unit drift, derived spark positions and equal ground /
  air A startup. The new focused driver independently brackets pre-impulse
  rear reach and exercises simultaneous rear trades with real controller timing.
- `tools/test_expansion_03_normal_balance.py::air_crossup`: its old post-impulse
  28-pixel cap now includes a four-pixel impulse. Its preservation helper also
  explicitly forbids the authorized movement / heavy / special revisions.
- CPU jump-in, wave-guard and recovery fixtures in `tools/test_inputs.py` and
  `tools/test_expansion_06_cpu_personality.py`: their fixed title delays and
  six/ten-tick anti-air / five/nine/fourteen-tick counter schedules are historical.
- Walking-duration, command-cancel deadline, real rear-contact, special-spacing
  and Training CPU/low-wave fixtures may need controller timing changes for
  slower ground movement and sampled defense. Preserve contact, eligibility,
  escape, legal-input, no-lookahead and unit-cadence assertions.
  Reston's low arc specifically requires committing air-kick startup before
  crossing at the slower ground chase speed; the focused fixture records
  this controller timing and still requires an actual rear contact inside
  the unchanged 26-pixel pre-impulse center cutoff.

This work does not claim any combined six-suite count, combined art/contact
approval, main merge, release certification or hardware/controller validation.
The parent must freeze combined source and regenerate every exact-ROM gate.
Stage PR #16 and super-art PR #17 are already integrated by the parent.
The parent reported two repeated TRACE frames during simultaneous combined
supers and a David finisher miss in an old 28-pixel contact fixture; a separate
contact optimization/trace worker owns those combined defects. This branch
does not enlarge contact reach or add invisible contact halos to address them.

## Isolated result

Source/harness freeze `9ff7011bff6e0b9a75de253407c8db2e7bfe3a2c` passed the all-twelve,
both-port focused run on cartridge SHA256
`1b38d1631453c6a90664454932a21a9387981af31e98b9acfc5eb6cc893e353d`. The run executed 238,765 focused
assertions across 1,836 distinct invariant labels in
974.141 seconds (the maximum of two concurrent disjoint
roster partitions on this exact source/harness/ROM; both commands and durations
are recorded). All failure arrays are empty. No results from other feature
cartridges or the six shared suites are included.
Native observations include 98,058 Rig callbacks,
26,160 super callbacks and 86,400 CPU encounter
callbacks (three difficulties plus each Hard noisy-P2 repeat).

All 219 generated assets and all 1,318 prior RAM labels remain exact; no new
RAM labels or mutable bytes exist. Retained local candidate ROM/symbols are
under ignored `build/v024-pacing-candidate.*`; tracked `dist` outputs are
restored to baseline before handoff. The committed report binds the exact
source/harness/core/host and records the small before/after Damian captures.
These are isolated pacing results and do not certify the combined ROM.
