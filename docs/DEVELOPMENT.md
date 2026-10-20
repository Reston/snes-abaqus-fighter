# Native SNES implementation

## Build

Supported build host: Windows x64. `tools/setup.ps1` downloads pinned official release archives into `.tools/` and verifies their SHA256. `tools/build.py` invokes 816-tcc, 816-opt, WLA-65816 and WLALINK directly, so a separate Make/MSYS installation is unnecessary.

The v0.5.0 ROM target is a 4 MiB FastROM LoROM image across 128 banks, NTSC, with no coprocessor or SRAM requirement. WLALINK writes the SNES header/checksum. The build independently checks the FastROM LoROM mapping byte, image size and calculated checksum before writing `dist/manifest.json`.

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

### Fighter animation contract

Every fighter has 48 uniform 96x80 native frames, for 576 roster frames total. The shared index contract is:

| Frame range | Content |
| --- | --- |
| `0-15` | Legacy neutral, walk, crouch, jump, normal, guard, hurt, victory, cast, uppercut, knockout and rush key poses |
| `16-31` | Motion and transition atlas: idle, forward gait, backward gait, crouch, jump and landing transitions |
| `32-47` | Action atlas: normal windup/active/recovery, specials, guard, hurt, victory and knockout transitions |

The two new source atlases are `animation-motion.png` and `animation-actions.png` under each fighter directory. Each is a 1254x1254 RGBA sheet with sixteen separately extracted figures in a four-by-four grid. The pipeline places the figures in uniform 96x80 native cells. The generated native review strip `assets/generated/fighterXX.png` is 4,608x80 RGBA, and the encoded frame data is divided into six contiguous eight-frame banks: `fighterXX`, `fighterXXb`, `fighterXXc`, `fighterXXd`, `fighterXXe` and `fighterXXf`. Every bank is 30,720 bytes, below the 32 KiB LoROM boundary. One fifteen-color OBJ palette is shared by that fighter's complete 48-frame set.

The first neutral frame of each new atlas is normalized once against the fighter's existing idle frame. That establishes one physical scale for all 48 frames. The result stays inside the 94x77 safe area of the 96x80 canvas with a native feet baseline at height 78. The renderer never rescales a pose independently, so a wide kick, rush or knockout does not change the fighter's apparent size.

Each fighter has a private animation clock. Idle uses four frames, forward and backward gait use four frames each, and crouch, jump and landing have explicit transitions. Normals and specials expose windup, active and recovery frames, while guard, hurt, victory and knockout have their own transitions. Gait advances from distance travelled, and the clock freezes during pause and hitstop.

`tools/fighter_assets.py` keeps the twelve identity masters, palettes and costumes separate. All twelve legacy masters remain selected in v0.5, including Reston's v3 short-hair correction. The new animation atlases are generated with the built-in imagegen workflow; each `animation.json` records its prompt and provenance. Raster resizing, palette quantization and tile encoding are deterministic hardware steps after authoring.

The v0.5 stage pipeline loads three independent PNG masters from `assets/art/stages/`, with `assets/art/stages/stages.json` describing their source metadata. The home screen, four-by-three fighter selection and arena plates use original art under `assets/art/menu/`, with prompts in `assets/art/menu/prompts.json`. Menu lettering is rendered from the project's original bitmap glyph set. Selected 64x80 profile portraits use a dedicated BG2 block and palette 1. Images use nearest-neighbor reduction to retain hard edges. `assets/generated/character-manifest.json` records source hashes, palette values, extraction boxes, uniform scales and native frame hashes for review.

## Simulation

Combat uses integer 12.4 fixed-point positions. Each attack has startup, active and recovery durations. Push boxes, direction, height, guard type and one-hit confirmation determine contact. Both normal-hit candidates are collected before resolving damage, allowing trades. Projectiles have independent lifetime, position and collision.

Input is sampled every simulation tick. Opposite horizontal or vertical directions resolve to neutral before movement and command recognition. Attack and jump edges have a six-tick buffer; a held Up input can carry a buffered jump through landing. A character special accepts a true twelve-tick Down -> Down+Forward -> Forward + punch motion, while the accessible Down + punch shortcut remains. The shortcut requires no Back direction, so Down + Back + punch is not treated as a special. Confirmed normals can cancel into heavier normals or a character special during their cancel window.

Hitstop freezes combat expiry, movement, animation clocks and effect clocks while input edges continue to be sampled for the buffer. Guard stun is eight ticks with approximately one pixel of blocked pushback; a real hit uses approximately two pixels. The air-normal path uses a legacy attack key pose plus a generic transition frame; dedicated air-specific art remains future work.

The game caches both active profile pointers when loading the fighters. Combat helpers reuse them instead of resolving a twelve-way roster lookup for every timing, collision and trace read. The rules and frame-data tables remain shared while every fighter keeps individual movement, jump, throw, normal and special tuning.

The CPU uses distance, opponent attack state, projectiles, a deterministic PRNG and three difficulty levels. It obeys the same attack startup, active and recovery rules as the player. Fighter selection, arcade progression, training reset and menu navigation remain native controller actions.

## Audio

The generator writes original Impulse Tracker modules with five synthesized samples. `smconv` creates the soundbank. SNESMod runs the music on the emulated SPC700. Short original sound effects are encoded to BRR and streamed through a reserved sound region. The sound table is explicitly reset to the first entry after initialization; otherwise later indexes would read beyond the table.

## Verification

`tools/emulator.py` hosts the official Snes9x 1.63 x64 libretro core. `tools/test_rom.py` supplies SNES controller inputs, captures actual video/audio and reads a reserved WRAM trace at `$7FFF00`. The host never writes game memory. Sprite checks compare actual emulated VRAM with the cartridge's encoded bytes.

`tools/test_characters.py` adds controller-driven verification of each fighter on both player sides, movement and jump differences, observable special-family behavior, exact rows from all six sprite banks and the uniform 96x80 proportion contract. `tools/test_presentation.py` verifies the home screen, four-by-three selection navigation, all twelve 64x80 profile portrait transfers and all three stage plates. `tools/test_inputs.py` covers SOCD neutralization, buffered attacks and jumps, true and shortcut motion commands, hitstop input capture, hit-confirm cancels, guard timing, animation freezing and the Training Select reset. All four suites capture audio data without opening an audio device or a native window; they preserve the user's foreground focus.

Each suite stores the tested ROM SHA256 in its report:

- `docs/test-report.json`
- `docs/character-test-report.json`
- `docs/presentation-test-report.json`
- `docs/input-test-report.json`

The reports are authoritative only when all four point to the exact current 4 MiB ROM. v0.5.0 passes 5,020 checks: 188 gameplay, 4,574 roster/animation, 161 presentation and 97 input. The cadence probe records 600 game ticks over 600 emulated frames. Screenshots and the 36 animation GIFs under `docs/screenshots/` come from the emulator, not composited game mockups.

Two issues found during earlier integration shaped the implementation:

1. C-level row-by-row sprite uploads exceeded vblank, leaving lower sprite rows blank. The native assembly transfer and one-pose budget fixed this class of failure; current validation still checks every row.
2. This 816-tcc build incorrectly lowered a chain of three negated `||` operands in the knockout condition. The condition uses explicit branches, with end-to-end round, timeout and arcade coverage in the gameplay suite.

The packager requires all four successful reports to match the current ROM before producing the offline archive. Real-console, flash-cartridge and additional-emulator verification remain on the roadmap, as do human balance sessions and more character-specific in-between art.
