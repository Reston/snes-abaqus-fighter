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

## Next opponent-quality milestone

The current CPU is a deterministic distance/random policy. Concrete limitations
remain before a public candidate:

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
