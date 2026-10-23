# Expansion 03: four-button normal balance

This isolated feature starts at integration commit
`610537d3da8f7005c28ea31d0a45a7c17f8f7ba8`. It changes the four normal roles
for all twelve fighters. The combined v0.22.0 integration, shared suites and
release status belong to the parent.

## Behavior and rationale

- **Y: quick light punch.** Startup is 2–5 native ticks, with 7–9 recovery
  ticks. It is the shortest normal and deals the least damage. First-active
  contact is −2 to −4 on block: fast close jabs can punish the slower
  recoveries, so pressing Y still calls for a spacing decision.
  A real hit still confirms into X or a paid special;
  a whiff or guarded contact never enables a cancel.
- **X: committed strong punch.** This is the highest-damage normal, with
  four active ticks and 14–23 recovery ticks. It reaches beyond the jab but
  less far than either kick. Every fighter's close blocked strong punch is
  punishable with the opponent's ordinary jab. Its existing restriction on
  cancelling to a special remains, so a confirmed Y→X is a commitment.
- **B: low/spacing light kick.** It starts one or two ticks after the jab,
  reaches beyond the strong punch and recovers in 7–9 ticks. First-active
  contact is −2 to −4 on block. The slow versions can be punished by
  Mamariaga's two-tick jab at close range; the same response whiffs after a
  tip-range blocked kick. Down+B retains the existing low property, beating
  high guard while remaining crouch-blockable, with no sweep knockdown.
- **A: strong kick and airborne cross-up.** This is the longest normal,
  with five active ticks and damage between the light kick and strong punch.
  Its original startup is retained to preserve each fighter's jump timing.
  Recovery is longer than in v0.21; a close blocked kick is jab-punishable.
  B→A remains a true confirmed chain. Only airborne action 5 retains the
  original short rear contact box; air strong punch still whiffs behind its
  facing. The rear box, recoil direction and landing behavior are unchanged.

The hierarchy is the same for every fighter: jab < light kick < strong kick
< strong punch in damage, and jab < strong punch < light kick < strong kick
in front reach. Individual speed, power, jump, movement and reach identities
remain; the roster is not flattened to one frame-data set. Strong-punch damage
rises by one profile point. Strong-kick damage rises by one to three points,
with longer recovery paying for that reward. Jab/light-kick damage is unchanged.

Jab total duration is matched to the unchanged native hitstun of its damage
(`12 + floor(damage / 3)` ticks). This leaves the earliest repeated jab
blockable when the defender holds back, including at the wall where recoil
cannot create distance. Three immediate corner follow-ups are checked for
every fighter on both ports. A deliberate Y→X confirm earns the combo instead
of obtaining an unbroken hit loop by repeating Y.

No cancel-policy code changes are needed: the existing real-hit gate already
supports Y→X, B→A and light-to-special confirms. The focused proof checks actual
two-hit continuity while the defender holds back. A confirmed special command
is tested for its real energy cost; it is not asserted to be a gapless combo
for every special family.

## Native data and measured results

Candidate ROM SHA256: `5a3403b08550799411a531a359e0a8f0adb342759a5f7a1ae1c63380616acd11`; native header checksum `BF3E`.

The full focused run passes **3,782 assertions** across all 24 fighter/port cases
in 244.469 seconds. All 54,713 observed gameplay callbacks advance
exactly one native frame. PPU overflow observations are empty; the sampled
resident-SPC backlog peaks at 0. These are focused results, not the six shared suites.

Each move cell is **startup/active/recovery; damage; front reach**. Startup
is the first contact tick; the active interval is `[startup, startup+active)`
and the action clears at `startup+active+recovery`. Timings exclude hitstop.
Damage is native unopposed HP loss including the fighter power adjustment,
with no counter bonus. Reach is the authored front reach in native pixels;
the controller proof brackets the actual center cutoff at reach + 10.
These P1 measurements match the P2 timing/damage/range measurements exactly.

| Fighter | Y: jab | X: strong punch | B: light kick | A: strong kick |
| --- | --- | --- | --- | --- |
| Damian | 4/3/7; 8; 26 | 9/4/18; 17; 38 | 5/3/7; 9; 42 | 7/5/17; 15; 46 |
| Ivo | 4/3/8; 9; 28 | 10/4/20; 19; 43 | 6/3/8; 10; 46 | 8/5/19; 17; 50 |
| Cristobal | 3/3/8; 6; 24 | 8/4/16; 14; 36 | 4/3/8; 7; 39 | 6/5/15; 12; 44 |
| Cote | 4/3/8; 10; 28 | 10/4/21; 20; 42 | 6/3/8; 11; 45 | 8/5/20; 18; 49 |
| Negger | 5/3/8; 13; 30 | 11/4/23; 24; 48 | 7/3/9; 14; 49 | 9/5/22; 21; 53 |
| David | 3/3/9; 10; 27 | 8/4/17; 19; 40 | 4/3/9; 11; 43 | 6/5/16; 17; 47 |
| Fernando | 5/3/7; 10; 29 | 11/4/22; 21; 45 | 7/3/9; 11; 47 | 9/5/21; 18; 51 |
| Cristian | 4/3/8; 9; 31 | 10/4/20; 18; 46 | 6/3/8; 10; 49 | 8/5/19; 16; 54 |
| Mamariaga | 2/3/8; 5; 23 | 7/4/14; 13; 34 | 3/3/8; 6; 37 | 5/5/14; 11; 42 |
| Reston | 5/3/7; 11; 30 | 10/4/21; 21; 47 | 7/3/8; 12; 49 | 9/5/20; 19; 56 |
| Roxana | 3/3/8; 7; 27 | 8/4/16; 16; 41 | 4/3/8; 8; 44 | 6/5/15; 14; 48 |
| Lars | 4/3/8; 10; 33 | 9/4/18; 20; 55 | 5/3/8; 11; 56 | 7/5/17; 18; 61 |

Block advantage below is measured after first-active contact: defender
recovery time minus attacker recovery time. Negative values mean the
defender recovers first. Late active contact can improve these figures.
The last two columns give measured damage of the real two-hit confirms
against held back. Both combos remain real hits, not guard strings.

| Fighter | Y block | X block | B block | A block | Y-X damage | B-A damage |
| --- | --- | --- | --- | --- | --- | --- |
| Damian | -2 | -14 | -2 | -14 | 25 | 24 |
| Ivo | -3 | -16 | -3 | -16 | 28 | 27 |
| Cristobal | -3 | -12 | -3 | -12 | 20 | 19 |
| Cote | -3 | -17 | -3 | -17 | 30 | 29 |
| Negger | -3 | -19 | -4 | -19 | 37 | 35 |
| David | -4 | -13 | -4 | -13 | 29 | 28 |
| Fernando | -2 | -18 | -4 | -18 | 31 | 29 |
| Cristian | -3 | -16 | -3 | -16 | 27 | 26 |
| Mamariaga | -3 | -10 | -3 | -11 | 18 | 17 |
| Reston | -2 | -17 | -3 | -17 | 32 | 31 |
| Roxana | -3 | -12 | -3 | -12 | 23 | 22 |
| Lars | -3 | -14 | -3 | -14 | 30 | 29 |

All 24 cases also block three immediate corner re-jabs after a genuine
first hit. Every strong punch/kick is actually punished by a close mirror
jab after block. Every tip light kick makes the fastest jab whiff.

The symbol audit preserves 1,242 named baseline RAM addresses
and all 219 generated files. Native linked sections occupy
3,267,827 bytes with 23 wholly unallocated ROM banks; every
checked section fits its LoROM bank. `attackActive` remains 110 code bytes
with zero added bytes. After normalizing the title version already changed
by the integration base, only 105 cartridge bytes differ: 99 in the existing
profiles, two active-duration bytes and four checksum bytes.

[Focused JSON evidence](expansion-03-report.json) includes the full per-port
measurements and source/core/cartridge hashes. Native examples:
[Damian rear cross-up](screenshots/expansion-03/00-p1-air-crossup.png) and
[Lars light kick at range](screenshots/expansion-03/11-p1-light_kick-tip.png).

## Focused proof and reproduction

`tools/test_expansion_03_normal_balance.py` boots local versus through the
native menu for every fighter on both physical ports. It uses the actual
Snes9x core with captured video/audio, no window or playback, and no save
states or emulated-memory writes. Controller walking establishes each range
fixture. Read-only native symbols label the timing cache and action tick;
the assertions then exercise real collision, HP, guard, combo, action and
landing behavior. Animation-clock telemetry is deliberately not used as the
action clock, because same-family confirmed chains may retain that clock.

For each fighter/port it exercises all four normals through the complete whiff
timeline and both sides of the front-reach cutoff; measures the first active
contact and damage; measures both recoveries after a blocked hit; attempts a
real immediate jab punish; rejects blocked special cancels; proves Y→X and
B→A against held back; proves Down+B high/low guard distinction; proves A rear
cross-up and X rear whiff; tests close/tip light kicks against Mamariaga;
checks paid jab-to-special and uncancellable strong-punch recovery; and
checks that three immediate corner re-jabs can be guarded after a real hit.

The air fixture uses two genuine controllers: the grounded opponent first
approaches, then follows the jumping fighter. A/X is pressed after crossing,
once the attacker is within the kick's vertical contact band. This gives the
different low/slow and high/fast jump arcs a fair rear-contact opportunity.
The reported rear gap includes the existing two-pixel impact recoil; the
actual collision cutoff remains 26 pixels between centers.

```powershell
& 'D:\snes-abaqus-fighter\.tools\python\python.exe' tools/build.py
& 'D:\snes-abaqus-fighter\.tools\python\python.exe' tools/run_background.py `
  --log build/expansion03/full.log -- `
  'D:\snes-abaqus-fighter\.tools\python\python.exe' `
  tools/test_expansion_03_normal_balance.py
```

The test compares preserved assets and symbols against the pinned Git base,
so it does not require an untracked baseline fixture. Its JSON records the
exact cartridge/core/symbol hashes, host contract, per-port native measurements,
cadence/PPU/SPC observations and each assertion. The committed native screenshots
show Damian/Lars hitting at each normal's tip and Damian's two mirrored rear
cross-ups. They are focused cartridge captures, not new source art.

## Preservation and integration

The implementation touches only the existing normal arrays in
`src/characters.h` and the two normal active-duration entries in `src/game.c`.
It adds zero mutable bytes, code branches, transfers, tile/palette assets,
sprites, audio payloads or bank sections. Fighter64/Wave16 and TRACE0..122 stay
intact. All 219 generated files are byte-identical to the base, including
approved Damian v5, every fighter bank/palette/portrait, stages and audio.
Hardware assembly, trace assembly and the knockdown/throw implementation are
byte-identical. Movement/jump, throw, special, legacy action-2 and sweep data
remain byte-identical; shoulder controls and input priorities are untouched.
The ROM comparison additionally verifies every byte outside the owned normal
tables and checksum against the base's carried v0.21 cartridge, accounting for
the v0.22 title literal already reserved by the integration branch.

Parent integration needs the current shared suites and independent smoke.
Existing hard-coded historical expectations need reconciliation with this
intentional tuning: in `tools/test_inputs.py`, Damian's A cross-up now deals
15 rather than 13 damage, and X has four active ticks rather than five
(including the grounded rear-whiff helper). Jab recovery and the space/timing
of older scripted pressure fixtures may also need updated controller routes.
No shared tests/reports or version/release documents are changed here.

These measurements establish useful roles and bounded risk/reward in the
tested native cases. Human gameplay/balance review, cross-feature integration,
full release-scale evidence and real-console validation remain separate work.
