# Office bonus rounds (isolated topic 2)

The Arcade ladder offers a short optional printer-jam round after the third
earned opponent win, and an inbox-overload round after the seventh. Each
starts immediately on the earned RESULT-to-next handoff. Their 12/15-second
clocks stop during pause. A 90-tick result automatically loads the next
opponent; success, timeout, and skip all advance exactly once. Local and
Training retain their ordinary flow. The eleven-opponent ladder and ending
remain the original ones.

Move left/right, jump with Up, and use Y/X for light/strong punches and B/A
for light/strong kicks. Fresh attacks score one/two clearance points when
within 62 pixels of the target and no more than 20 pixels above the floor.
There are 12 printer points / 18 inbox points. The target rolls across the
office twice as points accumulate. Strong attacks trade longer recovery
for two points. Held face buttons do not repeat attacks. Simultaneous
horizontal directions cancel. No HP, ladder reward, or combat stat changes.

Start from either controller pauses/resumes both the challenge and its result;
Start owns simultaneous skip/attack. Fresh Select from either pad skips a
live or paused challenge. Bonus pause uses only Start/Select; the normal
combat pause menu remains separate. P2 face buttons do not control the solo
hero. B is always a light kick during the live bonus. Entry and resume wait
for face-button release before accepting new attack edges.

## Integration hooks

- `src/bonus29.h` is included immediately before `menuTick`, after all existing
  game/UI/combat helpers. It contains the entire bonus engine.
- Call `bonus29TryBegin()` **before** a successful Arcade RESULT increments
  `arcade` or `arena`. If it returns 1, return from the result handler: BONUS
  owns handoff. The automatic-start topic must retain this call in its timed
  RESULT-to-next path. The hook expects zero-based won indices 2 and 6.
- Dispatch scene 5 to `bonus29TickFrame()` in the main active-display phase.
  The existing actor DMA slot consumes its queued approved hero pose. Keep
  BONUS's BG1 scroll at 16 to show the approved office viewport; no combat
  camera update or old ambient DMA runs there.
- `stageDepthPublish`'s existing non-FIGHT branch calls
  `bonus29PublishScroll()` to restore the office's 16-pixel gutter offset
  after the ordinary main scroll write. Live FIGHT keeps its original
  `bgSetScroll(0,scroll,511)` call; no per-frame bonus ternary runs there.
- `showSelect()` clears only `v29BonusState[0]`, starting a fresh milestone
  history. Continue does not clear it. Other feature state is untouched.
- Bonus exit increments `arcade` and rotates `arena` once, then calls the
  existing `beginMatch()`. That restores both fighters, palettes, actor bank
  pointers, combat/reset state and the original fight intro. Automatic-start
  may shorten that intro through its normal begin-match hook.
- Parent-owned Arcade fixtures that expect RESULT directly to FIGHT after
  wins 3/7 must play or Select-skip scene5, wait its automatic result, and then
  observe FIGHT. Preserve native input/tick assertions and never force state.

The child stays based on the assigned isolated contract commit `29fee83`.
Parent integration has advanced to `2b18b8e`; compose these hooks with the
automatic-start RESULT path, `audio29_native.h`, `defense29.h`, and the arena
animation hooks. Keep their direct-actor input fixes and thirteen semantic
audio slots. BONUS uses only existing cue 1 (contact), cue 3 (success), and
cue 0 (menu), whose meanings remain stable. Its target occupies only actor1;
it never writes the arena pool at BG1 words `$3400..36FF`. The shared
full-meter glyph correction below should survive the parent's composition.

## Assets and native ownership

Original built-in imagegen source is
`assets/art/bonus-v029/office-targets-v1.png`; its adjacent JSON retains the
exact prompt, no-reference record and output SHA256. Old art is retained.
`tools/bonus29_assets.py` separates the two complete authored silhouettes by
their thresholded alpha-column spans (66..975 / 1112..1815),
fits it proportionally inside 90x76 at native baseline 78, quantizes to 15
colors plus transparent zero, and encodes a 96x80 / 3840-byte actor stream.

The two-line `tools/make_assets.py` hook installs into the private `OUT`
**after** stage-depth install and **before** source-input recheck and
transactional publish. Never publish these files independently into the live
asset directory. Asset-cache dependency discovery follows the import.

Expected new output allowlist (7): `bonus29-assets.json`, and
`bonus29_printer.bin`, `bonus29_printer_pal.bin`, `bonus29_printer.png`,
`bonus29_inbox.bin`, `bonus29_inbox_pal.bin`, `bonus29_inbox.png`.
Only the existing `data.asm` and `assets.h` append declarations/size macros;
the other 224 original generated outputs remain exact. Four `superfree`
LoROM sections hold two 3840-byte streams and two 32-byte palettes, 7744
bytes total. No output exceeds a 32 KiB bank. Version stays parent-owned.

All mutable bonus state lives in `v29BonusState[64]`: bytes 0..15 are earned
mask, variant, result, pause, seconds, subtick, progress, target x, action,
tick, connection, pose, queued pose, walk phase, flash and facing; signed
16-bit fixed-point x/y/vy occupy 16..21; bytes 22..28 are result ticks, goal,
rolling stage, hits, button coverage, attack release gate and destination x.
Bytes 29..63 remain unused. Existing Fighter64/Wave16/TRACE and ASM are exact.
The linked reservation is `$7F:05A8..05E7`. All 1,321 prior variable/data
addresses stay exact; only the two end markers grow by the parent's combined
176-byte reservation. No feature adds a separate mutable definition.

BONUS borrows actor0 for the selected hero and actor1 for the target, at
VRAM words `$6000..69FF` / `$6A00..73FF`, OBJ palettes 0/1. Both streams load
under forced blank on entry. During the live bonus only one approved actor0
pose can be queued per vblank (3840 bytes). Actor1 never receives live DMA.
HUD 320-byte and banner 320-byte updates use the existing dirty queues and
yield to the actor slot. No new full-map UI transfer occurs during play.
The existing effects page/palette supplies the two ordinary shadows. OAM
contains 30 pieces per actor plus 2 shadows each (64 entries total, padded
actor blocks retained). Actor rows have at most 12 intersecting 16x16
pieces = 24 fetch tiles; the two shadow pairs at y200 add at most 4 pieces,
for 16 pieces / 32 tiles, below SNES's 32-object/34-tile per-line limits.

Final source QA corrected an equal-half crop assumption: the imagegen sheet
places its objects unevenly. The encoder now requires two isolated column
spans and retains each whole silhouette, eliminating both the printer trim
and the fragment previously included with the inbox. Master art is unchanged.
The final art update is checked against the prior cartridge for byte identity
outside the four target/palette payloads and the header checksum words.
`docs/bonus29-art-equivalence.json` binds that comparison. The earlier
`docs/bonus29-prior-full-roster.json` passed 1,371,431 checks on cartridge
`33d0e7bfe67ab349d3b5d554fd76cd71ceebb81070b6e08e5bebe4aea483b0a2`:
all twelve heroes earned both bonus rounds, and hero0 completed Champion.
The final art cartridge has identical compiled game assembly and every linked
address. That earlier cartridge's checks are excluded from final-ROM totals.

Office BG1 tiles/map/palettes and detailed floor bytes are reused intact.
The 64x32 map spans words `$3800..3FFF`; no animation writes to `$3C00`.
BG3 and HDMA remain disabled. No new resident audio or SPC allocation is
needed; existing contact/confirmation cues play through the usual queue.

## Focused verification

`tools/test_bonus29.py` drives actual SNES controllers and reads telemetry,
VRAM, PPU frames and captured PCM. It never writes memory or uses save states.
Reports bind the exact ROM, source/harness inventory, encoder/art/dependencies,
core hashes, commands and host affinity/priority. They publish atomically.

Two harness findings were resolved before the final proof. Snes9x's ordinary
frontend filters opposing directions, so this harness enables its existing
`snes9x_up_down_allowed=enabled` option, as the Training suite does, to deliver
both held bits to native cancellation. An Accuracy route failed an immediate
one-callback B assertion, and another remained at RESULT after a one-callback
A pulse. A separate earned-route
probe confirmed that native B selects action4 and a held B stops after its
one attack. The final harness uses the existing suites' three-callback held
button pulse for deliberate face/menu commands and immediate edge assertions. Every individual callback still
has strict cadence, SDK, OBJ, PCM and SPC checks; no emulated state is written.
The failed observations, observer log and canceled earlier partial roster run
remain under ignored `build/bonus29-*`; they are not pooled with final results.
The original close-only traversal also lost all eight attempts in Mamariaga's
first matchup, before reaching a bonus. The final controller driver follows
`test_expansion_09_arcade_story.py`: close play first, then ordinary jump-in
retries (bounded to 16 real attempts). Losses/continues remain earned and
visible in the report; no WRAM, difficulty, fighter stats or cadence changes
are used to manufacture progression. The earlier passed Accuracy ending
proof for the earlier `72751f4b...` cartridge is retained under ignored
`build/bonus29-72751f4/accuracy-ending.json` and is excluded from final totals.
A subsequent Mamariaga route exposed one live FIGHT SDK lag event. The first
candidate tested BONUS in a ternary at the ordinary per-frame scroll call;
the correction restores that original call and moves BONUS scroll work to
the existing non-FIGHT branch. The failed native report remains
`build/bonus29-mamariaga.json`; final proof reruns the corrected cartridge
with the same strict health assertions.
The approved baseline ROM also fails a strict live-frame check on the same
dual-meter transition: both energies 95 to 96. The native phase observers
are retained in `build/bonus29-phase-baseline.log` and
`build/bonus29-phase-candidate.log`; neither case is an intro or round load.
The shared `HUD_ACTOR` full-meter hint now uses the existing native
`drawGuideWord` for the same nine opaque glyph cells (byte offsets 258/300),
then retains the original gold-attribute loop. This one-line performance
correction preserves UI contents, meter/combat values, timing rules, all RAM
and hardware/trace ASM. The focused harness checks both resulting hints'
exact VRAM tile/attribute words and keeps the zero-lag assertions. The parent
must retain this shared HUD correction when resolving hooks.

Final focused evidence is `docs/bonus29-report.json`: **1,535,070 checks pass**
across six independent native sessions, 79 earned wins and 23 bonus rounds.
All runs bind cartridge
`7b44bcfd833a2b43ca80830dad264926f5fdf7b9934dd61e8b8b9625e0b32bb2`
and source/harness freeze `8024db8c456ee3cffed6d9423fc47655b5c8f083`.
Snes9x exercises every hero's first bonus, plus hero0's full eleven-win
Champion route, both bonuses, deliberate losses and continues. Accuracy
exercises Mamariaga's earned first/second bonuses and difficult matchup
retries. Separate timeout and paused-skip routes earn both milestones on
both cores. Local/Training exclusion, held buttons, Start priority, attack
roles, native target pixels and opponent-page restoration are asserted.

The final runs observe 16,045 BONUS and 363,200 live FIGHT callbacks with
zero SDK lag or OBJ overflow and no health failures; maximum SPC backlog
is 3 and at most one actor page changes per BONUS callback. The bonus engine
links as 6,074 bytes of code plus 12 timing-table bytes; every function and
asset section fits one LoROM bank, and the largest compiled local frame is
16 bytes. The build exits 0 and produces the 4,194,304-byte native cartridge.

| Final-ROM report | Passed checks | Seconds |
| --- | ---: | ---: |
| `bonus29-snes9x.json` | 707,746 | 282.094 |
| `bonus29-accuracy.json` | 333,300 | 530.469 |
| `bonus29-timeout-snes9x.json` | 133,954 | 53.360 |
| `bonus29-skip-snes9x.json` | 127,132 | 51.391 |
| `bonus29-timeout-accuracy.json` | 110,290 | 122.703 |
| `bonus29-skip-accuracy.json` | 122,648 | 136.453 |

Source-inventory SHA256 is
`da940dd1ae9eb2924cd04bbe403bb6b8635ae9f0d86214e66241392521495ab9`;
harness SHA256 is
`49ec68ed0a90ef914022ae58ae0384873d18139bca7bdd65f204193e7655398e`;
encoder SHA256 is
`88191286772b144c8ac534f7c385a3c098fe9a87f47df588f6256dde67d20eea`.
The aggregate records full runtime/art/dependency/core hashes and exact
per-run command arrays; it verifies every committed final capture's hash.
Final screenshots are in `docs/screenshots/bonus-v029/final-art`, `timeout`
and `skip`; older captures remain ignored historical diagnostics.

The parent owns the combined six suites, freeze/reproduction, generated
assets and cartridge publication, and merge to main. This child does not
claim combined verification, hardware playtesting or human acceptance.

The tested cartridge and complete generated candidate are retained under
ignored `build/bonus29-tested/`. Tracked `dist` and generated declarations are
restored before the evidence commit, as required by the child contract.

Every native command uses the same wrapper. Set the wrapper's affinity first;
its below-normal children inherit logical CPU4/5:

```powershell
$bonusHost=[System.Diagnostics.Process]::GetCurrentProcess()
$bonusHost.ProcessorAffinity=[intptr]48
$bonusHost.PriorityClass='BelowNormal'
$bonusPython=Join-Path (Get-Location) '.tools/python/python.exe'
& $bonusPython tools/run_background.py --log build/bonus29-build-art-final.log -- $bonusPython tools/build.py
& $bonusPython tools/run_background.py --log build/bonus29-snes9x.log -- $bonusPython tools/test_bonus29.py --core snes9x --through 3 --report docs/bonus29-snes9x.json --captures docs/screenshots/bonus-v029/final-art
& $bonusPython tools/run_background.py --log build/bonus29-accuracy.log -- $bonusPython tools/test_bonus29.py --core accuracy --fighters 8 --champion-hero -1 --report docs/bonus29-accuracy.json --captures docs/screenshots/bonus-v029/final-art
& $bonusPython tools/run_background.py --log build/bonus29-timeout-snes9x.log -- $bonusPython tools/test_bonus29.py --core snes9x --fighters 0 --champion-hero -1 --outcome timeout --report docs/bonus29-timeout-snes9x.json --captures docs/screenshots/bonus-v029/timeout
& $bonusPython tools/run_background.py --log build/bonus29-skip-snes9x.log -- $bonusPython tools/test_bonus29.py --core snes9x --fighters 1 --champion-hero -1 --outcome skip --report docs/bonus29-skip-snes9x.json --captures docs/screenshots/bonus-v029/skip
& $bonusPython tools/run_background.py --log build/bonus29-timeout-accuracy.log -- $bonusPython tools/test_bonus29.py --core accuracy --fighters 0 --champion-hero -1 --outcome timeout --report docs/bonus29-timeout-accuracy.json --captures docs/screenshots/bonus-v029/timeout
& $bonusPython tools/run_background.py --log build/bonus29-skip-accuracy.log -- $bonusPython tools/test_bonus29.py --core accuracy --fighters 1 --champion-hero -1 --outcome skip --report docs/bonus29-skip-accuracy.json --captures docs/screenshots/bonus-v029/skip
```
