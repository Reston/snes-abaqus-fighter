# v0.6 profile and opponent review

This is a source-based envelope review of `characters.h` and `game.c`, not a
matchup simulation or human balance verdict. Normal/throw damage below includes
the current `power[id]-2` adjustment. Normal contact reach includes the shared
10-pixel body half-width. Timing units are live simulation ticks; movement uses
12.4 fixed-point units.

| Property | Roster envelope |
| --- | --- |
| Normal startup / recovery | 2-12 / 7-26 ticks |
| Normal damage / total duration | 5-25 HP / 12-44 ticks |
| Normal contact reach | 35-71 pixels |
| Special startup / active / recovery | 4-15 / 1-8 / 18-29 ticks |
| Special damage / raw reach | 16-25 HP / 19-40 pixels |
| Throw range / damage | 24-36 pixels / 17-29 HP |
| Forward / backward speed | 16-26 / 11-18 fixed units per tick |
| Jump arc | Approximately 30-46 ticks, 39-63 pixel apex |
| Meter | 64 initial, 96 maximum, 32 special cost, +1 per 16 ticks, +8 real hit |

David's light punch has the highest raw damage per full action cycle (10 HP in
14 ticks, 39-pixel contact reach). Negger has strong raw damage (13 HP light
punch, 25 HP heavy kick, 29 HP throw). Lars's heavy kick reaches 71 pixels with
20 HP damage; his 25 HP groundwave starts at tick 15. Mamariaga trades damage
for speed (5 HP light punch, 14 HP heavy kick, 17 HP throw). Reston has the
shortest jump. These are intended-looking archetype differences that still
need scripted all-pair probes and human review.

The review found a correctness defect: back input could guard during a real hit
reaction. The v0.6 fix permits guarding only when free or already in guard stun;
real hitstun cannot break a true combo by holding back.

## Opponent findings in v0.6.0

The v0.6.0 CPU is a deterministic distance/random policy. The review identified
these concrete limitations:

- Special selection beyond 95 pixels suits waves, but rushes travel only about
  39 pixels and rising strikes have no horizontal movement. Use family-specific
  engagement distances and active-window decisions.
- Groundwaves currently provoke standing back guard. Add low-wave defense.
- The CPU supplies no commands during wake, giving every recovery the same
  passive outcome. Add bounded, difficulty-dependent wake decisions.
- The 29-46 pixel spacing interval often produces neutral waiting or whiffs.
  Validate approach, retreat and attack choices at both range boundaries.

Keep Training passive and resettable. Require deterministic controller probes,
profile-envelope checks and human sessions before treating CPU or roster
balance as complete; see [PUBLIC-RELEASE.md](PUBLIC-RELEASE.md).

## Verified v0.6.1 correction

The bounded policy update keeps the profile values and deterministic PRNG. It
checks approaching waves within 96 pixels of the CPU before ordinary attack
guarding. Normal and Hard hold crouch guard for low waves; Easy remains
fallible. A passed wave no longer keeps the CPU pinned in guard.

Special decisions retain their 97-tick opportunity cadence, require a free,
grounded fighter with sufficient meter, and use separate engagement bands:

- Projectile and groundwave: greater than 95 pixels.
- Rush: 45 pixels through `min(90, reach + 10 + (speed * active >> 4))`.
- Rising: within `reach + 10` against an airborne or active opponent.

The attack-window prediction uses the upcoming simulation tick because input
capture runs before action clocks advance. Normal and Hard send one jump edge
at wake tick zero; all other down-state ticks remain input-inert. Free fighters
advance through the former 29-46 pixel spacing gap and use their profile's throw
range. Crouch guard retains crouched art during blockstun.

Native verification includes a three-difficulty/four-family controller matrix,
special-range and approach probes, low-wave guard/chip and wake checks, and all
four canonical suites on one ROM hash. See [RELEASE-v0.6.1.md](RELEASE-v0.6.1.md)
for the evidence. These corrections do not provide a complete strategic
opponent: anti-air anticipation, recovery punishes, varied wake and throw
defense, all-pair matchup sweeps and human balance review remain future work.
