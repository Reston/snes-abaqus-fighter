# v0.17.0 human playtest guide
<!-- candidate-version: 0.17.0; rom-sha256: cf605438ea9a722c45dc9c0d73fb33a819ffa7c1d7d63fb69a22310a33005cfe -->

Review cartridge SHA256 `cf605438ea9a722c45dc9c0d73fb33a819ffa7c1d7d63fb69a22310a33005cfe`.
Choose Easy/Normal/Hard at home, then enter Training and select CPU from the
first PAUSED card. Check practice pacing, health recovery, clock 99, pause
readability and P1 Select reset. Reset should retain CPU and the opponent;
a new match should return to Stand. Try all five behaviors and both pause
controllers, arbitrary opponents and mirrors. P2 gameplay buttons should not
take control of the Training opponent.
Compare close jump-ins, anti-air startup/recovery and cross-up spacing. The
[practice companion](CROSSUP-PRACTICE-v0.17.0.html) retains fighter-specific
examples. Test both ports and all three arenas.

Also review A/Start menus, per-step motion help, Training mirror opponents,
Lars's face/hair, winner cards, the champion score and title transitions.
Actual earlier responses remain in [review-feedback.json](review-feedback.json);
this guide records no new approval. See [RELEASE-v0.17.0.md](RELEASE-v0.17.0.md)
for candidate verification and package status.

Use the cartridge identified above for new feedback. Historical notes below
retain earlier technical results and actual observations. Record likeness,
motion, fighting feel, pause help, Training, presentation, audio and onboarding
feedback. Leave unreviewed items blank or mark them unknown. A completed table
does not establish roster consent or public-release approval.

## A 20-30 minute route

Use Local Versus for the two-player checks and Training for repeatable moves.
Choose Normal difficulty after a quick Easy onboarding check. A reviewer can run the
route alone with two controllers, with a second person, or with the included
keyboard mappings.

| Time | Route | Record |
|---|---|---|
| 0-2 min | Boot the cartridge identified above; record its version and ROM SHA from manifest.json, read the first control hint, open fighter select and arena select, then confirm and back out once. | Is the first action clear? Are confirm, back and pause consistent? Do directional edges and Start/B/A priority produce one menu action? |
| 2-8 min | Sweep all twelve fighters. On each card, check the face, hair, costume colors, feet baseline and apparent size. In a short match or Training reset, make each fighter idle, walk forward/back, crouch, jump and perform one normal. Put each fighter on P1 once and P2 once so both right- and left-facing renders are seen. For Reston, compare the fuller short buzz cap in the v4 portrait and all 64 native poses. | Note likeness, proportions, silhouette changes and any fighter that needs a second look. Use the capture index below for native motion references. Record Reston likeness feedback separately from the art-integration review. |
| 8-13 min | Play the fundamentals: walk into standing guard, crouch guard a low kick or wave, take a real hit, jump forward and neutral, press light/medium/heavy normals, then repeat after the opponent blocks. | Does input feel immediate? Are pushback, hitstop, guard stun, chip and recovery readable? Any accidental attacks or missed edges? |
| 13-17 min | Verify the four special families with Damian (projectile), Cristobal (rush), Negger (low shockwave) and Roxana (rising strike). Try a confirmed normal into a heavier normal and then a special. At close range, throw a guarding opponent; attempt simultaneous throws once. | Record command reliability, cancel timing, special readability, throw timing and whether blocked/unblocked results make sense. |
| 17-21 min | Pause during a live exchange. Cycle the PAUSED card -> Controls -> Specials with Select, toggle pages with Left/Right, resume with Start/A and return to the roster with B when Start is not pressed. Confirm both live fighter names, special names and family labels appear. | Record guide clarity, page timing, stale text, Start/B/A/Select priority and whether the pause camera and HP display remain stable. |
| 21-24 min | In Training, open the first PAUSED card and cycle Stand, Guard High, Guard Low, Jump and CPU with Up/Down. Test relative guard, repeated jumps, CPU behavior at the chosen home difficulty and ignored P2 gameplay input. Use P1 Select to reset, then start a new match. | Record dummy behavior, CPU pacing, health recovery, clock 99 and pause errors. Reset must keep the behavior and matchup; a new match must start on Stand. |
| 24-27 min | Play one short round on each stage: Las Condes, El Castillo and La Oficina. Compare the live scenes with their complete arena thumbnails. Let the round run long enough to see ambient motion; pause, hitstop and round-end once. | Check floor readability, contrast, stage identity, matched thumbnail art, ambient motion, freeze behavior, effects and any busy area behind the fighters. |
| 27-30 min | Swap controller ports or mappings, run a two-player exchange, then listen to title/menu music, stage music and several hit, guard, throw, special, round and KO cues at a comfortable volume. | Record rollover/SOCD problems, stuck or cross-wired inputs, missing/clipped sounds, cue priority, mix balance and whether a new player could recover without coaching. |

Do not rush through a failing step to finish the route. Capture the smallest
repeatable example, note the fighter, stage, side and round state, then continue
so the remaining areas still receive a quick pass.

## Previous v0.10.0 snapshot evidence

- The frozen v0.10.0 candidate is commit
  `8536bb6956212952c17302a62cc6c1de7e12a65d`, tree
  `d524d3f960600dc5c9ff83578ac73675f9798735`; its ROM is SHA256
  `a8f7b797a06bd242a18bf54400e53f043d5a84f274765ba3a34f9d8289ac5445`, header
  `BE19`. Native PPU review accepted all three stage scenes and the arena
  picker; focused presentation, stage and menu probes pass. `Test.cmd` exits 0
  with all six reports matching this SHA: 2,595 gameplay, 18,081 roster, 1,756
  presentation, 1,020 focused-input, 8,131 stage and 622 Training checks
  (32,205 total). Fresh committed export validation passes 214 assets and
  symbols in 62.031 seconds. Endurance passes all three modes at 216,356 live
  frames each at 60.098811862348406 FPS, with wraps 4/4/3, peak SPC backlog 6
  and empty cadence, native-timing, ambient, PPU-overflow and SPC-FIFO failure
  arrays. The technical audio report passes 1,262/1,262 capture-only checks;
  all four cues and four scores are unclipped, four music captures run
  60.899688-63.079432 seconds, and no near-zero interval reaches 0.5 seconds.
  The 288-by-600 matchup/stage/policy/replay/symmetry run with four replays
  across all three stages, pinned bsnes smoke at 600/600 plus the independent
  28,800-frame run, and `validate_release_evidence` also pass. The current
  [v0.10.0 Windows package](../dist/Abaqus-After-Hours-v0.10.0-Windows.zip)
  is available and its archive audit passes 7,472 checks. Human listening,
  gameplay, controller, likeness/consent and public-use review remain open,
  with `public_release_certified=false`.
- It refreshes all three stage masters with original bold-navy cel-cartoon art,
  keeps complete matching art in each arena thumbnail, and retains the existing
  ambient cell/trace contracts. It also carries bounded menu-only correctness
  polish: cleaned directional edges, both-pad navigation only for the P2 roster
  case, Start > B > A menu priority, and immediate return after Back. The
  [stage pass note](STAGE-CARTOON-v2.md) and [cartoon preservation report](cartoon-preservation-report.json)
  record the source and preservation details, including 192 generated files
  retained from v0.9. Ambient change counts by phase are Las Condes
  `[0,20,20,20]`, El Castillo `[0,18,18,18]` and La Oficina `[0,6,6,6]`;
  the office keeps one 3-pixel monitor segment per monitor at `y114` while
  protecting the monitor digits.
- Candidate stage sources are `00-las-condes-cartoon-v2.png`,
  `01-castillo-cartoon-v2.png` and `02-oficina-cartoon-v2.png` under
  `assets/art/stages/`, with adjacent exact-basename JSON and raw inputs under
  `assets/art/stages/source-v2/`. `stages.json` is schema 2 and
  `stages-v0.4.json` is historical input.

- The [historical v0.9.0 ROM](../dist/abaqus-after-hours.sfc) has
  SHA256 `bce460fbaa6f63e2f9c614f5c6833c08fd70558d56e7a27adfad292d4d200639`
  and header checksum `6D41` in the [manifest](../dist/manifest.json). Verify
  the SHA before a session because the checkout's `dist/` files are mutable.
- Historical v0.9.0 source freeze: commit
  `76f0a08a7562800df01507db83c6877745c3bdcf`, tree
  `f37852da57a42d2d6819374db5d23278d12587a5`.
- All six historical v0.9.0 reports pass on its SHA: 2,595 gameplay, 18,081
  roster, 1,756 presentation, 997 focused-input, 8,131 stage and 622 Training
  checks (32,182 total). Matching compatibility, matchup, bounded independent
  combat, endurance, fresh-source and `validate_release_evidence` evidence also
  pass. `Test.cmd` exits 0. The historical [v0.9.0 Windows package](../dist/Abaqus-After-Hours-v0.9.0-Windows.zip)
  is available and its archive audit passes 7,471 checks. Keep historical
  v0.8.1 and v0.9.0 results separate from the current v0.10.0 reports; use the
  frozen SHA above for this candidate.
- The [last verified v0.8.1 ROM](../dist/abaqus-after-hours.sfc) is SHA256
  `76b456d1ac75471a8b9710c61b0ce4c6ab9ca344b1b8a1f17e38f36e52904466`, header
  checksum `A358`; its source freeze and package evidence are historical. Native
  C/ASM, controls, gameplay and audio are unchanged by the presentation pass.
  The first release is emulator-first by user choice; original-console and
  flash-cartridge support stays unverified.
- The separate historical [Mesen-S review](MESEN-REVIEW.md) passes 48 bounded
  combat cases, mode/guide checks and all three stages on the v0.8.1 ROM. The
  historical [audio review](AUDIO-REVIEW.md) supplies twelve captured WAVs and
  measured score repetition for listening. These supplements leave the packaged
  game unchanged and do not constitute v0.9.0 or v0.10.0 evidence or human
  play/listening approval.
- Historical [review captures](screenshots/) include the [title](screenshots/title.png),
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
| Live v0.8.1 presentation review | User reported clipped selection faces, Damian did not resemble the supplied photo closely enough, the arena picker looked ugly, and stage scenery showed through HUD/result lettering | Native v0.9.0 correction checks now pass on the exact SHA; human likeness/consent and broader gameplay review remain open |
| v0.10.0 cartoon-stage and menu candidate | No human response recorded yet | Review all three matched stage thumbnails, stage readability and menu edge/priority behavior on frozen SHA `a8f7b797a06bd242a18bf54400e53f043d5a84f274765ba3a34f9d8289ac5445`; native and extended technical evidence pass, while human approval remains open |
| Combat feel, balance and onboarding | Not covered by the presentation review | Human play on the exact candidate, including both player layouts and all twelve fighters |
| Music and effect mix | User heard the 14-second replay: "I heard it; no issue noticed" | Full score/cue and busy-exchange listening; playback device was not specified |
| First public-release platforms | User: "Emulators first; hardware support stays unverified" | Original hardware remains unverified future work; it is outside the selected first-release support scope |
| Physical controllers | No equipment result recorded | Two-controller session on the intended emulator setup |
| Public names, portraits and branding | No approval recorded | Review by the people/team responsible for those uses |

The [Reston feedback record](reston-likeness-report.json) and
[platform/play/listening record](review-feedback.json) preserve the exact
questions and responses. A positive hair comparison does not approve the rest
of the roster, gameplay, audio or public distribution. The other rows record
the remaining review scope; unreviewed items are not reported defects.

The live presentation findings are retained as four separate review targets:

- Selection faces were clipped by the old source-window fill. The candidate
  uses one contained, head-anchored crop for both the 32x40 card and 64x80
  portrait, with `portrait_framing` metadata and no head clipping.
- Damian's face did not match the supplied photo closely enough. The candidate
  carries the v4 source PNGs and provenance under
  `assets/art/characters/00-damian/`, with one reviewed neutral-height
  conversion per atlas; native palette, physical scale and 64-frame order stay
  locked. Human likeness approval remains open.
- The arena picker looked cramped and uneven. The candidate contains complete
  stage art in 60x52 thumbnails at `x18..77`, `y42..93` plus 56 pixels per row,
  keeps the cursor at `x8..247`, `y40..95` plus 56 pixels per row, and moves
  names/captions to a separate text column.
- Stage scenery showed through HUD and result lettering. FIGHT and RESULT now
  use opaque glyphs 256-383 for ASCII 32-127, while round markers 147/148 use
  the panel background at palette index 1.
- The v0.10.0 candidate refreshes all three stage masters in one bold-navy
  cel-cartoon direction and uses the same complete art in each arena thumbnail.
  Native PPU review accepted all three live scenes and the arena picker, and
  focused stage probes pass. Review stage identity, floor readability, contrast
  and consistency across the picker and live arena. The candidate's source
  provenance and schema-2 manifest are recorded in the [stage pass note](STAGE-CARTOON-v2.md).
- The candidate also carries bounded menu-only correctness polish: cleaned
  directional edges, both-pad navigation only for the P2 roster case, Start
  confirm before B back before A confirm, and an immediate return after Back.
  Check that one edge cannot trigger two scene actions.

The historical v0.9.0 presentation suite and matching technical evidence pass on
its SHA. The historical [v0.9.0 Windows package](../dist/Abaqus-After-Hours-v0.9.0-Windows.zip)
is available and its archive audit passes 7,471 checks. The v0.10.0 candidate's
six native reports, endurance, technical audio capture, matchup, pinned
bsnes/independent compatibility evidence and `validate_release_evidence` pass on
its frozen SHA. The current [v0.10.0 Windows package](../dist/Abaqus-After-Hours-v0.10.0-Windows.zip)
is available and its archive audit passes 7,472 checks; human review remains
open with `public_release_certified=false`. The observations above are actual
live feedback;
they do not establish human likeness/consent or public-use approval.

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
| v0.9.0 portrait, arena and HUD/result corrections |  |  |
| v0.10.0 cartoon stages and menu edge/priority contract |  |  |
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
