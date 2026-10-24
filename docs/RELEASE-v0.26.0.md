# v0.26 play-flow polish candidate
<!-- candidate-version: 0.26.0; identity: IN_PROGRESS; rom-sha256: PENDING_FINAL_VERIFICATION; source-freeze: PENDING_FINAL_VERIFICATION -->

This candidate builds on the slower movement, attack commitments, CPU pressure
and detailed floors from [v0.25](RELEASE-v0.25.0.md). Main remains the approved
v0.24 revision. [PR #22](https://github.com/Reston/snes-abaqus-fighter/pull/22)
stacks on the unmerged [PR #21](https://github.com/Reston/snes-abaqus-fighter/pull/21).
Combined verification and human playtest are pending while polish continues.

The eight-pass checkpoint passes **49,640 checks across all six native
suites** on ROM `e349b756fac379766501de87f7b58f9d45f924c439afbecb6e3099173f1d33d4`.
Later work will receive a new final frozen-ROM verification record; this
checkpoint does not certify untested follow-up edits.

Run [Play.cmd](../Play.cmd) from this checkout. Read **V0.26.0** on the title.
Keyboard/controller mappings are in the [player guide](PLAYER-GUIDE.md).

## What changed

- Local results identify the winning player even in mirror matches. Either
  pad can rematch or return to character select.
- Either pad can choose and confirm the Local Versus arena. Opposing
  directions cancel across controllers; Start, then B, then A wins a conflict.
- Arena thumbnails show the current stage scenery rather than older pictures.
- A full super gauge shows **SUPER Y+B** under that player's bars.
- **PUNISH!** identifies a hit that catches attack recovery, with unchanged
  damage/stun. Startup hits keep the existing **COUNTER!** meaning.
- Training drills supply their required Stand/CPU partner. **X** on Training
  Tools 3/3 restarts the drill while keeping its guide open.
- **X** on Training's ordinary PAUSED card enables **P2 Controller** practice;
  X again returns to Stand. Existing automated dummy choices remain.
- Arcade shows your **SHIFT 01/11** ladder position, previews the next/retry
  opponent and names CPU difficulty on pause.

The [pass notes](POLISH-v0.26.0.md) separate individual checkpoints from the
final combined result. No new offline archive or public-use approval is claimed.

## Quick review

1. Play a mirror match. Check the winning port on its result card; use P2 to
   rematch and select the next arena.
2. Let the thin energy bar fill. Use a fresh neutral Y+B chord, then check
   that its cue clears. Full meter still requires being grounded and free to act.
3. Open Training Tools 3/3. Choose a drill, restart with X and resume. Check
   that the guide, drill and CPU level stay useful for another attempt.
4. On ordinary PAUSED, choose P2 Controller with X. Practice real hit/block
   exchanges with both pads, then return to Stand with X.
5. Play Arcade. Check its progress and opponent preview, including Continue
   after a loss. Compare the retained slower pacing with your earlier feedback.
