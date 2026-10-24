# Abaqus: After Hours - player guide
<!-- candidate-version: 0.24.0; identity: TECHNICALLY_VERIFIED_USER_MERGE_APPROVED; rom-sha256: 408cadfdddef97a24215e40f6ddb366140bc68fc80e7f1de82ee87e4084beb79; source-freeze: a1ee733aea036ad985bca9bdee29cc170cabd2ac -->

The v0.24 combined playtest adds more readable combat, backward hit reactions,
coordinated attack and jump drawings, individual super poses and rebuilt stages.
<!-- v024-player-status:start -->
All six changes are merged into main through PR #14 with user approval.
Final technical verification passed; v0.24.0 is the current main revision.
Detailed live playtest feedback has not been recorded.
See the release guide for the final ROM and source/test identity.
<!-- v024-player-status:end -->
See the [playtest guide](RELEASE-v0.24.0.md) and [native review gallery](REVIEW-v0.24.0.html).

This is a native SNES game. On Windows use [Play.cmd](../Play.cmd); on other
platforms load `dist/abaqus-after-hours.sfc` in a SNES emulator.

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

- Walk, retreat and ordinary projectiles move about 18% slower. Ground heavy
  attacks and ordinary specials have longer windup and recovery; native video,
  input sampling, clocks and audio retain their normal cadence. Hit reactions
  ease away from the contact side, with heavier recoil for strong hits and
  smaller recoil on guard. Read the windup, then test a block or whiff punish.
- **Y** is the quick close jab. **X** is the heavy punch with committed
  recovery. **B** reaches farther for spacing; Down+B attacks low. **A** is
  the strong kick with a longer windup. Close blocked heavy punches/kicks
  leave time for a jab punish; use B to punish a more distant whiff. Each fighter
  still has individual speed, power and reach.
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
  guard. Time **A** as you jump past the opponent for the short rear air-kick
  cross-up; switch guard direction after a crossing.
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

- Alternate light and heavy attacks. Watch feet, hips, shoulders and guard
  move together; try reading and punishing a heavy windup or recovery.
- Compare light hits, strong hits and blocks at center and both walls. Recoil
  should move away from contact, including trades and rear airborne A kicks.
- Test fist/boot tips and projectile edges against standing, crouching and
  airborne targets. Report visible gap hits or clear overlapping misses.
- Jump and land with all twelve fighters, then try all four air buttons and
  rear A cross-ups from both ports. Watch takeoff, apex, descent and compression.
- Walk across **Las Condes, El Castillo and La Oficina**; check connected
  scenery, planted feet, floor detail, impact shake and the paused guide.
- Spend a full gauge on several supers. Compare charge, contact/cast/peak and
  recovery drawings; try interrupting and blocking them as well as landing them.

Approved walking, portraits, fighter palettes and physical height remain.
The revised combat poses are original full-body drawings; prior source masters
are retained. Include the title version, fighter pair, stage, player port and
repeatable input with feedback. Current combined clips are labeled separately
from the approved baseline and offline art diagnostics in the gallery. GIF
playback approximates timing; the native ROM's cadence is authoritative.
The combined human playtest is still pending. Historical approved-main notes
remain in [v0.23.1](RELEASE-v0.23.1.md).
