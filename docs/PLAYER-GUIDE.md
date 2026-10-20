# Abaqus: After Hours - player guide

Extract the Windows release ZIP and double-click `Play.cmd`, or run `Play.cmd` from the project checkout. Click the Snes9x window, then press **Enter**.

## Modes

**Arcade Shift:** defeat the other 11 coworkers. Each match is best of three rounds. A victory advances to another opponent and location. Losing offers a continue. Finishing the ladder awards Office Champion.

**Local Versus:** player one selects a fighter, then player two selects using either controller. Choose an arena and fight a best-of-three match. Both controllers use the same SNES button layout.

**Training:** a passive opponent recovers health, the clock stays at 99, and you can practice moves. Press **Select** for a quick round reset. Press Start, then B, to change fighters.

On the home screen, L/R cycles three CPU difficulty levels. The default is level 2. Menus use a single cursor, a four-by-three roster grid and one large selected portrait; the fighter cards do not display a statistics panel.

Choose Easy to learn the controls. Normal and Hard react more often, crouch
guard incoming low waves, and can jump after recovering from a knockdown.
Opponents choose specials at ranges suited to their move family.

The fighter select screen uses a four-by-three card layout. Left and right move across the roster; Up and Down move by four cards between rows and wrap around. The highlighted fighter's large profile portrait updates beside the cards. The arena menu uses the same row-based navigation for Las Condes, El Castillo and La Oficina.

## Controls

| SNES input | Included P1 keyboard | Action |
| --- | --- | --- |
| Left / right | Arrow keys | Move; hold away to guard |
| Up | Up arrow | Jump; a short press buffers for a few simulation ticks |
| Down | Down arrow | Crouch; combine with away to crouch guard |
| Y / X / L | A / S / D | Light / medium / heavy punch |
| B / A / R | Z / X / C | Light / medium / heavy kick |
| A | X | Confirm menus / resume pause |
| B | Z | Back in menus / roster from pause |
| Start | Enter | Confirm / pause |
| Select | Shift | Quick reset in Training |

Player two uses **I/J/K/L** for up/left/down/right, **numpad 7/8/9** for punches, **numpad 1/2/3** for kicks, **Space** for Start and **Q** for Select. Enable Num Lock. Any USB controller can be assigned through Snes9x's Input Configuration menu.

When opposite directions are held on the same axis, the input is neutral for that axis. This keeps keyboard rollover and controller SOCD behavior predictable.

## Fighting

- Hold **away from your opponent** to block. Crouch while holding away to block low kicks; the crouched guard pose is used while the low guard is active. Jumping attacks beat crouch guard.
- Perform your character special with a true quarter-circle motion: **Down -> Down + toward -> toward + Y or X** within the motion window. The accessible shortcut is **Down + Y/X**. **Down + away + Y/X is not a special.** It costs 32 meter; energy slowly regenerates and successful hits add more. The character guide lists the move families: projectile, advancing rush, low shockwave or rising strike.
- Press **Down + L** for a rising uppercut.
- Press **toward + L** at close range to throw through a guard. A successful
  throw lifts the defender, launches them, and applies throw damage at ground
  impact. If both players throw on the same contact snapshot, the throws tech
  and neither player takes throw damage.
- Attack and jump edges are buffered for six simulation ticks. A held Up input can carry a buffered jump through the landing transition, which makes short controller taps easier to perform without changing the jump arc.
- A diagonal jump commits its horizontal momentum at takeoff. Releasing or reversing the direction in midair does not steer the jump; facing updates on landing. A neutral jump stays vertical.
- A confirmed light or medium normal can cancel into the next heavier normal. A confirmed normal can also cancel into a character special during its cancel window. Press the next attack while the hit confirmation is active.
- A guarded strike does not enable a hit-confirm cancel. Combo counts describe
  uninterrupted hits; blocking or being interrupted breaks the chain. Receiving
  a real hit clears old queued attacks and jumps, while new hitstop taps are
  still sampled.
- Punches and kicks also work while jumping. Air punches and air kicks each use
  their own anticipation, active and recovery drawings. Crouching kicks are low
  attacks.

Guard stun lasts eight simulation ticks and blocked impact moves the defender one pixel. A real hit starts with a two-pixel impact and continues through a longer recoil reaction. Blocked specials may deal at most one chip point, while an unblocked special deals its normal damage.

Health is shown in gold. Energy is shown in teal. Win two rounds to take a match. At timeout, the fighter with more health wins; a tie restarts the round without awarding a round win.

The first fight intro shows a short control hint, then clears it to leave the
floor visible. Match results include the actual P1/P2 round score.

All twelve fighters have individual movement, jump arcs, normal attack speed and
reach, throws and special tuning. Each fighter now has 64 animation frames in
the shared 96x80 canvas: legacy key poses, motion transitions, action
windup/active/recovery frames, dedicated airborne attacks, throw roles and
knockdown/wake recovery. The original 48 frame pixels and palette stay locked;
the physical scale and feet baseline stay fixed across the full set. See
[CHARACTERS.md](CHARACTERS.md) for the roster and frame data.

## Animation and timing

Idle, forward gait, backward gait, crouch, jump and landing transitions use a
per-fighter animation clock. Actions expose windup, active and recovery frames
for normals, specials, guard, hurt, victory and knockout. Air normals select
dedicated punch or kick cycles. Throws select separate attacker and victim
roles, followed by lift, flight, floor, get-up and wake states. A downed player
cannot be hit again during the recovery sequence; four invulnerability ticks
start after waking. The final six ticks of the wake state accept one buffered
attack or jump edge. The clock advances with simulation and distance travelled,
and freezes during pause and hitstop so game and animation state remain aligned.

Training restores health only while a fighter is free of hurt, knockdown and
wake-invulnerability state. Select performs a complete round reset and clears
pending throw, downed and wake input state.

During hitstop the fight state and animation clocks remain frozen. The native
interface transfer yields to an actor upload, so impact feedback or an empty
combo banner can settle one to three video frames after the event without
changing its damage, guard or combo result.

## Emulator options

The included configuration uses a sharp 4x image with no smoothing. Snes9x supports fullscreen with Alt+Enter. Its Input Configuration menu supports controllers and custom keyboard mappings. If you change controls, the emulator saves them in its own folder.

The project ROM also runs independently of the launcher: open `abaqus-after-hours.sfc` in Snes9x. It is an NTSC image and needs no additional game files.
