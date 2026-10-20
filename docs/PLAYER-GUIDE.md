# Abaqus: After Hours — player guide

Extract the Windows release ZIP and double-click `Play.cmd`, or run `Play.cmd` from the project checkout. Click the Snes9x window, then press **Enter**.

## Modes

**Arcade Shift:** defeat the other 11 coworkers. Each match is best of three rounds. A victory advances to another opponent and location. Losing offers a continue. Finishing the ladder awards Office Champion.

**Local Versus:** player one selects a fighter, then player two selects using either controller. Choose an arena and fight a best-of-three match. Both controllers use the same SNES button layout.

**Training:** a passive opponent recovers health, the clock stays at 99, and you can practice moves. Press Start, then B, to change fighters.

On the home screen, L/R cycles three CPU difficulty levels. The default is level 2.

The fighter select screen uses a four-by-three card layout. Left and right move across the roster; Up and Down move by four cards between rows and wrap around. The highlighted fighter's large profile portrait updates beside the cards. The arena menu uses the same row-based navigation for Las Condes, El Castillo and La Oficina.

## Controls

| SNES input | Included P1 keyboard | Action |
| --- | --- | --- |
| Left / right | Arrow keys | Move |
| Up | Up arrow | Jump; combine with a direction to travel |
| Down | Down arrow | Crouch |
| Y / X / L | A / S / D | Light / medium / heavy punch |
| B / A / R | Z / X / C | Light / medium / heavy kick |
| A | X | Confirm menus / resume pause |
| B | Z | Back in menus / roster from pause |
| Start | Enter | Confirm / pause |

Player two uses **I/J/K/L** for up/left/down/right, **numpad 7/8/9** for punches, **numpad 1/2/3** for kicks and **Space** for Start. Enable Num Lock. Any USB controller can be assigned through Snes9x's Input Configuration menu.

## Fighting

- Hold **away from your opponent** to block. Crouch while holding away to block low kicks. Jump attacks beat crouch guard.
- Perform your **character special** with down, then toward your opponent, then Y/X. The accessible shortcut is **Down + Y/X**. It costs 32 meter; energy slowly regenerates and successful hits add more. The selection screen shows the move family: projectile, advancing rush, low shockwave or rising strike. Low shockwaves require crouch guard; rising attacks beat crouch guard.
- Press **Down + L** for a rising uppercut.
- Press **toward + L** at close range to throw through a guard.
- A confirmed light punch can cancel into medium or heavy punch. Light/medium kicks can cancel into a heavier kick. Release and press the next attack during the hit reaction.
- Punches and kicks also work while jumping. Crouching kicks are low attacks.

Health is shown in gold. Energy is shown in teal. Win two rounds to take a match. At timeout, the fighter with more health wins; a tie restarts the round without awarding a round win.

All twelve fighters have individual movement, jump arcs, normal attack speed and reach, throws and special tuning. Their sixteen poses share a 96×80 native canvas and one consistent physical scale per fighter, so a fighter's standing height can be slightly reduced to keep every attack and recovery pose inside the safe area. See [CHARACTERS.md](CHARACTERS.md) for the complete roster and each move's frame data.

## Emulator options

The included configuration uses a sharp 4× image with no smoothing. Snes9x supports fullscreen with Alt+Enter. Its Input Configuration menu supports controllers and custom keyboard mappings. If you change controls, the emulator saves them in its own folder.

The project ROM also runs independently of the launcher: open `abaqus-after-hours.sfc` in Snes9x. It is an NTSC image and needs no additional game files.
