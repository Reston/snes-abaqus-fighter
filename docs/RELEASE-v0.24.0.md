# v0.24.0 — readable combat playtest guide
<!-- candidate-version: 0.24.0; identity: TECHNICALLY_VERIFIED_HUMAN_PENDING; rom-sha256: 408cadfdddef97a24215e40f6ddb366140bc68fc80e7f1de82ee87e4084beb79; source-freeze: a1ee733aea036ad985bca9bdee29cc170cabd2ac -->

The combined revision gives attacks more time to read, clearer backward hit
reactions and coordinated whole-body animation. All twelve fighters gain new
attack, jump/landing and dedicated super drawings; all three stages gain
connected scenery and authored ground detail.

<!-- v024-release-status:start -->
**Combined candidate: technically verified; human playtest pending.**
The six feature PRs are merged into `integration/readable-combat-v024`.
[Playtest PR #14](https://github.com/Reston/snes-abaqus-fighter/pull/14) stays
**unmerged** into main for one human combined playtest. Final media and gates
are bound by [verification](verification-v0.24.0.json).
<!-- v024-release-status:end -->

## What changes in play

| Change | What to look for | Feature PR |
| --- | --- | --- |
| More readable pacing and recoil | Walking, retreat and ordinary projectiles move about 18% slower, with fixed-point rounding. Ground heavy punch, heavy kick and sweep gain 3 windup ticks and 4 recovery ticks; ordinary specials gain 3 / 5. Backward hit drift eases out, with stronger heavy reactions and smaller guard recoil. | [#20](https://github.com/Reston/snes-abaqus-fighter/pull/20) |
| Coordinated attack art | Support foot, hips, shoulders, guard and striking limb work together through anticipation, contact and retraction. Hurt and block poses show the reaction. | [#19](https://github.com/Reston/snes-abaqus-fighter/pull/19) |
| Visible contacts | Stable attack and body regions follow the drawn poses; projectile contact follows the visible projectile. Judge close hits, misses, guards and rear air kicks together with the final art. | [#15](https://github.com/Reston/snes-abaqus-fighter/pull/15) |
| Rebuilt stage08 depth | Las Condes, El Castillo and La Oficina use whole connected scenery behind fixed ground, with slab, stone and carpet detail. Buildings and desks should stay coherent as the view moves. | [#16](https://github.com/Reston/snes-abaqus-fighter/pull/16) |
| Jump and landing motion | Read takeoff, rise, compact apex, descent and grounded compression. Ivo, Negger, Fernando and Reston also receive adjusted jump height for standing clearance. | [#18](https://github.com/Reston/snes-abaqus-fighter/pull/18) |
| Dedicated super art | Every fighter has individual charge, contact/cast/peak and recovery drawings for their existing super. | [#17](https://github.com/Reston/snes-abaqus-fighter/pull/17) |

Native approximately 60 Hz video and
controller sampling, match/menu clocks and audio cadence keep their normal
rate. Jabs and light kicks retain their quick timing; longer projectile life
preserves nominal travel. Hit reactions push away from the actual contact
side, including rear hits and trades. CPU defense and recovery reactions use
slower, fallible sampling. Supers keep their existing command and
96-energy cost. Rising specials now prepare on the ground and launch with the
active fist, keeping their longer windup readable at close range. The human combined playtest remains pending.

The revision preserves the approved full-body walking poses, fighter
likeness/costume references, portraits, fighter palettes and physical scale;
old masters remain retained. The final inventory is 226 generated assets;
all 1,318 prior RAM labels retain their addresses. Final evidence is bound by the verification record.
Scope is pacing/recoil plus proposals 1–5 only; proposals 6–10 are excluded.

## Play and controls

This remains a **native SNES game requiring an SNES emulator**. Use
[Play.cmd](../Play.cmd) or load `dist/abaqus-after-hours.sfc` in the emulator.
The technically verified combined runtime is identified below; the human
playtest remains pending. Approved main remains v0.23.1.

| SNES input | Action |
| --- | --- |
| Left / Right; Up / Down | Move; jump / crouch. Hold away to guard, Down+away to guard low. |
| Y / X | Light / strong punch |
| B / A | Light / strong kick |
| Down+X; toward+X | Uppercut; close throw |
| Down+A; Down+B | Sweep; low light kick |
| Down+Y or quarter-circle toward+Y/X | Ordinary special, 32 energy |
| Fresh neutral Y+B together | Super, full 96 energy. Release directions and both buttons first; activate while grounded and free to act. |
| Start; Select while paused | Pause/resume; cycle guide pages |

Choose **LOCAL 1V1 / 2P** for the existing two native controller ports. Included
keyboard defaults: P1 arrows with A/S punches and Z/X kicks; P2 I/J/K/L with
numpad 7/8 punches and 1/2 kicks (Num Lock on). P1/P2 super chords are A+Z /
numpad 7+1 after releasing directions and those buttons. Existing emulator
mappings may differ. [Full controls and Training help](PLAYER-GUIDE.md).

## Combined playtest tasks

1. Walk forward and retreat, then alternate light and heavy attacks. Can you
   read a heavy windup, block it and punish its recovery? Try Y-hit → X and
   B-hit → A confirms without getting a cancel from a block or miss.
2. Compare light hits, heavy hits and guards at center and near each wall.
   Check that recoil moves away from contact and settles cleanly, including
   trades and a rear airborne A kick. Watch for repeated corner stun loops.
3. Test visible fist/boot tips and projectile edges at close miss/hit distances.
   Try both players, standing/crouching targets and jumping opponents. Record
   any clear gap hit or obvious overlapping strike that misses.
4. Jump, attack in the air and land with each fighter, especially the four
   adjusted arcs. Check held guard, apex/descent, cross-ups and immediate
   movement or attack after landing; compare likeness and scale with walking.
5. Move to both sides of every stage, trade hits and open the pause guide.
   Check connected architecture, readable feet/shadows, ground detail and HUD.
   Trigger each fighter's full-meter super and judge charge/contact/recovery.

Report the fighter pair, stage, player port, input and visible problem, plus
the frozen candidate identity when available. Actual human responses belong
in [review feedback](review-feedback.json); these tasks do not mark them done.

## Media and verification status

The [review gallery](REVIEW-v0.24.0.html) separates current combined native
captures, approved v0.23.1 comparisons and offline art/geometry diagnostics.
The six `COMBAT-24-*` feature notes are implementation/history links; their
isolated runs do not establish current whole-game behavior. GIF playback
approximates timing; native ROM cadence is authoritative.

<!-- v024-media-status:start -->
- **Pacing:** six native before/current samples and the full-roster focused proof.
- **Attacks:** all twelve new combined-versus-historical sequences and both-port hurt/block captures.
- **Contacts:** native baseline-left/current-right clips; final-art overlays are offline diagnostics.
- **Stages:** current Accuracy movement and right/left views; no stale center views or prototype comparisons.
- **Jumps:** new combined comparisons and both-port native examples.
- **Supers:** refreshed native before/current examples; roster conversion sheet remains an offline diagnostic.

All linked media hashes are checked against final verification or its hash-bound capture reports.
<!-- v024-media-status:end -->

<!-- v024-technical-status:start -->
**Technical verification passed; one human combined playtest remains pending.**

| Identity | Final value |
| --- | --- |
| Version / mapping | 0.24.0 / 4 MiB NTSC FastROM LoROM |
| ROM SHA256 | `408cadfdddef97a24215e40f6ddb366140bc68fc80e7f1de82ee87e4084beb79` |
| Header checksum | `4857` |
| Source/test freeze | `a1ee733aea036ad985bca9bdee29cc170cabd2ac` |
| Generated assets / retained prior RAM labels | 226 / 1,318 |

All six native suites pass **29,595 checks**: 2,595 gameplay, 17,906 roster, 3,728 presentation, 1,443 input, 735 stages, 3,188 Training. Matching pinned
Accuracy smoke, all six focused proofs, final-freeze fresh ROM/assets/symbol
reproduction and authoring guards pass. Focused counts: pacing/recoil 238,137; attacks 2,539; contacts 9,165; stages 735; jumps 1,741; supers 4,730.
Stage focused coverage shares the stage suite's native execution and is not
counted again as an independent run. Isolated/interim counts are not pooled.
See [final exact-ROM verification](verification-v0.24.0.json).
Human playtest remains pending; PR #14 stays unmerged. No offline package or human approval is claimed.
<!-- v024-technical-status:end -->

Approved historical baseline: v0.23.1 [release](RELEASE-v0.23.1.md) and
[verification](verification-v0.23.1.json). No v0.24 offline package, main merge
or human approval exists. Human balance/motion/likeness, listening, physical
controllers and consent/public-use reviews remain open; original hardware is
unverified. Technical finalization leaves the human combined playtest pending.
