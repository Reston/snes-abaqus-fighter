# Abaqus: After Hours - player guide
<!-- candidate-version: 0.23.1; rom-sha256: 057139801b64d1d486c91e18f456e01519dd4d25c3d0d6a92e61f311b99da3fd -->

## Approved main walking revision: v0.23.1

The user rejected v0.23.0's torso/legs mismatch. PR #12 now replaces each
fighter's eight complete walking poses with coordinated head, guard, torso,
hip and foot motion, removing the fixed waist splice. Other 56 poses and
original portraits/palettes remain. All six suites pass 36,219 current-ROM
checks, matching independent smoke and fresh reproduction pass. The user
approved the revision and PR #12 merge on 2026-10-23 ("yes good, merge it").
Run `Play.cmd` from main to play v0.23.1.
[Current art, native clips, controls and evidence](RELEASE-v0.23.1.md). Main is
v0.23.1; 08 remains deferred. The notes below retain their historical scope.

## Rejected historical walking candidate: v0.23.0

Main is v0.22.1 with the nine approved improvements merged; feature 08 remains
deferred and its checkout is retained. The old merged branches/worktrees are
cleaned. [PR #12](https://github.com/Reston/snes-abaqus-fighter/pull/12) adds
eight-phase walking to all twelve fighters and the clearer **LOCAL 1V1 / 2P**
menu label. Local two-port multiplayer was already supported. Run `Play.cmd`
from `feature/walking-cycles-v023` to test this unmerged candidate.
All six native suites pass 36,219 current-ROM checks; independent smoke,
all-roster walking proof and fresh-source reproduction pass.
[Walking, two-player controls, art/prompts and evidence](RELEASE-v0.23.0.md).
The older notes below retain their historical scope.

## Current v0.22.1: nine approved improvements

Features 01–07, 09 and 10 are approved for main. **Feature 08 is deferred**:
the camera and ambient art are restored to v0.21.0; its branch/worktree remain
for polish. The six native suites pass 36,253 exact-ROM checks and matching
independent smoke passes. [Current release and scope](RELEASE-v0.22.1.md).
Local 1v1 already works in **Local Versus** with separate controller ports.
Walking improvements and clearer local-play discovery are the next follow-ups.
The v0.22.0 material below is historical, including its ten-feature review gallery.

## Historical v0.22.0 combined notes

This guide describes all ten improvements together on
`integration/ten-improvements-v022`. Run the root [Play.cmd](../Play.cmd) from
that checkout to play in Snes9x; on other platforms open
`dist/abaqus-after-hours.sfc` in a SNES emulator. Main remains v0.21.0 pending
your combined playtest and [final PR #1](https://github.com/Reston/snes-abaqus-fighter/pull/1).
The title's lower-right version label identifies your game. Combined native
verification passes; no v0.22.0 playtest approval or offline ZIP exists.
The latest full offline archive is v0.19.0, which uses its older six-button
combat layout. See the [combined release guide](RELEASE-v0.22.0.md) for all ten
changes and their feature links.

Focus Snes9x and press **Enter**. **Alt+Enter** toggles fullscreen;
**Input -> Input Configuration** maps controllers. The launcher prepares
pinned local tools on first use, without an administrator account or global
installation. Existing emulator mappings may differ from the defaults below.

## Controls

| SNES input | Included P1 keyboard | Action |
| --- | --- | --- |
| Left / Right | Arrow keys | Walk; hold away from the opponent to guard |
| Up / Down | Up / Down arrows | Jump / crouch; Down+away guards low |
| Y / X | A / S | Light / strong punch |
| B / A | Z / X | Light / strong kick |
| Down+X / toward+X | Down+S / toward+S | Uppercut / close throw |
| Down+A / Down+B | Down+X / Down+Z | Sweep / low light kick |
| Down+Y | Down+A | Quick special, costs 32 energy |
| Down, Down+toward, toward+Y/X | Same directions, then A/S | Motion special, costs 32 energy |
| Fresh neutral Y+B together | Release directions and A/Z, then press A+Z together | Super, costs the full 96 energy |
| Start | Enter | Confirm / pause / resume |
| A / B in menus or pause | X / Z | Confirm or resume / back or return to roster |
| Select | Shift | Cycle pause pages; P1 live Training reset |
| L / R shoulders | D / C | CPU level at home or on Training's CPU PAUSED card |

**P2 defaults:** I/J/K/L move up/left/down/right; numpad 7/8 punch, numpad 1/2
kick, Space is Start, Q is Select and numpad 9/3 are L/R. Enable Num Lock.
The P2 super is fresh neutral numpad 7+1. Shoulders do not attack.
Opposite directions cancel. Menu priority is Start, then B, then A.

## Fighting

- **Y** is the quick close jab. **X** is the heavy punch with committed
  recovery. **B** reaches farther for spacing; Down+B attacks low. **A** is
  the longest normal. Close blocked heavy punches/kicks leave time for a jab
  punish. Each fighter still has individual speed, power and reach.
- Confirm a real **Y hit into X**, or **B into A**. A confirmed light normal
  or strong kick can cancel into a special during its window. A whiff or block
  does not enable a cancel; repeating Y is not an automatic continuous combo.
- For a motion special, press punch with the final toward direction. Each
  progressing step has twelve live ticks; holding away cancels the motion.
  Down+Y is the shortcut. Energy regenerates slowly and real hits add energy.
- For a **super**, release Y and B and all directions, then press both together
  with full meter while grounded and free to act. Wait for your existing
  projectile to finish. Adding a button to a held one or holding the chord
  until meter fills will not activate it. Supers have vulnerable startup and
  punishable recovery; some multi-hit sequences have gaps.
- Hold away to guard, or Down+away against low attacks. Jump-ins can beat low
  guard. Jump past the opponent and press **A** just after crossing for the
  short rear air-kick cross-up; switch guard direction after a crossing.
- Toward+X throws at close range, including through guard; damage lands when
  the defender reaches the floor. Simultaneous throws tech. During the final
  get-up phase, a fresh attack or jump can buffer; enter special motions after
  recovery.

Gold health turns red at one quarter or less; the thin teal bar is energy and
diamond medals count round wins. Win two rounds to take a match. At timeout,
more health wins; a tie restarts without awarding a round. Light hits use small
amber sparks, heavy hits larger gold bursts, and blocks hollow cyan braces.

## Modes and pause

**Arcade Shift:** defeat all eleven other fighters. Each matchup opens with a
short two-speaker exchange: wait about six seconds or press **P1 A** (keyboard
X) to skip into the countdown. Start pauses first. Continue retries the same
opponent after a loss. Individual winner quotes and a personal trophy ending
follow your victories; the original Champion music remains.

**Local Versus:** choose both fighters and an arena for a best-of-three match.
Both physical ports share the four-button layout, specials and super command.

**Training:** choose PLAYER 1, any DUMMY (including a mirror), then an arena.
Either pad can choose the dummy; B backs up to PLAYER 1. Health recovers and
the clock stays at 99. Physical P2 gameplay buttons do not drive the opponent.
Home L/R selects Easy/Normal/Hard. CPU personalities differ in spacing,
pressure, guarding, throws and recovery answers. Normal/Hard can attempt
fallible supers after defense; Easy does not choose supers.

**Start** pauses or resumes from either pad. Without Start, **B** returns to
the roster, **A** resumes and **Select** cycles pages. Start wins even with
Select held. From PAUSED, Training's Select cycle is Controls **1/3**, Move
List **2/3**, Training Tools **3/3**, then PAUSED. Versus and Arcade have the
first two guide pages. Left/Right cycles within the guide pages. Move List
names both fighters' specials and supers.

On Training's ordinary **PAUSED** card, Up/Down selects **Stand, Guard High,
Guard Low, Jump or CPU**. Guards hold position and Jump repeats on landing.
With CPU selected, either pad's L/R changes the shared difficulty once per
press; opposing held shoulders cancel even across pads. These dummy/level
controls stay on the ordinary card.

## Training tools

On **Training Tools 3/3**, **Up** shows/hides the live footer and **Down** chooses
one of three drills:

1. **Normal -> Special:** choose Stand and get close. Hit a normal, then link
   a special while the opponent is still in the same hit-stun chain. Try Y
   then Down+Y; a slower special may need A's longer hit stun. Both attacks
   must hit. `SP!` alone does not complete the drill.
2. **Block a Low Attack:** choose CPU on the ordinary card, then hold
   Down+away against a real low attack. A high block does not count; taking
   damage shows Retry. Select restores space for another attempt.
3. **Air Kick Cross-up:** choose Stand, jump past and press A just after
   crossing. The kick must hit from behind; a front hit or block does not count.

The footer shows five P1 commands, oldest first, as **direction + YXBA**.
Directions use absolute numpad notation: 1/2/3 down, 4/5/6 level, 7/8/9 up.
`6Y---` means Right+Y; `-` marks an unpressed button. Neutral releases leave
useful motion steps visible. History keeps recording while hidden.

`NOW` gives the current combo's hits (`H`) and real HP damage (`D`); `LAST`
retains it after the chain ends. `SP!` means an accepted ordinary special
executed and paid energy, even if it missed. It does not identify a super.
Drills show `READY`, `LINK!`, `DONE!` or `RETRY`. The footer can catch up after
a busy exchange.

**Live P1 Select** resets the round, history, combo totals and drill progress,
keeping both fighters, dummy, difficulty, selected drill and display setting.
A new Training match returns to Stand, a visible footer and the first drill.

## What to try in the combined game

- With Damian and Reston, walk, jump, throw and win a round. Watch planted
  steps, landing/get-up transitions, individual opening gestures and winner poses.
- In Training, compare Y/X/B/A reach and hit/block feedback, confirm Y-to-X
  and B-to-A, and complete a drill using the history and damage display.
- Compare CPUs at the same difficulty, then spend a full gauge on different
  supers. Try blocking and interrupting them as well as landing them.
- Walk together across **Las Condes, El Castillo and La Oficina**. Scenery
  shifts subtly above the fixed floor; a round win triggers ambient cheers.
- Play Arcade with a rival pair such as Damian/Reston. Read or skip the
  exchange, hear Round/Fight/K O, compare light/heavy/guard sounds and listen
  for music ducking and the victory cadence. Finish a ladder for its ending.

All twelve original illustrated fighters, approved Damian likeness, portraits
and costumes are retained. Record the title version, exact cartridge hash and
a repeatable example with feedback. No v0.22.0 human approval is recorded;
gameplay/balance, full listening, physical controllers, likeness/consent and
public-use reviews remain open. `public_release_certified` is false, and
original-console/flash-cartridge support remains unverified.
