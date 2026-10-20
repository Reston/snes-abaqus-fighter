# Art direction and image generation

## Current direction: v0.3 individual cartoon roster

The roster now uses twelve separate illustrated masters with individual bodies, costumes, facial features and silhouettes. Six art subagents each developed two fighters using the **built-in imagegen** tool, public appearance references and the existing cartoon style reference. The shared sixteen-pose layout supports the same native renderer; it does not imply a shared recolored body. Roxana has her own woman character design and poses.

Each directory contains `atlas.png`, the complete generation prompt/provenance in `prompt.json`, and `identity.md` describing the fictional costume and recognition cues:

| Fighter | Master directory | Costume |
| --- | --- | --- |
| Damián | `assets/art/characters/00-damian/` | Cobalt rolled-sleeve blazer |
| Ivo | `assets/art/characters/01-ivo/` | Emerald jacket, charcoal shirt |
| Cristóbal | `assets/art/characters/02-cristobal/` | Orange work jacket |
| Cote | `assets/art/characters/03-cote/` | Crimson waistcoat, pale sleeves |
| Negger | `assets/art/characters/04-negger/` | Purple bomber jacket |
| David | `assets/art/characters/05-david/` | Amber shirt, suspenders |
| Fernando | `assets/art/characters/06-fernando/` | Teal field jacket |
| Cristián | `assets/art/characters/07-cristian/` | Navy sweater vest |
| Mamariaga | `assets/art/characters/08-mamariaga/` | Chartreuse hoodie, glasses |
| Reston | `assets/art/characters/09-reston/` | Copper jacket, pale collar |
| Roxana | `assets/art/characters/10-roxana/` | Magenta jacket, wide-leg slacks |
| Lars | `assets/art/characters/11-lars/` | Ice-blue jacket |

The sixteen key poses are idle, two walk steps, crouch, jump, jab, cross, high kick, sweep, block, hurt, victory, cast, rising uppercut, knockout and rush. Each master is isolated and reduced to the unchanged 64×80 native stream format. Every fighter gets one shared fifteen-color palette across their frames; source-master crops provide matching selection portraits. Native previews, extraction boxes and hashes are saved under `assets/generated/`. Source fixes are recorded in each prompt file; earlier source variants are preserved beside the selected master when applicable.

The stages retain the bright illustrated v0.2 masters. No CLI/API image-generation fallback or commercial game sprites were used. More in-between animation and more individualized hit effects remain future art work.

## Historical direction: v0.2 cartoon arcade

The user requested a more cartoon-like Street Fighter II aesthetic. The current masters replace the realistic suit rendering and photographic selection portraits with original illustrated arcade art: oversized expressive faces and fists, broader silhouettes, clean navy outlines, cel shading and saturated costume colors. The [official Capcom reference](https://captown.capcom.com/en/classic_games/22) informed the visual direction; no commercial sprites were imported.

Project-bound masters generated for v0.2 with the **built-in imagegen** tool:

- `assets/art/fighter-atlas-cartoon.png` — historical shared sixteen-pose style reference.
- `assets/art/stage-atlas-cartoon.png` — brighter illustrated Las Condes, El Castillo and La Oficina.
- `assets/art/portraits-cartoon.png` — historical twelve-portrait atlas.

The exact final prompt set and reference roles are saved in [`assets/art/cartoon-prompts.json`](../assets/art/cartoon-prompts.json). The original two atlases below are retained as historical references and are no longer compiled into the current ROM.

The v0.2 asset pipeline used nearest-neighbor scaling, an authored fifteen-color material palette and native head-detail variations on a shared body. The v0.3 pipeline replaces that approach with the individual masters above.

## Historical direction: v0.1

Mode: **built-in imagegen**, using the `imagegen` skill. No image-generation API keys or fallback CLI were used.

Original project-bound masters:

- `assets/art/stage-atlas.png` — original three-location pixel-art backdrop atlas.
- `assets/art/fighter-atlas.png` — original Damián-based sixteen-pose animation master, generated with his public headshot as the appearance reference.

Native derivatives live in `assets/generated/`; `tools/make_assets.py` documents the deterministic processing. The original release used the supplied public team photos on the selection screen. The v0.2 release replaced those with its illustrated portrait atlas and retained a shared base body. The individual v0.3 masters supersede both fighter approaches.

## Stage master — final prompt

Use case: illustration-story. Create a production game asset: a single pixel-art background atlas for an original 1993 Super Nintendo 2D fighting game called Abaqus After Hours. Three equally sized horizontal panoramas stacked vertically, hard straight panel divisions: TOP Las Condes Santiago glass office tower entrance with giant 140 numbers, glass canopy, metallic columns, burgundy tree to right, Chilean Andes glimpse, warm dusk; MIDDLE El Castillo elegant white two-story Chilean party house with balcony and black iron railing, sunset, festive string lights, red party cups and a few small cheering office coworkers behind the fighting area; BOTTOM La Oficina contemporary office with rows of dual monitors and code, exposed ceiling lights, windows over Santiago at blue hour, monitors with 11 Mbps and 8.1 Mbps motif. Each panel is a strictly side-on fighting stage with same horizon, empty continuous flat fightable floor in lower quarter; no foreground fighters. All three have rich original meticulously hand-placed chunky pixel art with 16-bit palette discipline, atmospheric light, strong architectural silhouettes and subtle dithering, arcade illustration not photorealistic, no blurry edges. Wide panels, each aspect 8:7; whole sheet width about 1024 and height about 2688. No borders, no UI, no health bars. Inspired by the attached location photos' architecture as described here, not by any existing game assets.

## Fighter master — final prompt

Use case: illustration-story. Production transparent sprite animation atlas for a native SNES office fighting game. Use provided headshot as appearance reference for Damián: light-skinned bald smiling middle-aged man, dark charcoal office suit, white open-collar shirt, black shoes, no tie. Athletic believable 1993 arcade pixel-art proportions, NOT tiny chibi. Exact regular 4 column by 4 row grid, 16 equally sized cells, one full-body side-view fighter centered in each cell, facing RIGHT, same body scale and feet baseline in every cell, generous transparent empty space around each sprite. Entire sheet transparent, NO text labels, NO panel outlines, NO shadows, NO duplicated people per cell. Crisp pixel art with dark outline, 12-color limit, strong anatomy and clean readable silhouette, actual visible large chunky pixels. Row 1 four cells: fighting guard idle, walking front step, walking back step, low crouching guard. Row 2 four cells: forward jump with knees tucked, extended straight jab punch to right, forceful cross punch to right, high side kick extended right. Row 3 four cells: low sweeping kick right, arms raised blocking stance, recoiling from punch to face, raised arms victory pose. Row 4 four cells: both hands casting cyan energy to right with no projectile, rising uppercut, lying knocked-out on ground head left feet right, strong forward shoulder lunge. Keep all sixteen sprite poses fully separated, none may cross any cell boundary. This is original game art, do not copy any existing Street Fighter character costume or sprites.
