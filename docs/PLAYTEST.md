# v0.8.1 human playtest guide

This is a short review route for the verified v0.8.1 technical snapshot. It
collects human feedback on likeness, motion, fighting feel, pause help,
Training behavior, presentation, audio and onboarding; it is not a release
approval form. Leave an item blank or mark it unknown when it was not reviewed.
Do not infer roster consent or public-release approval from a completed table.

## Snapshot under review

- Source freeze commit: `fe05e5fd1391a1db20f1b66f1e9f6e699445e77a`,
  tree `46e1af160ffb8ab6cb768e3d9deec1352d77ae83`.
- [Verified ROM](../dist/abaqus-after-hours.sfc) SHA256:
  `76b456d1ac75471a8b9710c61b0ce4c6ab9ca344b1b8a1f17e38f36e52904466`,
  header checksum `A358` in the [manifest](../dist/manifest.json). Verify the
  SHA before a session because the checkout's `dist/` files are mutable.
- [v0.8.1 Windows package](../dist/Abaqus-After-Hours-v0.8.1-Windows.zip) is
  the current packaged snapshot. Its archive audit passes 7,471 technical
  checks. Two packaging runs produce identical 6,546,645-byte archives, SHA256
  `04d951c3abef278afada5a666f9eec8a04d140650354bd82506e750e2849e0b6`.
- All six native reports pass on this SHA with 30,641 checks. Fresh committed
  export, matchup, stage, policy, replay, symmetry, pinned bsnes, bounded
  independent and endurance evidence also pass. Native C/ASM, controls,
  gameplay and audio are unchanged. Reston's full64 native visual review
  accepted v4 for integration. The user subsequently confirmed the revised
  buzz cut looks closer; see the scoped record below. Final team likeness and
  consent, balance, full listening, controller and branding review still need
  explicit human results. The first release is emulator-first by user choice;
  original-console/flash-cartridge support stays unverified.
- The separate [Mesen-S review](MESEN-REVIEW.md) passes 48 bounded combat cases,
  mode/guide checks and all three stages on this same ROM. The
  [audio review](AUDIO-REVIEW.md) supplies twelve captured WAVs and measured
  score repetition for listening. These supplements leave the packaged game
  unchanged and do not constitute human play or listening approval.
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

## Review already received

| Review | Actual response | Scope still open |
|---|---|---|
| Reston's revised short buzz cut, 2026-10-20 | User: "Yes, closer" | Final team likeness review, motion approval and public-use consent |
| Combat feel, balance and onboarding | User: "havent tested" | Human play on the exact package, including both player layouts and all twelve fighters |
| Music and effect mix | User heard the 14-second replay: "I heard it; no issue noticed" | Full score/cue and busy-exchange listening; playback device was not specified |
| First public-release platforms | User: "Emulators first; hardware support stays unverified" | Original hardware remains unverified future work; it is outside the selected first-release support scope |
| Physical controllers | No equipment result recorded | Two-controller session on the intended emulator setup |
| Public names, portraits and branding | No approval recorded | Review by the people/team responsible for those uses |

The [Reston feedback record](reston-likeness-report.json) and
[platform/play/listening record](review-feedback.json) preserve the exact
questions and responses. A positive hair comparison does not approve the rest
of the roster, gameplay, audio or public distribution. The other rows record
the remaining review scope; unreviewed items are not reported defects.

## A 20-30 minute route

Use Local Versus for the two-player checks and Training for repeatable moves.
Start on Normal after a quick Easy onboarding check. A reviewer can run the
route alone with two controllers, with a second person, or with the included
keyboard mappings.

| Time | Route | Record |
|---|---|---|
| 0-2 min | Boot the exact verified ROM, read the first control hint, open fighter select and arena select, then confirm and back out once. | Is the first action clear? Are confirm, back and pause consistent? |
| 2-8 min | Sweep all twelve fighters. On each card, check the face, hair, costume colors, feet baseline and apparent size. In a short match or Training reset, make each fighter idle, walk forward/back, crouch, jump and perform one normal. Put each fighter on P1 once and P2 once so both right- and left-facing renders are seen. For Reston, compare the fuller short buzz cap in the v4 portrait and all 64 native poses. | Note likeness, proportions, silhouette changes and any fighter that needs a second look. Use the capture index below for native motion references. Record Reston likeness feedback separately from the art-integration review. |
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

The [listening pack and observation sheet](AUDIO-REVIEW.md) provide matched
cue pairs and approximately one-minute captures of each score. Use that sheet
for device, gain and loop/mix observations, then check a live busy exchange as
well. The automated PCM report establishes technical properties, not whether
the mix sounds good to the reviewer.

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

## Future real-console record

The user selected emulators for the first public release. Original hardware
support stays unverified; this record is for later hardware validation.
Keep it separate from the emulator session. If a flash cartridge and original
hardware are available, record the SNES/Super Famicom model and region, flash
cart and firmware, display, controller ports, audio path, ROM SHA, date and
whether the result was complete or partial. Check boot, both controllers, all
three stages, audio, pause/reset and a short match. A missing hardware session
is `Not reviewed`; it is not a failure and it does not block recording the
emulator findings.
