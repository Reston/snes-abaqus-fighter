# Credits and provenance

## Original game

Abaqus: After Hours is an original homebrew fighting game created for this project. Its arcade match format and six-button combat are inspired by Street Fighter II. No Capcom ROM, sprites, music or source code are included.

Game code, UI, tile pipeline, combat implementation, tracker compositions and synthesized BRR effects were authored for this repository. Pixel-art master atlases were created with the built-in image generation tool, then converted to SNES tiles and palettes. Prompts and processing notes are in [ART-DIRECTION.md](ART-DIRECTION.md).

## People

Identity photographs and public names were sourced from the user-provided [Solutions team page](https://abaqus.io/es/abaqus-solutions/team) and [Wealth Care page](https://abaqus.io/es/wealth-care/about-us). The twelve individual fighter atlases are original cartoon illustrations generated from those references, with matching 32×40 selection cards and 64×80 profile portraits cropped from each master. The v0.4 likeness pass refreshed Damián, Cote, Negger, Fernando, Mamariaga, Reston and Roxana with built-in imagegen v2 edits; the earlier v2 masters for Ivo, Cristóbal, David, Cristián and Lars remain selected. Full prompts and identity notes accompany every character under `assets/art/characters/`. The source photographs remain subject to the original owners' rights. Download URLs are retained in `assets/references/team.json` and `wealth.json`.

| Game slot | Public reference | User-supplied nickname |
| --- | --- | --- |
| Damián | Damián Gelerstein | Damián |
| Ivo | Ivo Kovacevic | Ivo |
| Cristóbal | Cristóbal Mackenzie | Cristóbal |
| Cote | José Ignacio Villarroel | Cote |
| Negger | Gonzalo Reyes | Negger |
| David | David Ponce | David Ponce |
| Fernando | Fernando Pérez | Fernando Pérez |
| Cristián | Cristián Valdés | Cristian |
| Mamariaga | Ignacio Madariaga | Mamariaga |
| Reston | José David Ordoñez | Reston |
| Roxana | Roxana Espínola | Roxana |
| Lars | Rodrigo Lártiga | Lars |

Cristóbal, Cristián, Mamariaga and Reston were matched to the corresponding public team references above. Game move names, stats, outfits and victory lines are fictional, playful character design.

## Places

The user supplied three photographs: the Las Condes glass entrance marked 140; El Castillo's white party house; and the office with two internet-speed monitors. The three independent stage PNGs under `assets/art/stages/` are original illustrations of those themes, described in `stages.json`. They are adaptations, not exact architectural reconstructions. The source photographs were not added to the public project asset tree.

## Software

- [PVSnesLib 4.6.0](https://github.com/alekmaul/pvsneslib/releases/tag/4.6.0), Alekmaul and contributors: C toolchain and SNES hardware library. License: `licenses/PVSnesLib.txt`.
- SNESMod by mukunda, with WLA conversion by KungFuFurby and PVSnesLib adaptations: SPC700 audio driver, bundled with PVSnesLib. License notice: `licenses/SNESMod.txt`.
- [Snes9x 1.63](https://github.com/snes9xgit/snes9x/releases/tag/1.63), the Snes9x team: official Windows player and libretro test core. License: `licenses/Snes9x.txt`; the offline player ZIP includes its original license.
- [Python 3.12.10](https://www.python.org/downloads/release/python-31210/) and [Pillow](https://python-pillow.github.io/): local build/asset tooling, downloaded separately.
- Menu lettering uses original project-authored bitmap glyphs; no Arial or other system font is used or redistributed.

Abaqus branding and team photography are not relicensed by the source-code MIT license. This repository was requested as a coworker-themed project; it does not claim to be an official Capcom product.
