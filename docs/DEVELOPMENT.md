# Native SNES implementation

## Build

Supported build host: Windows x64. `tools/setup.ps1` downloads pinned official release archives into `.tools/` and verifies their SHA256. `tools/build.py` invokes 816-tcc, 816-opt, WLA-65816 and WLALINK directly, so a separate Make/MSYS installation is unnecessary.

The ROM is 1 MiB, FastROM LoROM, NTSC, with no coprocessor or SRAM requirement. WLALINK writes the SNES header/checksum. The build independently checks the mapping byte, image size and calculated checksum before writing `dist/manifest.json`.

`Build.cmd` rebuilds from committed native assets. `Build.cmd --assets` regenerates the full asset set first. Source portrait downloads can be refreshed with `tools/fetch_references.py`; rebuilding the game does not require fetching the team pages.

## Rendering

The PPU uses Mode 1. BG1 holds the stage; BG2 holds the interface. Stage tiles use six 16-color palette banks (15 opaque colors each). The interface reserves the first two palette banks. Fighter and effect palettes occupy OBJ CGRAM.

| VRAM word address | Contents |
| --- | --- |
| `$0000–$37FF` | BG1 stage tiles, at most 896 4bpp tiles |
| `$3800–$3BFF` | BG1 32×32 tilemap |
| `$4000–$49FF` | BG2 interface/font tiles |
| `$5800–$5BFF` | BG2 interface tilemap |
| `$6000–$69FF` | Two 64×80 actor frame slots, interleaved by tile row |
| `$7800–$7BFF` | Impact, projectile and shadow tiles |

Each actor uses twenty 16×16 hardware sprites. The 65816 renderer writes an actor's OAM entries in one call. A strided DMA routine uploads ten 256-byte rows for one pose. Each vblank streams at most one actor frame, alternating priority if both change together. The second actor can visually trail its requested pose by one video frame; combat state stays independent of that upload queue.

`tools/fighter_assets.py` prepares twelve separate master atlases under `assets/art/characters/`. Master sprites are isolated by connected-component labels, scaled to individual standing heights of 66–74 pixels, quantized to fifteen opaque colors per fighter, and divided into two eight-pose ROM banks. Isolating each alpha mask avoids neighboring pose pixels inside a crop rectangle. Translucent source fringes are rejected before isolation. Each palette is derived from that fighter's opaque pixels across all sixteen poses, and the native preview uses the SNES's five-bit color precision. Each contiguous pose bank stays at 20,480 bytes, below the LoROM 32 KiB boundary.

The v0.2 stages retain their cartoon illustrations. The v0.3 selection portraits crop the upper body from each individual art master, so faces and costumes match the runtime fighter. Images use nearest-neighbor reduction to retain hard edges. `assets/generated/character-manifest.json` records source hashes, palette values, extracted source boxes and native pose hashes for review.

## Simulation

Combat uses integer 12.4 fixed-point positions. Each attack has startup, active and recovery durations. Push boxes, direction, height, guard type and one-hit confirmation determine contact. Both normal-hit candidates are collected before resolving damage, allowing trades. Projectiles have independent lifetime, position and collision.

The game has title, fighter selection, arena selection, match and result screens. Matches contain intro, live combat, pause and round-end phases. Arcade selects the eleven other roster entries and rotates the three arenas.

The CPU uses distance, opponent attack state, projectiles, a deterministic PRNG and three difficulty levels. It obeys the same attack startup, energy and hit rules as the player. `src/characters.h` provides individual normal frame data, movement, jumps, throws and tuned projectile/rush/low-shockwave/rising specials; the rules and pose indices remain shared.

The match caches both active profile pointers when loading the fighters. Combat helpers reuse them instead of resolving a twelve-way roster lookup for every timing, collision and trace read. This restored the measured idle cadence to 597 simulation ticks per 600 emulated NTSC frames after the profile pass.

## Audio

The generator writes original Impulse Tracker modules with five synthesized samples. `smconv` creates the soundbank. SNESMod runs the music on the emulated SPC700. Short original sound effects are encoded to BRR and streamed through a reserved sound region. The sound table is explicitly reset to the first entry after initialization; otherwise later indexes would read beyond the table.

## Verification

`tools/emulator.py` hosts the official Snes9x 1.63 x64 libretro core. `tools/test_rom.py` supplies SNES controller inputs, captures actual video/audio and reads telemetry from reserved WRAM `$7FFF00`. The host never writes game memory. Sprite checks compare actual emulated VRAM with the cartridge's encoded bytes.

`tools/test_characters.py` adds controller-driven verification of each fighter on both player sides, movement and jump differences, observable special-family behavior and exact rows from both sprite banks. Both suites capture audio data without opening an audio device or a native window. They preserve the user's foreground focus.

Both reports store the tested ROM SHA256. Release packaging refuses a ROM whose hash differs from either report or its manifest. Screenshots under `docs/screenshots/` come from the emulator, not composited game mockups.

Two issues found during integration testing shaped the implementation:

1. C-level row-by-row sprite uploads exceeded vblank, leaving lower sprite rows blank. The native assembly transfer and one-pose budget fixed this; the suite checks every row for every fighter.
2. This 816-tcc build incorrectly lowered a chain of three negated `||` operands in the knockout condition. The condition now uses explicit branches, with end-to-end best-of-three, timeout and arcade tests covering the resulting transitions.

The ROM has been tested in emulation. Real-console, flash-cartridge and additional-emulator verification remain on the roadmap.
