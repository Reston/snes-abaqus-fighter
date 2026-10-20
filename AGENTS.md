# Project instructions

This is a native SNES fighting game. The authoritative deliverable is
`dist/abaqus-after-hours.sfc`, built with PVSnesLib 4.6.0 from C and 65816 assembly.
The current v0.4 cartridge is a 2 MiB NTSC FastROM LoROM image across 64 banks.
Preserve the native emulator requirement when extending the project.

- Read `docs/DEVELOPMENT.md` before changing memory layout or hardware transfers.
- Build with `Build.cmd`; regenerate assets with `Build.cmd --assets`.
- Run `Test.cmd` after gameplay, graphics-transfer, audio, menu, presentation or
  progression changes. It runs the actual ROM in Snes9x and records the tested
  ROM hash for the gameplay, roster and presentation suites.
- Run agent verification silently and headlessly. The libretro test host may
  capture audio data for assertions, but must not play it through the speakers.
  Do not launch, reopen, refocus, or bring emulator windows forward for testing;
  the user may be playing another game in fullscreen. Keep their focus intact.
- Do not report emulator pass counts or release readiness until all three
  current-ROM reports point to the exact same ROM SHA256.
- Keep the one-actor-per-vblank transfer budget, 32 KiB LoROM bank boundaries,
  OBJ scanline limits and reserved palette banks in mind.
- The v0.4 renderer uses thirty 16×16 sprites per actor at OAM byte 0 and 128,
  with 3,840-byte pose streams in actor pages `$6000–$69FF` and `$6A00–$73FF`.
  Keep the 96×80 canvas, 94×77 safe area and one uniform physical scale per
  fighter across all sixteen poses.
- Keep twelve individual illustrated fighter masters and their identities,
  palettes and costumes separate. Seven likeness v2 masters were refreshed for
  Damián, Cote, Negger, Fernando, Mamariaga, Reston and Roxana; the earlier v2
  masters for Ivo, Cristóbal, David, Cristián and Lars remain selected. All
  twelve have matching 32×40 card and 64×80 profile portraits.
- The v0.4 presentation uses three independent stage PNGs described by
  `assets/art/stages/stages.json`, plus original home/select/arena menu art
  under `assets/art/menu/`. Keep `assets/art/menu/prompts.json` with the source
  prompt set and keep menu lettering on the original project glyphs.
- Keep original art masters and prompts in the repository. Do not import
  commercial game ROMs, Capcom sprites, or commercial game audio.
- Preserve future scope for in-between animation, balance tuning and stage
  parallax; do not imply those roadmap items are complete.
- Do not commit `.tools/`, emulator saves, build intermediates or release ZIPs.
- Rebuild the offline package with `tools/package.py` only after all three
  suites pass against the exact current ROM. Keep third-party license notices
  intact.
