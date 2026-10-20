# Project instructions

This is a native SNES fighting game. The authoritative deliverable is
`dist/abaqus-after-hours.sfc`, built with PVSnesLib 4.6.0 from C and 65816
assembly. The current integration targets a 4 MiB NTSC FastROM LoROM image
across 128 banks.
Preserve the native emulator requirement when extending the project.

- The current verified source/evidence milestone is v0.7.0 stage/effect
  integration. All five native reports and the separate pinned bsnes2014
  Accuracy smoke report pass against ROM SHA256
  `e44a739488bd549cfcffbe35bbb32bb5e71d9d2dce12bea6562ebd3dd0c15b84`, a
  4 MiB image with header checksum `0953`: 2,595 gameplay, 18,085 roster,
  215 presentation, 854 focused-input and 4,537 stage checks (26,286 total in
  the current report snapshot). The canonical `Test.cmd` run passed with
  4,528 stage checks; a focused stage extension added nine patch-only PPU
  assertions and reran against the unchanged ROM/engine for the current 4,537
  stage report. The CPU distance/reaction corrections, crouch-guard pose
  selection and stage/effect checks are verified. Human balance, public-release,
  independent full-combat/soak and real-console gates remain open. The v0.7.0
  offline archive passes 214 technical audit checks and reproduces byte for
  byte from identical inputs. Follow
  `docs/COMBAT-ANIMATION-CONTRACT.md` for the native contract.

- Read `docs/DEVELOPMENT.md` before changing memory layout or hardware transfers.
- Build with `Build.cmd`; regenerate assets with `Build.cmd --assets`.
- Run `Test.cmd` after gameplay, graphics-transfer, audio, menu, presentation or
  progression changes. It runs the actual ROM in Snes9x and records the tested
  ROM hash for the gameplay, roster, presentation, focused-input and stage
  suites.
- Run automated verification silently and headlessly. The libretro test host
  may capture audio for assertions, but must not play it through the speakers.
  The user has also authorized muted live emulator review now that they are
  no longer playing another fullscreen game. Keep GUI review muted and separate
  from the reproducible headless suites. Default to preserving foreground focus
  during future automated work.
- Do not report emulator pass counts or release readiness until all five current
  native ROM reports point to the exact same ROM SHA256:
  `docs/test-report.json`, `docs/character-test-report.json`,
  `docs/presentation-test-report.json`, `docs/input-test-report.json` and
  `docs/stage-test-report.json`. The package gate also requires
  `docs/compatibility-test-report.json` to pass against that same SHA. It is a
  separate pinned bsnes2014 Accuracy smoke, not part of the five-suite
  `Test.cmd` batch. The current v0.7 native reports and compatibility smoke
  point to the exact SHA above. The focused stage extension is a supplemental
  nine-check rerun on the same unchanged ROM; it does not change the canonical
  `Test.cmd` stage count.
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
  selected portrait.
- Keep original art masters and prompts in the repository. Do not import
  commercial game ROMs, Capcom sprites, or commercial game audio.
- Preserve future scope for art review, balance tuning, stage parallax, human
  playtesting and real-console/flash-cartridge verification; do not imply those
  roadmap items are complete. The latest report snapshot is evidence for the
  exact ROM above; public-release gates still govern public readiness.
- Do not commit `.tools/`, emulator saves, build intermediates or release ZIPs.
- Rebuild the offline package with `tools/package.py` only after all five native
  suites and the matching compatibility smoke pass against the exact current
  ROM. The v0.7 offline archive passes 214 technical checks and repeated
  packaging produces identical ZIP bytes. Keep third-party license notices
  intact.
