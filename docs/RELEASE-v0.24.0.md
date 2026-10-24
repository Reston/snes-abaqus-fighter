# v0.24.0 — readable combat playtest guide
<!-- candidate-version: 0.24.0; identity: PENDING_FINAL_VERIFICATION; rom-sha256: PENDING_FINAL_VERIFICATION; source-freeze: PENDING_FINAL_VERIFICATION -->

The combined revision gives attacks more time to read, clearer backward hit
reactions and coordinated whole-body animation. All twelve fighters gain new
attack, jump/landing and dedicated super drawings; all three stages gain
connected scenery and authored ground detail.

**Combined candidate: PENDING_FINAL_VERIFICATION.** The six feature PRs are
merged into `integration/readable-combat-v024`.
[Draft playtest PR #14](https://github.com/Reston/snes-abaqus-fighter/pull/14)
remains **unmerged** into main for the human combined playtest. The final ROM,
source freeze, matching captures and technical verification are pending.

## What changes in play

| Change | What to look for | Feature PR |
| --- | --- | --- |
| More readable pacing and recoil | Walking, retreat and ordinary projectiles move about 18% slower, with fixed-point rounding. Ground heavy punch, heavy kick and sweep gain 3 windup ticks and 4 recovery ticks; ordinary specials gain 3 / 5. Backward hit drift eases out, with stronger heavy reactions and smaller guard recoil. | [#20](https://github.com/Reston/snes-abaqus-fighter/pull/20) |
| Coordinated attack art | Support foot, hips, shoulders, guard and striking limb work together through anticipation, contact and retraction. Hurt and block poses show the reaction. | [#19](https://github.com/Reston/snes-abaqus-fighter/pull/19) |
| Visible contacts | Stable attack and body regions follow the drawn poses; projectile contact follows the visible projectile. Judge close hits, misses, guards and rear air kicks together with the final art. | [#15](https://github.com/Reston/snes-abaqus-fighter/pull/15) |
| Rebuilt stage08 depth | Las Condes, El Castillo and La Oficina use whole connected scenery behind fixed ground, with slab, stone and carpet detail. Buildings and desks should stay coherent as the view moves. | [#16](https://github.com/Reston/snes-abaqus-fighter/pull/16) |
| Jump and landing motion | Read takeoff, rise, compact apex, descent and grounded compression. Ivo, Negger, Fernando and Reston also receive adjusted jump height for standing clearance. | [#18](https://github.com/Reston/snes-abaqus-fighter/pull/18) |
| Dedicated super art | Every fighter has individual charge, contact/cast/peak and recovery drawings for their existing super. | [#17](https://github.com/Reston/snes-abaqus-fighter/pull/17) |

This is **not a global clock slowdown**: native approximately 60 Hz video and
controller sampling, match/menu clocks and audio cadence keep their normal
rate. Jabs and light kicks retain their quick timing; longer projectile life
preserves nominal travel. Hit reactions push away from the actual contact
side, including rear hits and trades. CPU defense and recovery reactions use
slower, fallible sampling. Supers keep their existing command and
96-energy cost. Rising specials now prepare on the ground and launch with the
active fist, keeping their longer windup readable at close range. Final
combined behavior still needs verification and playtest.

The revision preserves the approved full-body walking poses, fighter
likeness/costume references, portraits, fighter palettes and physical scale;
old masters remain retained. Combined preservation evidence is pending.
Scope is pacing/recoil plus proposals 1–5 only; proposals 6–10 are excluded.

## Play and controls

This remains a **native SNES game requiring an SNES emulator**. Once the parent
provides the frozen candidate, use [Play.cmd](../Play.cmd) or load
`dist/abaqus-after-hours.sfc` in the emulator. The file currently at that path
is not identified as the final playtest ROM by this guide.

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

The [review gallery](REVIEW-v0.24.0.html) contains representative native
before/after clips and links to all-twelve evidence. **Every current feature
figure/report is ISOLATED / HISTORICAL**, not a capture or pass result from the
final combined candidate. The approved v0.23.1 [release](RELEASE-v0.23.1.md) and
[verification](verification-v0.23.1.json) identify the historical main baseline.
GIF playback approximates native timing and cannot establish frame cadence.

Final ROM SHA256, header checksum, source freeze, combined captures and every
exact-ROM gate: **PENDING_FINAL_VERIFICATION**. The parent will finalize these
and [verification-v0.24.0.json](verification-v0.24.0.json) (**pending file**).
Isolated reports are never added together to claim a combined pass count.
No final readiness, new offline package, main merge or human approval is
claimed here. Human balance/motion/likeness, listening, physical controllers
and consent/public-use reviews remain open; original hardware is unverified.
