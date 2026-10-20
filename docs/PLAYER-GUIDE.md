# Abaqus: After Hours - player guide

## Current version

This manual describes the verified v0.8.0 technical snapshot. The matching ROM is the 4 MiB
NTSC file `abaqus-after-hours.sfc`, SHA256 prefix
`53ef44225c83bd52...12c13090`, header checksum `6A21`. Verify the complete
SHA256 in the accompanying manifest before recording feedback for a build.
Packaging and archive audit are pending the next package run. Human review of
likeness, balance, audio, controllers, branding and real hardware is still open.

## Launch

From the project checkout, run `Play.cmd`, focus the Snes9x window and press
**Enter**. You can also open `abaqus-after-hours.sfc` directly in Snes9x.
For a quiet session, mute Snes9x or the system before launching; this does not
change game input. Snes9x supports fullscreen with **Alt+Enter** and controller
assignment through **Input -> Input Configuration**.

## Modes

**Arcade Shift**: defeat the other eleven coworkers in best-of-three matches.
Each victory advances to another opponent and location. A continue is offered
after a loss; completing the ladder awards Office Champion.

**Local Versus**: choose a fighter for each player, choose an arena and play a
best-of-three match. Both controller ports use the same six-button layout.

**Training**: practice against a configurable opponent with a clock fixed at 99.
Press **Select** for a live round reset. Press **Start**, then **B**, to return
to fighter select and change the matchup.

At home, **L/R** changes CPU difficulty between Easy, Normal and Hard. Easy is
the recommended starting point. Normal and Hard defend and recover more often.

## Fighters and stages

The roster has twelve illustrated coworkers:

Damian, Ivo, Cristobal, Jose "Cote" Ignacio, Gonzalo "Negger" Reyes, David
Ponce, Fernando Perez, Cristian, Ignacio "Mamariaga", Jose "Reston" Ordonez,
Roxana and Rodrigo "Lars" Lartiga.

Fighter select uses a four-by-three grid. **Left/Right** moves one card;
**Up/Down** moves by four cards and wraps around. The selected fighter appears
in the large portrait. Choose from the three arenas: **Las Condes**, **El
Castillo** and **La Oficina**. In the arena menu, **Up/Down** chooses the row.

## Controls

| SNES input | Included P1 keyboard | Action |
| --- | --- | --- |
| Left / Right | Arrow keys | Move; hold away from the opponent to guard |
| Up | Up arrow | Jump |
| Down | Down arrow | Crouch; combine with away for low guard |
| Y / X / L | A / S / D | Light / medium / heavy punch |
| B / A / R | Z / X / C | Light / medium / heavy kick |
| A | X | Confirm menus / resume pause |
| B | Z | Back in menus / roster from pause |
| Start | Enter | Confirm / pause |
| Select | Shift | Training reset / pause page cycle |

Player two's included keyboard uses **I/J/K/L** for Up/Left/Down/Right,
numpad **7/8/9** for punches, numpad **1/2/3** for kicks, **Space** for
Start and **Q** for Select. In menus and pause, numpad **2** is A
(confirm/resume) and numpad **1** is B (back/roster). Enable Num Lock. Assign
controllers through Snes9x **Input Configuration**.

Holding Left and Right together neutralizes that axis. A short attack or jump
press remains buffered briefly, so use a clean press when checking a move.

## Pause guide and Training dummy

Press **Start** during a match to pause. **Start** resumes first from either
controller. If Start is not pressed, **B** returns to the roster; otherwise
**A** resumes and **Select** changes the guide page.

The pause card has three pages:

- **Normal** shows pause status and the current Training dummy mode.
- **Controls** lists movement, guard, six-button attacks, throw, uppercut,
  confirmed attacks and the pause shortcuts.
- **Specials** shows the live P1/P2 names, each special and its family.

**Select** advances Normal -> Controls -> Specials -> Normal. **Left/Right**
also toggles the guide pages. The guide names the actual fighters in the
match, rather than showing a generic roster description.

In Training, pause on **Normal** and press **Up/Down** to choose **Stand**,
**Guard High**, **Guard Low** or **Jump**. Guard holds relative back without
retreating. The Jump dummy automatically jumps again after landing. A live **Select** reset keeps
the chosen dummy mode; starting a new Training match returns the dummy to
Stand.

## Fighting

- Hold **away from the opponent** to block. Hold Down as well to crouch guard
  low attacks. A jump-in attack can beat crouch guard.
- Press **Down + L** for a rising uppercut.
- Press **toward + L** at close range to throw through a guard. A throw applies
  damage when the defender reaches the floor. Simultaneous throws tech.
- Perform a special with **Down -> Down + toward -> toward + Y/X** within the
  twelve-tick motion window. **Down + Y/X** is the quick shortcut. **Down +
  away + Y/X** is not a special. A special costs 32 energy; energy regenerates
  slowly and successful hits add more.
- A confirmed light or medium normal can cancel into a heavier normal. A
  confirmed normal can cancel into a special during its cancel window.
- Punches and kicks work in the air. Crouching kicks are low attacks. Keep an
  eye on the gold health bar and teal energy bar.

Win two rounds to take the match. At timeout, the fighter with more health
wins; a tie restarts the round without awarding a round win.

## Human review note

Use the build's exact SHA when recording feedback. Check all twelve faces and
both facing directions, idle/walk/attack proportions, guard/throw/special
response, all three arenas, both controller ports, keyboard rollover and the
music/effects mix. Record a repeatable example for any issue. A review result
does not by itself grant likeness consent or public-release approval.
