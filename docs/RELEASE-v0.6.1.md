# v0.6.1 - CPU spacing and defensive decisions

This development update addresses the concrete opponent-policy defects recorded
in [BALANCE-AUDIT-v0.6.md](BALANCE-AUDIT-v0.6.md), preserving the v0.6.0 roster,
animation, input, contact and recovery contracts.

The CPU uses family-specific special ranges, approaching low-wave defense
before ordinary attack guarding, a deterministic wake input at the start of
the wake window, and approach through the old spacing dead zone. Throws use
the fighter's profile range. Normal attack defense predicts the upcoming
contact tick because input capture precedes the action-clock update.

Normal and Hard crouch-guard approaching low waves and buffer one wake-up jump;
Easy retains fallible low-wave reactions and neutral wake. Crouch guard also
keeps crouched art through blockstun, matching the body's contact height.
Training remains passive. No fighter profile values, native asset pixels,
trace offsets or animation-bank layouts change.

The broader CPU cadence probe exposed a knockout-frame budget spike. Round
damage, winner and timer resolve immediately; banner/name/HUD construction
now runs on the following frozen round-end tick. This preserves the final
contact tick's native frame budget without changing combat outcomes.

## Verification

The canonical silent `Test.cmd` batch passes on the 4,194,304-byte ROM:

`945540153834953a1da1c3dd401ef203443da55aee37d916289a8a6c0c93aeee`

Regenerating all assets and rebuilding with `Build.cmd --assets` after the
canonical batch reproduced this exact cartridge hash.

| Suite | Passing checks |
| --- | ---: |
| Gameplay and progression | 2,595 |
| Characters and animation | 18,085 |
| Presentation | 215 |
| Input, CPU, recovery, audio and cadence | 854 |
| Total | 21,749 |

The CPU matrix covers four special-family representatives at three difficulty
levels, with 600 live ticks per case (7,200 total). A fixture restarts after an
actual knockout when more live ticks are required. Every counted native step
must advance by one; there is no lookahead exclusion for a stalled contact.
Separate probes cover special manifestations and forbidden far starts,
mid-range approach, low-wave chip/guard posture and wake buffering. The prior
roster, input, guard, throw, ladder and two-controller regressions remain.

A separate pinned bsnes2014 Accuracy host also passes on this exact ROM: four
distinct nonblank screens, controller movement/jump, captured PCM, and 600
consecutive neutral frame deltas of one. Its scope and source/core hashes are
recorded in [COMPATIBILITY.md](COMPATIBILITY.md). The core is a test prerequisite
and is not bundled in the player ZIP. This smoke test does not substitute for
full combat/roster coverage on a second engine or longer endurance runs.

The offline Windows package passes 202 technical audit checks. It includes
the tested ROM, Snes9x and control defaults, the four native reports and scoped
compatibility evidence, guides and licenses. ZIP metadata is fixed so repeated
packaging of identical inputs produces identical archive bytes.

Strategic CPU variety, all-pair balance probes, human play/listening review,
endurance, controller/hardware results and public-use approval remain open in
[PUBLIC-RELEASE.md](PUBLIC-RELEASE.md).
