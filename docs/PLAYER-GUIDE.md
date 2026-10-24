# Abaqus: After Hours - player guide
<!-- candidate-version: 0.26.0; identity: IN_PROGRESS; rom-sha256: PENDING_FINAL_VERIFICATION; source-freeze: PENDING_FINAL_VERIFICATION -->

The v0.26 polish candidate retains v0.25's slower fight rhythm and detailed
floors, with clearer local menus, super cues and quicker practice retries.
Main's approved revision is v0.24.0; combined checks and human playtest are pending.
See the [playtest guide](RELEASE-v0.26.0.md) and [pass notes](POLISH-v0.26.0.md).

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
Hold a D-pad direction or arrow key to scroll after a short delay. Confirm
and Back remain single-press actions even when held.

## Fighting

- Walk, retreat and ordinary projectiles move about 25% slower than v0.24.
  All normals have longer windup and recovery, jumps have more airtime, and
  CPU pressure is less frequent. Light/strong/guard contact pauses are 7/10/5
  ticks. Ground heavy attacks and ordinary specials commit for longer; native video,
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

If both grounded throws connect together, **THROW TECH!** identifies the
existing non-damaging escape. Toward+X must request a throw for both fighters;
an ordinary throw against a late button still follows the normal throw rules.

Gold health turns red at one quarter or less; the thin teal bar is energy and
diamond medals count round wins. Win two rounds to take a match. At timeout,
more health wins; a tie restarts without awarding a round. Light hits use small
amber sparks, heavy hits larger gold bursts, and blocks hollow cyan braces.
At full energy, **SUPER Y+B** appears beneath that player's bars; spending the
gauge clears it. The cue shows full meter, while grounded/free-to-act rules remain.
**COUNTER!** identifies a hit during the opponent's startup. **PUNISH!** identifies
a hit during attack recovery. The new punish cue adds feedback without a damage
bonus or extra stun; a displayed combo still requires uninterrupted hit stun.

## Modes and pause

**Arcade Shift:** defeat all eleven other fighters. Each matchup opens with a
short two-speaker exchange: wait about six seconds or press **P1 A** (keyboard
X) to skip into the countdown. Start pauses first. Continue retries the same
opponent after a loss. Individual winner quotes and a personal trophy ending
follow your victories; the original Champion music remains.
The exchange/result shows **SHIFT 01/11** through **SHIFT 11/11**. Results name
the next opponent or the opponent you will retry; pause names CPU difficulty.

**Local Versus:** choose both fighters and an arena for a best-of-three match.
Both physical ports share the four-button layout, specials and super command.
Either pad chooses the arena and controls the result card. A/Start rematches,
B returns to character select, and the winner label names Player 1 or Player 2.

**Training:** choose PLAYER 1, any DUMMY (including a mirror), then an arena.
Either pad can choose the dummy; B backs up to PLAYER 1. Health recovers and
the clock stays at 99. Automated dummies ignore physical P2 gameplay buttons.
Home L/R selects Easy/Normal/Hard. CPU personalities differ in spacing,
pressure, guarding, throws and recovery answers. Normal/Hard can attempt
fallible supers after defense; Easy does not choose supers.

**Start** pauses or resumes from either pad. Without Start, **B** returns to
the roster, **A** resumes and **Select** cycles pages. Start wins even with
Select held. From PAUSED, Training's Select cycle is Controls **1/3**, Move
List **2/3**, Training Tools **3/3**, then PAUSED. Versus and Arcade have the
first two guide pages. Left/Right cycles within the guide pages. Move List
names both fighters' specials and supers.

On **Move List 2/3** (2/2 outside Training), **Up** cycles the special list,
Player 1 normal timing and Player 2 normal timing. **S/A/R** shows startup,
active time and recovery in live simulation ticks for the four standing
ground attacks. Contact hitstop adds its separate pause; crouching/air moves
can differ. The fight stays frozen while you browse.

On a full guide page, **SNES L** (P1 keyboard **D**, P2 numpad **9**) toggles
music with a short fade. Combat sounds and announcements remain audible.
The preference survives menu/match changes and resets on cold boot. The
caption shows its state; opposite shoulders cancel. On ordinary Training
PAUSED with CPU selected, L/R keep their difficulty-setting role.

On Training's ordinary **PAUSED** card, Up/Down selects **Stand, Guard High,
Guard Low, Jump, Guard After Hit or CPU**. Guards hold position and Jump repeats
on landing. Guard After Hit stands for the opener, then holds away during the
combo window: true links connect, while late high follow-ups are blocked.
With CPU selected, either pad's L/R changes the shared difficulty once per
press; opposing held shoulders cancel even across pads. These dummy/level
controls stay on the ordinary card.

On that ordinary PAUSED card, **SNES X selects P2 Controller** (P1 keyboard
**S**, P2 numpad **8**) for two-person
Training. P2 then uses the complete shared fighting controls. X again returns
to Stand; Up selects CPU and Down selects Stand from manual control. The
Up from Stand still selects CPU directly. P1 live Select retains
manual control when resetting; P2 live Select does not reset the fight.

## Training tools

On **Training Tools 3/3**, **Up** shows/hides the live footer and **Down** chooses
one of three drills:

1. **Hit Confirm:** get close, land Y, then press X; or land B, then press A.
   Both hits must be in the same uninterrupted combo. The prepared opponent
   guards after the opener, so a late follow-up shows Retry. A linked special
   can also complete it; `SP!` alone does not.
2. **Block a Low Attack:** choose CPU on the ordinary card, then hold
   Down+away against a real low attack. A high block does not count; taking
   damage shows Retry. Select restores space for another attempt.
3. **Air Kick Cross-up:** choose Stand, jump past and press A just after
   crossing. The kick must hit from behind; a front hit or block does not count.

Choosing a drill supplies its required recovery-guard/CPU/Stand partner, keeping the chosen
CPU difficulty. **SNES X on Training Tools 3/3 restarts that drill** while leaving
the guide open: positions, health, energy, progress, history and combo totals
reset. Fighter choices, arena, drill and display preference remain. Start/B/A/
Select still take priority over X. Override the prepared partner on ordinary
PAUSED if you want to practice that drill against a second person.

The footer shows five P1 commands, oldest first, as **direction + YXBA**.
Directions use absolute numpad notation: 1/2/3 down, 4/5/6 level, 7/8/9 up.
`6Y---` means Right+Y; `-` marks an unpressed button. Neutral releases leave
useful motion steps visible. History keeps recording while hidden.

Tools 3/3 also shows **BEST**: your highest-damage earned combo in this Training
session, with its hit count. Equal damage keeps the combo with more hits.
Select and X retries keep that record; returning to character select clears
it for a new session. The live NOW/LAST totals still describe the current or
last attempt separately.

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
