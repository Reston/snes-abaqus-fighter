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

## Pass 3: full super-meter cue

A full 96-energy gauge adds **SUPER Y+B** beneath its own health/energy bars.
The gold command cue occupies the existing HUD bottom rule, leaving the mode
label and round medals visible. Spending the gauge restores the rule. The
cue communicates full meter; the existing grounded/free-to-act requirements
still apply. No flashing or new audio is added.

The focused proof naturally regenerates 95 and 96 energy, spends each port's
meter through a real super command, and checks native bar/cue cells for all
twelve fighters. It also checks that both cues can coexist without replacing
the central mode label. Native cadence, OBJ and audio checks remain strict.
The HUD stays within its original 320-byte transfer and uses no new art/RAM.

## Pass 4: shared local arena selection

Either controller can now move, confirm or leave the arena picker in Local
Versus. Its footer says **LOCAL 1V1: EITHER PAD**. Opposing directions cancel
across controllers, and the shared Start/B/A priority matches the result card.
Arcade and Training arena selection keep their existing ownership. The focused
proof checks both ports' routes, simultaneous inputs and those mode boundaries.

## Pass 5: Arcade orientation

The matchup exchange and ordinary result card show **SHIFT 01/11** through
**SHIFT 11/11**. A win previews the next opponent; a loss names the opponent
you will retry. The ordinary Arcade pause card names Easy, Normal or Hard.
Champion artwork, stories, six-second auto-advance, controls and ladder rules
remain intact.

The focused proof earns a complete eleven-opponent ladder, checks the 09/10/11
boundary and wraparound opponent previews, and verifies an actual Hard-mode
loss and Continue. It also proves that P2's new local controls do not advance
Arcade results. The checkpoint passes 89 focused checks plus native text/pixel
and combat-health checks. Scene-load monitoring uses the direct scene byte;
forced-blank result loaders are outside the live combat cadence interval.

## Pass 6: two-person Training

On the ordinary Training PAUSED card, **X selects P2 Controller**. The physical
second controller then drives the opponent using the same movement, four
attack buttons, specials and super as Local Versus, with Training health
recovery and clock behavior. **X returns to Stand**. The original five dummy
choices and Stand-to-CPU Up shortcut remain; manual control is an explicit
toggle rather than an extra stop in that cycle. Up/Down leaves manual mode
for CPU/Stand respectively.

Either pad can enable manual practice. Start/B/A/Select keep priority; P2 live
Select still cannot reset the round. Live P1 Select retains manual control.
Selecting/restarting a prepared drill supplies its intended Stand/CPU partner.
The focused checkpoint passes all twelve fighters' P2 movement, opposing
directions, four normal buttons, ordinary special, naturally funded super,
reset retention and return-to-Stand checks. Default Stand keeps ignoring P2
combat buttons. No new global state or fighter ABI fields are added.

## Pass 7: reward readable defense

An unblocked hit during an opponent's attack recovery displays **PUNISH!**.
The existing **COUNTER!** cue retains its startup-hit meaning and damage bonus.
Punish feedback adds no damage, stun, meter gain or recovery changes. Blocks
and ordinary neutral hits do not advertise a punish. The existing deferred
impact banner carries the cue; no new RAM or transfer range is used.

The full proof passes 120 paired baseline/candidate cases: blocked heavy punch
and kick into real jab retaliation, startup counter, ordinary hit and guard,
for all twelve fighters on both ports. Identical controller streams preserve
every unmasked Fighter/Wave byte, RNG and controller latch. Native glyph/PPU
checks verify the actual feedback; strict cadence, OBJ and audio checks pass.

## Pass 8: arena previews match current stages

The picker previously retained historical cartoon-stage pictures while combat
used the rebuilt scenery. It now derives each 104x52 landmark view from the
current converted native BG1 tiles, map and palette, including the center
viewport's camera gutters. The aspect-correct crop avoids hidden HUD rows.
Names, descriptions, cursor geometry, title/roster plates and fighter portraits
are retained. No new stage artwork is generated or retouched.

The focused proof rebuilds the arena payloads in an isolated sink, checks the
native picker on Snes9x and pinned Accuracy, loads each chosen stage and
independently decodes its uploaded VRAM. All three source viewports match
exactly. Only the four arena outputs and their size declaration change in
this pass; the existing 226-file asset inventory remains.
