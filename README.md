# Abaqus: After Hours

An original six-button fighting game for the **Super Nintendo**, inspired by the arcade structure of Street Fighter II and the people and places of Abaqus in Santiago.

**Current release: v0.5.1.** The cartridge is a 4 MiB NTSC FastROM LoROM image across 128 banks, compiled from C and 65816 assembly. It runs in Snes9x with ordinary SNES controllers. Silent native verification passes 5,073 checks across gameplay, roster animation, presentation and input feel.

The [v0.5.1 release notes](docs/RELEASE-v0.5.1.md) cover clearer fight/results screens, more consistent contact rules, truthful hit confirms and sharp emulator defaults. The [v0.5 notes](docs/RELEASE-v0.5.md) describe the 48-frame roster animation and buffered inputs.

![Abaqus After Hours](docs/screenshots/fight.png)

## Play

On Windows, double-click **[Play.cmd](Play.cmd)**. The launcher downloads the official Snes9x 1.63 release into `.tools/` on its first run, verifies its SHA256, and opens the game. No administrator account or global installation is needed. The tools are already present in this checkout.

For offline Windows play, extract [Abaqus-After-Hours-v0.5.1-Windows.zip](dist/Abaqus-After-Hours-v0.5.1-Windows.zip) and run its `Play.cmd`.

On other platforms, open **[dist/abaqus-after-hours.sfc](dist/abaqus-after-hours.sfc)** in a SNES emulator. No BIOS or commercial ROM is required.

With the included keyboard configuration:

| Action | Player 1 |
| --- | --- |
| Move / jump / crouch | Arrow keys |
| Light / medium / heavy punch | A / S / D |
| Light / medium / heavy kick | Z / X / C |
| Confirm a menu choice | X or Enter |
| Back from a menu | Z |
| Pause | Enter |
| Character special | Down, toward, then A or S |
| Rising uppercut | Down + D |
| Throw | Toward opponent + D, at close range |

See the [player guide](docs/PLAYER-GUIDE.md) for SNES button mappings, player two, buffered motion inputs, blocking and combos. Controllers can be mapped in Snes9x under **Input -> Input Configuration**.

## Included

- All 12 requested fighters, with individual illustrated identities, costumes and legacy key poses. Their identity masters remain unchanged in v0.5, including Reston's v3 short-hair correction.
- Forty-eight uniform 96x80 native frames per fighter: legacy frames 0-15, motion and transition frames 16-31, and action frames 32-47. Thirty-two new in-between frames per fighter were drawn across 24 built-in imagegen atlases and retained with their `animation.json` prompts.
- Las Condes, El Castillo and La Oficina, illustrated as original pixel-art stages from the supplied location references.
- Arcade Shift: fight the other 11 coworkers across the three locations and become Office Champion.
- Local Versus: two controllers, independent input, best-of-three matches and rematches.
- Training: a passive opponent, automatic health recovery, unlimited time and a Select quick reset.
- A clean royal-navy, white and gold home/select/arena presentation with one cursor, the same four-by-three roster grid and a large selected portrait. The selection screen keeps the focus on the fighter instead of a statistics panel.
- Six normal attacks, jumping attacks, crouching attacks, high/low blocking, throws, a universal uppercut and confirmed normal/special cancels.
- Twelve tuned specials across four families: projectile, advancing rush, low shockwave and rising strike. [Character profiles](docs/CHARACTERS.md) explain the roster and move families.
- Health, regenerating energy, round counters, timer, hitstop, impact effects, camera shake, pause, four original tracker music arrangements and original BRR sound effects.

The renderer keeps the 96x80 canvas, 94x77 safe area and one physical scale per fighter across all 48 frames. The first neutral frame of each new atlas is normalized against that fighter's old idle pose once; the resulting scale is shared by the full animation set. A fighter's baseline remains at native height 78. Each fighter's 48 frames are encoded into six 30,720-byte LoROM-safe banks (`fighterXX`, `fighterXXb` through `fighterXXf`) with a shared fifteen-color OBJ palette. More unique in-betweens, richer effects, stage parallax and extensive human balance work remain on the [polish roadmap](docs/ROADMAP.md). Hardware and flash-cartridge testing remain future work.

## Build and verify

Windows x64:

```powershell
.\Build.cmd
.\Test.cmd
```

`Build.cmd` bootstraps pinned project-local tools, then builds from the committed hardware-ready assets. To regenerate all graphics and music:

```powershell
.\Build.cmd --assets
```

The four verification suites run the actual ROM silently and headlessly in the official Snes9x libretro core: gameplay, roster, presentation and focused input. They send controller input and read WRAM/VRAM, rendered frames and captured audio without playing it. Each report records the exact tested ROM hash. Before packaging v0.5.0, all four reports must point to the same current ROM SHA256:

- `docs/test-report.json`
- `docs/character-test-report.json`
- `docs/presentation-test-report.json`
- `docs/input-test-report.json`

The [manifest](dist/manifest.json) includes the ROM SHA256 and header checksum. The v0.5.1 reports match that exact image: 188 gameplay checks, 4,574 roster/animation checks, 178 presentation checks and 133 focused input checks. The cadence probe records 600 game ticks across 600 emulated frames. Native screenshots and 36 animation GIFs are retained under `docs/screenshots/`.

## Project map

| Location | Purpose |
| --- | --- |
| `src/game.c` | Combat, input buffering, animation state, AI, menus, rounds and arcade progression |
| `src/characters.h` | Individual combat profiles and special families |
| `src/hardware.asm` | Native metasprite rendering, OAM and strided DMA |
| `src/animation_banks.h` | Six-bank fighter frame lookup for the 48-frame contract |
| `assets/art/` | Original character masters, animation atlases, independent stage PNGs and menu art |
| `assets/generated/` | Reproducible SNES tiles, six fighter banks, palettes and music |
| `tools/` | Bootstrap, encoding, build, emulator tests and packaging |
| `dist/` | Playable ROM and release manifest |
| `docs/` | Controls, technical notes, animation contract, art prompts, credits, roadmap and QA evidence |

Git tracks the source, master art, generated cartridge assets and ROM. Downloaded toolchains and release ZIPs stay outside history. Prior releases are tagged `v0.1.0`, `v0.2.0`, `v0.3.0`, `v0.3.1`, `v0.4.0`, `v0.4.1` and `v0.5.0`; the current release is tagged `v0.5.1`. No remote repository is configured by this project.

Team references: [Abaqus Solutions](https://abaqus.io/es/abaqus-solutions/team) and [Abaqus Wealth Care](https://abaqus.io/es/wealth-care/about-us). See [credits and asset provenance](docs/CREDITS.md), [art prompts](docs/ART-DIRECTION.md), and [technical notes](docs/DEVELOPMENT.md).
