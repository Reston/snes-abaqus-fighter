# Project instructions

This is a native SNES fighting game. The authoritative deliverable is
`dist/abaqus-after-hours.sfc`, built with PVSnesLib 4.6.0 from C and 65816 assembly.
Preserve the native emulator requirement when extending the project.

- Read `docs/DEVELOPMENT.md` before changing memory layout or hardware transfers.
- Build with `Build.cmd`; regenerate assets with `Build.cmd --assets`.
- Run `Test.cmd` after gameplay, graphics-transfer, audio or progression changes.
  It runs the actual ROM in Snes9x and records the tested ROM hash.
- Run agent verification silently and headlessly. The libretro test host may
  capture audio data for assertions, but must not play it through the speakers.
  Do not launch, reopen, refocus, or bring emulator windows forward for testing;
  the user may be playing another game in fullscreen. Keep their focus intact.
- Keep the one-actor-per-vblank transfer budget, 32 KiB LoROM bank boundaries,
  OBJ scanline limits and reserved palette banks in mind.
- Keep original art masters and prompts in the repository. Do not import
  commercial game ROMs, Capcom sprites, or commercial game audio.
- The v0.3 roster uses twelve individual illustrated sixteen-pose atlases,
  with a shared pose-index contract and renderer. Keep their identities and
  palettes separate; further in-between animation and balance work remains.
- Do not commit `.tools/`, emulator saves, build intermediates or release ZIPs.
- Rebuild the offline package with `tools/package.py` only after tests pass
  against the exact current ROM. Keep third-party license notices intact.
