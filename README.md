# Abaqus: After Hours

An original six-button fighting game for the **Super Nintendo**, inspired by the arcade structure of Street Fighter II and the people and places of Abaqus in Santiago.

**Character likeness release: v0.3.1.** The cartridge is a 1 MiB NTSC FastROM LoROM image, compiled from C and 65816 assembly. It runs in Snes9x with ordinary SNES controllers.

Each of the twelve fighters now has an individual illustrated sixteen-pose atlas, silhouette, costume and palette in the cartoon arcade style. Matching selection portraits come from the new art masters. Public team photos serve as appearance references.

![Abaqus After Hours](docs/screenshots/fight.png)

## Play

On Windows, double-click **[Play.cmd](Play.cmd)**. The launcher downloads the official Snes9x 1.63 release into `.tools/` on its first run, verifies its SHA256, and opens the game. No administrator account or global installation is needed. The tools are already present in this checkout.

For offline play, extract `dist/Abaqus-After-Hours-v0.3.1-Windows.zip` and run its `Play.cmd`. The package contains the ROM, emulator, default controls, guide, character profiles and credits.

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
| Character special | Down + A or S |
| Rising uppercut | Down + D |
| Throw | Toward opponent + D, at close range |

See the [player guide](docs/PLAYER-GUIDE.md) for SNES button mappings, player two, motion inputs, blocking and combos. Controllers can be mapped in Snes9x under **Input → Input Configuration**.

## Included

- All 12 requested fighters, with individual illustrated bodies and sixteen poses each, matching portraits, costumes, movement, jump arcs, normal frame data, reach and throws.
- Las Condes, El Castillo and La Oficina, illustrated as original pixel-art stages from the supplied location references.
- Arcade Shift: fight the other 11 coworkers across the three locations and become Office Champion.
- Local Versus: two controllers, independent input, best-of-three matches and rematches.
- Training: passive opponent, automatic health recovery and unlimited time.
- Six normal attacks, jumping attacks, crouching attacks, high/low blocking, throws, a universal uppercut and light-to-heavy attack cancels.
- Twelve tuned specials across four families: projectile, advancing rush, low shockwave and rising strike. The selection screen displays each fighter's family; [character profiles](docs/CHARACTERS.md) explain the roster.
- Health, regenerating energy, round counters, timer, hitstop, impact effects, camera shake, pause, four original tracker music arrangements and original BRR sound effects.

The renderer and sixteen-pose index layout remain shared. More animation in-betweens, richer character-specific hit effects and extensive human balance work remain on the [polish roadmap](docs/ROADMAP.md). Hardware and flash-cartridge testing have not yet been performed.

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

Both integration suites run the actual ROM silently and headlessly in the official Snes9x libretro core. They send controller input and read WRAM/VRAM, rendered frames and captured audio without playing it. The [gameplay report](docs/test-report.json) and [roster report](docs/character-test-report.json) record the exact tested ROM hash. The [manifest](dist/manifest.json) includes the ROM SHA256 and header checksum.

A Windows GitHub Actions workflow builds the cartridge, checks its hash against the committed release, and runs the emulator suite when the repository is pushed to a remote.

## Project map

| Location | Purpose |
| --- | --- |
| `src/game.c` | Combat, AI, menus, rounds, arcade progression |
| `src/characters.h` | Individual combat profiles and special families |
| `src/hardware.asm` | Native metasprite rendering and strided DMA |
| `assets/art/` | Original generated master atlases |
| `assets/references/` | Public team portrait references and source URLs |
| `assets/generated/` | Reproducible SNES tiles, palettes, animation banks and music |
| `tools/` | Bootstrap, encoding, build, emulator tests and packaging |
| `dist/` | Playable ROM and release manifest |
| `docs/` | Controls, technical notes, art prompts, credits and QA evidence |

Git tracks the source, master art, generated cartridge assets and ROM. Downloaded toolchains and release ZIPs stay outside history. Prior releases are tagged `v0.1.0`, `v0.2.0` and `v0.3.0`; the five-character face correction is `v0.3.1`. No remote repository is configured by this project.

Team references: [Abaqus Solutions](https://abaqus.io/es/abaqus-solutions/team) and [Abaqus Wealth Care](https://abaqus.io/es/wealth-care/about-us). See [credits and asset provenance](docs/CREDITS.md), [art prompts](docs/ART-DIRECTION.md), and [technical notes](docs/DEVELOPMENT.md).
