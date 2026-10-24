# v0.24.0 — readable combat playtest guide
<!-- candidate-version: 0.24.0; identity: PENDING_FINAL_VERIFICATION; rom-sha256: PENDING_FINAL_VERIFICATION; source-freeze: PENDING_FINAL_VERIFICATION -->

The combined revision gives attacks more time to read, clearer backward hit
reactions and coordinated whole-body animation. All twelve fighters gain new
attack, jump/landing and dedicated super drawings; all three stages gain
connected scenery and authored ground detail.

<!-- v024-release-status:start -->
**Combined candidate: PENDING_FINAL_VERIFICATION.** The six feature PRs are
merged into `integration/readable-combat-v024`.
[Draft playtest PR #14](https://github.com/Reston/snes-abaqus-fighter/pull/14)
remains **unmerged** into main for one human combined playtest. Current combined
captures are interim. A full attack proof found native startup lag; runtime
optimization, regenerated media and final exact-ROM verification remain pending.
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
active fist, keeping their longer windup readable at close range. Final
technical status and human playtest remain pending.

The revision preserves the approved full-body walking poses, fighter
likeness/costume references, portraits, fighter palettes and physical scale;
old masters remain retained. The current inventory is 226 generated assets;
all 1,318 prior RAM labels retain their addresses. Final collation is pending.
Scope is pacing/recoil plus proposals 1–5 only; proposals 6–10 are excluded.

## Play and controls

This remains a **native SNES game requiring an SNES emulator**. Use
[Play.cmd](../Play.cmd) or load `dist/abaqus-after-hours.sfc` in the emulator.
The current combined runtime is identified below; final technical verification
is still pending. Approved main remains v0.23.1.

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

The [review gallery](REVIEW-v0.24.0.html) separates interim combined native
captures, approved v0.23.1 comparisons and offline art/geometry diagnostics.
The six `COMBAT-24-*` feature notes are implementation/history links; their
isolated runs do not establish current whole-game behavior. GIF playback
approximates timing; native ROM cadence is authoritative.

<!-- v024-media-status:start -->
These captures bind the interim combined runtime below. The parent will
regenerate them at the same paths for the corrected final ROM.

- **Pacing:** six current before/after light, strong and guard GIFs are bound by
  [the sample record](combat-24-pacing-samples.json). This limited capture
  record does not replace the pending full-roster pacing proof.
- **Attacks:** new `XX-combined-vs-historical-sequences.gif` and
  `XX-combined-P1/P2-hurt/block.gif` files are being produced. The gallery uses
  existing new files as provisional media only; the successful full-run
  [attack report](combat-24-attack-report.json) and complete inventory are pending.
- **Contacts:** paired native clips compare approved baseline left/current
  combined right. All64/roster/edge overlays use final art and are offline
  diagnostics. [Current contact report](combat-24-contact-report.json).
- **Stages:** current Accuracy stage0 movement, stage1 right and stage2 left
  views are used. Earlier center views and the floor prototype are omitted.
  [Both-core stage report](combat-24-stage08-report.json).
- **Jumps:** the new `jump-combined-vs-historical.gif`,
  `air-a-combined-vs-historical.gif` and `combined-*.gif` native media are bound
  by [the current jump report](combat-24-jumps-report.json), with 19 captures.
- **Supers:** the roster conversion sheet shows current art as an offline
  diagnostic. Current native after clips await a successful full
  [super report](combat-24-super-report.json); old after GIFs remain historical.
<!-- v024-media-status:end -->

<!-- v024-technical-status:start -->
**Interim combined ROM only; final ROM will change:**

| Identity | Interim value |
| --- | --- |
| Version / mapping | 0.24.0 / 4 MiB NTSC FastROM LoROM |
| ROM SHA256 | `28d770aca1cc489c70d7370329e785cb223c0703d807f07d627d461ba8dbdb85` |
| Header checksum | `5872` |
| Final source/test freeze | **Pending parent collation**; recent driver checkpoints are interim |
| Generated assets / retained prior RAM labels | 226 / 1,318 |
| Final technical identity | **PENDING_FINAL_VERIFICATION** |

`Test.cmd` exited 0 on this interim ROM: 2,595 gameplay, 17,906 roster, 3,728 presentation,
1,443 input, 735 stages and 3,188 Training checks, **29,595 total** on this
combined ROM. Matching pinned Accuracy smoke passed. Completed focused proofs
are contact **9,165** (108 sessions / 61,704 callbacks), jumps **1,741** (all
twelve / both ports) and stages **735** (both cores). The stage focused proof
shares `Test.cmd`'s native execution; it is not counted again as an independent run.

The full attack proof confirmed native startup lag during simultaneous
Cristobal specials (tick 9 / frame 1039, SDK lag +1). Runtime optimization is
underway. Full pacing, attack and super proofs remain unfinished; all final
gates and media must bind the corrected ROM and settled source/test freeze.
Interim passes above do not transfer to that ROM. The earlier `003661c` fresh export reproduced this ROM,
226 assets and normalized symbols, but is **interim**, not final-freeze proof.
The parent will write `docs/verification-v0.24.0.json` after collation succeeds.
No isolated or incomplete result is pooled into a combined pass claim.
<!-- v024-technical-status:end -->

Approved historical baseline: v0.23.1 [release](RELEASE-v0.23.1.md) and
[verification](verification-v0.23.1.json). No v0.24 offline package, main merge
or human approval exists. Human balance/motion/likeness, listening, physical
controllers and consent/public-use reviews remain open; original hardware is
unverified. Technical finalization leaves the human combined playtest pending.
