# Art direction and image generation

## v0.6 combat-animation and menu direction

The v0.6 pass keeps all twelve identity masters, costumes and palettes separate
and unchanged, including Reston's selected v3 short-hair correction. It retains
the motion and action atlases, then adds one `animation-airborne.png` atlas per
fighter. Each airborne atlas has adjacent `animation-airborne.json` prompt and
provenance metadata. The new range gives every fighter dedicated air punch and
air kick anticipation, active and recovery drawings, separate thrower and
victim poses, and distinct knockdown and wake art.

Every fighter now has 64 uniform 96x80 native frames: legacy key poses 0-15,
motion and transition frames 16-31, action frames 32-47, and airborne,
throw-role, knockdown and wake frames 48-63. The original 48 frame pixels and
palette bytes remain locked. All 64 frames share one physical scale inside the
94x77 safe area with a feet baseline at native height 78. The generated
6,144x80 review strip and eight 30,720-byte native banks use one shared
fifteen-color OBJ palette per fighter. The earlier motion/action prompts and
provenance remain beside those atlases in `animation.json`.

Runtime motion keeps a private per-fighter clock and distance-driven gait, with
pause and hitstop stable. Combat now distinguishes throw lift, flight, floor,
get-up and wake states; throw damage lands at floor impact, simultaneous throws
tech, wake grants four invulnerability ticks, and the final six wake ticks
accept buffered attack or jump input. Training health recovery is gated while a
fighter is hurt, downed or wake-invulnerable, and Select clears active
throw/down/wake state.

The home, fighter-select and arena menus follow a clean royal-navy, white and
gold direction with a single cursor, original project glyphs, the four-by-three
roster grid and one large selected portrait. Profile power, speed and family
statistics are no longer the visual focus of selection. The current v0.7.0
canonical silent `Test.cmd` batch passes all five native suites against ROM SHA
`e44a739488bd549cfcffbe35bbb32bb5e71d9d2dce12bea6562ebd3dd0c15b84`; the
separate pinned bsnes2014 Accuracy smoke passes against the same image. The
focused stage extension adds nine patch-only PPU assertions to the canonical
4,528 stage checks, producing the current 4,537-check stage report without an
engine change. Public release, human art/balance review, independent-emulator
combat review and real-console gates remain open.

The authored art remains inside the existing 96x80, fifteen-color OBJ and
reserved-interface palette contracts. Native health and energy bars keep their
original glyph formulas. During hitstop, interface DMA yields to actor uploads,
so an impact cue or cleared banner can appear one to three video frames after
the event while the fight state and animation remain frozen.

## v0.7 stage and effect direction (verified source integration)

The v0.7 pass adds restrained ambient motion while keeping the art masters
original and separate. Each stage supplies four code-native phases built from
eight BG1 tiles at indices `960..967` in VRAM `$3C00-$3C7F`; the source stage
masters, encoded graphics and palettes are unchanged; eight runtime map cells
point to the dynamic block. Las Condes uses leaf shimmer and
glass reflection, El Castillo uses string lights, a party gesture and window
light, and La Oficina uses left and right monitor changes. The phase request
advances during live combat and freezes for intro, pause, hitstop and round end.
Ambient transfers yield to actor and interface work and use no additional OBJ
sprites.

The effect pass authors small phase variants in the existing native cells for
strike, guard contact, high projectile and ground wave. The floor shadow's
blank top rows were removed so its visible ellipse sits on the floor with the
updated OAM position and priority, preserving its intended on-screen footprint. These changes
preserve the original palette and native transfer contracts; they do not add
new illustrated masters. The v0.7 stage/effect build and stage report pass on
the current ROM; the archive passes 214 technical checks and repeated
packaging produces identical bytes. This source evidence does not
close the public, human, independent full-combat/soak or real-console gates.

## v0.4.1 Reston hair correction

The user's new photo shows a short dark buzz cut across Reston's top and crown,
with a receding hairline. A targeted built-in imagegen edit replaces the
overly bald depiction in all sixteen poses. The previous master is retained
as `assets/art/characters/09-reston/atlas-v2.png`; the selected `atlas.png` and
full prompt/provenance are recorded in that folder's `likeness-v3.json`.
Matching card and profile portraits are regenerated from the revised master.

## v0.4.0 proportion and presentation polish

The v0.4 pass keeps twelve individual illustrated masters and tightens the native presentation around them. Seven likeness v2 masters were refreshed with the built-in imagegen edit workflow for Damián, Cote, Negger, Fernando, Mamariaga, Reston and Roxana; the five earlier likeness v2 masters for Ivo, Cristóbal, David, Cristián and Lars remain selected. All twelve now have close 32×40 selection cards and 64×80 profile portraits derived from their own source masters.

Every fighter uses one uniform physical scale across all sixteen legacy poses. The renderer places the result inside a 96×80 native canvas with a 94×77 safe area, so the effective standing height may reduce when another legacy pose is wider or taller. This keeps head, torso, hands and feet at a consistent scale between idle, attacks, jumps, blocks, knockouts and rushes while preserving the shared legacy pose-index contract. The v0.5 animation atlases add the separate motion and action ranges; v0.6 extends the same scale contract through frames 48-63 with dedicated airborne, throw, knockdown and wake art.

The three stages are now independent PNG masters under `assets/art/stages/`, described by `assets/art/stages/stages.json`. The home screen, four-by-three fighter selection and arena menu use new original plates under `assets/art/menu/`; the complete image-generation prompt set is `assets/art/menu/prompts.json`. Menu lettering is rendered from original project glyphs rather than Arial or another system font. The selected fighter's 64×80 profile portrait is transferred to BG2 at word `$4A00–$4EFF` with palette 1.

## Historical direction: v0.3.1 likeness correction

The user requested closer face likenesses for Ivo, Cristóbal, David, Cristián and Lars, explicitly specifying black hair for Cristóbal and darker black hair for David. Five focused **built-in imagegen** edits use each person's public headshot as the identity reference and their v0.3 atlas as the edit target. The selected masters remain at the character paths below. Each revised character directory includes `likeness-v2.json` with the full edit prompt, input roles and provenance.

The pass emphasizes Ivo's mature facial proportions and natural short hair; Cristóbal's cropped black hair and full black beard; David's black tied-back hair, moustache and goatee; Cristián's fuller clean-shaven face and short black hair; and Lars's broad clean-shaven face and wavy side-swept fringe. The original cartoon arcade style, costumes and sixteen-pose contract continue. Matching select portraits are regenerated from the revised masters.

## Historical direction: v0.3 individual cartoon roster

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

The sixteen key poses are idle, two walk steps, crouch, jump, jab, cross, high kick, sweep, block, hurt, victory, cast, rising uppercut, knockout and rush. The v0.3 runtime used a 64×80 frame; v0.4 supersedes that with a 96×80 canvas and one uniform per-fighter scale across all sixteen poses. Every fighter gets one shared fifteen-color palette across their frames; source-master crops provide matching selection portraits. Native previews, extraction boxes and hashes are saved under `assets/generated/`. Source fixes are recorded in each prompt file; earlier source variants are preserved beside the selected master when applicable.

The v0.3 stages retained the bright illustrated v0.2 masters. The v0.4 stage pass reorganizes them as three independent PNG masters and adds the redesigned menu plates. No CLI/API image-generation fallback or commercial game sprites were used. Review of the new airborne, throw and wake drawings, more character-specific in-between art, layered stage parallax and richer effect variants remain future art work beyond the v0.7 source integration.

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
