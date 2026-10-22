# Art direction and image generation

The v0.10.1 review candidate revises Lars's photo likeness across all 64 poses
and replaces the small whole-scene arena thumbnails with wider filtered
landmark views. Source prompts, processing and review evidence are recorded
in [POLISH-v0.10.1.md](POLISH-v0.10.1.md). Earlier passes below remain history.

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
statistics are no longer the visual focus of selection. The historical v0.7.1
technical snapshot passed all five native suites against ROM SHA
`64dca043c8407659d05a22cc68b36d589d96bf4785fa630297d4e1526ed56022`: 2,595
gameplay, 18,085 roster, 215 presentation, 999 focused-input and 8,143 stage
checks. The independent bsnes smoke and bounded 28,800-frame run also pass.
The historical package passed 6,153 technical audit checks. Human likeness and
balance, listening, controller, real-console and branding gates remain open.

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
strike, guard contact, high projectile and ground wave. The shadow source
ellipse moves from cell rows `Y22..27` to `Y16..21` (up six pixels); its OAM
position moves from `Y196` to `Y202` (down six pixels), retaining visible screen
rows `202..207` at priority 2. These changes
preserve the original palette and native transfer contracts; they do not add
new illustrated masters. The v0.7 stage/effect build and stage report pass on
the verified v0.7.0 baseline ROM; the archive passes 214 technical checks and repeated
packaging produces identical bytes. This source evidence does not
close the public, human, independent full-combat/soak or real-console gates.

## v0.7.1 historical technical feedback timing

The source freeze is commit `6d756749dbc3fa176e26217f2f59525c9af360d8`, tree
`fa15fea48b5cc2a09608da199810db885872e434`; its canonical ROM is
`64dca043c8407659d05a22cc68b36d589d96bf4785fa630297d4e1526ed56022`. The
canonical batch records 30,037 native checks. The technical snapshot keeps the v0.7.0
art masters, palettes and native effect cells unchanged. Its impact path leaves
the first frozen tick quiet for the second actor upload, then updates the HUD
and constructs the `COUNTER!` or `COMBO!` tile row together on the second
frozen tick. KO cards use quiet-first/panel-second timing. Training Select
applies the round reset immediately, then uses three frozen reset frames to
flush HUD, banner and footer state without rebuilding unchanged labels. Intro
ticks 109, 108 and 107 are quiet, `GET READY`, and HUD. Fresh export, native
endurance and independent smoke evidence passed, as did the package audit.
Human likeness/balance, listening, controller, real-console and branding gates
remained open.

## v0.8.0 historical pause-guide direction

The verified v0.8.0 source-freeze snapshot kept the twelve fighter masters,
costumes, palettes, 64-frame atlases, native proportions and all stage masters
unchanged. Reston's hair/likeness review remained open; that snapshot did not
turn the review into an approval.

The pause overlay follows the established minimal royal-navy, white and gold
language and uses opaque original glyphs 256-383 in the reserved interface
window `$5000-$57FF`. It adds a Normal card plus Controls and Specials pages,
with one simple page cursor rather than a new statistics panel. The Specials
page shows both live fighter names, special names and family types. The Controls
page shows the six-button layout, throws, uppercut, confirmed heavier attacks,
the true twelve-tick quarter-circle motion and 32-energy cost. The selected
profile portrait remains at `$4A00`; the BG2 map remains at `$5800`.

Guide rows 5-27 publish over three paused ticks and yield to actor uploads.
Pause camera shake is frozen, and the first quiet paused tick after contact
settles the actual health display. Training adds four clear dummy states:
Stand, Guard High, Guard Low and Jump. Guard holds relative back without
retreat, while the Jump dummy automatically jumps again after landing. The
fighter art is unchanged; visual review of the guide and Reston's remaining
likeness issue is still required.

The six native suites passed on the verified v0.8.0 ROM SHA with 30,641 checks.
Matching compatibility, matchup, bounded independent-combat, endurance and
fresh-source evidence also passed. The offline package passed 7,471 technical
audit checks; human likeness, balance, listening, controller, real-console and
branding review remained open.

## v0.8.1 historical verified Reston v4 direction

The historical v0.8.1 snapshot is an art-only source revision. Reston's complete 64-frame
set and selected portrait use a fuller very-short near-black buzz cap across the
top and crown, with the mature forehead and face retained. The versioned source
files are `atlas-v4.png`, `animation-motion-v4.png`,
`animation-actions-v4.png` and `animation-airborne-v4.png`; the original v3
sources remain retained. `likeness-v4.json`, `animation-v4.json`,
`animation-airborne-v4.json` and `native-revision.json` preserve the three
imagegen provenance records, source hashes, expected native hashes and review
scope.

The immutable v0.8.0 baseline pins all twelve prior 64-frame sets. The other
eleven fighter bank bytes are identical, all twelve palettes and uniform scales
are unchanged, and Reston's source normalization, palette and scale are locked
to the established values. The native revision records expected frame-hash
digest `7fe74ce9c1d771203191606d8f9ea05398eebb2507f7ab7dc538c766c274bfda`,
the unchanged palette SHA256
`0fa34b1d226a993d001bd2df79e0b4f69827c214668446fe7b3b19bb3c64aa1d` and
uniform/physical scale `0.2280130293159609`.

Full64 native visual review accepted the revision for integration. Actual human
likeness/consent feedback remains pending. Native C/ASM, controls, gameplay and
audio are unchanged. All six native reports and matching expanded evidence pass
for the historical ROM SHA256
`76b456d1ac75471a8b9710c61b0ce4c6ab9ca344b1b8a1f17e38f36e52904466`
(header `A358`), including fresh export, matchup, stage, policy, replay,
symmetry, pinned bsnes and endurance checks. The historical v0.8.1 package and
its 7,471-check audit pass; public, human-balance, listening, controller,
real-console and branding gates stay open. A later live review found four
presentation defects; the v0.9.0 correction pass below now has native evidence
and a packaged technical archive. Public, human-balance, listening, controller, real-console and
branding gates stay open.

## Historical v0.9.0 presentation correction pass (packaged technical snapshot)

The live review of the historical v0.8.1 presentation found four concrete
problems: selection faces were clipped, Damian did not resemble the supplied
photo closely enough, the arena picker read as cramped and uneven, and BG1
scenery showed through HUD and result lettering. The historical v0.9.0 pass addresses
each while preserving the native menu geometry, VRAM allocation and interface
palette contracts.

Selection cards and profile portraits now share one head-anchored, contained
composition at 32x40 and 64x80. `tools/portrait_assets.py` records the source
crop, head anchor, margins, scale and `head_clipped=false` as
`portrait_framing` in `assets/generated/character-manifest.json`. Nearest
neighbor resampling keeps the authored pixel edges and leaves a small backdrop
margin around the head.

The arena picker retains its three-row cursor at `x8..247`, `y40..95` plus
56 pixels per row. Each complete stage image fits inside a 60x52 thumbnail at
`x18..77`, `y42..93` plus 56 pixels per row. Location names and short captions
occupy a separate text column, so the gold cursor does not touch scene pixels.

FIGHT and RESULT lettering uses the existing opaque glyphs 256-383 for ASCII
32-127 in the `$5000-$57FF` interface window. Title, roster and arena menu text
keep the original ASCII bank. Round marker tiles 147/148 use the opaque panel
background at palette index 1, removing the BG1 scenery bleed through those
cells.

Damian's v4 legacy, motion, actions and airborne source PNGs and provenance
files remain under `assets/art/characters/00-damian/`. The approved
`neutral-height` normalization converts each atlas once to the 311-pixel
reference neutral with pinned factors: legacy `0.9255952381`, motion
`0.9904458599`, and actions/airborne `0.9936102236`. The native idle height is
69. The baseline, native palette and physical scale remain locked, and the
corrected 64-frame contract hash is
`00f90a6765904c546284832d399c1a5ec581f08fed64a7f7bedc6d9df985e261`.
The other eleven fighter banks and all twelve palettes remain unchanged.
Native visual review accepted the corrected all64 set; human likeness and
consent approval remain open.

No combat, controls, audio, trace, memory-layout or Fighter/Wave ABI change is
part of this pass. The historical corrected source freeze is commit
`76f0a08a7562800df01507db83c6877745c3bdcf`, tree
`f37852da57a42d2d6819374db5d23278d12587a5`. The historical v0.9.0 manifest
identifies ROM SHA256
`bce460fbaa6f63e2f9c614f5c6833c08fd70558d56e7a27adfad292d4d200639` (header
`6D41`). All six native reports pass on this SHA: 2,595 gameplay, 18,081 roster,
1,756 presentation, 997 focused-input, 8,131 stage and 622 Training checks
(32,182 total). The 288-by-600 matchup/stage/policy/replay/symmetry evidence,
pinned bsnes smoke plus bounded 48-by-600 run, endurance of 216,356 live frames
in each of three modes, fresh 214-asset export in 75.078 seconds and
`validate_release_evidence` also pass. The historical [v0.9.0 Windows package](../dist/Abaqus-After-Hours-v0.9.0-Windows.zip)
is available and its archive audit passes 7,471 checks. Public review remains open.

## v0.10.0 cartoon-stage candidate (historical packaged technical snapshot; human gates pending)

The candidate refreshes all three arena masters in a stronger early-1990s
arcade direction: original bold navy outlines, clean cel shading, saturated
location colors and readable architectural silhouettes. Las Condes, El Castillo
and La Oficina each use one complete stage composition, and the arena picker
thumbnails use the same art so the three choices read as one coherent set.

The versioned masters are `00-las-condes-cartoon-v2.png`,
`01-castillo-cartoon-v2.png` and `02-oficina-cartoon-v2.png` under
`assets/art/stages/`. Each has an adjacent exact-basename JSON provenance file;
the raw built-in-imagegen source-v2 inputs remain under
`assets/art/stages/source-v2/`. The selected `assets/art/stages/stages.json`
uses schema 2 and `stages-v0.4.json` remains the previous manifest history.
`tools/stage_sources.py` owns path, hash, RGB 1024x896, exact 4x-native
dimensions and at-most-90-color source validation. `tools/stage_cartoon.py` adapts the authored feature and ambient
work to the candidate palette/map.

The existing four 256-byte ambient phases, eight dynamic BG1 cells, transfer
budget and `TRACE[115..118]` contract remain unchanged. Alongside the stage
asset refresh, the candidate carries bounded menu-only correctness polish:
cleaned directional edges, both-pad navigation only for the P2 roster case,
Start > B > A priority and immediate return after Back. Active combat, the
Fighter/Wave ABI, fighters, portraits, audio and trace contract remain
unchanged. Ambient change counts by phase are Las Condes `[0,20,20,20]`,
El Castillo `[0,18,18,18]` and La Oficina `[0,6,6,6]`; the office keeps one
3-pixel monitor segment per monitor at `y114` while protecting the monitor
digits. The [stage pass note](STAGE-CARTOON-v2.md) and [cartoon preservation
report](cartoon-preservation-report.json) record the source and preservation
details, including 192 generated files retained from v0.9 across fighter
64-frame banks, palettes, portraits, UI, audio, title and select assets.

The source freeze is commit `8536bb6956212952c17302a62cc6c1de7e12a65d`, tree
`d524d3f960600dc5c9ff83578ac73675f9798735`; the ROM is SHA256
`a8f7b797a06bd242a18bf54400e53f043d5a84f274765ba3a34f9d8289ac5445` (header
`BE19`). Native PPU review accepted all three stage scenes and the arena
picker; focused presentation, stage and menu probes pass. `Test.cmd` exits 0
with all six reports matching this SHA: 2,595 gameplay, 18,081 roster, 1,756
presentation, 1,020 focused-input, 8,131 stage and 622 Training checks
(32,205 total). Fresh committed export validation passes 214 assets and symbols
in 62.031 seconds. Endurance passes all three modes at 216,356 live frames
each at 60.098811862348406 FPS, with wraps 4/4/3, peak SPC backlog 6 and empty
cadence, native-timing, ambient, PPU-overflow and SPC-FIFO failure arrays. The
technical audio report passes 1,262/1,262 capture-only checks with all four
cues and four scores unclipped; the four music captures run 60.899688-63.079432
seconds and their longest near-silence is 0.075499-0.078652 seconds, below the
0.5-second near-zero threshold. Its separate listening pack is 15,447,456 bytes
with SHA256 `5afec27e3022f87580e21991beb6785b9366dfb9bf16bf2abb45a08400309c70`.
The 288-by-600 matchup/stage/policy/replay/symmetry run with four replays across
all three stages, pinned bsnes smoke at 600/600 plus the independent 28,800-frame
run, and `validate_release_evidence` all pass. The historical [v0.10.0 Windows
package](../dist/Abaqus-After-Hours-v0.10.0-Windows.zip) is available and its
archive audit passes 7,472 checks. Human listening, stage, likeness/consent,
gameplay, controller and public-use review remain open, with
`public_release_certified=false`.

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
