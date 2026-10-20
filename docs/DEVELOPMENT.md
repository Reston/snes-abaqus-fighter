# Native SNES implementation

## Build

Supported build host: Windows x64. `tools/setup.ps1` downloads pinned official release archives into `.tools/` and verifies their SHA256. `tools/build.py` invokes 816-tcc, 816-opt, WLA-65816 and WLALINK directly, so a separate Make/MSYS installation is unnecessary.

The v0.6.0 integration targets a 4 MiB FastROM LoROM image across 128 banks,
NTSC, with no coprocessor or SRAM requirement. WLALINK writes the SNES
header/checksum. The build independently checks the FastROM LoROM mapping byte,
image size and calculated checksum before writing `dist/manifest.json`. The
latest four reports pass against ROM SHA256
`0d907717d284c9d0056434e69da0a265c2b09cf4c84761aa32998b4fc0bbd5ae`. The
canonical silent `Test.cmd` batch passes on that image.
`Build.cmd --assets` subsequently reproduced the same ROM SHA, confirming
deterministic source/asset output for this evidence snapshot.

`Build.cmd` rebuilds from committed native assets. `Build.cmd --assets` regenerates the full asset set first. Source portrait downloads can be refreshed with `tools/fetch_references.py`; rebuilding the game does not require fetching the team pages.

## Rendering

The PPU uses Mode 1. BG1 holds the stage; BG2 holds the interface and selected profile portrait. Stage tiles use six 16-color palette banks (15 opaque colors each). The interface reserves the first two palette banks, and the large profile portrait uses BG2 palette 1. Fighter and effect palettes occupy OBJ CGRAM.

| VRAM word address | Contents |
| --- | --- |
| `$0000-$37FF` | BG1 stage tiles, at most 896 4bpp tiles |
| `$3800-$3BFF` | BG1 32x32 tilemap |
| `$4000-$49FF` | BG2 interface/font tiles |
| `$4A00-$4EFF` | Selected 64x80 profile portrait, an eight-by-ten 4bpp tile block using BG2 palette 1 |
| `$5800-$5BFF` | BG2 32x32 tilemap |
| `$6000-$69FF` | Actor 0 padded frame page; 3,840-byte pose stream plus blank row padding |
| `$6A00-$73FF` | Actor 1 padded frame page; 3,840-byte pose stream plus blank row padding |
| `$7800-$7BFF` | Impact, projectile and shadow tiles |

Each actor uses thirty 16x16 hardware sprites: six columns by five rows. Actor 0 begins at OAM byte 0 and actor 1 at OAM byte 128, with two padded slots per actor block. The 65816 renderer writes an actor's OAM entries in one call. A strided DMA routine streams one 3,840-byte 96x80 frame into the actor's padded VRAM page, leaving the page's blank tail predictable. Each vblank streams at most one actor frame, alternating priority if both change together. The second actor can visually trail its requested frame by one video frame; combat state stays independent of that upload queue.

OBJSEL uses the 8/16 size pair; all live pieces select its 16-pixel size. The renderer packs each actor's repeating six-column X9 pattern once, then writes tile/attribute pairs together. Source-bank selection and frame-offset arithmetic happen before `WaitForVBlank`; the blanking interval only executes the prepared DMA and interface transfers. The HUD caches health, energy, wins and seconds, updating only changed fields and partial energy tiles to preserve the simulation budget.

### v0.6 integration performance notes

The native fast path caches actor-bank selection and per-action timing selection.
The packed `Fighter` layout uses stride 64 and `Wave` uses stride 16; both
layouts are compile-checked before assembly offsets are consumed. OAM and shadow
work is cached by integer position and facing, so unchanged actors do not rebuild
their sprite attributes every tick. Native health and energy bars retain their
existing glyph formulas. Impact HUD and empty-banner clears are serviced during
hitstop ticks, while interface DMA yields when an actor frame is being uploaded.
The engine and VRAM contract are unchanged. Interface impact feedback can settle
one to three video frames after the combat event while hitstop keeps the fight
state frozen.

`src/trace.asm` writes the read-only telemetry region with direct stores at the
stable `TRACE[0..113]` offsets. A change to the native `Fighter` or `Wave`
struct layout therefore requires updating the assembly offsets and the documented
trace contract together; the C fields alone are not a safe layout change.

### Fighter animation contract

Every fighter has 64 uniform 96x80 native frames, for 768 roster frames total.
The shared index contract is:

| Frame range | Content |
| --- | --- |
| `0-15` | Legacy neutral, walk, crouch, jump, normal, guard, hurt, victory, cast, uppercut, knockout and rush key poses |
| `16-31` | Motion and transition atlas: idle, forward gait, backward gait, crouch, jump and landing transitions |
| `32-47` | Action atlas: normal windup/active/recovery, specials, guard, hurt, victory and knockout transitions |
| `48-63` | v0.6 airborne, throw-role, knockdown and wake frames: dedicated air punch/kick cycles, thrower/victim roles, launch/fall, get-up and wake guard |

The source atlases are `animation-motion.png`, `animation-actions.png` and the
v0.6 `animation-airborne.png` under each fighter directory. Each source sheet
is a 1254x1254 RGBA sheet with sixteen separately extracted figures in a
four-by-four grid. The pipeline places the figures in uniform 96x80 native
cells. The generated native review strip `assets/generated/fighterXX.png` is
6,144x80 RGBA, and the encoded frame data is divided into eight contiguous
eight-frame banks: `fighterXX` through `fighterXXh`. Every bank is 30,720
bytes, below the 32 KiB LoROM boundary. One fifteen-color OBJ palette is shared
by that fighter's complete 64-frame set.

The first neutral frame of each new atlas is normalized once against the
fighter's existing idle frame. That establishes one physical scale for all 64
frames. The original 48 frame pixels and palette bytes remain locked; the new
range is normalized at the established scale. The result stays inside the
94x77 safe area of the 96x80 canvas with a native feet baseline at height 78.
The renderer never rescales a pose independently, so a wide kick, rush,
throw, knockdown or wake pose does not change the fighter's apparent size.

Each fighter has a private animation clock. Idle uses four frames, forward and backward gait use four frames each, and crouch, jump and landing have explicit transitions. Normals and specials expose windup, active and recovery frames, while guard, hurt, victory and knockout have their own transitions. Gait advances from distance travelled, and the clock freezes during pause and hitstop.

`tools/fighter_assets.py` keeps the twelve identity masters, palettes and
costumes separate. All twelve identity masters remain selected, including
Reston's v3 short-hair correction. The twelve new airborne atlases are
generated with the built-in imagegen workflow; each `animation-airborne.json`
records its prompt and provenance, while the earlier motion/action metadata is
retained. Raster resizing, palette quantization and tile encoding are
deterministic hardware steps after authoring.

The v0.5 stage pipeline loads three independent PNG masters from `assets/art/stages/`, with `assets/art/stages/stages.json` describing their source metadata. The home screen, four-by-three fighter selection and arena plates use original art under `assets/art/menu/`, with prompts in `assets/art/menu/prompts.json`. Menu lettering is rendered from the project's original bitmap glyph set. Selected 64x80 profile portraits use a dedicated BG2 block and palette 1. Images use nearest-neighbor reduction to retain hard edges. `assets/generated/character-manifest.json` records source hashes, palette values, extraction boxes, uniform scales and native frame hashes for review.

## Simulation

Combat uses integer 12.4 fixed-point positions. Standing, crouching and airborne bodies use feet-relative contact rectangles independent of the 96x80 art canvas. The body half-width is ten pixels; action-specific vertical bands intersect the standing or crouching body. Throws use their exact profile range without the normal-attack reach padding. Equal-center overlaps and post-impact stage clamps are symmetric. Each attack has startup, active and recovery durations. Push boxes, direction, height, guard type and one-hit confirmation determine contact. Both normal-hit candidates are collected before resolving damage, allowing trades. Projectiles have independent lifetime, position and collision.

Input is sampled every simulation tick. Opposite horizontal or vertical directions resolve to neutral before movement and command recognition. Attack and jump edges have a six-tick buffer; a held Up input can carry a buffered jump through landing. A character special accepts a true twelve-tick Down -> Down+Forward -> Forward + punch motion, while the accessible Down + punch shortcut remains. The shortcut requires no Back direction, so Down + Back + punch is not treated as a special. Normals confirmed by real damage can cancel into heavier normals or a character special during their cancel window; a guarded contact does not enable these hit-confirm cancels.

Hitstop freezes combat expiry, movement, animation clocks and effect clocks while
input edges continue to be sampled for the buffer. Guard stun is eight ticks
with approximately one pixel of blocked pushback; a real hit uses approximately
two pixels. Air punch and kick each have dedicated anticipation, active and
recovery art. Heavy uppercuts, heavy low kicks and rising specials can start a
knockdown sequence. Throws use separate thrower/victim poses, delay damage until
ground impact, and tech when both players throw on the same contact snapshot.
The downed flow distinguishes lift, flight, floor, get-up and wake; wake grants
four invulnerability ticks and accepts buffered attack or jump input during its
final six ticks. Training reset clears active throw/down/wake state, and health
recovery is gated until the fighter is free of hurt and wake invulnerability.

The game caches both active profile pointers when loading the fighters. Combat helpers reuse them instead of resolving a twelve-way roster lookup for every timing, collision and trace read. The rules and frame-data tables remain shared while every fighter keeps individual movement, jump, throw, normal and special tuning.

Direct contact outcomes are `0` none, `1` guarded and `2` real damage. Projectile
impacts do not mark an unrelated current normal as confirmed. A combo links only
while the defender remains in unblocked hit stun; its 45-tick banner timer is
cosmetic. Blocking breaks the attacking chain, and receiving a real hit clears
the defender's previous chain and stale input buffers. Inputs sampled after the
impact during hitstop retain the existing six-tick buffering semantics.

Fight hints occupy BG2 rows 26-27 during the first intro only. A separate dirty
flag clears these 128 bytes without forcing a full interface transfer alongside
the actor upload. Results place the P1/P2 round score on row 15 and quote on 17.

The CPU samples one decision per live tick using distance, opponent attack state, projectiles, a deterministic PRNG and three difficulty levels. Its neutral facing is updated before that decision. It obeys the same attack startup, active and recovery rules as the player. Fighter selection, arcade progression, training reset and menu navigation remain native controller actions.

## Audio

The generator writes original Impulse Tracker modules with five synthesized PCM
samples. `smconv` creates the soundbank and SNESMod runs the music on the
emulated SPC700. Combat audio uses four resident SPC effects loaded alongside
each music module: `effects.it` occupies soundbank module 0, while music keeps
module IDs 1-4. Scene load calls `spcLoadEffect(0)` through `spcLoadEffect(3)`
to populate resident effect slots. `spcAllocateSoundRegion(0)` disables the
separate streaming region. Gameplay uses
`spcEffect` with pitch 2 at 8 kHz and the existing volume/pan values, preserving
the synthesized cues while avoiding per-hit BRR streaming stalls.

If several cues arrive on the same simulation frame, the sound path coalesces
them by priority: round, impact, special, then swing. The generated effects-first
module order is checked at compile time; scene loading reloads the four effect
slots after replacing the music module. The resident-effect migration is part of
the unverified v0.6 integration.

## Verification

`tools/emulator.py` hosts the official Snes9x 1.63 x64 libretro core. `tools/test_rom.py` supplies SNES controller inputs, captures actual video/audio and reads a reserved WRAM trace at `$7FFF00`. The host never writes game memory. Sprite checks compare actual emulated VRAM with the cartridge's encoded bytes.

`tools/test_characters.py` adds controller-driven verification of each fighter on
both player sides, movement and jump differences, observable special-family
behavior, exact rows from all eight sprite banks and the uniform 96x80
proportion contract. `tools/test_presentation.py` verifies the home screen,
four-by-three selection navigation, all twelve 64x80 profile portrait transfers
and all three stage plates. `tools/test_inputs.py` covers SOCD neutralization,
buffered attacks and jumps, true and shortcut motion commands, hitstop input
capture, hit-confirm cancels, guard timing, animation freezing and the Training
Select reset. The latest v0.6 snapshot has all four reports passing against
ROM SHA256 `0d907717d284c9d0056434e69da0a265c2b09cf4c84761aa32998b4fc0bbd5ae`:
2,595 gameplay, 18,085 roster, 215 presentation and 604 focused-input checks
(21,499 total). The canonical silent `Test.cmd` batch passed on that image; all
four suites capture audio data without opening an audio device or a native
window and preserve the user's foreground focus.

Each suite stores the tested ROM SHA256 in its report:

- `docs/test-report.json`
- `docs/character-test-report.json`
- `docs/presentation-test-report.json`
- `docs/input-test-report.json`

The reports are authoritative for the exact ROM SHA recorded in each file. The
canonical v0.6.0 batch points all four reports to
`0d907717d284c9d0056434e69da0a265c2b09cf4c84761aa32998b4fc0bbd5ae`; the
batch covers both boot phases, two-controller air/trades/combo cadence and
resident-audio probes. The cadence probe and native screenshot/GIF evidence
remain tied to their recorded ROM hash and must not be reused after a hash
change.

An earlier four-family 600-frame probe was too narrow to characterize worst-case
audio or UI timing. Two-actor attack/impact scenarios exposed additional lag,
which is why that probe is not used as worst-case evidence. The canonical batch
covers the current suite evidence; broader human and independent-engine review
remains part of the open polish gates.

Two issues found during earlier integration shaped the implementation:

1. C-level row-by-row sprite uploads exceeded vblank, leaving lower sprite rows blank. The native assembly transfer and one-pose budget fixed this class of failure; current validation still checks every row.
2. This pinned 816-tcc build incorrectly lowers logical-OR expressions with
   three or more terms, including knockout resolution and hurt/down/air
   eligibility. Use individual branches. The build lint rejects new `||` chains
   with three or more terms in project C/headers. A related real-hitstun guard
   correction gates blocked eligibility with `(!d->hurt || d->guard)`: a new hit
   cannot become a guard during real hitstun, while existing guard stun remains
   blockable; real hits also clear guard. Native tests cover contact, guard,
   downed control, facing, round, timeout and arcade outcomes.

The packager requires all four successful reports to match the current ROM before
producing the offline archive; the canonical snapshot satisfies that exact-ROM
evidence gate. Human balance sessions, art review, independent Mesen/bsnes runs,
real-console/flash-cartridge testing and public-release review remain separate
open gates.
