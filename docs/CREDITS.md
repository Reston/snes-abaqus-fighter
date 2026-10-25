# Credits and provenance

## Original game

Abaqus: After Hours is an original homebrew fighting game created for this project. Its arcade match format and six-button combat are inspired by Street Fighter II. No Capcom ROM, sprites, music or source code are included.

Game code, UI, tile pipeline, combat implementation, tracker compositions and synthesized BRR effects were authored for this repository. Pixel-art master atlases were created with the built-in image generation tool, then converted to SNES tiles and palettes. Prompts and processing notes are in [ART-DIRECTION.md](ART-DIRECTION.md).

The v0.13 Office Champion victory score is an original sixteen-bar tracker
arrangement using the title's existing synthesized instruments. Its authoring
code, source preservation and capture-only evidence are described in
[CHAMPION-AUDIO.md](CHAMPION-AUDIO.md). Human full listening remains open.

## v0.5 animation references and art

The v0.5 animation pass adds 24 original built-in imagegen atlases, two for
each fighter (`animation-motion.png` and `animation-actions.png`). They provide
32 new drawn in-between frames per fighter while preserving each fighter's
legacy identity master, costume, palette and source portrait. Reston's v3
short-hair correction is retained as the pre-v0.8.1 source. Every atlas keeps its full
prompt, reference role and provenance in the adjacent `animation.json`.

Official reference material was used only for menu structure, controller
mapping and the broad six-button fighting-game vocabulary:

- [Capcom Town: Street Fighter II](https://captown.capcom.com/en/classic_games/22)
- [Capcom Town: Super Street Fighter II](https://captown.capcom.com/en/classic_games/30)
- [Nintendo Super NES developer interview](https://www.nintendo.com/en-gb/News/2017/September/Nintendo-Classic-Mini-SNES-developer-interview-Volume-1-Star-Fox-+Star-Fox-2-1273086.html)

No commercial game ROM, sprite sheet, animation frame, font, music or source
code was imported. These references do not grant rights to Capcom or Nintendo
assets.

The v0.6 pass adds twelve original built-in ImageGen airborne/throw/recovery
atlases, one per fighter. Full prompts, input roles, source paths and hashes
are in each character's `animation-airborne.json`. Frames 48-63 share the
existing physical scale and palette; native frames 0-47 remain unchanged.
The four original synthesized sound cues are also encoded as resident SPC
effects to avoid transferring sample data during combat. No outside audio
was added.

The v0.7.1 resident-command adapter follows the FIFO/acknowledgement protocol
in [PVSnesLib 4.6 SNESMod](https://github.com/alekmaul/pvsneslib/blob/4.6.0/pvsneslib/source/snesmodwla.asm).
It services at most one ready command per frame; the SDK still owns boot,
module/sample loading and scene-load flushes. The game does not use streamed
sample playback. PVSnesLib and SNESMod license notices remain included below
and in the offline package.

The v0.8.1 likeness pass uses four built-in imagegen edits for Reston's fuller
short buzz cap across all 64 poses and derived portraits. The selected sources
are `atlas-v4.png`, `animation-motion-v4.png`, `animation-actions-v4.png` and
`animation-airborne-v4.png` in his character folder. Full prompts, input roles
and output hashes are retained in `likeness-v4.json`, `animation-v4.json` and
`animation-airborne-v4.json`; `native-revision.json` pins the reviewed output.
The original sources remain intact. This technical art review does not imply
the depicted person's approval or public-use consent.

## People

The v0.10.1 review candidate revises Lars's likeness with four original
built-in imagegen atlas edits and one airborne spacing repair. His original
masters remain retained; the selected v4 sources, exact prompts, input roles
and source hashes are under `assets/art/characters/11-lars/`. The revised
location previews are crops and filtered reductions of the existing original
stage art. See [POLISH-v0.10.1.md](POLISH-v0.10.1.md).

Identity photographs and public names were sourced from the user-provided [Solutions team page](https://abaqus.io/es/abaqus-solutions/team) and [Wealth Care page](https://abaqus.io/es/wealth-care/about-us). The twelve individual fighter atlases are original cartoon illustrations generated from those references, with matching 32×40 selection cards and 64×80 profile portraits cropped from each master. The v0.4 likeness pass refreshed Damián, Cote, Negger, Fernando, Mamariaga, Reston and Roxana with built-in imagegen v2 edits; the earlier v2 masters for Ivo, Cristóbal, David, Cristián and Lars remained selected in that historical pass. Full prompts and identity notes accompany every character under `assets/art/characters/`. The source photographs remain subject to the original owners' rights. Download URLs are retained in `assets/references/team.json` and `wealth.json`.

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
- [bsnes2014 Accuracy](https://github.com/libretro/bsnes2014/tree/libretro), byuu and Libretro contributors: optional independent-engine smoke testing. This GPLv3 core is downloaded separately and is not included in the player ZIP; source, license and pinned hashes are recorded in [COMPATIBILITY.md](COMPATIBILITY.md).
- [Python 3.12.10](https://www.python.org/downloads/release/python-31210/) and [Pillow](https://python-pillow.github.io/): local build/asset tooling, downloaded separately.
- Menu lettering uses original project-authored bitmap glyphs; no Arial or other system font is used or redistributed.

Abaqus branding and team photography are not relicensed by the source-code MIT license. This repository was requested as a coworker-themed project; it does not claim to be an official Capcom product.

## v0.25 detailed floor material

Outdoor floor textures reuse the approved stage source masters. The office
carpet strip was created with built-in imagegen; its [saved source](../assets/art/stages/floor-v025/02-oficina.png)
and [exact prompt, references and provenance](../assets/art/stages/floor-v025/02-oficina.json)
are retained. Native conversion uses the existing six 4bpp stage palettes.
