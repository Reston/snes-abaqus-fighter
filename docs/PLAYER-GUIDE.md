# Abaqus: After Hours - player guide
<!-- candidate-version: 0.12.0; rom-sha256: 33502fba12bf2cf02e6244174449c678ad1dd704afc754e7819f815489c6fa83 -->

## Current version

The current candidate is **v0.12.0**, adding Training opponent and mirror-match
selection and an original Office Champion trophy scene. It includes the revised Lars likeness, clearer location previews
and a result card with the winner's portrait,
round score and quote. In Local Versus, A or Start begins a rematch. Arcade
victory advances to the next challenger; a loss offers a continue. After
Office Champion, A or Start returns to the title. B returns to fighter select.

## Launch

In the source checkout, run the root `Play.cmd`; it prepares pinned tools on
first use and opens `dist/abaqus-after-hours.sfc` in Snes9x. On other platforms,
open that cartridge in your SNES emulator.

For an offline Windows package, extract the whole ZIP first and run its
`Play.cmd`. Keep the `emulator` folder beside the cartridge and launcher. The
included `manifest.json` identifies the packaged version and ROM SHA256;
`RELEASE.md` records its verification scope. Source checkouts use the versioned
release note under `docs/`. No global installation or administrator account is
needed. Human gameplay, listening, controller, likeness/consent and team/public
use review remain open; original hardware support stays unverified.
The package's `REVIEW.html` contains selected native screenshots and a 2x view.

Known v0.12.0 review issue: in paused Training, press Start alone to resume.
Pressing Start+Select together also resets the round. The next input-priority
fix is under separate verification.

Focus Snes9x and press **Enter**. Use **Alt+Enter** for fullscreen and
**Input -> Input Configuration** to assign controllers. For a quiet session,
mute Snes9x or the system before launching.

## Modes

**Arcade Shift**: defeat the other eleven coworkers in best-of-three matches.
Each victory advances to another opponent and location. A continue is offered
after a loss; completing the ladder awards Office Champion.

**Local Versus**: choose a fighter for each player, choose an arena and play a
best-of-three match. Both controller ports use the same six-button layout.

**Training**: choose your fighter at **PLAYER 1**, then choose any opponent at
**DUMMY**, including the same fighter for a mirror match. The dummy cursor
starts on the next roster entry. P1 can operate both steps; either controller
can choose the dummy. Press **A** or **Start** to confirm each fighter, then
choose an arena. **B** on DUMMY returns to PLAYER 1. The clock stays at 99.
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
in a large portrait. Choose from the three arenas: **Las Condes**, **El Castillo**
and **La Oficina**. In the arena menu, **Up/Down** chooses the row; each
thumbnail shows landmarks from the matching stage inside its box, with the location
name and caption in a separate text column.

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
In menus, **Start** confirms first, **B** backs out, and **A** confirms; a Back
edge returns immediately so one edge cannot trigger two scene actions.

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
both chosen fighters and the chosen dummy mode; starting a new Training match
returns the dummy behavior to Stand.

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

During the final part of getting up, a fresh attack or jump press can be
buffered. A quarter-circle motion must be entered after recovery; directions
entered while getting up do not carry over into a later punch.

Win two rounds to take the match. At timeout, the fighter with more health
wins; a tie restarts the round without awarding a round win.

## Human review note

Use the build's exact SHA when recording feedback. Check all twelve faces and
both facing directions, idle/walk/attack proportions, guard/throw/special
response, all three arenas, both controller ports, keyboard rollover and the
music/effects mix. Record a repeatable example for any issue. A review result
does not by itself grant likeness consent or public-release approval.
