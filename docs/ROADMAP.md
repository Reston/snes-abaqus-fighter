# Polish roadmap
<!-- candidate-version: 0.22.1; rom-sha256: 52725899fa86b4ee3d3f3f022dae374c1ab4ff8777bdab4a7134640c34dc8727 -->

## Current v0.22.1: nine approved improvements

Features 01–07, 09 and 10 are approved for main. **Feature 08 is deferred**:
the camera and ambient art are restored to v0.21.0; its branch/worktree remain
for polish. The six native suites pass 36,253 exact-ROM checks and matching
independent smoke passes. [Current release and scope](RELEASE-v0.22.1.md).
Local 1v1 already works in **Local Versus** with separate controller ports.
Walking improvements and clearer local-play discovery are the next follow-ups.
The v0.22.0 material below is historical, including its ten-feature review gallery.

## Historical v0.22.0 combined notes

The active public-release target and evidence gates are in
[PUBLIC-RELEASE.md](PUBLIC-RELEASE.md). Treat this roadmap as the work backlog;
the release gates decide when the public candidate is actually ready.

The active integration candidate is **v0.22.0**, with all ten feature PRs merged
into `integration/ten-improvements-v022`. Main remains v0.21.0 until your combined
playtest and [PR #1](https://github.com/Reston/snes-abaqus-fighter/pull/1)
merge. `Play.cmd` in that checkout runs the combined game. The
[all-ten release guide](RELEASE-v0.22.0.md) maps each feature and its PR.
Combined automated verification passes: 36,253 six-suite checks, matching
independent smoke, all ten focused proofs, preservation/bank/transfer checks
and a fresh export. See [the exact-ROM record](expansion-v0.22.0-verification.json). No v0.22.0 human approval, offline archive or
full release-scale evidence exists; `public_release_certified` remains false.

The latest full offline archive is **v0.19.0**, which added paused CPU level
controls, visible version identity and canonical generated text. Its six suites
passed 35,715 exact-ROM checks, with extended combat, three native live hours
and a committed-source rebuild. Two identical Windows packages passed 9,299
technical audit checks. See [that historical note](RELEASE-v0.19.0.md).
Human approvals remain open.

## Combined v0.22.0 review milestone

- Animation weight and individual intro/victory gestures reuse all twelve
  existing 64-frame sets, preserving approved Damian v5 and every portrait/palette/scale.
- Light/strong/guard feedback and tuned Y/X/B/A roles add clearer contact and
  risk/reward. Twelve full-96-energy supers use fresh neutral Y+B; Normal/Hard
  CPU choices are fallible and follow defense priority.
- Training page 3 provides five-command history, current/last combo damage,
  ordinary-special `SP!` and three drills. Original PAUSED dummy/CPU-level
  controls and reset priorities remain.
- CPU personalities, subtle band parallax, refreshed ambient cells and winner
  reactions, personal Arcade exchanges/quotes/endings, and resident speech/cues
  are combined. The original fighter/stage masters and five scores remain.
- Review the completed combined candidate in one human playtest before merging.
  Then resolve reported defects before the main merge. Regenerate release-scale
  evidence and audit a new package separately if a v0.22.0 archive is requested.

Human balance/feel, full listening, physical controllers, likeness/consent and
public-use review remain future work. The native band-scroll implementation
does not complete the broader layered-art roadmap or original-console support.

Delivered since v0.10 are the corrected Lars portrait/location previews and
winner cards (v0.10.1/v0.11), arbitrary or mirror Training opponents and original
champion illustration (v0.12), original victory music and pause priority/cold
build fixes (v0.13), clearer menu/motion help and authoring guards (v0.14), and
rear medium-kick contacts with landing-safe recoil and practice cues (v0.15).
Bounded Normal/Hard CPU anti-air and all-roster cross-up practice shipped in
v0.16. CPU Training and its timing fixes shipped in v0.17. Historical sections below retain their original evidence scope.

The v0.1 release established a playable native cartridge, the requested roster and locations, a reproducible toolchain and emulator-based integration coverage. The v0.2 pass set the cartoon arcade direction. v0.3 introduced twelve individual sixteen-pose atlases and likeness correction. v0.4 standardized the 96x80 physical scale and rebuilt the presentation. v0.5.0 adds animation, simpler menus and buffered inputs. v0.5.1 tightens contact, hit-confirm and combo rules, clears live-fight instructions, adds result scores and corrects emulator scaling. The v0.6.0 source integration adds the final airborne, throw, knockdown and wake frame range and combat flow. The v0.6.1 CPU-correctness pass has four-suite and pinned compatibility evidence on one ROM SHA, with public gates still open. v0.7.0 stage/effect integration has a verified ROM, a 214-check archive audit and reproducible development packaging. The historical v0.7.1 package has a 6,153-check audit. v0.8.0 remains the historical pause-guide and Training baseline. v0.8.1 is the historical Reston art snapshot; v0.9.0 remains the historical packaged technical fallback. The v0.10.0 cartoon-stage candidate now has matching six-suite native reports, passing extended technical evidence and a 7,472-check packaged archive; human review remains open.

## v0.5 baseline

The v0.5 baseline added the following source and asset contracts:

- The target cartridge is a 4 MiB NTSC FastROM LoROM image across 128 banks.
- Every fighter has 48 uniform 96x80 frames. Legacy frames 0-15 are followed by 16 motion/transition frames and 16 action frames, for 576 native frames across the 12-fighter roster.
- Twenty-four built-in imagegen animation atlases provide 32 new drawn in-between frames for each fighter. Each new atlas is normalized once against the existing neutral idle, then shares one physical scale across all 48 frames. The original identity masters remain unchanged, including Reston's v3 short-hair correction.
- Native frame data is divided into six 30,720-byte banks per fighter, with a shared fifteen-color OBJ palette and 4,608x80 native review strip for each 48-frame set.
- Per-fighter animation clocks use distance for forward/backward gait and cover idle, forward, backward, crouch, jump, landing, attack windup/active/recovery, guard, hurt, victory and knockout. Pause and hitstop freeze the clock.
- The input path adds six-tick attack/jump buffering, held-Up landing autojump, opposite-axis neutralization, a twelve-tick Down -> Down+Forward -> Forward punch motion and hit-confirm normal/special cancels. The legacy Down+P shortcut remains available; Down+Back+P is not a special.
- Guard stun is eight simulation ticks with about one pixel of blocked pushback; real hits use about two pixels. Training exposes a Select quick reset.
- Home, fighter select and arena menus use a minimal royal-navy, white and gold layout with one cursor, the four-by-three roster grid and the selected large portrait. The old profile statistics/family panel is removed from the visual hierarchy.

These changes preserve the native emulator requirement and the fixed actor canvas.
The v0.6 integration supersedes the legacy air-attack placeholder with
dedicated source art; its latest evidence snapshot is documented below.

## v0.6.0 combat-animation integration

The current source milestone carries the following contracts forward from the
v0.5.1 baseline:

- Every fighter has 64 uniform 96x80 frames: legacy 0-15, motion/transition
  16-31, action 32-47 and airborne/throw/knockdown/wake 48-63. The original 48
  frame pixels and palette bytes remain locked.
- Twelve new `animation-airborne.png` atlases and adjacent provenance files
  provide dedicated air punch and kick anticipation, active and recovery art,
  thrower/victim roles, knockdown poses and wake poses. Identity masters and
  costumes remain separate.
- Native data uses eight 30,720-byte banks per fighter and a 6,144x80 review
  strip, with one shared fifteen-color palette and one uniform physical scale
  across all 64 frames.
- Combat distinguishes throw lift, flight, floor, get-up and wake. Throw damage
  lands at ground impact; simultaneous throws tech; heavy uppercuts, heavy low
  kicks and rising specials can cause knockdown; wake grants four invulnerability
  ticks and accepts buffered attack or jump input during its final six ticks.
- Training health recovery is gated while a fighter is hurt, downed or
  wake-invulnerable, and Select resets the round while clearing active
  throw/down/wake state.
- The native fast path caches actor-bank and per-action timing selection, uses
  compile-checked `Fighter` stride 64 and `Wave` stride 16 layouts, and caches
  unchanged OAM/shadow work by integer position and facing. Native health and
  energy bars preserve their glyph formulas; impact HUD and empty-banner clear
  continue through hitstop ticks while interface DMA yields to actor uploads.
  The engine and VRAM contract are unchanged, although interface feedback may
  settle one to three video frames after the combat event.
- `src/trace.asm` writes read-only telemetry directly at stable `TRACE[0..113]`
  offsets. Any packed `Fighter` or `Wave` layout change requires updating the
  assembly offsets and the trace documentation together. The earlier four-family
  600-frame probe was too narrow to characterize worst-case timing; two-actor
  attack/impact scenarios exposed additional audio and interface lag, so it is
  not used as worst-case evidence.
- The original streamed-BRR combat cues caused real stalls under simultaneous
  attack/impact cases. The v0.6 audio path loads four resident SPC effects from
  `effects.it` at scene load, keeps music module IDs 1-4, uses `spcEffect` at
  pitch 2 and 8 kHz with the existing mix values, and coalesces same-frame cues
  by round, impact, special, then swing priority.
- The v0.6.0 baseline reports pass against ROM SHA256
  `0d907717d284c9d0056434e69da0a265c2b09cf4c84761aa32998b4fc0bbd5ae`:
  2,595 gameplay, 18,085 roster, 215 presentation and 604 focused-input
  checks (21,499 total). The later v0.6.1 evidence superseded that baseline;
  it does not close public, human-playtest, independent-emulator or real-console
  gates.

## Future art and animation

- Review the new airborne, throw, knockdown and wake drawings, then add more
  character-specific in-between art for weight and footwork after human review.
- Align hands and feet more closely to gameplay contact points and add per-pose hitboxes.
- Review v0.22.0's delivered band parallax and winner reactions; further illustrated layers and coworker animation must preserve native tile, OBJ and vblank budgets.
- Review the delivered original champion illustration and winner cards with
  the team; further presentation changes should follow actual feedback.

## v0.6.1 CPU-correctness pass

The historical verified source is ROM SHA256
`945540153834953a1da1c3dd401ef203443da55aee37d916289a8a6c0c93aeee`. It keeps
the v0.6.0 art, character profiles and native ABI unchanged while correcting
CPU timing and reaction cases:

- CPU attack defense checks the opponent's upcoming active window at `tick+1`,
  because controller capture precedes physics.
- Incoming waves have priority within a 96-pixel approach window; Normal and
  Hard crouch-guard low waves.
- Special decisions use family-specific distance bands, the approach branch
  closes the 29-46 pixel gap, and throw decisions use each profile's
  `throwRange`.
- Normal and Hard send a wake jump edge at `DOWN_WAKE` tick 0. Crouch guard
  selects its crouched pose so the visible frame matches the logical guard.

The four native reports pass with 2,595 gameplay, 18,085 roster, 215
presentation and 854 focused-input checks (21,749 total). CPU coverage spans
three difficulties and four special families for 600 live ticks each, with
near-special, far-negative, 29-46 approach, low-guard, wake and strict no-KO
lookahead cases. A separate pinned bsnes2014 Accuracy smoke passes on the same
ROM for title/select/arena/fight captures, controller movement and jump, 600
one-tick cadence frames and captured audio. These are correctness and smoke
checks; they do not establish strategic AI or complete human balance tuning.

Real KO contact resolution keeps damage, winner selection, timers and layout
unchanged; `roundBannerPending` keeps the first frozen `roundEnd` tick quiet,
then transfers panel/name/HUD on the second tick to avoid a contact-time stall.

## v0.7.0 stage/effect integration (verified source milestone)

The current source pass adds restrained, code-native motion to the three stage
masters without changing their original graphics or palettes:

- Four ambient phases per stage use eight BG1 tiles at indices `960..967`,
  uploaded in the `$3C00-$3C7F` dynamic tile window as 256 bytes per phase.
- Las Condes animates leaves and glass reflection; El Castillo animates string
  lights, a party gesture and a window light; La Oficina animates its monitors.
- The phase request advances every 16 live combat frames and freezes during
  intro, pause, hitstop and round end. Ambient DMA yields to actor and
  interface transfers and uses no additional OBJ sprites.
- Original native effect cells gain small authored phases for strike, guard
  contact, high projectile and ground wave. The shadow source ellipse moves
  from cell rows `Y22..27` to `Y16..21`; OAM moves from `Y196` to `Y202`,
  retaining visible screen rows `202..207` at priority 2.
- `main` records post-wait `STAT77` at `TRACE[114]`; `TRACE[115..118]` record
  completed phase, live clock, pending phase and pending age. The Fighter/Wave ABI at
  `0..113` remains unchanged.

The historical v0.7.0 ROM is SHA256
`e44a739488bd549cfcffbe35bbb32bb5e71d9d2dce12bea6562ebd3dd0c15b84` with
header checksum `0953`. Five native reports pass with 2,595 gameplay, 18,085
roster, 215 presentation, 854 focused-input and 4,537 stage checks (26,286 in
the v0.7.0 report snapshot). The canonical `Test.cmd` run recorded 4,528
stage checks; a focused extension added nine patch-only PPU assertions and
reran the unchanged ROM/engine. The expanded compatibility smoke also passes
against the same SHA. The v0.7 archive passes 214 technical checks and repeated
packaging produces identical ZIP bytes. Public, human-balance, independent full-combat/soak and real-console
gates remain open.
The phase captures changed `17/18/18`, `13/16/13` and `8/8/8` pixels across
the three stages (phases 1-3); the synchronized two-wave check peaked at 28
tiles / 14 sprites with `STAT77` `0x01` and overflow mask `0xC0` clear.

## v0.7.1 historical technical snapshot

Source freeze commit:
`6d756749dbc3fa176e26217f2f59525c9af360d8`; tree:
`fa15fea48b5cc2a09608da199810db885872e434`.
Canonical ROM SHA256:
`64dca043c8407659d05a22cc68b36d589d96bf4785fa630297d4e1526ed56022`, header
checksum `9496`. The canonical `Test.cmd` batch passes all five native suites:
2,595 gameplay, 18,085 roster, 215 presentation, 999 focused-input and 8,143
stage checks (30,037 total). Thirty mirrored both-pad pause/cadence regressions
and bounded `clearFightHint`/`fillPausePanel` coverage are included. Full native
288-case x 600-frame coverage plus four replays passes; the independent bsnes
smoke and bounded 48 x 600 (28,800-frame) run pass too.

The CPU keeps the natural long-range projectile/low-wave opening above phase
97, skips a CPU-owned wave while active, and preserves family bands. The first
frozen impact tick is quiet for the second actor upload; HUD and
`COUNTER!`/`COMBO!` construction run together on the second tick. KO cards are
quiet first/panel second. Training Select applies the round state immediately,
flushes HUD/banner/footer over three frozen reset frames and resets `fightClock`
to zero. Intro ticks 109, 108 and 107 are quiet, `GET READY`, and HUD.

Fresh export validation matches the exact ROM/manifest plus 214 assets and
symbols in 63.25 seconds. Native endurance passes 216,356 live frames in each
of three modes at 60.098811862 FPS, one boot/unload with zero reboots, wraps
4/4/3, all coverage true and all five failure arrays empty. Video and PCM are
healthy, SPC peaks at six and drains, stable FIGHT lag is zero, maximum
non-fight windows are 402/587/252, and the accelerated run took 164.968
seconds. `validate_release_evidence` passes. The test driver uses the shortest
four-by-three grid with at most three pulses per fighter; all 720 timeout,
loaded-ID, stage and cadence checks remain unchanged, so this is test overhead
only.

The package passed 6,153 technical audit checks. Human likeness and balance,
listening, controller, real-console and branding gates remained open; no
public-readiness claim was made.

## v0.8.0 historical verified pause-guide and Training snapshot

The verified source-freeze snapshot is commit
`48f3ccb539492247b83f4360a50bdc020bad9dd6`, tree
`e571aca40019b868bf224bb619390f5ea651434e`. Its 4 MiB ROM is SHA256
`53ef44225c83bd52ee0eea3910ba74ade5ba949af7aa7440c74d959812c13090`, header
`6A21`.

- Pause now cycles Normal, Controls and Specials with Select. Left/Right toggles
  guide pages. Start resumes first; otherwise B returns to the roster, A resumes
  and Select cycles pages. The Specials page reads both live fighter names, special names and
  family types. The Controls page documents the six buttons, throws, uppercut,
  confirmed heavier attacks, the true twelve-tick quarter-circle and 32-energy
  cost.
- Training pause Up/Down cycles Stand, Guard High, Guard Low and Jump. Guard
  holds relative back without retreat, and the Jump dummy automatically jumps
  again after landing. Live Select resets the round while preserving the dummy choice. A new
  Training match starts at Stand. Pause camera shake freezes and the first quiet
  paused tick after contact settles the actual HP bar.
- The guide uses original opaque glyphs 256-383 in VRAM `$5000-$57FF`, leaves
  the portrait at `$4A00` and the BG2 map at `$5800`, and publishes rows 5-27
  over three paused ticks while yielding to actor DMA. Fighter assets and the
  Fighter/Wave layout remain unchanged. Trace fields 119-122 expose pause page,
  guide build stage, dummy mode and guide dirty state after the unchanged
  fields 0-118.
- `tools/test_training.py` is the sixth required `Test.cmd` suite. All six
  reports pass on the exact ROM SHA with 30,641 checks: 2,595 gameplay, 18,081
  roster, 215 presentation, 997 focused-input, 8,131 stage and 622 Training.
  Matching compatibility, matchup, bounded independent-combat, endurance and
  fresh-source evidence also pass. The training host enables
  `snes9x_up_down_allowed`; the offline `Controls::AllowLeftRight` preference
  does not change existing user settings.

Reston's remaining likeness review and human balance/listening/controller,
real-console and branding review stay open. The offline package passes 7,471
technical audit checks; this section records historical evidence, not public
approval.

## v0.8.1 historical verified Reston v4 art integration

The historical verified source freeze is commit
`fe05e5fd1391a1db20f1b66f1e9f6e699445e77a`, tree
`46e1af160ffb8ab6cb768e3d9deec1352d77ae83`. Its 4 MiB ROM is SHA256
`76b456d1ac75471a8b9710c61b0ce4c6ab9ca344b1b8a1f17e38f36e52904466`, header
`A358`. The revision changes Reston's art sources only: all 64 frames and the
portrait use `atlas-v4.png`, `animation-motion-v4.png`,
`animation-actions-v4.png` and `animation-airborne-v4.png`; the original v3
sources remain retained.

The immutable v0.8.0 baseline pins all twelve old 64-frame sets. The other
eleven fighter bank bytes are identical, all twelve palettes and uniform scales
are unchanged, and Reston's source normalization, palette and scale are locked.
`likeness-v4.json`, `animation-v4.json`, `animation-airborne-v4.json` and
`native-revision.json` retain imagegen provenance and expected native hashes.
Full64 native visual review accepted the revision for integration. The user
confirmed the revised short buzz cut looks closer; the
[scoped feedback record](RESTON-LIKENESS-v4.md) retains that response. Final team
likeness and public-use consent remain pending. Native C/ASM, controls,
gameplay and audio are unchanged.

The historical six native reports pass on this SHA: 2,595 gameplay, 18,081 roster, 215
presentation, 997 focused-input, 8,131 stage and 622 Training checks (30,641
total). Fresh committed export, 288-by-600 matchup/stage/policy/replay/symmetry,
pinned bsnes, bounded independent and three-mode endurance evidence also pass.
The historical v0.8.1 package and its 7,471-check audit pass; the v0.8.0 reports and
package remain historical evidence.

## Historical v0.9.0 packaged presentation correction

The live review of the historical v0.8.1 build identified four presentation
defects: clipped faces in selection portraits, a Damian likeness mismatch, a
weak arena-picker composition and stage pixels showing through HUD/result
lettering. The historical v0.9.0 pass addresses them without changing combat,
controls, audio, trace offsets, memory layout or the Fighter/Wave ABI.

- Selection cards and 64x80 profile portraits share a contained,
  head-anchored composition. `portrait_framing` records the source crop, head
  anchor, margin and scale for both 32x40 and 64x80 targets.
- Arena thumbnails contain complete stage art inside 60x52 boxes at
  `x18..77`, `y42..93` plus 56 pixels per row. The native three-row cursor stays
  at `x8..247`, `y40..95` plus 56 pixels per row, and labels use a separate
  column.
- FIGHT and RESULT map ASCII `32..127` to opaque glyphs `256..383`; round
  marker tiles `147/148` use the opaque panel background at palette index 1.
  Title, roster and arena menu lettering retains the original ASCII bank.
- Damian's four v4 source PNGs remain under `assets/art/characters/00-damian/`
  with provenance. The approved `neutral-height` conversion uses the 311-pixel
  reference neutral and pinned per-atlas factors; its native idle is 69 while
  the baseline, palette and physical scale remain locked. The corrected contract
  hash is `00f90a6765904c546284832d399c1a5ec581f08fed64a7f7bedc6d9df985e261`.
  The other eleven fighter banks and all twelve palettes remain unchanged.

The historical corrected source freeze is commit
`76f0a08a7562800df01507db83c6877745c3bdcf`, tree
`f37852da57a42d2d6819374db5d23278d12587a5`. Its ROM is
`bce460fbaa6f63e2f9c614f5c6833c08fd70558d56e7a27adfad292d4d200639` (header
checksum `6D41`). All six native reports pass on this SHA: 2,595 gameplay,
18,081 roster, 1,756 presentation, 997 focused-input, 8,131 stage and 622
Training checks (32,182 total). The 288-by-600 matchup/stage/policy/replay/
symmetry evidence, pinned bsnes smoke plus bounded 48-by-600 run, endurance of
216,356 live frames in each of three modes, fresh 214-asset export in 75.078
seconds and
`validate_release_evidence` also pass; `Test.cmd` exits 0. The historical [v0.9.0
Windows package](../dist/Abaqus-After-Hours-v0.9.0-Windows.zip) is available and its
archive audit passes 7,471 checks. The native all64 visual review accepted the corrected Damian set for
integration; human likeness/consent and public-release review remain open.

## v0.10.0 cartoon-stage and menu snapshot (historical; human gates pending)

The v0.10.0 candidate refreshed Las Condes, El Castillo and La Oficina with
original bold-navy cel-cartoon masters and matching complete arena thumbnails.
The versioned PNGs, adjacent exact-basename provenance JSON, `source-v2` raw
inputs, schema-2 selected manifest and historical `stages-v0.4.json` are
documented in [ART-DIRECTION.md](ART-DIRECTION.md). The RGB 1024x896, exact
4x-native, at-most-90-color source and palette contracts are checked by
`tools/stage_sources.py`; `tools/stage_cartoon.py`
adapts the existing feature-driven ambient work to the candidate palette/map.

Root also added bounded menu-only correctness polish: cleaned directional edges
drive menu navigation, both pads participate only in the P2 roster case, and
menu priority is Start confirm, B back, then A confirm, with an immediate return
after back to prevent two scene actions from one edge. Active combat, ABI,
timing, fighters, portraits and audio remain unchanged. The four 256-byte
ambient phases, eight cells and `TRACE[115..118]` remain unchanged. Ambient
change counts by phase are Las Condes `[0,20,20,20]`, El Castillo
`[0,18,18,18]` and La Oficina `[0,6,6,6]`; the office keeps one 3-pixel
monitor segment per monitor at `y114` while protecting the monitor digits. The
[stage pass note](STAGE-CARTOON-v2.md) and [cartoon preservation report](cartoon-preservation-report.json)
record the candidate details and 192 generated files retained from v0.9,
including fighter 64-frame banks, palettes, portraits, UI, audio, title and
select assets.

The source freeze is commit `8536bb6956212952c17302a62cc6c1de7e12a65d`, tree
`d524d3f960600dc5c9ff83578ac73675f9798735`; the ROM is SHA256
`a8f7b797a06bd242a18bf54400e53f043d5a84f274765ba3a34f9d8289ac5445` (header
`BE19`). Native PPU review accepted all three stage scenes and the arena
picker; focused presentation, stage and menu probes pass. Fresh committed
export validation passes 214 assets and symbols in 62.031 seconds. `Test.cmd`
exits 0 with all six reports matching this SHA: 2,595 gameplay, 18,081 roster,
1,756 presentation, 1,020 focused-input, 8,131 stage and 622 Training checks
(32,205 total). Endurance passes all three modes at 216,356 live frames each at
60.098811862348406 FPS, with wraps 4/4/3, peak SPC backlog 6 and empty
cadence, native-timing, ambient, PPU-overflow and SPC-FIFO failure arrays. The
technical audio report passes 1,262/1,262 capture-only checks with all four cues
and four scores unclipped; four music captures run 60.899688-63.079432 seconds
and their longest near-silence is 0.075499-0.078652 seconds, below the
0.5-second near-zero threshold. The 288-by-600 matchup/stage/policy/replay/
symmetry run with four replays across all three stages, pinned bsnes smoke at
600/600 plus the independent 28,800-frame run, and `validate_release_evidence`
also pass. The historical [v0.10.0 Windows package](../dist/Abaqus-After-Hours-v0.10.0-Windows.zip)
is available and its archive audit passes 7,472 checks. Human listening, stage,
gameplay, controller, likeness/consent and public-use review remain open, with
`public_release_certified=false`.

## Next combat pass

- Tune frame data, reach, damage, push boxes, jump arcs, throw ranges and meter
  gain through human playtesting. The v0.6 values are an integration baseline,
  not a balance conclusion.
- Continue human tuning of CPU spacing, anti-air behavior, defensive variety and
  difficulty progression after the correctness pass; the new distance bands and
  wave/wake reactions do not establish strategic AI or balance completion.
- Review the delivered v0.22.0 command history, combo display and drills; hitbox display, frame-step tools and more rematch options remain future work.
- Review the twelve delivered v0.22.0 supers before extending effect art, command variations or the four special families further.
- Audit aerial normal collision, throw contact and wake input timing against the
  dedicated air and recovery illustrations.

## Release-quality validation

- Keep running gameplay, roster, presentation, focused input, stage and
  Training suites after changes. The historical v0.8.1 reports all match ROM SHA
  `76b456d1ac75471a8b9710c61b0ce4c6ab9ca344b1b8a1f17e38f36e52904466` and record
  30,641 checks; matching compatibility, matchup, bounded independent-combat,
  endurance and fresh-source evidence also pass. The historical package and
  7,471-check archive audit pass. The historical v0.9.0 reports and extended evidence pass
  32,182 native checks on the corrected SHA; the historical [v0.9.0 Windows
  package](../dist/Abaqus-After-Hours-v0.9.0-Windows.zip) is available and its
  archive audit passes 7,471 checks. The frozen v0.10.0 candidate has all six
  reports matching its SHA (32,205 checks), plus focused PPU, presentation,
  stage and menu evidence recorded above. Endurance and technical audio capture
  pass as documented above; matchup, pinned bsnes/independent compatibility
  evidence and `validate_release_evidence` also pass. The historical [v0.10.0
  Windows package](../dist/Abaqus-After-Hours-v0.10.0-Windows.zip)
  is available and its archive audit passes 7,472 checks. Human listening,
  playtesting, controller, likeness/consent and public-release review remain
  open, with `public_release_certified=false`. The user
  selected an emulator-first release; original-console support stays unverified
  future work. Use [PLAYTEST.md](PLAYTEST.md) for the human review route and
  [review-feedback.json](review-feedback.json) for the actual platform,
  presentation and brief-listening responses.
- Playtest with two controllers and several keyboard layouts, including keyboard rollover constraints, SOCD edge cases, motion buffering and hitstop inputs.
- Profile worst-case combat frames, eight-bank animation uploads, resident
  audio effects, dynamic stage uploads, `STAT77`/OBJ overflow and vblank use
  across Snes9x, Mesen and bsnes.
  The optional [Mesen-S 0.4.0 supplement](MESEN-REVIEW.md) now passes 48 bounded
  combat cases, three-stage pixel/freeze checks, mode/guide smoke and a
  synchronized low-wave probe. It does not establish a modern Mesen desktop
  test, a full ordered-pair sweep or an independent hour-per-mode soak.
- Test an original SNES or Super Famicom through a flash cartridge. Real-console and flash-cartridge testing have not yet been performed.
- Record regression movies, verify every arcade ending and run longer stability sessions.
- Review branding and portrait usage with the team before a public release.

The [audio listening pack](AUDIO-REVIEW.md) now provides reproducible native
captures, mixed-cue comparisons and measured score repetition on the same ROM.
The user heard the short title/impact/special replay with no issue noticed;
full four-score, cue-clarity and busy-exchange judgments remain open. The pack
gives that review concrete material without changing the cartridge. The current
[playtest guide](PLAYTEST.md#review-already-received) records the live v0.8.1
presentation defects and distinguishes the candidate correction from open
gameplay, audio, equipment and public-use gates.

Commercial fighting-game polish requires repeated art, animation, audio, balance and QA passes. The project is organized so those passes can be reviewed and versioned without replacing the native engine.
