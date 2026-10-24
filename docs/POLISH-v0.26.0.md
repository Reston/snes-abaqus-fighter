# v0.26 play-flow polish

This candidate stacks on the unmerged v0.25 pacing/floor candidate in
[PR #21](https://github.com/Reston/snes-abaqus-fighter/pull/21). It retains that
slower fight rhythm, detailed floors and approved fighter art. Main remains
v0.24.0. These are focused work checkpoints; final combined verification and
human playtest are pending.

## Pass 1: local match results

Local result cards identify the winning controller as **PLAYER 1 WINS** or
**PLAYER 2 WINS**, so a mirror match is unambiguous. Either player can press
A/Start for a rematch or B for character select. Start, then B, then A owns a
simultaneous sample across both participating pads. Rematches preserve the
fighters and arena and reset both scores. Other modes retain their ownership.

The controller-only focused proof earns twenty real two-round victories and
checks ten routes for each winning side. Both mirror-match winner cards are
checked against native glyph/score pixels. The first checkpoint passed 141
focused checks and 1,752 presentation checks. Reports are regenerated after
the final source freeze; checkpoint captures are under
[screenshots/play-flow-v026](screenshots/play-flow-v026/result-p2-mirror.png).

No new art, global RAM, fighter state fields or native transfer ranges are
introduced. The v0.25 preservation/bank/asset check passes on this checkpoint.

## Pass 2: quick Training retries

Choosing a drill now supplies its required dummy: CPU for low-block practice,
Stand for normal-to-special links and rear air kicks. CPU difficulty remains
the player's choice. The ordinary PAUSED card can still override the dummy.

On Training Tools 3/3, **X restarts the selected drill** while keeping the guide
open. It restores positions, health and energy, clears recorded progress and
input history, and retains the fighter choices, arena, drill and difficulty.
Start/B/A/Select retain priority. X on other pause pages has no reset action.

The first focused checkpoint passes 72 drill/port/fighter combinations and
556 checks across all twelve fighters, with 5,088 measured native callbacks
and zero cadence, OBJ or audio failures. Reset work and guide construction
run on separate frames after an initial prototype exposed a one-frame stall;
the failed prototype report remains under ignored build diagnostics.
