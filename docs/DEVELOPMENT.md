# Native SNES implementation

## Build

Supported build host: Windows x64. `tools/setup.ps1` downloads pinned official release archives into `.tools/` and verifies their SHA256. `tools/build.py` invokes 816-tcc, 816-opt, WLA-65816 and WLALINK directly, so a separate Make/MSYS installation is unnecessary.

The v0.7.0 integration targets a 4 MiB FastROM LoROM image across 128 banks,
NTSC, with no coprocessor or SRAM requirement. WLALINK writes the SNES
header/checksum. The build independently checks the FastROM LoROM mapping byte,
image size and calculated checksum before writing `dist/manifest.json`. The
current ROM SHA256 is
`e44a739488bd549cfcffbe35bbb32bb5e71d9d2dce12bea6562ebd3dd0c15b84`, with
header checksum `0953`. The five native reports pass with 2,595 gameplay,
18,085 roster, 215 presentation, 854 focused-input and 4,537 stage checks
(26,286 total in the current report snapshot). The separate pinned bsnes2014
Accuracy smoke report passes against the same SHA. `Build.cmd --assets` has
reproduced this SHA. The CPU distance/reaction, crouch-guard and stage/effect
checks are verified without changing fighter profile data or the native ABI.
The offline archive passes 214 technical audit checks and repeated packaging
produces identical ZIP bytes.

`Build.cmd` rebuilds from committed native assets. `Build.cmd --assets` regenerates the full asset set first. Source portrait downloads can be refreshed with `tools/fetch_references.py`; rebuilding the game does not require fetching the team pages.

## Rendering

The PPU uses Mode 1. BG1 holds the stage; BG2 holds the interface and selected profile portrait. Stage tiles use six 16-color palette banks (15 opaque colors each). The interface reserves the first two palette banks, and the large profile portrait uses BG2 palette 1. Fighter and effect palettes occupy OBJ CGRAM.

| VRAM word address | Contents |
| --- | --- |
| `$0000-$37FF` | BG1 stage tiles, at most 896 4bpp tiles |
| `$3800-$3BFF` | BG1 32x32 tilemap |
| `$3C00-$3C7F` | v0.7 dynamic BG1 ambient tiles: eight tiles, one 256-byte phase |
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

`src/trace.asm` writes the read-only combat telemetry at the stable
`TRACE[0..113]` offsets and the ambient stores at `TRACE[115..118]`. `main`
samples post-wait PPU `STAT77` into `TRACE[114]` before DMA. A change to the
native `Fighter` or `Wave` struct layout therefore requires updating the
assembly offsets and the documented trace contract together; the C fields alone
are not a safe layout change. The Fighter/Wave ABI at `0..113` is unchanged.

### v0.7 stage/effect integration notes

The stage/effect pass is implemented and verified in the current ROM. Each of
the three stages has four original,
code-native ambient phases. A phase is eight 4bpp BG1 tiles (256 bytes) at
indices `960..967`, uploaded at VRAM word `$3C00`; each 256-byte phase occupies
VRAM words `$3C00-$3C7F`. The original stage graphics, tilemap
masters and palette masters are unchanged. Las Condes uses leaf shimmer and
glass reflection, El Castillo uses string lights, a party gesture and window
light, and La Oficina uses left and right monitor changes.

The ambient phase request advances every 16 live combat frames and is frozen
during intro, pause, hitstop and round-end states. An ambient upload yields to
the one-actor-per-vblank transfer and interface DMA, so it adds no actor or OBJ
budget and can complete after the request. `main` captures post-wait `STAT77`
in `TRACE[114]`; `TRACE[115..118]` expose completed phase, live clock, pending phase
and pending age for read-only diagnostics.

The original native effect cells now have authored phase variants for strike,
guard contact, high projectile and ground wave. The shadow ellipse was moved
down to the floor-visible rows and raised in OAM priority while retaining its
lower ink rows. `tools/stage_assets.py`, `tools/effect_assets.py` and
`tools/test_stages.py` document the deterministic asset and verification paths.
The instrumented `STAT77` bit-7 overflow baseline has ROM SHA prefix `868f7dc` with
two low waves. The v0.7 native stage report records 4,537 checks against the
current SHA, including the nine focused patch-only PPU assertions added after
the canonical `Test.cmd` run's 4,528 stage checks. The separate compatibility
smoke covers all three stages and actual PPU phases, freeze behavior and
synchronized low-wave combat against the same SHA. The v0.7 archive passes
214 technical checks and repeated packaging produces identical ZIP bytes.

The focused PPU phase captures observed changed-pixel counts of `17/18/18` for
Las Condes, `13/16/13` for El Castillo and `8/8/8` for La Oficina across
phases 1-3; phase 0 is the source-identical baseline. The synchronized
two-wave check peaked at 28 tiles (14 sprites), with `STAT77` equal to `0x01`
and overflow mask `0xC0` clear.

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

The CPU samples one decision per live tick using distance, opponent attack
state, projectiles, a deterministic PRNG and three difficulty levels. Its
neutral facing is updated before that decision. The verified v0.6.1 logic checks
the opponent's upcoming active window at `tick+1` because controller capture
precedes physics, prioritizes approaching waves within 96 native pixels, and
uses family-specific special distance bands. Normal and Hard crouch-guard low
waves, while the same levels send a wake jump edge at `DOWN_WAKE` tick 0. The
approach branch closes the 29-46 pixel gap, and throw decisions use each
profile's `throwRange`. Crouch guard selects animation frame 3 so the visible
pose matches logical guard pose 9. Input coverage exercises all three
difficulties and four special families for 600 live ticks each, with near/far,
approach, low-guard, wake and strict no-KO lookahead cases. These are CPU
correctness checks, not a strategic-AI or balance-completion claim.
Fighter selection, arcade progression, training reset and menu navigation remain
native controller actions.

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
slots after replacing the music module. The resident-effect migration is
included in the verified v0.6.1 baseline; the CPU pass does not change the
audio path.

## Verification

`tools/emulator.py` hosts the official Snes9x 1.63 x64 libretro core. `tools/test_rom.py` supplies SNES controller inputs, captures actual video/audio and reads a reserved WRAM trace at `$7FFF00`. The host never writes game memory. Sprite checks compare actual emulated VRAM with the cartridge's encoded bytes.

`tools/test_characters.py` adds controller-driven verification of each fighter on
both player sides, movement and jump differences, observable special-family
behavior, exact rows from all eight sprite banks and the uniform 96x80
proportion contract. `tools/test_presentation.py` verifies the home screen,
four-by-three selection navigation, all twelve 64x80 profile portrait transfers
and all three stage plates. The v0.7 `tools/test_stages.py` suite adds native
checks for the four-phase BG1 ambient tiles, dynamic map entries, source
palette/graphics preservation, live-only phase timing, actor/interface DMA
yields, pause/hitstop/round-end freezes and stage effect/OAM behavior. It has
passed against the current ROM. The canonical `Test.cmd` stage portion recorded
4,528 checks; a focused extension added nine patch-only PPU assertions and
reran the unchanged ROM/engine, so the current stage report records 4,537.
`tools/test_inputs.py` covers SOCD neutralization,
buffered attacks and jumps, true and shortcut motion commands, hitstop input
capture, hit-confirm cancels, guard timing, animation freezing and the Training
Select reset. The current v0.7.0 snapshot has all five native reports passing
against ROM SHA256
`e44a739488bd549cfcffbe35bbb32bb5e71d9d2dce12bea6562ebd3dd0c15b84`:
2,595 gameplay, 18,085 roster, 215 presentation, 854 focused-input and 4,537
stage checks (26,286 total in the current report snapshot). The canonical
silent `Test.cmd` batch passed on that image; its stage portion recorded 4,528
checks, then the focused stage extension added nine patch-only PPU assertions
and reran the unchanged ROM/engine. All five suites capture audio data without
opening an audio device or a native window and preserve the user's foreground
focus. Input coverage spans three difficulties and four special families for
600 live ticks each (7,200 total), plus near-special, far-negative, 29-46
approach, low-guard, wake and strict no-KO lookahead cases.

The separate `docs/compatibility-test-report.json` passes against the same ROM
SHA using the pinned bsnes2014 Accuracy core. Its scope is an independent smoke:
title/select/arena/fight captures, controller movement and jump, all three
stages across four actual PPU phases with intro/pause/hitstop/round-end freeze,
static plate color samples within eight channel levels (maximum delta 7),
synchronized low-wave combat and neutral 600-frame cadence with every delta
equal to one, plus captured audio. The low-wave probe observed 37 two-wave
frames in 600 with `STAT77` at `0x01` and overflow mask `0xC0` clear. It is not
full combat, soak or human verification. Run it with PowerShell
`tools/setup-compat.ps1` followed by `python tools/test_compatibility.py`.

The five native reports and compatibility report now carry the same current
v0.7.0 SHA. The compatibility host uses the pinned core's actual 512x224,
2048-byte-pitch BGRX callbacks with stride-authoritative decoding; this fixes
the prior pixel-format metadata limitation and makes the stage color assertions
meaningful. The v0.7 archive passes 214 technical checks and reproduces byte
for byte, while human balance,
art review, independent full-combat/soak, real-console and public-release
gates remain open.

Each suite stores the tested ROM SHA256 in its report:

- `docs/test-report.json`
- `docs/character-test-report.json`
- `docs/presentation-test-report.json`
- `docs/input-test-report.json`
- `docs/compatibility-test-report.json`
- `docs/stage-test-report.json`

The reports are authoritative for the exact ROM SHA recorded in each file. The
current v0.7.0 native reports and compatibility report point to
`e44a739488bd549cfcffbe35bbb32bb5e71d9d2dce12bea6562ebd3dd0c15b84`; the native
batch covers both boot phases, two-controller air/trades/combo cadence,
resident-audio probes, CPU reactions and stage/effect PPU behavior. The cadence
probe and native screenshot/GIF evidence remain tied to their recorded ROM hash
and must not be reused after a hash change. The v0.6.1 four-suite snapshot
remains historical evidence for the earlier SHA.

An earlier four-family 600-frame probe was too narrow to characterize worst-case
audio or UI timing. The current input suite expands CPU coverage to three
difficulties, four families and 7,200 live ticks, with explicit spacing,
low-guard, wake and no-KO lookahead cases. The independent bsnes report remains
a narrower smoke rather than full combat or soak evidence. Broader human and
independent-engine review remains part of the open polish gates.

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

3. Real KO contact resolution keeps damage, winner selection, timers and layout
   unchanged. `roundBannerPending` defers the panel, name and HUD transfer until
   the first frozen `roundEnd` tick, avoiding a contact-time stall.

The v0.6.1 packager run required its four native reports and the separate
compatibility report to match the earlier ROM; its offline package passed 202
technical audit checks and repeated packaging with identical inputs produced
identical ZIP bytes. The current v0.7.0 five native reports plus compatibility
match the exact SHA above. The v0.7 archive passes 214 technical checks;
repeated packaging with identical inputs produces identical ZIP bytes.
Human balance sessions, art review, independent Mesen/bsnes combat runs,
real-console/flash-cartridge testing and public-release review remain separate
open gates.
