# v0.8.0 human playtest guide

This is a short review route for the verified v0.8.0 technical snapshot. It
collects human feedback on likeness, motion, fighting feel, pause help,
Training behavior, presentation, audio and onboarding; it is not a release
approval form. Leave an item blank or mark it unknown when it was not reviewed.
Do not infer roster consent or public-release approval from a completed table.

## Snapshot under review

- Source freeze commit: `48f3ccb539492247b83f4360a50bdc020bad9dd6`, tree
  `e571aca40019b868bf224bb619390f5ea651434e`.
- [v0.8.0 Windows package](../dist/Abaqus-After-Hours-v0.8.0-Windows.zip).
  Extract its cartridge for a frozen review. The 6,546,556-byte archive has
  SHA256 `1b7b685264a867f54ab4b05203cf168b0ddf6353f26ce4da419b9823e21ee359`.
  Repository tag: `v0.8.0`.
- [Verified ROM](../dist/abaqus-after-hours.sfc) SHA256:
  `53ef44225c83bd52ee0eea3910ba74ade5ba949af7aa7440c74d959812c13090`,
  header checksum `6A21` in the [manifest](../dist/manifest.json). Verify the
  SHA before a session because the checkout's `dist/` files are mutable.
- The [v0.7.1 Windows package](../dist/Abaqus-After-Hours-v0.7.1-Windows.zip)
  is historical; use the v0.8.0 archive for this review.
- The six native suites and matching compatibility evidence pass on this SHA;
  the broader matchup, independent-combat, endurance and fresh-source evidence
  also pass. The offline package passes 7,471 technical audit checks. Human likeness,
  balance, listening, controller, real-console and branding review still need
  explicit human results.
- [Review captures](screenshots/) include the [title](screenshots/title.png),
  [select](screenshots/select.png), [arenas](screenshots/arenas.png),
  [fight](screenshots/fight.png), [block](screenshots/block.png),
  [combo](screenshots/combo.png), [jump](screenshots/jump.png),
  [special](screenshots/special.png), [pause](screenshots/pause.png) and
  [victory](screenshots/victory.png) scenes. Character GIFs are in
  [screenshots/characters/](screenshots/characters/). The eight pause-guide and
[Training captures](screenshots/training/) are [Arcade controls](screenshots/training/mode0-controls.png),
[Arcade specials](screenshots/training/mode0-specials.png),
[Versus controls](screenshots/training/mode1-controls.png),
[Versus specials](screenshots/training/mode1-specials.png),
[Training controls](screenshots/training/mode2-controls.png),
[Training specials](screenshots/training/mode2-specials.png),
[P1 special page](screenshots/training/special-page-00.png) and
[P2 special page](screenshots/training/special-page-11.png).

If the ROM changes, start a new review record with its new SHA. Do not attach
results from this guide to a later build.

## A 20-30 minute route

Use Local Versus for the two-player checks and Training for repeatable moves.
Start on Normal after a quick Easy onboarding check. A reviewer can run the
route alone with two controllers, with a second person, or with the included
keyboard mappings.

| Time | Route | Record |
|---|---|---|
| 0-2 min | Boot the exact verified ROM, read the first control hint, open fighter select and arena select, then confirm and back out once. | Is the first action clear? Are confirm, back and pause consistent? |
| 2-8 min | Sweep all twelve fighters. On each card, check the face, hair, costume colors, feet baseline and apparent size. In a short match or Training reset, make each fighter idle, walk forward/back, crouch, jump and perform one normal. Put each fighter on P1 once and P2 once so both right- and left-facing renders are seen. | Note likeness, proportions, silhouette changes and any fighter that needs a second look. Use the capture index below for native motion references. |
| 8-13 min | Play the fundamentals: walk into standing guard, crouch guard a low kick or wave, take a real hit, jump forward and neutral, press light/medium/heavy normals, then repeat after the opponent blocks. | Does input feel immediate? Are pushback, hitstop, guard stun, chip and recovery readable? Any accidental attacks or missed edges? |
| 13-17 min | Verify the four special families with Damian (projectile), Cristobal (rush), Negger (low shockwave) and Roxana (rising strike). Try a confirmed normal into a heavier normal and then a special. At close range, throw a guarding opponent; attempt simultaneous throws once. | Record command reliability, cancel timing, special readability, throw timing and whether blocked/unblocked results make sense. |
| 17-21 min | Pause during a live exchange. Cycle Normal -> Controls -> Specials with Select, toggle pages with Left/Right, resume with Start/A and return to the roster with B when Start is not pressed. Confirm both live fighter names, special names and family labels appear. | Record guide clarity, page timing, stale text, Start/B/A/Select priority and whether the pause camera and HP display remain stable. |
| 21-24 min | In Training, pause on Normal and cycle Stand, Guard High, Guard Low and Jump with Up/Down. Test a guarded dummy's relative back hold, the Jump dummy's automatic repeat after landing and live Select reset; start a new Training match. | Record dummy behavior, retreat or jump-repeat errors, preserved/reset dummy state and any way to act through pause. |
| 24-27 min | Play one short round on each stage: Las Condes, El Castillo and La Oficina. Let the round run long enough to see ambient motion; pause, hitstop and round-end once. | Check floor readability, contrast, stage identity, ambient motion, freeze behavior, effects and any busy area behind the fighters. |
| 27-30 min | Swap controller ports or mappings, run a two-player exchange, then listen to title/menu music, stage music and several hit, guard, throw, special, round and KO cues at a comfortable volume. | Record rollover/SOCD problems, stuck or cross-wired inputs, missing/clipped sounds, cue priority, mix balance and whether a new player could recover without coaching. |

Do not rush through a failing step to finish the route. Capture the smallest
repeatable example, note the fighter, stage, side and round state, then continue
so the remaining areas still receive a quick pass.

## Roster and motion capture index

The existing P1 GIFs are visual references for idle, forward motion, a normal,
an air attack and a throw sequence. They are evidence to inspect, not a
substitute for playing the build. The current repository contains P2 air and
throw GIFs for Damian as orientation references; perform the P2-facing checks
live for the other eleven fighters.

| ID | Fighter | Native review set |
|---:|---|---|
| 00 | Damian | [idle](screenshots/characters/00-idle-animation.gif) · [walk](screenshots/characters/00-walk-animation.gif) · [attack](screenshots/characters/00-attack-animation.gif) · [P1 air](screenshots/characters/00-p1-air-b.gif) · [P1 throw](screenshots/characters/00-p1-throw-sequence.gif) · [P2 air](screenshots/characters/00-p2-air-b.gif) · [P2 throw](screenshots/characters/00-p2-throw-sequence.gif) |
| 01 | Ivo | [idle](screenshots/characters/01-idle-animation.gif) · [walk](screenshots/characters/01-walk-animation.gif) · [attack](screenshots/characters/01-attack-animation.gif) · [P1 air](screenshots/characters/01-p1-air-b.gif) · [P1 throw](screenshots/characters/01-p1-throw-sequence.gif) |
| 02 | Cristóbal | [idle](screenshots/characters/02-idle-animation.gif) · [walk](screenshots/characters/02-walk-animation.gif) · [attack](screenshots/characters/02-attack-animation.gif) · [P1 air](screenshots/characters/02-p1-air-b.gif) · [P1 throw](screenshots/characters/02-p1-throw-sequence.gif) |
| 03 | José “Cote” | [idle](screenshots/characters/03-idle-animation.gif) · [walk](screenshots/characters/03-walk-animation.gif) · [attack](screenshots/characters/03-attack-animation.gif) · [P1 air](screenshots/characters/03-p1-air-b.gif) · [P1 throw](screenshots/characters/03-p1-throw-sequence.gif) |
| 04 | Gonzalo “Negger” | [idle](screenshots/characters/04-idle-animation.gif) · [walk](screenshots/characters/04-walk-animation.gif) · [attack](screenshots/characters/04-attack-animation.gif) · [P1 air](screenshots/characters/04-p1-air-b.gif) · [P1 throw](screenshots/characters/04-p1-throw-sequence.gif) |
| 05 | David | [idle](screenshots/characters/05-idle-animation.gif) · [walk](screenshots/characters/05-walk-animation.gif) · [attack](screenshots/characters/05-attack-animation.gif) · [P1 air](screenshots/characters/05-p1-air-b.gif) · [P1 throw](screenshots/characters/05-p1-throw-sequence.gif) |
| 06 | Fernando | [idle](screenshots/characters/06-idle-animation.gif) · [walk](screenshots/characters/06-walk-animation.gif) · [attack](screenshots/characters/06-attack-animation.gif) · [P1 air](screenshots/characters/06-p1-air-b.gif) · [P1 throw](screenshots/characters/06-p1-throw-sequence.gif) |
| 07 | Cristian | [idle](screenshots/characters/07-idle-animation.gif) · [walk](screenshots/characters/07-walk-animation.gif) · [attack](screenshots/characters/07-attack-animation.gif) · [P1 air](screenshots/characters/07-p1-air-b.gif) · [P1 throw](screenshots/characters/07-p1-throw-sequence.gif) |
| 08 | Ignacio “Mamariaga” | [idle](screenshots/characters/08-idle-animation.gif) · [walk](screenshots/characters/08-walk-animation.gif) · [attack](screenshots/characters/08-attack-animation.gif) · [P1 air](screenshots/characters/08-p1-air-b.gif) · [P1 throw](screenshots/characters/08-p1-throw-sequence.gif) |
| 09 | José “Reston” | [idle](screenshots/characters/09-idle-animation.gif) · [walk](screenshots/characters/09-walk-animation.gif) · [attack](screenshots/characters/09-attack-animation.gif) · [P1 air](screenshots/characters/09-p1-air-b.gif) · [P1 throw](screenshots/characters/09-p1-throw-sequence.gif) |
| 10 | Roxana | [idle](screenshots/characters/10-idle-animation.gif) · [walk](screenshots/characters/10-walk-animation.gif) · [attack](screenshots/characters/10-attack-animation.gif) · [P1 air](screenshots/characters/10-p1-air-b.gif) · [P1 throw](screenshots/characters/10-p1-throw-sequence.gif) |
| 11 | Rodrigo “Lars” | [idle](screenshots/characters/11-idle-animation.gif) · [walk](screenshots/characters/11-walk-animation.gif) · [attack](screenshots/characters/11-attack-animation.gif) · [P1 air](screenshots/characters/11-p1-air-b.gif) · [P1 throw](screenshots/characters/11-p1-throw-sequence.gif) |

For every fighter, compare the face and hair to the source reference before
judging the sprite's style. Check that grounded idle, walk and attack poses
share one floor; verify that air and throw transitions use the intended lift
and landing positions and return to that baseline. A left-facing pose should
be a mirror of the same scale rather than a different-sized drawing. Record a
likeness concern separately from an animation or collision concern.

## Controls and listening notes

The included P1 keyboard is arrows for movement, `A/S/D` for light/medium/heavy
punch, `Z/X/C` for light/medium/heavy kick, `Enter` for Start/pause and `Shift`
for Training Select. P2 uses `I/J/K/L`, numpad `7/8/9` punches, numpad
`1/2/3` kicks, Space for Start and `Q` for Select; Num Lock must be enabled.
Controllers can be assigned through Snes9x **Input → Input Configuration**.

Test a short simultaneous exchange on both controller ports. Hold opposite
directions together once, press jump and attack together once, and try both
players pressing attacks on the same frame. Record whether neutralization,
rollover and port assignment behave predictably. Keep keyboard-only findings
separate from controller findings.

For listening, check the relative level of music, normal hit, guard, throw,
special, round and KO cues. Listen during a quiet menu, a live stage and a
busy exchange with both fighters attacking. Record clipping, missing cues,
loop gaps, harsh priority changes, or a sound that masks a necessary gameplay
cue. A human reviewer may choose headphones or speakers; automated evidence is
captured without speaker playback.

## Result sheet

Use `Pass`, `Needs work`, `Blocked` or `Not reviewed`; add issue IDs rather than
writing a long explanation in the table.

| Area | Status | Issue IDs / evidence |
|---|---|---|
| Twelve likenesses and identity references |  |  |
| P1/P2 facing and uniform proportions |  |  |
| Idle, walk, normals and air motion |  |  |
| Throw, knockdown, wake and recovery |  |  |
| Guard, low guard, hitstop and chip |  |  |
| Cancels, specials and input response |  |  |
| Las Condes / El Castillo / La Oficina |  |  |
| Controller ports and keyboard rollover |  |  |
| Music, effects and mix |  |  |
| Onboarding and accessibility |  |  |
| Team branding, names and likeness consent |  |  |

Reviewer: ____________________  Date/build: ____________________  Mode/setup: ____________________

## Issue format

One issue per entry is easier to reproduce than a combined list:

```text
ID / severity (Blocker, Major, Minor, Polish):
ROM SHA / tag:
Mode / stage / round / fighters / side:
Steps and exact inputs:
Expected:
Observed:
Repeat count:
Capture path or screenshot:
Notes / owner:
```

Use **Blocker** for a crash, soft lock, unusable control or progression stop;
**Major** for a repeatable gameplay, audio or presentation failure that harms a
match; **Minor** for a bounded defect with a workaround; and **Polish** for
likeness, timing, wording or feel that needs refinement. A likeness concern
should identify the person/reference and the exact pose or orientation. A name,
face or branding concern must be reviewed by the team before any public use;
this document records the concern and does not grant consent.

## Optional real-console record

Keep this separate from the emulator session. If a flash cartridge and original
hardware are available, record the SNES/Super Famicom model and region, flash
cart and firmware, display, controller ports, audio path, ROM SHA, date and
whether the result was complete or partial. Check boot, both controllers, all
three stages, audio, pause/reset and a short match. A missing hardware session
is `Not reviewed`; it is not a failure and it does not block recording the
emulator findings.
