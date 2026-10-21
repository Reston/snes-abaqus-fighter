# Native SNES implementation

## Build

Supported build host: Windows x64. `tools/setup.ps1` downloads pinned official release archives into `.tools/` and verifies their SHA256. `tools/build.py` invokes 816-tcc, 816-opt, WLA-65816 and WLALINK directly, so a separate Make/MSYS installation is unnecessary.

The v0.10.0 cartoon-stage pass is the current packaged technical snapshot; its six native
suites now pass on the exact current ROM. The source freeze is commit
`8536bb6956212952c17302a62cc6c1de7e12a65d`, tree
`d524d3f960600dc5c9ff83578ac73675f9798735`; the ROM is SHA256
`a8f7b797a06bd242a18bf54400e53f043d5a84f274765ba3a34f9d8289ac5445`, header
`BE19`. Native PPU review accepted all three stage scenes and the arena picker;
focused presentation, stage and menu probes pass. `Test.cmd` exits 0 with all
six reports matching this SHA: 2,595 gameplay, 18,081 roster, 1,756
presentation, 1,020 focused-input, 8,131 stage and 622 Training checks
(32,205 total). Fresh committed export validation passes 214 assets and
symbols in 62.031 seconds. See the [stage pass note](STAGE-CARTOON-v2.md) and
[cartoon preservation report](cartoon-preservation-report.json).

It adds three versioned original built-in-imagegen stage masters:
`assets/art/stages/00-las-condes-cartoon-v2.png`,
`assets/art/stages/01-castillo-cartoon-v2.png` and
`assets/art/stages/02-oficina-cartoon-v2.png`. Each has an adjacent
exact-basename JSON provenance file and raw source under
`assets/art/stages/source-v2/`. The selected `assets/art/stages/stages.json`
uses schema 2; `stages-v0.4.json` remains historical manifest input.
`tools/stage_sources.py` validates path, hash, RGB 1024x896, exact 4x-native
dimensions and at most 90 colors. `tools/stage_cartoon.py` adapts the existing feature-driven ambient
work to the new palette/map while retaining the four 256-byte phases and eight
ambient cells. Ambient change counts by phase are Las Condes
`[0,20,20,20]`, El Castillo `[0,18,18,18]` and La Oficina `[0,6,6,6]`;
the office keeps one 3-pixel monitor segment per monitor at `y114` while
protecting the monitor digits. The [cartoon preservation report](cartoon-preservation-report.json)
records 192 generated files retained from v0.9, including all fighter 64-frame
banks, palettes, portraits, UI, audio, title and select assets. The candidate
also carries bounded menu-only correctness polish:
cleaned directional edges, both-pad navigation only for the P2 roster case,
Start > B > A priority and immediate return after Back. Active combat, the
Fighter/Wave ABI, fighters, portraits, audio and trace contract are unchanged.
Endurance passes all three modes at 216,356 live frames each at
60.098811862348406 FPS, with wraps 4/4/3, peak SPC backlog 6 and empty
cadence, native-timing, ambient, PPU-overflow and SPC-FIFO failure arrays. The
technical audio report passes 1,262/1,262 capture-only checks: all four cues
and four scores are unclipped, four music captures run 60.899688-63.079432
seconds, and no near-zero interval reaches 0.5 seconds (longest near-silence
0.075499-0.078652 seconds). Its separate listening pack is 15,447,456 bytes,
SHA256 `5afec27e3022f87580e21991beb6785b9366dfb9bf16bf2abb45a08400309c70`.
The 288-by-600 matchup/stage/policy/replay/symmetry run with four replays
across all three stages, pinned bsnes smoke at 600/600 plus the independent
28,800-frame run, and `validate_release_evidence` all pass on this SHA.
The current [v0.10.0 Windows package](../dist/Abaqus-After-Hours-v0.10.0-Windows.zip)
is available and `tools/audit_release.py` passes 7,472 checks against it.
Human listening, gameplay, controller, likeness/consent and public-use review
remain open, with `public_release_certified=false`.

The historical v0.9.0 presentation pass was the corrected native candidate. A live v0.8.1 review
found clipped selection faces, a Damian likeness mismatch, a weak arena-picker
composition, and stage pixels showing through HUD and result lettering. The
historical v0.9.0 pass applied presentation-only corrections for those findings.
Its historical candidate manifest identifies ROM SHA256
`bce460fbaa6f63e2f9c614f5c6833c08fd70558d56e7a27adfad292d4d200639`, header
checksum `6D41`. The historical corrected source freeze is commit
`76f0a08a7562800df01507db83c6877745c3bdcf`, tree
`f37852da57a42d2d6819374db5d23278d12587a5`. All six native reports pass on
this SHA: 2,595 gameplay, 18,081 roster, 1,756 presentation, 997 focused-input,
8,131 stage and 622 Training checks (32,182 total). The 288-by-600 matchup,
stage, policy, replay and symmetry evidence, pinned bsnes smoke plus bounded
48-by-600 run, endurance of 216,356 live frames in each of three modes, fresh
214-asset export in
75.078 seconds and `validate_release_evidence` pass on this SHA. `Test.cmd`
exits 0. The historical [v0.9.0 Windows package](../dist/Abaqus-After-Hours-v0.9.0-Windows.zip)
is available and its `tools/audit_release.py` audit passes 7,471 checks. The last verified v0.8.1 source freeze is commit
`fe05e5fd1391a1db20f1b66f1e9f6e699445e77a`, tree
`46e1af160ffb8ab6cb768e3d9deec1352d77ae83`. It targets a 4 MiB FastROM LoROM
image across 128 banks, NTSC, with no coprocessor or SRAM requirement. WLALINK
writes the SNES header/checksum. The ROM SHA256 is
`76b456d1ac75471a8b9710c61b0ce4c6ab9ca344b1b8a1f17e38f36e52904466`, header
checksum `A358`. Native C/ASM, controls, gameplay and audio are unchanged.
The historical v0.8.1 `Test.cmd` run exits 0 with all six reports on this SHA: 2,595 gameplay, 18,081
roster, 215 presentation, 997 focused-input, 8,131 stage and 622 Training
checks (30,641 total). Fresh committed export validation reproduces the ROM,
manifest, 214 assets and symbols in 76.344 seconds. The 288-by-600 native
matchup, all-three-stage, two-policy, four-replay and symmetry checks pass. The
pinned bsnes smoke matches this SHA with 600/600 cadence, healthy PPU/PCM and
ambient freeze, and the bounded 48-by-600 run passes. Native endurance passes
216,356 live frames in each of three modes at 60.0988118623 FPS, wraps 4/4/3,
peak SPC six, zero stable FIGHT lag and empty failure arrays.
`validate_release_evidence` passes. The historical v0.8.1 offline package passes
7,471 technical audit checks; the v0.8.0 package is historical. Human review
gates remain open.

`Build.cmd` rebuilds from committed native assets. `Build.cmd --assets` regenerates the full asset set first. Source portrait downloads can be refreshed with `tools/fetch_references.py`; rebuilding the game does not require fetching the team pages.

## Rendering

The PPU uses Mode 1. BG1 holds the stage; BG2 holds the interface and selected profile portrait. Stage tiles use six 16-color palette banks (15 opaque colors each). The interface reserves the first two palette banks, and the large profile portrait uses BG2 palette 1. Fighter and effect palettes occupy OBJ CGRAM.

| VRAM word address | Contents |
| --- | --- |
| `$0000-$37FF` | BG1 stage tiles, at most 896 4bpp tiles |
| `$3800-$3BFF` | BG1 32x32 tilemap |
| `$3C00-$3C7F` | v0.7 dynamic BG1 ambient tiles: eight tiles, one 256-byte phase |
| `$4000-$49FF` | BG2 interface/font tiles |
| `$4A00-$4EFF` | Selected 64x80 profile portrait, an eight-by-ten 4bpp tile block using BG2 palette 1 |
| `$5000-$57FF` | v0.8 opaque original pause-guide glyph tiles 256-383 |
| `$5800-$5BFF` | BG2 32x32 tilemap |
| `$6000-$69FF` | Actor 0 padded frame page; 3,840-byte pose stream plus blank row padding |
| `$6A00-$73FF` | Actor 1 padded frame page; 3,840-byte pose stream plus blank row padding |
| `$7800-$7BFF` | Impact, projectile and shadow tiles |

Each actor uses thirty 16x16 hardware sprites: six columns by five rows. Actor 0 begins at OAM byte 0 and actor 1 at OAM byte 128, with two padded slots per actor block. The 65816 renderer writes an actor's OAM entries in one call. A strided DMA routine streams one 3,840-byte 96x80 frame into the actor's padded VRAM page, leaving the page's blank tail predictable. Each vblank streams at most one actor frame, alternating priority if both change together. The second actor can visually trail its requested frame by one video frame; combat state stays independent of that upload queue.

OBJSEL uses the 8/16 size pair; all live pieces select its 16-pixel size. The renderer packs each actor's repeating six-column X9 pattern once, then writes tile/attribute pairs together. Source-bank selection and frame-offset arithmetic happen before `WaitForVBlank`; the blanking interval only executes the prepared DMA and interface transfers. The HUD caches health, energy, wins and seconds, updating only changed fields and partial energy tiles to preserve the simulation budget.

The v0.8 pause guide owns BG2 rows 5-27 as a 1,472-byte panel.
`fillGuidePanel` and `drawGuideWord` build it over three paused ticks, then
publish the full range after actor DMA has yielded. The portrait block and BG2
map addresses do not move. The guide uses original opaque glyphs 256-383; the
paused camera remains still and a contact-adjacent pause settles the actual HP
bar before the panel is reviewed.

### Historical v0.9.0 presentation corrections (packaged technical snapshot)

The presentation pass keeps the native menu and rendering contracts while
addressing four findings from the live v0.8.1 review:

- `tools/portrait_assets.py` derives one shared, head-anchored contained
  composition for the 32x40 selection card and 64x80 profile portrait. The
  generated `character-manifest.json` records the source crop, head anchor,
  margins, scale and `head_clipped=false` in `portrait_framing`; nearest-neighbor
  resampling keeps the authored edges intact.
- The arena picker keeps its native three-row cursor at `x8..247`,
  `y40..95` plus 56 pixels per row. Each complete stage image is contained in a
  `60x52` thumbnail at `x18..77`, `y42..93` plus 56 pixels per row. Location
  names and short captions use a separate text column, so the cursor does not
  cover scene pixels.
- FIGHT and RESULT text map ASCII `32..127` to the existing opaque glyphs
  `256..383` in the same `$5000-$57FF` guide-glyph VRAM window. Title, roster
  and arena menu text retain the original ASCII bank. Round markers `147/148`
  use the opaque panel background at palette index 1, preventing BG1 scenery
  from showing through interface cells.
- Damian's 64 v4 source PNGs and adjacent provenance files remain under
  `assets/art/characters/00-damian/`. Each legacy, motion, actions and
  airborne atlas receives one explicit, reviewed reference conversion under
  the `neutral-height` policy to the 311-pixel reference neutral before native
  encoding. The pinned factors are legacy `0.9255952381`, motion
  `0.9904458599`, and actions/airborne `0.9936102236`. The native idle height
  is 69, while the baseline, native palette and physical scale stay locked.
  The corrected contract records all 64 expected frame hashes under the Damian
  revision metadata; its hash is
  `00f90a6765904c546284832d399c1a5ec581f08fed64a7f7bedc6d9df985e261`.
  The other eleven fighter banks and all twelve palettes remain unchanged.

No combat, controls, audio, trace offsets, memory layout or Fighter/Wave ABI
change is part of this pass. The presentation suite and all five other native
reports, compatibility smoke, source-freeze evidence, matchup, bounded
independent combat, endurance and fresh-source validation now pass on the
corrected SHA. The historical [v0.9.0 Windows package](../dist/Abaqus-After-Hours-v0.9.0-Windows.zip)
is available and its archive audit passes 7,471 checks. Public-release review
remains open. This section is historical evidence for the v0.10.0 candidate.

### v0.10.0 cartoon-stage candidate (current packaged technical snapshot; human gates pending)

The candidate stage pass strengthens the early-1990s arcade direction with
original bold-navy cel-cartoon masters. Las Condes, El Castillo and La Oficina
each receive one versioned master, and the arena thumbnails use the same
complete scene art as their corresponding stage so the picker reads as one
coherent set:

- `assets/art/stages/00-las-condes-cartoon-v2.png`
- `assets/art/stages/01-castillo-cartoon-v2.png`
- `assets/art/stages/02-oficina-cartoon-v2.png`

Each PNG has an adjacent exact-basename JSON provenance file. The raw
`source-v2` images remain under `assets/art/stages/source-v2/`; the selected
`assets/art/stages/stages.json` uses schema 2 and `stages-v0.4.json` remains the
historical manifest. `tools/stage_sources.py` checks path, hash, RGB 1024x896,
exact 4x-native dimensions and at most 90 colors. `tools/stage_cartoon.py` maps
the authored stage features and existing ambient behavior into the candidate
palette/map. See the [stage pass note](STAGE-CARTOON-v2.md) and [cartoon
preservation report](cartoon-preservation-report.json).

The existing four 256-byte ambient phases, eight dynamic BG1 tiles, stage
transfer budget and `TRACE[115..118]` contract remain in force. Ambient change
counts by phase are Las Condes `[0,20,20,20]`, El Castillo `[0,18,18,18]` and
La Oficina `[0,6,6,6]`; the office keeps one 3-pixel monitor segment per
monitor at `y114` while protecting the monitor digits. This is a presentation
asset pass plus bounded menu-only correctness polish; active combat, C/ASM
fighter data, portraits, audio and the Fighter/Wave ABI remain unchanged.
Source freeze `8536bb6956212952c17302a62cc6c1de7e12a65d` / tree
`d524d3f960600dc5c9ff83578ac73675f9798735`, ROM SHA256
`a8f7b797a06bd242a18bf54400e53f043d5a84f274765ba3a34f9d8289ac5445` (header
`BE19`), native PPU review and focused probes are recorded. `Test.cmd` exits 0
with all six reports matching this SHA: 2,595 gameplay, 18,081 roster, 1,756
presentation, 1,020 focused-input, 8,131 stage and 622 Training checks
(32,205 total). Endurance and technical audio capture pass as documented above;
the 288-by-600 matchup/stage/policy/replay/symmetry run with four replays across
all three stages, pinned bsnes smoke at 600/600 plus the independent 28,800-frame
run, and `validate_release_evidence` also pass. The current [v0.10.0 Windows
package](../dist/Abaqus-After-Hours-v0.10.0-Windows.zip) is available and its
archive audit passes 7,472 checks. Human listening, gameplay, controller,
likeness/consent and public-use review remain open, with
`public_release_certified=false`.

### v0.6 integration performance notes

The native fast path caches actor-bank selection and per-action timing selection.
The packed `Fighter` layout uses stride 64 and `Wave` uses stride 16; both
layouts are compile-checked before assembly offsets are consumed. OAM and shadow
work is cached by integer position and facing, so unchanged actors do not rebuild
their sprite attributes every tick. Native health and energy bars retain their
existing glyph formulas. Impact HUD and empty-banner clears are serviced during
hitstop ticks, while interface DMA yields when an actor frame is being uploaded.
The engine and VRAM contract are unchanged. Interface impact feedback can settle
one to three video frames after the combat event while hitstop keeps the fight
state frozen.

`src/trace.asm` writes the read-only combat telemetry at the stable
`TRACE[0..113]` offsets and the ambient stores at `TRACE[115..118]`. `main`
samples post-wait PPU `STAT77` into `TRACE[114]` before DMA. v0.8 appends
`TRACE[119]` pause page, `[120]` guide build stage, `[121]` Training dummy and
`[122]` guide dirty; the earlier Fighter/Wave and ambient fields are unchanged.
A change to the native `Fighter` or `Wave` struct layout therefore requires
updating the assembly offsets and the documented trace contract together; the C
fields alone are not a safe layout change.

### v0.7 stage/effect integration notes

The stage/effect pass is implemented and verified in the v0.7.0 baseline ROM. Each of
the three stages has four original,
code-native ambient phases. A phase is eight 4bpp BG1 tiles (256 bytes) at
indices `960..967`, uploaded at VRAM word `$3C00`; each 256-byte phase occupies
VRAM words `$3C00-$3C7F`. The original stage graphics, tilemap
masters and palette masters are unchanged. Las Condes uses leaf shimmer and
glass reflection, El Castillo uses string lights, a party gesture and window
light, and La Oficina uses left and right monitor changes.

The ambient phase request advances every 16 live combat frames and is frozen
during intro, pause, hitstop and round-end states. An ambient upload yields to
the one-actor-per-vblank transfer and interface DMA, so it adds no actor or OBJ
budget and can complete after the request. `main` captures post-wait `STAT77`
in `TRACE[114]`; `TRACE[115..118]` expose completed phase, live clock, pending phase
and pending age for read-only diagnostics.

The original native effect cells now have authored phase variants for strike,
guard contact, high projectile and ground wave. The shadow source ellipse moves
from cell rows `Y22..27` to `Y16..21` (up six pixels); its OAM position moves
from `Y196` to `Y202` (down six pixels), retaining visible screen rows
`202..207` at priority 2. `tools/stage_assets.py`, `tools/effect_assets.py` and
`tools/test_stages.py` document the deterministic asset and verification paths.
The instrumented `STAT77` bit-7 overflow baseline has ROM SHA prefix `868f7dc` with
two low waves. The v0.7 native stage report records 4,537 checks against the
verified v0.7.0 baseline SHA, including the nine focused patch-only PPU assertions added after
the canonical `Test.cmd` run's 4,528 stage checks. The separate compatibility
smoke covers all three stages and actual PPU phases, freeze behavior and
synchronized low-wave combat against the same SHA. The v0.7 archive passes
214 technical checks and repeated packaging produces identical ZIP bytes.

The focused PPU phase captures observed changed-pixel counts of `17/18/18` for
Las Condes, `13/16/13` for El Castillo and `8/8/8` for La Oficina across
phases 1-3; phase 0 is the source-identical baseline. The synchronized
two-wave check peaked at 28 tiles (14 sprites), with `STAT77` equal to `0x01`
and overflow mask `0xC0` clear.

### v0.7.1 verified technical snapshot

The source freeze is commit
`6d756749dbc3fa176e26217f2f59525c9af360d8`, tree
`fa15fea48b5cc2a09608da199810db885872e434`. The canonical ROM is SHA256
`64dca043c8407659d05a22cc68b36d589d96bf4785fa630297d4e1526ed56022`, header
checksum `9496`; all five native reports point to it: 2,595 gameplay, 18,085
roster, 215 presentation, 999 focused-input and 8,143 stage checks (30,037
total). Thirty mirrored both-pad pause/cadence regressions and bounded
`clearFightHint`/`fillPausePanel` coverage are included. All native 288-case x
600-frame checks plus four replays pass, as do the independent bsnes smoke and
bounded 48 x 600 (28,800-frame) run.

- Projectile and low-wave CPU profiles choose their natural neutral opening when
  distance is greater than 110 native pixels and energy is at least 64, before
  the existing phase-97 cadence. Remaining cadence and family-distance bands
  are unchanged. The CPU skips this command while its own wave is active.
- The first frozen impact tick is quiet so the second actor upload can settle;
  HUD and counter/combo banner construction run together on the second frozen
  tick from the contact snapshot. Pending banner state clears on pause and
  reset. Damage, hit timing, combo linking and round outcomes are unchanged.
- Training Select applies `resetRoundState()` immediately and holds three frozen
  reset frames to flush HUD, banner and footer state; `fightClock` resets to zero.
  Unchanged labels are not rebuilt. KO cards are quiet first/panel second, and
  intro ticks 109, 108 and 107 are quiet, `GET READY`, and HUD.
- Native hot paths keep one resident ready-only FIFO record in `main`, with no
  poll or stream path and unchanged SDK loading. The streamed API and nonzero
  `AllocateRegion` require future stream service. `applyHitReaction` uses the
  256-entry ROM lookup of `12 + floor(final_u8_damage/3)` for every wrapped
  `u8` damage value and resets reaction fields;
  `fillBannerPanel` writes exact 96-word rows 10-12. Native geometry/cache
  refreshes `refreshFighterOam`, packed XY words feed OAM, and `queueFighter`
  preserves its four-byte pointer while uploading 3,840 bytes. The OAM audit
  passes 746 controller frames, comparing the full 544 OAM bytes and geometry
  for each frame.
- Fresh export validation matches the exact ROM and manifest plus 214 assets and
  symbols in 63.25 seconds; the invalid external SDK override was removed and
  source-local SDK tree pins are used. Native endurance passes 216,356 live
  frames in each of three modes at 60.098811862 FPS, one boot/unload with zero
  reboots, wraps 4/4/3, all coverage true and all five failure arrays empty.
  Video and PCM are healthy, SPC peaks at six and drains, stable FIGHT lag is
  zero, maximum non-fight windows are 402/587/252, and the accelerated run took
  164.968 seconds. `validate_release_evidence` passes.
- The test driver now uses the shortest four-by-three grid with at most three
  pulses per fighter; all 720 timeout, loaded-ID, stage and cadence checks remain
  unchanged, so this fixes test overhead rather than game behavior.

The v0.7.1 package and audit are historical. The v0.8.0 snapshot passed its
package guards and 7,471-check archive audit; it remains historical. The
historical v0.8.1 package also passes 7,471 technical audit checks. No public
release-readiness claim is made.

### v0.8.0 historical pause-guide and Training snapshot

The verified source-freeze snapshot is commit
`48f3ccb539492247b83f4360a50bdc020bad9dd6`, tree
`e571aca40019b868bf224bb619390f5ea651434e`; its ROM is SHA256
`53ef44225c83bd52ee0eea3910ba74ade5ba949af7aa7440c74d959812c13090`, header
`6A21`. Fighter assets, the 96x80 canvas, the original 48-frame hashes,
`Fighter` stride 64, `Wave` stride 16 and the existing trace fields through
`TRACE[118]` are unchanged.

The pause overlay cycles Normal, Controls and Specials with Select. Left/Right
toggles the guide pages. Start resumes first; otherwise B returns to the roster,
A resumes and Select cycles pages. The Specials page reads both live fighters and publishes
their names, special names and family types. The Controls page documents the
buttons, throws, uppercut, confirmed heavier attacks, the twelve-tick
quarter-circle motion and 32-energy cost. The guide is built through three
paused ticks, uses opaque original glyphs 256-383 at VRAM `$5000-$57FF`, and
does not overwrite the portrait block at `$4A00` or BG2 map at `$5800`.

Training pause Up/Down selects Stand, Guard High, Guard Low or Jump. Guard holds
relative back without retreat; the Jump dummy automatically jumps again after
landing. A live Select reset preserves the selected dummy, while starting a new Training match
returns it to Stand. Pause camera shake freezes, and pause-after-contact settles
the actual HP bar on the first quiet paused tick. The clean pause direction path
rejects same-pad and cross-pad opposite directions before guide or dummy actions
are applied.

`Test.cmd` requires `tools/test_training.py` as a sixth native suite. The six
reports and expanded evidence above are historical v0.8.0 results: 2,595
gameplay, 18,081 roster, 215 presentation, 997 focused-input, 8,131 stage and
622 Training checks (30,641 total), with a 7,471-check offline package audit.
The historical v0.8.1 verified snapshot supersedes those historical v0.8.0
results; its package and 7,471-check audit pass.

### v0.8.1 historical verified Reston v4 art revision

The historical v0.8.1 snapshot is an art-only source revision. Reston's complete 64-frame
set and selected portrait use the short-buzz-cap v4 sources:
`atlas-v4.png`, `animation-motion-v4.png`, `animation-actions-v4.png` and
`animation-airborne-v4.png`. The original v3 source files remain retained for
provenance. The adjacent `likeness-v4.json`, `animation-v4.json`,
`animation-airborne-v4.json` and `native-revision.json` record the imagegen
prompts, source hashes, expected native frame hashes and review scope.

The immutable v0.8.0 baseline pins all twelve prior 64-frame sets. The other
eleven fighter bank bytes are unchanged, and all twelve palettes and uniform
physical scales remain unchanged. Reston's source normalization, palette and
scale are locked at the established values; `native-revision.json` records the
old/new frame-hash digests, unchanged palette SHA256
`0fa34b1d226a993d001bd2df79e0b4f69827c214668446fe7b3b19bb3c64aa1d` and
uniform/physical scale `0.2280130293159609`.

The full64 native visual review accepted this historical revision for integration. Actual
human likeness and consent feedback remains pending. Native C/ASM, controls,
gameplay, audio, the 96x80 proportion contract and the native transfer ABI are
unchanged. All six native reports and the matching compatibility smoke pass
against ROM SHA256 `76b456d1ac75471a8b9710c61b0ce4c6ab9ca344b1b8a1f17e38f36e52904466`,
header `A358`, with the expanded matchup, stage, policy, replay, symmetry,
endurance and fresh-source evidence described above. The package and 7,471-check
audit pass; no public-readiness claim is made. The later live presentation review
identified the four defects tracked by the v0.9.0 correction pass.

### Fighter animation contract

Every fighter has 64 uniform 96x80 native frames, for 768 roster frames total.
The shared index contract is:

| Frame range | Content |
| --- | --- |
| `0-15` | Legacy neutral, walk, crouch, jump, normal, guard, hurt, victory, cast, uppercut, knockout and rush key poses |
| `16-31` | Motion and transition atlas: idle, forward gait, backward gait, crouch, jump and landing transitions |
| `32-47` | Action atlas: normal windup/active/recovery, specials, guard, hurt, victory and knockout transitions |
| `48-63` | v0.6 airborne, throw-role, knockdown and wake frames: dedicated air punch/kick cycles, thrower/victim roles, launch/fall, get-up and wake guard |

The source atlases are `animation-motion.png`, `animation-actions.png` and the
v0.6 `animation-airborne.png` under each fighter directory. Each source sheet
is a 1254x1254 RGBA sheet with sixteen separately extracted figures in a
four-by-four grid. The pipeline places the figures in uniform 96x80 native
cells. The generated native review strip `assets/generated/fighterXX.png` is
6,144x80 RGBA, and the encoded frame data is divided into eight contiguous
eight-frame banks: `fighterXX` through `fighterXXh`. Every bank is 30,720
bytes, below the 32 KiB LoROM boundary. One fifteen-color OBJ palette is shared
by that fighter's complete 64-frame set.

The first neutral frame of each new atlas is normalized once against the
fighter's existing idle frame. That establishes one physical scale for all 64
frames. The original 48 frame pixels and palette bytes remain locked; the new
range is normalized at the established scale. The result stays inside the
94x77 safe area of the 96x80 canvas with a native feet baseline at height 78.
The renderer never rescales a pose independently, so a wide kick, rush,
throw, knockdown or wake pose does not change the fighter's apparent size.

Each fighter has a private animation clock. Idle uses four frames, forward and backward gait use four frames each, and crouch, jump and landing have explicit transitions. Normals and specials expose windup, active and recovery frames, while guard, hurt, victory and knockout have their own transitions. Gait advances from distance travelled, and the clock freezes during pause and hitstop.

`tools/fighter_assets.py` keeps the twelve identity masters, palettes and
costumes separate. The historical v0.8.0 baseline keeps all twelve prior
masters selected; the historical v0.8.1 snapshot adds Reston's v4 short-buzz-cap
sources while retaining the v3 files. The v0.9.0 presentation pass adds
Damian's v4 source set while retaining the v0.8.1 native palette and physical
scale; its per-atlas neutral-height conversions are recorded in the revision
metadata. The twelve new airborne atlases are
generated with the built-in imagegen workflow; each `animation-airborne.json`
records its prompt and provenance, while the earlier motion/action metadata is
retained. Raster resizing, palette quantization and tile encoding are
deterministic hardware steps after authoring.

The v0.5 stage pipeline loads three independent PNG masters from `assets/art/stages/`, with `assets/art/stages/stages.json` describing their source metadata. The home screen, four-by-three fighter selection and arena plates use original art under `assets/art/menu/`, with prompts in `assets/art/menu/prompts.json`. Menu lettering is rendered from the project's original bitmap glyph set. Selected 64x80 profile portraits use a dedicated BG2 block and palette 1; v0.9.0 adds the shared head-anchored contained composition for both 32x40 and 64x80 portraits, recorded as `portrait_framing` in `assets/generated/character-manifest.json`. Images use nearest-neighbor reduction to retain hard edges. `tools/portrait_assets.py` owns the shared crop metadata. The manifest records source hashes, palette values, extraction boxes, uniform scales and native frame hashes for review.

The frozen v0.10.0 stage candidate adds the three versioned cartoon masters,
adjacent exact-basename provenance JSON and `assets/art/stages/source-v2/` raw
inputs. The selected `assets/art/stages/stages.json` uses schema 2, while
`stages-v0.4.json` remains historical. `tools/stage_sources.py` validates the
path, hash, RGB 1024x896, exact 4x-native dimensions and at most 90 colors;
`tools/stage_cartoon.py` adapts the existing feature-driven ambient work to the
new palette/map. The four 256-byte phases, eight dynamic cells and
`TRACE[115..118]` contract stay unchanged. Focused PPU/presentation/stage/menu
  probes pass and all six current reports match the frozen SHA; the extended
  technical evidence and `validate_release_evidence` also pass. Packaging and
  human review remain open.

## Simulation

Combat uses integer 12.4 fixed-point positions. Standing, crouching and airborne bodies use feet-relative contact rectangles independent of the 96x80 art canvas. The body half-width is ten pixels; action-specific vertical bands intersect the standing or crouching body. Throws use their exact profile range without the normal-attack reach padding. Equal-center overlaps and post-impact stage clamps are symmetric. Each attack has startup, active and recovery durations. Push boxes, direction, height, guard type and one-hit confirmation determine contact. Both normal-hit candidates are collected before resolving damage, allowing trades. Projectiles have independent lifetime, position and collision.

Input is sampled every simulation tick. Opposite horizontal or vertical directions resolve to neutral before movement and command recognition. Attack and jump edges have a six-tick buffer; a held Up input can carry a buffered jump through landing. A character special accepts a true twelve-tick Down -> Down+Forward -> Forward + punch motion, while the accessible Down + punch shortcut remains. The shortcut requires no Back direction, so Down + Back + punch is not treated as a special. Normals confirmed by real damage can cancel into heavier normals or a character special during their cancel window; a guarded contact does not enable these hit-confirm cancels.

Hitstop freezes combat expiry, movement, animation clocks and effect clocks while
input edges continue to be sampled for the buffer. Guard stun is eight ticks
with approximately one pixel of blocked pushback; a real hit uses approximately
two pixels. Air punch and kick each have dedicated anticipation, active and
recovery art. Heavy uppercuts, heavy low kicks and rising specials can start a
knockdown sequence. Throws use separate thrower/victim poses, delay damage until
ground impact, and tech when both players throw on the same contact snapshot.
The downed flow distinguishes lift, flight, floor, get-up and wake; wake grants
four invulnerability ticks and accepts buffered attack or jump input during its
final six ticks. Training reset clears active throw/down/wake state, and health
recovery is gated until the fighter is free of hurt and wake invulnerability.

The game caches both active profile pointers when loading the fighters. Combat helpers reuse them instead of resolving a twelve-way roster lookup for every timing, collision and trace read. The rules and frame-data tables remain shared while every fighter keeps individual movement, jump, throw, normal and special tuning.

Direct contact outcomes are `0` none, `1` guarded and `2` real damage. Projectile
impacts do not mark an unrelated current normal as confirmed. A combo links only
while the defender remains in unblocked hit stun; its 45-tick banner timer is
cosmetic. Blocking breaks the attacking chain, and receiving a real hit clears
the defender's previous chain and stale input buffers. Inputs sampled after the
impact during hitstop retain the existing six-tick buffering semantics.

Fight hints occupy BG2 rows 26-27 during the first intro only. A separate dirty
flag clears these 128 bytes without forcing a full interface transfer alongside
the actor upload. Results place the P1/P2 round score on row 15 and quote on 17.

The CPU samples one decision per live tick using distance, opponent attack
state, projectiles, a deterministic PRNG and three difficulty levels. Its
neutral facing is updated before that decision. The verified v0.6.1 logic checks
the opponent's upcoming active window at `tick+1` because controller capture
precedes physics, prioritizes approaching waves within 96 native pixels, and
uses family-specific special distance bands. Normal and Hard crouch-guard low
waves, while the same levels send a wake jump edge at `DOWN_WAKE` tick 0. The
approach branch closes the 29-46 pixel gap, and throw decisions use each
profile's `throwRange`. Crouch guard selects animation frame 3 so the visible
pose matches logical guard pose 9. Input coverage exercises all three
difficulties and four special families for 600 live ticks each, with near/far,
approach, low-guard, wake and strict no-KO lookahead cases. These are CPU
correctness checks, not a strategic-AI or balance-completion claim.
Fighter selection, arcade progression, training reset and menu navigation remain
native controller actions.

## Audio

The generator writes original Impulse Tracker modules with five synthesized PCM
samples. `smconv` creates the soundbank and SNESMod runs the music on the
emulated SPC700. Combat audio uses four resident SPC effects loaded alongside
each music module: `effects.it` occupies soundbank module 0, while music keeps
module IDs 1-4. Scene load calls `spcLoadEffect(0)` through `spcLoadEffect(3)`
to populate resident effect slots. `spcAllocateSoundRegion(0)` disables the
separate streaming region. Gameplay uses
`spcEffect` with pitch 2 at 8 kHz and the existing volume/pan values, preserving
the synthesized cues while avoiding per-hit BRR streaming stalls.

If several cues arrive on the same simulation frame, the sound path coalesces
them by priority: round, impact, special, then swing. The generated effects-first
module order is checked at compile time; scene loading reloads the four effect
slots after replacing the music module. The resident-effect migration is
included in the verified v0.6.1 baseline; the CPU pass does not change the
audio path.

## Verification

`tools/emulator.py` hosts the official Snes9x 1.63 x64 libretro core. `tools/test_rom.py` supplies SNES controller inputs, captures actual video/audio and reads a reserved WRAM trace at `$7FFF00`. The host never writes game memory. Sprite checks compare actual emulated VRAM with the cartridge's encoded bytes.

The historical v0.8.0 snapshot added `tools/test_training.py` as a sixth required
native suite. It reads pause-guide trace fields 119-122, verifies staged guide
publishing and VRAM placement, cycles all four Training dummy modes, checks
pause SOCD and both-pad resume/roster priority, and remains headless and
silent. The historical six reports pass on its exact SHA with 30,641 checks;
compatibility, matchup, bounded independent combat, endurance and fresh-source
evidence also pass. The historical v0.8.1 results are recorded above.

`tools/test_characters.py` adds controller-driven verification of each fighter on
both player sides, movement and jump differences, observable special-family
behavior, exact rows from all eight sprite banks and the uniform 96x80
proportion contract. `tools/test_presentation.py` verifies the home screen,
four-by-three selection navigation, all twelve 64x80 profile portrait transfers
and all three stage plates. The v0.9.0 presentation pass extends that review to
the complete 32x40/64x80 portrait compositions, arena thumbnail containment and
HUD/result glyph background cells. The v0.7 `tools/test_stages.py` suite adds native
checks for the four-phase BG1 ambient tiles, dynamic map entries, source
palette/graphics preservation, live-only phase timing, actor/interface DMA
yields, pause/hitstop/round-end freezes and stage effect/OAM behavior. It passes
against the historical verified v0.8.1 source-freeze ROM; that stage report records 8,131
checks, including exact shadow geometry and the focused PPU assertions.
`tools/test_inputs.py` covers SOCD neutralization,
buffered attacks and jumps, true and shortcut motion commands, hitstop input
capture, hit-confirm cancels, guard timing, animation freezing and the Training
Select reset. On the historical corrected v0.9.0 SHA, all six reports pass: 2,595 gameplay,
18,081 roster, 1,756 presentation, 997 focused-input, 8,131 stage and 622
Training checks (32,182 total). The 288-by-600 matchup/stage/policy/replay/
symmetry run, pinned bsnes smoke with bounded 48-by-600 coverage, endurance of
216,356 live frames in each of three modes, fresh 214-asset export in 75.078
seconds and
`validate_release_evidence` also pass. The historical [v0.9.0 Windows package](../dist/Abaqus-After-Hours-v0.9.0-Windows.zip)
is available and its archive audit passes 7,471 checks. The historical v0.7.1 snapshot had all five native reports passing
against ROM SHA256
`64dca043c8407659d05a22cc68b36d589d96bf4785fa630297d4e1526ed56022`:
2,595 gameplay, 18,085 roster, 215 presentation, 999 focused-input and 8,143
stage checks (30,037 total). Thirty mirrored both-pad pause/cadence regressions
and bounded `clearFightHint`/`fillPausePanel` coverage are included. All five
suites capture audio data without
opening an audio device or a native window and preserve the user's foreground
focus. Input coverage spans three difficulties and four special families for
600 live ticks each (7,200 total), plus near-special, far-negative, 29-46
approach, low-guard, wake and strict no-KO lookahead cases.

The historical `docs/compatibility-test-report.json` passed against the same ROM
SHA using the pinned bsnes2014 Accuracy core. Its scope is an independent smoke:
title/select/arena/fight captures, controller movement and jump, all three
stages across four actual PPU phases with intro/pause/hitstop/round-end freeze,
static plate color samples within eight channel levels (maximum delta 7),
synchronized low-wave combat and neutral 600-frame cadence with every delta
equal to one, plus captured audio. The low-wave probe observed 37 two-wave
frames in 600 with `STAT77` at `0x01` and overflow mask `0xC0` clear. It is not
full combat, soak or human verification. Run it with PowerShell
`tools/setup-compat.ps1` followed by `python tools/test_compatibility.py`.

The historical five native reports and compatibility report carried the same
v0.7.1 SHA. The compatibility host uses the pinned core's actual 512x224,
2048-byte-pitch BGRX callbacks with stride-authoritative decoding; this fixes
the prior pixel-format metadata limitation and makes the stage color assertions
meaningful. That historical technical snapshot recorded 30,037 native checks,
independent smoke plus bounded 28,800-frame coverage, and the full native
endurance run. Human balance, art review, real-console and public-release
gates remained open; the offline package passed 6,153 technical audit checks.

Each suite stores the tested ROM SHA256 in its report:

- `docs/test-report.json`
- `docs/character-test-report.json`
- `docs/presentation-test-report.json`
- `docs/input-test-report.json`
- `docs/compatibility-test-report.json`
- `docs/stage-test-report.json`
- `docs/training-test-report.json` (v0.8.1 verified Training suite)

The reports are authoritative for the exact ROM SHA recorded in each file. The
historical v0.8.1 native reports and compatibility report point to
`76b456d1ac75471a8b9710c61b0ce4c6ab9ca344b1b8a1f17e38f36e52904466`; the native
batch covers both boot phases, two-controller air/trades/combo cadence,
resident-audio probes, CPU reactions and stage/effect PPU behavior. The cadence
probe and native screenshot/GIF evidence remain tied to their recorded ROM hash
and must not be reused after a hash change. Earlier v0.8.0, v0.7.0 and v0.6.1
snapshots remain historical evidence for their respective SHAs.

An earlier four-family 600-frame probe was too narrow to characterize worst-case
audio or UI timing. Those v0.7.1 results remain historical; the historical
v0.8.1 six-suite and broader technical evidence cover the expanded cases. Human
review remains open; the v0.8.0 offline package and its 7,471 technical audit
checks remain historical fallback evidence. The historical v0.9.0 reports and
extended evidence pass on the corrected SHA; the packaged v0.9.0 technical
audit passes 7,471 checks. The verified v0.10.0 snapshot has all six reports
matching its SHA (32,205 checks) plus focused PPU, presentation, stage and menu
evidence; endurance, audio, matchup, pinned bsnes/independent compatibility
evidence and `validate_release_evidence` all pass. The current [v0.10.0 Windows
package](../dist/Abaqus-After-Hours-v0.10.0-Windows.zip) is available and its
archive audit passes 7,472 checks. Human listening, gameplay, controller,
likeness/consent and public-use review remain open, with
`public_release_certified=false`.
Two issues found during earlier integration shaped the implementation:

1. C-level row-by-row sprite uploads exceeded vblank, leaving lower sprite rows blank. The native assembly transfer and one-pose budget fixed this class of failure; current validation still checks every row.
2. This pinned 816-tcc build incorrectly lowers logical-OR expressions with
   three or more terms, including knockout resolution and hurt/down/air
   eligibility. Use individual branches. The build lint rejects new `||` chains
   with three or more terms in project C/headers. A related real-hitstun guard
   correction gates blocked eligibility with `(!d->hurt || d->guard)`: a new hit
   cannot become a guard during real hitstun, while existing guard stun remains
   blockable; real hits also clear guard. Native tests cover contact, guard,
   downed control, facing, round, timeout and arcade outcomes.

3. Real KO contact resolution keeps damage, winner selection, timers and layout
   unchanged. `roundBannerPending` keeps the first frozen `roundEnd` tick quiet,
   then transfers the panel, name and HUD on the second tick, avoiding a
   contact-time stall.

The v0.6.1 packager run and its 202-check audit remain historical. The historical
v0.8.1 six native reports plus compatibility match their exact SHA, and the
source-freeze, fresh-export and endurance evidence passes are complete. The
historical v0.8.1 package and 7,471-check audit pass; the v0.8.0 offline package passes
7,471 technical audit checks as historical evidence; the
v0.7.1 offline package and its 6,153-check audit remain historical.
Human balance sessions, art review, real-console/flash-cartridge testing and
public-release review remain separate open gates.

Two consecutive historical v0.8.1 packaging runs produce identical 6,546,645-byte Windows
archives, SHA256
`04d951c3abef278afada5a666f9eec8a04d140650354bd82506e750e2849e0b6`.
The matching final audit passes 7,471 technical checks and keeps
`public_release_certified=false`.

Historical v0.8.0 packaging produced a 6,546,551-byte Windows archive, SHA256
`44f92c041563badc1a6b903e859ad4dd5258b5bd85f6d253cdf74b5c06641869`.
That historical archive audit passed 7,471 checks with
`public_release_certified=false`.
