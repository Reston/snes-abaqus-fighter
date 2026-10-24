# v0.24 isolated jump, air attack and landing workstream

This feature targets `integration/readable-combat-v024` from contract commit
`3f51120` / approved main `f75005d`. It supplies the jump workstream only.
Combined release identity, shared-suite fixtures and final native gates belong
to the parent integration; no main merge or combined pass count is claimed.

All twelve fighters have a new, individual built-in imagegen sixteen-pose
atlas and exact prompt/reference/raw-output provenance. The raw selected PNG
is retained unchanged as `assets/art/characters/<fighter>/jump-v1.png`.
`assets/art/jump-v1.json` uses the parent's common schema and applies exactly
native frames **29, 30, 31, 49, 50, 51, 52, 53, 54, 55**. Six source poses
are deliberately unmapped. Source pose zero is an upright neutral anchor;
one isotropic scale, `HEIGHTS[fighter] / anchor.height`, converts every owned
pose. Physical heights remain 69/72/68/69/72/68/67/73/66/70/68/74 pixels.
No limb or torso overlays, recolored shared bodies or per-pose resizing occur.

The figures coordinate knees, pelvis, torso, shoulders, guard and head. Slots
29/30 introduce takeoff compression and upward extension, 55 holds the compact
apex guard, 54 opens the legs for descent, and 31 absorbs actual floor contact.
Punch 49/50/51 and kick 52/53/54 provide windup, contact and recovery drawings.
The ten drawings use the existing fixed OBJ palettes and 96x80 canvases with
sole baseline 78. Approved walking 20..27, idle 16..19, portraits, old masters
and every other native drawing remain byte-exact against approved main.

`src/animation_weight.h` selects ordinary rise/apex/descent by physical
vertical velocity. Early takeoff compression is restricted to rising motion
near the floor, so finishing an air attack does not restart takeoff. An air
attack's final recovery returns to its actual flight phase. Ground contact
selects 31; the existing six-sample presentation release then uses 54 before
idle. Any accepted attack, jump, step, crouch or guard keeps selection priority
over release. Active contact IDs remain **punch 50 / kick 53**, with no active
cycling, matching the contact owner's `contactActionFrame()` mapping.

A controller-only baseline arc survey found that Ivo and Reston never reached
the standing-body clearance height; Negger and Fernando did not stay above it
long enough for their slower horizontal motion to cross. Their jumpVy values
change from -84 to -96, -84 to -105, -82 to -86 and -80 to -86 respectively.
These are the only four physics scalar changes. All gravity, uppercut/special
velocities, horizontal movement/steering, combat timing, input buffers and
landing availability remain exact. The other eight jump profiles are exact.
The focused report measures old/new arcs and requires both-port standing
cross-ups plus real rear strong-kick contacts on the candidate for all twelve.

## Integration boundaries

Only the state-4 flight branch, state-15 landing release and the `airAction`
recovery tail change in `animation_weight.h`. The grounded-attack owner edits
other branches in that file; retain both sets when resolving the shared-file
conflict. In `characters.h`, preserve only the jumpVy columns for IDs 1/4/6/9
when resolving the pacing owner's other profile fields. There are no `game.c`,
collision, version, native assembly or shared pipeline edits. Frames 1/2/4
remain the super owner's slots; frames
48/56..63 remain the original throw/down/get-up drawings.

There is no added RAM, ABI field, trace word, frame bank, VRAM, CGRAM, HDMA,
OBJ, DMA or audio resource. Fighter64/Wave16/TRACE0..122 remain unchanged.
The existing thirty 16x16 OBJ pieces and single 3,840-byte actor transfer per
vblank render the new drawings. The cartridge remains 4 MiB FastROM LoROM
with 32 KiB banks. Generated files and dist artifacts are local proof only
and are deliberately absent from this feature's commits.

## Focused verification

Run using the shared pinned tools junction and canonical Python, silently and
without an emulator window or speaker output:

```powershell
.tools/python/python.exe tools/run_background.py --log build/jump-assets-build.log -- D:/snes-abaqus-fighter/.tools/python/python.exe tools/build.py --assets
.tools/python/python.exe tools/run_background.py --log build/combat-24-jumps.log -- D:/snes-abaqus-fighter/.tools/python/python.exe tools/test_combat_24_jumps.py
```

The focused driver writes `docs/combat-24-jumps-report.json`, identifying the
isolated ROM, source/harness/core hashes, command and host. It checks all twelve
fighters on both ports: ordered takeoff/rise/apex/descent/floor/release,
grounded soles/shared scale, all four air normals, real air-punch and front/rear
strong-kick contacts, locked facing, released jump/attack/wake buffers,
immediate landing-release interruption and corner landings. Every sampled
callback checks consecutive native ticks, SDK lag/vblank counters, intact actor
payloads, thirty-piece OAM geometry, OBJ overflow, single-actor DMA and captured
PCM/SPC FIFO health. The eight unchanged profiles compare all non-animation
Fighter bytes and non-animation public trace samples against identical baseline
inputs. The four intentional jumpVy revisions instead carry measured baseline
and candidate flight arcs; an independent source check allows exactly those
four scalar differences and preserves all other character data. The art proof restricts
all generated fighter changes to the ten owned frames and verifies exact
palette, portrait and protected-pose preservation.

Agent visual inspection covered the Damian native-size sequence first, then
all twelve roster sequences. `docs/screenshots/combat-24-jumps/` contains those conversion sheets
and headless native clips, including baseline/current paired jump and strong
air-kick clips (baseline left, candidate right). GIF timing approximates the
native capture; cadence conclusions use SDK counters and consecutive trace.

The parent must rerun this focused proof against final pacing/contact changes,
refresh shared jump/landing fixtures honestly (old release expected 28/19;
the new release is 54), update preservation policy for these disjoint frames,
and regenerate all exact-ROM shared evidence. Human combined motion/likeness
review and physical controller/original hardware checks remain separate.
Walk speed also contributes to takeoff vx (`walkSpeed + 8`), so the pacing
merge must repeat the fixed-distance standing-cross and rear-contact cases.
This isolated driver's exact-other-fields/art guards need the parent's declared
combined policy when other authorized workstreams are present.

## Isolated result

Source/harness freeze `c95dfea5ce67161ca823a7c72712bbf67e9a63e8` passes **1,530 checks** on ROM
`74589f915d4429cf1af18fa001c6536d47e1d0a14bc6434683ae9872c4eaab40` (header `D6A3`).
The twelve candidate sessions cover **52,478 consecutive live callbacks**,
both ports, 24 standing-cross arcs and 72 real air contacts. All native timing,
cadence, OBJ, actor payload/geometry and SPC/PCM failure arrays are empty.
All 1,213 prior WRAM symbol addresses remain exact.

| Fighter ID | jumpVy | Measured apex px | Flight samples |
| --- | --- | --- | --- |
| 1 | -84 → -96 | 46.81 → 60.69 | 35 → 40 |
| 4 | -82 → -86 | 55.19 → 60.56 | 43 → 45 |
| 6 | -80 → -86 | 52.56 → 60.56 | 42 → 45 |
| 9 | -84 → -105 | 39.44 → 60.81 | 30 → 37 |

Exactly 37 of the existing 219 generated files differ: character-manifest.json,
and each fighter PNG plus banks d/g. Every packed 3,840-byte unowned frame is
byte-exact, including all approved walking/idle frames; palettes and portraits
are byte-exact. The frozen full-asset rebuild reproduces this same ROM. Generated
files and dist output remain uncommitted; the retained isolated cartridge and
symbols are `build/v024-jumps.sfc` and `build/v024-jumps.sym`.

[Baseline/current native jump clip](screenshots/combat-24-jumps/jump-before-after.gif)
and [air strong-kick clip](screenshots/combat-24-jumps/air-a-before-after.gif)
show baseline left and isolated candidate right. These counts identify this
isolated feature only; all combined-ROM evidence remains the parent
integration's responsibility.
