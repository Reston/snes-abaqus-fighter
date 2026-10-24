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
