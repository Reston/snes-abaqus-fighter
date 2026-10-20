# Abaqus: After Hours

An original six-button fighting game for the **Super Nintendo**, inspired by the arcade structure of Street Fighter II and the people and places of Abaqus in Santiago.

**Current verified technical snapshot: v0.7.1.** The native source targets a
4 MiB NTSC FastROM LoROM cartridge across 128 banks, compiled from C and 65816
assembly. All five native reports point to ROM SHA256
`64dca043c8407659d05a22cc68b36d589d96bf4785fa630297d4e1526ed56022`, header
checksum `9496`: 2,595 gameplay, 18,085 roster, 215 presentation, 999
focused-input and 8,143 stage checks (30,037 total). The input suite includes
30 mirrored both-pad pause/cadence regressions and bounded
`clearFightHint`/`fillPausePanel` coverage. Full native 288-case x 600-frame
coverage plus four replays passes. The independent bsnes smoke and bounded
48 x 600 (28,800-frame) run pass as well.

Fresh export validation matches the exact ROM, manifest, 214 assets and symbols
in 63.25 seconds. Native endurance passes 216,356 live frames in each of three
modes at 60.098811862 FPS, one boot/unload with zero reboots, wraps 4/4/3,
all coverage true and all five failure arrays empty; video and PCM are healthy,
SPC peaks at six and drains, and stable FIGHT lag is zero. The full accelerated
run took 164.968 seconds, and `validate_release_evidence` passes. The offline
package passes 6,153 technical audit checks. Human likeness/balance, listening, controller,
real-console and branding gates remain open, so `public_release_certified` is
false.

The [v0.6.0 development notes](docs/RELEASE-v0.6.0.md) describe the packaged
64-frame roster, air attacks, throws and recovery. The
[v0.5.1 notes](docs/RELEASE-v0.5.1.md) retain the previous baseline's evidence.
The [v0.6.1 development notes](docs/RELEASE-v0.6.1.md) describe the CPU and
crouch-guard corrections. That historical offline package passes 202 technical audit
checks; identical packaging inputs produce identical ZIP bytes.
Public-release gates remain open.

The v0.7.0 stage/effect integration is verified in the v0.7.0 baseline ROM. It adds
restrained code-native ambient motion to the three stages and original strike,
guard, high-wave and ground-wave effect phases while preserving the native
actor and interface budgets. The v0.7 offline package passes 214 technical
audit checks and repeated packaging produces identical ZIP bytes. See the
[v0.7.0 development notes](docs/RELEASE-v0.7.0.md).

The v0.7.1 source freeze is commit
`6d756749dbc3fa176e26217f2f59525c9af360d8`, tree
`fa15fea48b5cc2a09608da199810db885872e434`. The canonical ROM above includes
the long-range projectile/low-wave opening, the active-own-wave guard and the
quiet-first/combined-second impact transfer. Training reset, KO-card and intro
sequencing remain bounded at three reset frames, quiet-first/panel-second and
intro ticks 109/108/107 respectively. The test driver now uses the shortest
four-by-three grid with at most three pulses per fighter; all 720 timeout,
loaded-ID, stage and cadence checks remain unchanged, so this only reduces test
overhead. Technical validation and packaging are complete; human likeness,
balance, listening, controller, real-console and branding gates remain open.

![Abaqus After Hours](docs/screenshots/fight.png)

## Play

On Windows, double-click **[Play.cmd](Play.cmd)**. The launcher downloads the official Snes9x 1.63 release into `.tools/` on its first run, verifies its SHA256, and opens the game. No administrator account or global installation is needed. The tools are already present in this checkout.

For offline Windows play, extract the verified development package
[Abaqus-After-Hours-v0.7.1-Windows.zip](dist/Abaqus-After-Hours-v0.7.1-Windows.zip).
Run its `Play.cmd`. It includes the current ROM, Snes9x, control defaults,
native and independent-engine reports, endurance and source-rebuild evidence,
guides and license notices. See the [v0.7.1 release notes](docs/RELEASE-v0.7.1.md).

The archive is 6,452,958 bytes. Two consecutive packaging runs produced identical
bytes, SHA256 `6ab177a1ef5a101a6f60086fd651c9b7f3f92e3276d519385c3227cb10061a38`.
The [technical audit](docs/release-audit.json) passes 6,153 checks and keeps
public-release certification false.

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
- v0.7.0 integration work for four-phase stage ambient motion and original
  combat-effect cells. The source stage masters and palettes remain unchanged;
  the verified v0.7.0 baseline ROM and native/compatibility reports verify this milestone.
- v0.7.1 source-freeze CPU opening, active-wave guard and staged impact/reset
  feedback are included in the verified technical snapshot and offline package
  above. Human/listening/controller/console/branding gates remain open.

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

The verified v0.7.1 `Test.cmd` batch runs five native suites silently and headlessly in the official Snes9x libretro core: gameplay, roster, presentation, focused input and stage dynamics. They send controller input and read WRAM/VRAM, rendered frames and captured audio without playing it. Each report records the exact tested ROM hash. Its canonical batch passes against the v0.7.1 source-freeze image with 8,143 stage checks; the separate pinned compatibility smoke also matches that SHA and runs outside the five-suite `Test.cmd` batch:

- `docs/test-report.json`
- `docs/character-test-report.json`
- `docs/presentation-test-report.json`
- `docs/input-test-report.json`
- `docs/compatibility-test-report.json`
- `docs/stage-test-report.json`

The [manifest](dist/manifest.json) includes the ROM SHA256 and header checksum.
The current v0.7.1 snapshot has all five native reports passing against
`64dca043c8407659d05a22cc68b36d589d96bf4785fa630297d4e1526ed56022`: 2,595
gameplay, 18,085 roster, 215 presentation, 999 focused-input and 8,143 stage
checks, or 30,037 total. Thirty mirrored both-pad pause/cadence regressions and
bounded `clearFightHint`/`fillPausePanel` coverage are included. The native
batch covers both boot phases, two-controller air/trades/combo cadence,
resident-audio probes, CPU coverage across three difficulties and four special
families for 600 live ticks each (7,200 total), and the full 288-case x 600-frame
run plus four replays. The input suite also covers near-special, far-negative,
29-46 approach, low-guard and wake cases with strict no-KO lookahead. Native
screenshots and animation review captures are retained under
`docs/screenshots/`.

The separate pinned bsnes2014 Accuracy report passes against the same v0.7.1
SHA with title/select/arena/fight captures, controller movement and jump, all
three stages across four actual PPU ambient phases with freeze checks,
synchronized low-wave combat, 600 one-tick cadence frames and captured audio.
The synchronized low-wave probe observed 37 two-wave frames in 600, all 600
cadence deltas were one, and `STAT77` stayed at `0x01` with overflow bits
`0xC0` clear.
Its static stage plates match all 15,360-15,616 sampled pixels within eight
channel levels (maximum delta 7). It is an independent smoke only; it does not
replace full combat, soak or human verification. Run it with PowerShell
`tools/setup-compat.ps1` followed by `python tools/test_compatibility.py`.

The earlier four-family 600-frame probe remains historical v0.7.0 evidence. The
current input suite covers 288 native cases at 600 frames each plus four
replays, and adds 30 mirrored both-pad pause/cadence regressions. The
independent bsnes smoke and bounded 48 x 600 (28,800-frame) run pass; video
and PCM remain healthy, with bounded SPC effects. The compatibility host
decodes the pinned core's actual 512x224, 2048-byte-pitch BGRX callbacks using
stride; its prior pixel-format metadata mismatch no longer masks the stage
color assertions.

The v0.7.1 QA paths are bounded and silent: `python tools/test_matchups.py`
runs the ordered 12-by-12 local-versus matrix across all three stages;
`python tools/test_endurance.py --benchmark` precedes the uninterrupted
per-mode hour gate run with `python tools/test_endurance.py`; and
`python tools/test_fresh_build.py` rebuilds a committed source export with
freshly extracted pinned tools. Fresh export validation passes in 63.25 seconds
with exact ROM/manifest and 214 asset/symbol matches. The full native endurance
passes 216,356 live frames in each of three modes at 60.098811862 FPS, with one
boot/unload, zero reboots, wraps 4/4/3, all coverage true, empty failure arrays,
stable FIGHT lag 0, healthy video/PCM and SPC maximum six drained. The
accelerated run took 164.968 seconds; `validate_release_evidence` passes.

The v0.6 native fast path caches actor-bank and per-action timing selection,
uses compile-checked `Fighter` stride 64 and `Wave` stride 16 layouts, and
caches unchanged OAM/shadow work by integer position and facing. Health and
energy bars retain their native glyph formulas. Impact HUD and empty-banner
clears continue through hitstop ticks, while interface DMA yields when an actor
frame is uploaded; the engine and VRAM contract stay unchanged. As a result,
interface impact feedback may settle one to three video frames after the combat
event while hitstop keeps the fight state frozen.

The current source freeze keeps one resident ready-only FIFO record in `main`
for native work; there is no polling or streaming path, and SDK loading is
unchanged. The streamed API and nonzero `AllocateRegion` remain future stream
service prerequisites. `applyHitReaction` uses a 256-entry ROM lookup of
`12 + floor(final_u8_damage/3)` for every wrapped `u8` damage value and resets
reaction fields; `fillBannerPanel` writes exact 96-word rows 10-12. Native geometry/cache refreshes `refreshFighterOam`, OAM
uses packed XY words, and `queueFighter` preserves its four-byte pointer while
uploading 3,840 bytes. The source-freeze OAM audit passes 746 controller frames,
comparing the full 544 OAM bytes and geometry for each frame.

Real KO contact resolution keeps damage, winner selection, timers and layout
unchanged. `roundBannerPending` keeps the first frozen `roundEnd` tick quiet,
then transfers the panel, name and HUD on the second tick, avoiding a
contact-time stall.

Fresh source export validation reproduced the v0.7.1 source-freeze ROM SHA with
the exact manifest and 214 asset/symbol matches in 63.25 seconds.
The archive passes 6,153 technical audit checks; its checksum is recorded in
`dist/release-sha256.txt`.

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
| `src/trace.asm` | Direct read-only combat/ambient telemetry stores at `0..113` and `115..118`; `main` samples PPU `STAT77` at `114` |
| `src/animation_banks.h` | Eight-bank fighter frame lookup for the 64-frame contract |
| `assets/art/` | Original character masters, animation atlases, independent stage PNGs and menu art |
| `assets/generated/` | Reproducible SNES tiles, eight fighter banks, palettes, music and resident effect data |
| `tools/` | Bootstrap, encoding, build, stage/effect generation, emulator tests and packaging |
| `tools/test_matchups.py` | Bounded ordered local-versus matrix for candidate balance evidence |
| `tools/test_endurance.py` / `tools/longrun_host.py` | Silent uninterrupted hour/mode endurance gate and callback host |
| `tools/test_fresh_build.py` | Fresh pinned-tool extraction and committed-source rebuild gate |
| `dist/` | Playable ROM and release manifest |
| `docs/` | Controls, technical notes, animation contract, art prompts, credits, roadmap and QA evidence |

Git tracks the source, master art, generated cartridge assets and ROM. Downloaded toolchains and release ZIPs stay outside history. Prior releases are tagged `v0.1.0`, `v0.2.0`, `v0.3.0`, `v0.3.1`, `v0.4.0`, `v0.4.1`, `v0.5.0` and `v0.5.1`; `v0.6.0` records the animation baseline, `v0.6.1` the CPU update, and `v0.7.0` the verified stage/effect update and development package. v0.7.1 records the verified technical CPU/impact-feedback snapshot and development package; public gates remain open. No remote repository is configured by this project.

Team references: [Abaqus Solutions](https://abaqus.io/es/abaqus-solutions/team) and [Abaqus Wealth Care](https://abaqus.io/es/wealth-care/about-us). See [credits and asset provenance](docs/CREDITS.md), [art prompts](docs/ART-DIRECTION.md), and [technical notes](docs/DEVELOPMENT.md).
