# Native SNES implementation

## Build

Supported build host: Windows x64. `tools/setup.ps1` downloads pinned official release archives into `.tools/` and verifies their SHA256. `tools/build.py` invokes 816-tcc, 816-opt, WLA-65816 and WLALINK directly, so a separate Make/MSYS installation is unnecessary.

The v0.4 ROM is a 2 MiB FastROM LoROM image across 64 banks, NTSC, with no coprocessor or SRAM requirement. WLALINK writes the SNES header/checksum. The build independently checks the FastROM LoROM mapping byte, image size and calculated checksum before writing `dist/manifest.json`.

`Build.cmd` rebuilds from committed native assets. `Build.cmd --assets` regenerates the full asset set first. Source portrait downloads can be refreshed with `tools/fetch_references.py`; rebuilding the game does not require fetching the team pages.

## Rendering

The PPU uses Mode 1. BG1 holds the stage; BG2 holds the interface and selected profile portrait. Stage tiles use six 16-color palette banks (15 opaque colors each). The interface reserves the first two palette banks, and the large profile portrait uses BG2 palette 1. Fighter and effect palettes occupy OBJ CGRAM.

| VRAM word address | Contents |
| --- | --- |
| `$0000–$37FF` | BG1 stage tiles, at most 896 4bpp tiles |
| `$3800–$3BFF` | BG1 32×32 tilemap |
| `$4000–$49FF` | BG2 interface/font tiles |
| `$4A00–$4EFF` | Selected 64×80 profile portrait, an eight-by-ten 4bpp tile block using BG2 palette 1 |
| `$5800–$5BFF` | BG2 interface tilemap |
| `$6000–$69FF` | Actor 0 padded frame page; 3,840-byte pose stream plus blank row padding |
| `$6A00–$73FF` | Actor 1 padded frame page; 3,840-byte pose stream plus blank row padding |
| `$7800–$7BFF` | Impact, projectile and shadow tiles |

Each actor uses thirty 16×16 hardware sprites: six columns by five rows. Actor 0 begins at OAM byte 0 and actor 1 at OAM byte 128, with two padded slots per actor block. The 65816 renderer writes an actor's OAM entries in one call. A strided DMA routine streams one 3,840-byte 96×80 pose into the actor's padded VRAM page, leaving the page's blank tail predictable. Each vblank streams at most one actor frame, alternating priority if both change together. The second actor can visually trail its requested pose by one video frame; combat state stays independent of that upload queue.

OBJSEL uses the 8/16 size pair; all live pieces select its 16-pixel size. The renderer packs each actor's repeating six-column X9 pattern once, then writes tile/attribute pairs together. Source-bank selection and pose-offset arithmetic happen before `WaitForVBlank`; the blanking interval only executes the prepared DMA and interface transfers. The HUD caches health, energy, wins and seconds, updating only changed fields and partial energy tiles to preserve the simulation budget.

`tools/fighter_assets.py` prepares twelve separate master atlases under `assets/art/characters/`. Master sprites are isolated by connected-component labels and scaled once per fighter for all sixteen poses. The uniform result fits a 94×77 safe area inside the 96×80 native canvas; a fighter's effective standing height can therefore be lower than its requested height when another pose is wider or taller. Each fighter has a close 32×40 card portrait and a 64×80 profile portrait, both derived from the same source master. The sixteen poses are quantized to fifteen opaque colors per fighter and divided into two eight-pose ROM banks. Isolating each alpha mask avoids neighboring pose pixels inside a crop rectangle. Translucent source fringes are rejected before isolation. Each palette is derived from that fighter's opaque pixels across all sixteen poses, and the native preview uses the SNES's five-bit color precision. Each contiguous pose bank stays below the 32 KiB LoROM boundary.

The v0.4 stage pipeline loads three independent PNG masters from `assets/art/stages/`, with `assets/art/stages/stages.json` describing their source metadata. The v0.4 menu pipeline composes the authored home, four-by-three fighter select and arena plates from `assets/art/menu/`. Selected 64×80 profile portraits use a dedicated BG2 block and palette 1. All final menu lettering uses the project's original bitmap glyph set, so the native build no longer depends on Arial. Images use nearest-neighbor reduction to retain hard edges. `assets/generated/character-manifest.json` records source hashes, palette values, extracted source boxes, uniform scales and native pose hashes for review.

## Simulation

Combat uses integer 12.4 fixed-point positions. Each attack has startup, active and recovery durations. Push boxes, direction, height, guard type and one-hit confirmation determine contact. Both normal-hit candidates are collected before resolving damage, allowing trades. Projectiles have independent lifetime, position and collision.

The game has a redesigned home screen, a four-by-three fighter selection with a large profile portrait, arena selection, match and result screens. Fighter selection supports horizontal movement and ±4-row navigation across the three rows. Matches contain intro, live combat, pause and round-end phases. Arcade selects the eleven other roster entries and rotates the three independent arenas.

The CPU uses distance, opponent attack state, projectiles, a deterministic PRNG and three difficulty levels. It obeys the same attack startup, energy and hit rules as the player. `src/characters.h` provides individual normal frame data, movement, jumps, throws and tuned projectile/rush/low-shockwave/rising specials; the rules and pose indices remain shared.

The match caches both active profile pointers when loading the fighters. Combat helpers reuse them instead of resolving a twelve-way roster lookup for every timing, collision and trace read. The profile pass keeps the native cadence stable while the renderer uses the single 96×80 pose contract.

## Audio

The generator writes original Impulse Tracker modules with five synthesized samples. `smconv` creates the soundbank. SNESMod runs the music on the emulated SPC700. Short original sound effects are encoded to BRR and streamed through a reserved sound region. The sound table is explicitly reset to the first entry after initialization; otherwise later indexes would read beyond the table.

## Verification

`tools/emulator.py` hosts the official Snes9x 1.63 x64 libretro core. `tools/test_rom.py` supplies SNES controller inputs, captures actual video/audio and reads telemetry from reserved WRAM `$7FFF00`. The host never writes game memory. Sprite checks compare actual emulated VRAM with the cartridge's encoded bytes.

`tools/test_characters.py` adds controller-driven verification of each fighter on both player sides, movement and jump differences, observable special-family behavior, exact rows from both sprite banks and the uniform 96×80 proportion contract. `tools/test_presentation.py` verifies the home screen, four-by-three selection navigation, all twelve 64×80 profile portrait transfers and all three stage plates. All three suites capture audio data without opening an audio device or a native window. They preserve the user's foreground focus.

Each suite stores the tested ROM SHA256 in its report (`docs/test-report.json`, `docs/character-test-report.json` and `docs/presentation-test-report.json`). Run results are authoritative only when all three reports point to the exact current `dist/abaqus-after-hours.sfc`; do not infer pass counts from source inspection. Screenshots under `docs/screenshots/` come from the emulator, not composited game mockups.

Two issues found during integration testing shaped the implementation:

1. C-level row-by-row sprite uploads exceeded vblank, leaving lower sprite rows blank. The native assembly transfer and one-pose budget fixed this; the suite checks every row for every fighter.
2. This 816-tcc build incorrectly lowered a chain of three negated `||` operands in the knockout condition. The condition now uses explicit branches, with end-to-end best-of-three, timeout and arcade tests covering the resulting transitions.

The ROM has been tested in emulation during earlier releases. Real-console, flash-cartridge and additional-emulator verification remain on the roadmap. The v0.4 presentation and proportion reports must be generated against the final 2 MiB ROM before packaging.
