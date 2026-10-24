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
over release. Physics, jump velocities, gravity, horizontal steering, combat
timing, input buffers and landing availability are unchanged.

## Integration boundaries

Only the state-4 flight branch, state-15 landing release and the `airAction`
recovery tail change in `animation_weight.h`. The grounded-attack owner edits
other branches in that file; retain both sets when resolving the shared-file
conflict. There are no `game.c`, `characters.h`, version, native assembly or
shared pipeline edits. Frames 1/2/4 remain the super owner's slots; frames
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
PCM/SPC FIFO health. Identical baseline inputs compare all non-animation
Fighter bytes and non-animation public trace samples. The art proof restricts
all generated fighter changes to the ten owned frames and verifies exact
palette, portrait and protected-pose preservation.

The Damian native-size sequence was reviewed first, then all twelve roster
sequences. `docs/screenshots/combat-24-jumps/` contains those conversion sheets
and headless native clips, including baseline/current paired jump and strong
air-kick clips (baseline left, candidate right). GIF timing approximates the
native capture; cadence conclusions use SDK counters and consecutive trace.

The parent must rerun this focused proof against final pacing/contact changes,
refresh shared jump/landing fixtures honestly (old release expected 28/19;
the new release is 54), update preservation policy for these disjoint frames,
and regenerate all exact-ROM shared evidence. Human combined motion/likeness
review and physical controller/original hardware checks remain separate.
