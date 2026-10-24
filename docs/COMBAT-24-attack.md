# v0.24 isolated attack art and grounded animation

This feature replaces exactly 24 poses for each of the twelve fighters with
individual whole-body built-in imagegen artwork. It targets
`integration/readable-combat-v024`, based on contract commit `3f51120` and
approved main `f75005d`. It is one child workstream for the combined human
playtest, with no main merge or combined validation claim.

`assets/art/attack-v1.json` selects twelve adjacent provenance records. Each
fighter has two untouched transparent 4x4 PNG outputs, exact prompts, source
and reference hashes, fixed OBJ palette hash, explicit pose/frame mappings,
and a neutral anchor at source A pose 0. The eight unused companion cells map
to null. There is one isotropic conversion per fighter, using the approved
standing height divided by the neutral source height. No body parts are
pasted, stretched, recolored from another fighter or resized individually.
Damian's two atlases and native-size preview established the example before
the roster pass. Every later fighter uses their own approved action reference.

Owned slots are `5,6,7,8,9,10,12,13,15,32..45,47`. Every other native slot,
including walking `20..27`, idle `16..19`, standing identity `0`, portraits,
fixed palette and old art/provenance, remains byte exact against main.
New attack sources draw supporting feet, hip/shoulder rotation, guarded
anticipation, extended contacts, retraction and backward hurt/block feedback.

The only production code edit is in `src/animation_weight.h`:

- High guard uses brace `40` while block stun is above four ticks, then hold
  `9`. Pre-existing held guard now shows a brace on contact; neutral back
  guard does not show an unsolicited impact pose.
- Hurt uses backward impact `10` until the final six stun ticks, then recovery
  `41`. Both existing timers freeze during pause/hitstop.
- Cross and grounded kick/sweep switch to their authored retraction at the
  native active-end boundary. They previously held the contact drawing two
  ticks into recovery. Projectile/groundwave casts retain their existing
  seven-tick release hold before `43` retraction: their one-tick emit window
  must remain visible across the alternating one-actor-per-vblank DMA.

Active contact mappings are unchanged, explicitly for contact PR #15:

| Action | Old active frame | New active frame |
| --- | --- | --- |
| Jab 1 | 5 | 5 |
| Cross 2/3 | 6 | 6 |
| Grounded kick 4/5/6 | 7 | 7 |
| Crouched kick/sweep 4/5/6 | 8 | 8 |
| Projectile/groundwave special 7 | 12 | 12 |
| Rising special 7 / uppercut 8 | 13 | 13 |
| Rush special 7 / fallback rush | 15 | 15 |

Jump/landing and airborne-action branches, super routing, personality victory,
intro hooks, throw/down/get-up routing and all gameplay timing/damage/reach are
unchanged. Conflict boundary: apply only the high-guard/hurt lines and grounded
action recovery lines; retain the jump owner's changes around state 4/state 15
and the airborne branch. Parent retains all shared importer, preservation,
version, report and hardware integration ownership.

The focused driver is `tools/test_combat24_attack.py`. Run from this checkout:

```powershell
.tools/python/python.exe tools/run_background.py --log build/combat24-attack-build.log -- D:/snes-abaqus-fighter/.tools/python/python.exe tools/build.py --assets
.tools/python/python.exe tools/run_background.py --log build/combat24-attack-proof.log -- D:/snes-abaqus-fighter/.tools/python/python.exe tools/test_combat24_attack.py
```

The focused report records exact ROM/source/harness/core/host identities,
failure arrays, all-roster/both-port phase and hardware observations, and
before/after native clips with complete sequences. Its per-pose native boxes
and literal opaque row edges supply measured final raster geometry to the
contact owner; these observations are not gameplay hitboxes. Parent must
regenerate contact geometry and every combined exact-ROM gate after merging.

Local build delta is limited to four encoded banks (`fighterXX`, `b`, `e`,
`f`) and the native review strip for each fighter, plus
`character-manifest.json`: 61 changed outputs and 158 preserved out of 219.
No generated or dist outputs are committed. Fighter64/Wave16, TRACE0..122,
3840-byte actor uploads, 30 OBJ/actor, VRAM/CGRAM reservations and 4 MiB
FastROM LoROM bank allocation remain unchanged. The tested cartridge and
symbols are retained under ignored `build/v024-attack-candidate/`.

Validation results and exact tested identities are in
`combat-24-attack-report.json`; figures in
`screenshots/combat-24-attack/` are real silent libretro PPU captures. GIF
timing is a cumulative 10/20 ms approximation to native NTSC playback.
Human review of the combined animation and contact alignment remains with
the parent playtest PR.

The stronger active-VRAM check found that immediate cast retraction could
skip P2's release art during simultaneous casts. That isolated regression
(`b8ad1631...15a08`) was repaired by restoring the established release hold;
the assertion that each port actually uploads its active pose remains enabled.
