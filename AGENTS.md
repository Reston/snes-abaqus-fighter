# Project instructions

This is a native SNES fighting game. The authoritative deliverable is
`dist/abaqus-after-hours.sfc`, built with PVSnesLib 4.6.0 from C and 65816
assembly. The current integration targets a 4 MiB NTSC FastROM LoROM image
across 128 banks.
Preserve the native emulator requirement when extending the project.

- The current verified technical snapshot is v0.8.0. Its source freeze is
  commit `48f3ccb539492247b83f4360a50bdc020bad9dd6`, tree
  `e571aca40019b868bf224bb619390f5ea651434e`; the ROM is SHA256
  `53ef44225c83bd52ee0eea3910ba74ade5ba949af7aa7440c74d959812c13090`, header
  checksum `6A21`. `Test.cmd` exits 0 with all six reports on that SHA:
  2,595 gameplay, 18,081 roster, 215 presentation, 997 focused-input, 8,131
  stage and 622 Training checks (30,641 total). The matching compatibility,
  matchup, bounded independent-combat, endurance and fresh-source evidence also
  passes. The offline package passes 7,471 technical audit checks; human
  likeness/balance, listening, controller, real-console and branding gates stay
  open.

- v0.8.0 adds a pause overlay with Normal, Controls and Specials pages. Select
  cycles the pages, and Left/Right toggles the guide pages. Start resumes
  first; otherwise B returns to the roster, A resumes and Select cycles pages.
  The Controls page keeps the original glyph
  set and the Specials page names both live fighters, their specials and family
  types, including the true 12-tick quarter-circle motion and 32-energy cost.
  Training pause Up/Down cycles Stand, Guard High, Guard Low and Jump; guard
  holds relative back without retreat, and the Jump dummy automatically jumps
  again after landing. Live Select resets the round while preserving the dummy choice and
  returning a new match to Stand. Pause camera shake is frozen and a pause
  after contact settles the actual HP bar on the first quiet paused tick.

- The guide uses opaque original glyphs 256-383 in VRAM `$5000-$57FF`; the
  selected portrait remains at `$4A00`. Its rows 5-27 publish as a 1,472-byte
  staged panel over three paused ticks and yield to actor DMA. `drawGuideWord`
  and the native full-clear UI path are part of the hardware contract. The
  Fighter/Wave layout and fighter assets are unchanged. Stable trace offsets
  `0..118` remain unchanged; v0.8 appends `TRACE[119]` pause page,
  `[120]` guide build stage, `[121]` Training dummy mode and `[122]` guide dirty.

- Read `docs/DEVELOPMENT.md` before changing memory layout or hardware transfers.
- Build with `Build.cmd`; regenerate assets with `Build.cmd --assets`.
- Run `Test.cmd` after gameplay, graphics-transfer, audio, menu, presentation or
  progression changes. It runs the actual ROM in Snes9x and records the tested
  ROM hash for the gameplay, roster, presentation, focused-input, stage and
  Training suites.
- Run automated verification silently and headlessly. The libretro test host
  may capture audio for assertions, but must not play it through the speakers.
  The user has also authorized muted live emulator review now that they are
  no longer playing another fullscreen game. Keep GUI review muted and separate
  from the reproducible headless suites. Default to preserving foreground focus
  during future automated work.
- Do not report emulator pass counts or release readiness until all six current
  native ROM reports point to the exact same ROM SHA256:
  `docs/test-report.json`, `docs/character-test-report.json`,
  `docs/presentation-test-report.json`, `docs/input-test-report.json`,
  `docs/stage-test-report.json` and `docs/training-test-report.json`. The
  package gate also requires `docs/compatibility-test-report.json` to pass
  against that same SHA. The compatibility report is a separate pinned
  bsnes2014 Accuracy smoke, not part of the six-suite `Test.cmd` batch. The
  current v0.8.0 reports all match the verified SHA and record 30,641 passed
  checks. The compatibility report is also matched; package and audit pass 7,471 technical checks.
- The v0.6 fast path caches actor-bank and per-action timing selection, uses the
  compile-checked `Fighter` stride 64 and `Wave` stride 16 layouts, and caches
  unchanged OAM/shadow work by integer position and facing. Native health and
  energy bars keep their glyph formulas; impact HUD and empty-banner clears are
  serviced through hitstop, while interface DMA yields to an actor upload.
  Interface feedback may therefore lag one to three video frames while hitstop
  keeps combat state frozen.
- `src/trace.asm` writes read-only telemetry directly at stable `TRACE[0..113]`
  offsets and ambient stores `TRACE[115..118]`; `main` samples post-wait PPU
  `STAT77` into `TRACE[114]` before DMA. Any native `Fighter` or `Wave` struct
  layout change requires an assembly-offset audit and a matching trace-contract
  update; offsets `0..113` remain the Fighter/Wave ABI.
- Keep the one-actor-per-vblank transfer budget, 32 KiB LoROM bank boundaries,
  OBJ scanline limits and reserved palette banks in mind.
- The v0.6 renderer uses thirty 16x16 sprites per actor at OAM byte 0 and 128,
  with 3,840-byte pose streams in actor pages `$6000-$69FF` and `$6A00-$73FF`.
  Keep the 96x80 canvas, 94x77 safe area, native feet baseline at height 78
  and one uniform physical scale per fighter across all 64 frames. The native
  review strip is 6,144x80 RGBA. Eight contiguous 30,720-byte banks
  (`fighterXX` and `fighterXXb` through `fighterXXh`) hold each fighter's
  native data; each fighter uses one shared fifteen-color OBJ palette.
- The v0.8 pause guide uses original opaque glyphs 256-383 in VRAM
  `$5000-$57FF`, before the BG2 map at `$5800`; the selected portrait remains
  at `$4A00-$4EFF`. Keep its 1,472-byte rows 5-27 panel within the three-tick
  paused DMA path and yield to actor uploads.
- v0.7 stage ambient work uses BG1 tile indices 960-967 at VRAM `$3C00-$3C7F`:
  four 256-byte phases provide eight dynamic 4bpp tiles while the original
  stage graphics, map and palette masters remain unchanged. Ambient uploads
  yield to actor and interface DMA and advance only during live combat; intro,
  pause, hitstop and round-end states freeze them. The stage effects use no
  additional OBJ budget.
- Each fighter has legacy frames 0-15, motion/transition frames 16-31, action
  frames 32-47 and the v0.6 airborne/throw/knockdown range 48-63. Preserve the
  original 48 frame hashes and palette bytes while adding the new range.
- Keep twelve individual illustrated fighter masters and their identities,
  palettes and costumes separate. The v0.6 animation pass adds twelve new
  built-in-imagegen `animation-airborne.png` atlases while leaving all twelve
  identity masters unchanged. Reston's selected master remains the v3 short-hair
  correction. Keep every airborne atlas's full prompt and provenance in its
  adjacent `animation-airborne.json`; retain the earlier motion/action metadata.
- The v0.5 presentation uses three independent stage PNGs described by
  `assets/art/stages/stages.json`, plus original home/select/arena menu art
  under `assets/art/menu/`. Keep `assets/art/menu/prompts.json` with the source
  prompt set and keep menu lettering on the original project glyphs. The menu
  direction is minimal royal navy, white and gold with one cursor and one large
  selected portrait. v0.8 adds pause Controls/Specials guide pages without
  changing the menu grid or portrait contract.
- Keep original art masters and prompts in the repository. Do not import
  commercial game ROMs, Capcom sprites, or commercial game audio.
- Preserve future scope for art review, balance tuning, stage parallax, human
  playtesting and real-console/flash-cartridge verification; do not imply those
  roadmap items are complete. The v0.8.0 verified snapshot keeps fighter assets
  unchanged; Reston's remaining hair/likeness review is still future work.
  Evidence is tied to the exact ROM above; public-release gates still govern
  public readiness.
- Do not commit `.tools/`, emulator saves, build intermediates or release ZIPs.
- Rebuild the offline package with `tools/package.py` only after all six native
  suites and the matching compatibility smoke pass against the exact current
  ROM. It also requires the current full matchup matrix, bounded independent
  combat, three native live-hour sessions and isolated source rebuild through
  `tools/release_evidence.py`. Run `tools/audit_release.py` on the result.
  The v0.7.1 offline archive and its 6,153-check audit are historical. The
  v0.8.0 package passes 7,471 technical audit checks. Keep third-party
  license notices intact. Two consecutive runs produce identical ZIP bytes:
  6,546,556 bytes, SHA256
  `1b7b685264a867f54ab4b05203cf168b0ddf6353f26ce4da419b9823e21ee359`.
