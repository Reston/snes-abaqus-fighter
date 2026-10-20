# Abaqus: After Hours

An original six-button fighting game for the **Super Nintendo**, inspired by the arcade structure of Street Fighter II and the people and places of Abaqus in Santiago.

**Current evidence snapshot: v0.6.0 combat-animation integration.** The native
source targets a 4 MiB NTSC FastROM LoROM cartridge across 128 banks, compiled
from C and 65816 assembly. The latest four reports pass against ROM SHA256
`0d907717d284c9d0056434e69da0a265c2b09cf4c84761aa32998b4fc0bbd5ae`; the
canonical silent `Test.cmd` batch passes on that image. Public-release, human,
independent-emulator and real-console gates remain open.

The [v0.6.0 development notes](docs/RELEASE-v0.6.0.md) describe the current
64-frame roster, air attacks, throws and recovery. The
[v0.5.1 notes](docs/RELEASE-v0.5.1.md) retain the previous baseline's evidence.
Public-release gates remain open.

![Abaqus After Hours](docs/screenshots/fight.png)

## Play

On Windows, double-click **[Play.cmd](Play.cmd)**. The launcher downloads the official Snes9x 1.63 release into `.tools/` on its first run, verifies its SHA256, and opens the game. No administrator account or global installation is needed. The tools are already present in this checkout.

For offline Windows play, extract the verified development package
[Abaqus-After-Hours-v0.6.0-Windows.zip](dist/Abaqus-After-Hours-v0.6.0-Windows.zip)
and run its `Play.cmd`. It includes the current ROM, emulator, controls,
four exact-ROM reports and license notices. Public-release gates remain open.

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

- All 12 requested fighters, with individual illustrated identities, costumes and legacy key poses. Their identity masters remain unchanged through v0.6, including Reston's v3 short-hair correction.
- Sixty-four uniform 96x80 native frames per fighter: legacy frames 0-15, motion and transition frames 16-31, action frames 32-47, and airborne/throw/knockdown frames 48-63. Twelve new airborne atlases supply dedicated air punch and air kick anticipation, active and recovery drawings plus throw and wake art; each keeps its `animation-airborne.json` prompt and provenance.
- Las Condes, El Castillo and La Oficina, illustrated as original pixel-art stages from the supplied location references.
- Arcade Shift: fight the other 11 coworkers across the three locations and become Office Champion.
- Local Versus: two controllers, independent input, best-of-three matches and rematches.
- Training: a passive opponent, gated automatic health recovery, unlimited time and a Select quick reset that clears active throw/knockdown state.
- A clean royal-navy, white and gold home/select/arena presentation with one cursor, the same four-by-three roster grid and a large selected portrait. The selection screen keeps the focus on the fighter instead of a statistics panel.
- Six normal attacks, dedicated air punch/kick transitions, crouching attacks, high/low blocking, throws with delayed impact damage and simultaneous throw tech, a universal uppercut and confirmed normal/special cancels.
- Twelve tuned specials across four families: projectile, advancing rush, low shockwave and rising strike. [Character profiles](docs/CHARACTERS.md) explain the roster and move families.
- Health, regenerating energy, round counters, timer, hitstop, impact effects, camera shake, pause, four original tracker music arrangements and four resident SPC combat effects using the same synthesized cues.

The renderer keeps the 96x80 canvas, 94x77 safe area, native baseline 78 and
one physical scale per fighter across all 64 frames. The legacy 48 frame
pixels and shared fifteen-color OBJ palette are locked; the new airborne range
is normalized at the established scale. Each fighter's data is encoded into
eight 30,720-byte LoROM-safe banks (`fighterXX` through `fighterXXh`) and the
native review strip is 6,144x80 RGBA. Distinct lift, flight, floor, get-up and
wake states, four wake-invulnerability ticks and a final six-tick wake input
buffer are part of the v0.6 source integration. More human balance review,
stage parallax and hardware verification remain on the [polish roadmap](docs/ROADMAP.md).

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

The four verification suites run the actual ROM silently and headlessly in the official Snes9x libretro core: gameplay, roster, presentation and focused input. They send controller input and read WRAM/VRAM, rendered frames and captured audio without playing it. Each report records the exact tested ROM hash. After the v0.6.0 build, all four reports must point to the same current ROM SHA256 before packaging:

- `docs/test-report.json`
- `docs/character-test-report.json`
- `docs/presentation-test-report.json`
- `docs/input-test-report.json`

The [manifest](dist/manifest.json) includes the ROM SHA256 and header checksum.
The latest v0.6.0 snapshot has all four reports passing against
`0d907717d284c9d0056434e69da0a265c2b09cf4c84761aa32998b4fc0bbd5ae`: 2,595
gameplay, 18,085 roster, 215 presentation and 604 focused-input checks, or
21,499 total. The canonical silent `Test.cmd` batch passed against this exact
snapshot, including both boot phases, two-controller air/trades/combo cadence
and resident-audio probes. Native screenshots and animation review captures are
retained under `docs/screenshots/`.

An earlier four-family 600-frame probe was too narrow to characterize worst-case
timing. Two-actor attack/impact scenarios exposed additional audio and interface
lag, so that probe is not treated as worst-case evidence. Public-release gates
remain open after the resident-effect audio migration.

The v0.6 native fast path caches actor-bank and per-action timing selection,
uses compile-checked `Fighter` stride 64 and `Wave` stride 16 layouts, and
caches unchanged OAM/shadow work by integer position and facing. Health and
energy bars retain their native glyph formulas. Impact HUD and empty-banner
clears continue through hitstop ticks, while interface DMA yields when an actor
frame is uploaded; the engine and VRAM contract stay unchanged. As a result,
interface impact feedback may settle one to three video frames after the combat
event while hitstop keeps the fight state frozen.

Combat sound effects now load as four resident SPC slots alongside the music:
`effects.it` is soundbank module 0 and music modules remain IDs 1-4. Scene load
uses `spcLoadEffect0..3`; gameplay calls `spcEffect` at pitch 2 and 8 kHz with
the existing volumes and pan. Same-frame cues coalesce by priority—round,
impact, special, then swing—to avoid competing effect streams. This replaces
the streamed-BRR path that stalled under two simultaneous attack/impact cases.

## Project map

| Location | Purpose |
| --- | --- |
| `src/game.c` | Combat, input buffering, animation state, AI, menus, rounds and arcade progression |
| `src/characters.h` | Individual combat profiles and special families |
| `src/hardware.asm` | Native metasprite rendering, OAM and strided DMA |
| `src/trace.asm` | Direct read-only telemetry stores at stable trace offsets `0..113` |
| `src/animation_banks.h` | Eight-bank fighter frame lookup for the 64-frame contract |
| `assets/art/` | Original character masters, animation atlases, independent stage PNGs and menu art |
| `assets/generated/` | Reproducible SNES tiles, eight fighter banks, palettes, music and resident effect data |
| `tools/` | Bootstrap, encoding, build, emulator tests and packaging |
| `dist/` | Playable ROM and release manifest |
| `docs/` | Controls, technical notes, animation contract, art prompts, credits, roadmap and QA evidence |

Git tracks the source, master art, generated cartridge assets and ROM. Downloaded toolchains and release ZIPs stay outside history. Prior releases are tagged `v0.1.0`, `v0.2.0`, `v0.3.0`, `v0.3.1`, `v0.4.0`, `v0.4.1`, `v0.5.0` and `v0.5.1`; `v0.6.0` records the current verified development milestone, with public-release gates still open. No remote repository is configured by this project.

Team references: [Abaqus Solutions](https://abaqus.io/es/abaqus-solutions/team) and [Abaqus Wealth Care](https://abaqus.io/es/wealth-care/about-us). See [credits and asset provenance](docs/CREDITS.md), [art prompts](docs/ART-DIRECTION.md), and [technical notes](docs/DEVELOPMENT.md).
