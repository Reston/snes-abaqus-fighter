# Project instructions

This is a native SNES fighting game. The authoritative deliverable is
`dist/abaqus-after-hours.sfc`, built with PVSnesLib 4.6.0 from C and 65816
assembly. The v0.5 target is a 4 MiB NTSC FastROM LoROM image across 128 banks.
Preserve the native emulator requirement when extending the project.

- Read `docs/DEVELOPMENT.md` before changing memory layout or hardware transfers.
- Build with `Build.cmd`; regenerate assets with `Build.cmd --assets`.
- Run `Test.cmd` after gameplay, graphics-transfer, audio, menu, presentation or
  progression changes. It runs the actual ROM in Snes9x and records the tested
  ROM hash for the gameplay, roster, presentation and focused-input suites.
- Run automated verification silently and headlessly. The libretro test host
  may capture audio for assertions, but must not play it through the speakers.
  The user has also authorized muted live emulator review now that they are
  no longer playing another fullscreen game. Keep GUI review muted and separate
  from the reproducible headless suites. Default to preserving foreground focus
  during future automated work.
- Do not report emulator pass counts or release readiness until all four current
  ROM reports point to the exact same ROM SHA256:
  `docs/test-report.json`, `docs/character-test-report.json`,
  `docs/presentation-test-report.json` and `docs/input-test-report.json`.
- Keep the one-actor-per-vblank transfer budget, 32 KiB LoROM bank boundaries,
  OBJ scanline limits and reserved palette banks in mind.
- The v0.5 renderer uses thirty 16x16 sprites per actor at OAM byte 0 and 128,
  with 3,840-byte pose streams in actor pages `$6000-$69FF` and `$6A00-$73FF`.
  Keep the 96x80 canvas, 94x77 safe area, native feet baseline at height 78
  and one uniform physical scale per fighter across all 48 frames.
- Each fighter has legacy frames 0-15, motion/transition frames 16-31 and action
  frames 32-47. Six contiguous 30,720-byte banks (`fighterXX` and `fighterXXb`
  through `fighterXXf`) hold the native data; each fighter uses one shared
  fifteen-color OBJ palette.
- Keep twelve individual illustrated fighter masters and their identities,
  palettes and costumes separate. The v0.5 animation pass adds 24 new
  built-in-imagegen atlases (`animation-motion.png` and `animation-actions.png`)
  while leaving all twelve identity masters unchanged. Reston's selected master
  remains the v3 short-hair correction. Keep each atlas's full prompt and
  provenance in its adjacent `animation.json`.
- The v0.5 presentation uses three independent stage PNGs described by
  `assets/art/stages/stages.json`, plus original home/select/arena menu art
  under `assets/art/menu/`. Keep `assets/art/menu/prompts.json` with the source
  prompt set and keep menu lettering on the original project glyphs. The menu
  direction is minimal royal navy, white and gold with one cursor and one large
  selected portrait.
- Keep original art masters and prompts in the repository. Do not import
  commercial game ROMs, Capcom sprites, or commercial game audio.
- Preserve future scope for more unique in-between art, balance tuning, stage
  parallax, human playtesting and real-console/flash-cartridge verification;
  do not imply those roadmap items are complete.
- Do not commit `.tools/`, emulator saves, build intermediates or release ZIPs.
- Rebuild the offline package with `tools/package.py` only after all four suites
  pass against the exact current ROM. Keep third-party license notices intact.
