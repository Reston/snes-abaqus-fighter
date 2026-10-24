# v0.26 native polish contract

This candidate builds on v0.25's slower profiles and detailed floors. Main
remains approved v0.24; the current PR stack awaits a combined playtest.

## Preservation

`tools/v026_contracts.py` independently compares generated/source bytes with
v0.25 commit `7ba40c106000b2b2eb916f6b35d47065334dd4c7`. Of 226 generated
files, 221 remain exact. Only four derived arena outputs and their size header
change. All fighter frames, portraits, palettes, scale, stage payloads and
audio assets remain exact. The inherited v0.25 check also recomputes stage
conversion and protects earlier art/provenance, the 1,318 RAM labels and banks.

Standing/air physics, damage/reach, normal/special/super timings, ordinary CPU
policy, contact geometry and native assembly remain. The practice-only manual
input/guard branches are checked explicitly. Feedback state uses the existing
banner classifier; startup-counter Fighter flags and damage remain unchanged.

## Existing state and transfer ownership

The historical sixteen-byte stage reservation keeps its addresses. Its ten
table bytes now have these owners:

| Bytes | Owner |
| --- | --- |
| 0 | Scenery enabled |
| 1–2 | Menu hold/repeat |
| 3 | Paused normal-timing view |
| 4–6 | Training session-best hits/damage |
| 7–8 | Local session match wins |
| 9 | Still-background preference |

No byte is a live HDMA table. Scene changes clear transient menu/view state;
new Training selection clears its best, new fighter selection clears local
session wins, and a cold boot restores background motion. Still affects only
BG1 scroll publication. Existing actor positions, impact shake state and clocks
continue normally.

The actor budget remains one 3,840-byte upload per frame. HUD, banner, guide
and Training footer use their existing ranges. Drill reset and guide building
occupy separate frames. Best-combo formatting runs in the deferred UI/reset
path; contact resolution gains no formatting work. BG1 scenery/ground keeps
word gfx `$0000..$37FF`, map `$3800..$3FFF`, with BG3 and live stage DMA off.

## Evidence

`candidate_sources.snapshot` binds all C/assembly and tool Python/PowerShell
sources plus Build/Test/Play entry commands. The current six-suite runner
records their actual command exit, exact report hashes/counts and unchanged
cartridge/core identity. Each focused producer attaches its fixed media
inventory; the collator verifies current bytes, coverage and source freeze.

The retained simultaneous-special producer supplies 432 strict native cases.
Current callbacks are never collapsed. This candidate health proof does not
claim baseline byte equivalence. Separate feedback/throw and motion proofs
retain their explicit unmasked Snes9x comparisons. Accuracy byte equivalence
is unclaimed.

Fresh export, matching pinned Accuracy smoke, both interpreter-mode authoring
and host guards, focused pacing/supers/CPU/stage proofs and the complete new
polish proofs must pass before final verification. Stage suite/focused coverage
shares one execution, counted once. No new offline package or human approval
is implied by these technical checks.
