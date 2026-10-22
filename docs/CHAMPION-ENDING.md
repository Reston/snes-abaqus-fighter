# Original Office Champion ending

This isolated candidate adds an earned ending after the eleventh Arcade
opponent. Its trophy, star medallion, keyboard plinth and Santiago night-office
scene are original built-in-imagegen art. The concept was accepted for native
integration; human art approval remains pending. No version bump or package
is part of this child change. The parent v0.11 verification checkout is untouched.

## Artwork and reproducibility

The exact RGB 1340x1174 output is retained at
`assets/art/menu/source-champion-v1/champion-raw-v1.png`, SHA256
`5de9abb1669e5c2c9a1c7ad40ae119c4e7392e4a55be72432bf0d3f627bfb62e`.
The adjacent `generation-v1.json` is the unmodified exact-prompt record supplied
by the parent. `assets/art/menu/champion-ending-v1.json` links both to the
canonical opaque RGB 1024x896 master and records its hashes and preparation.
The JSON record hash uses LF-normalized text for reproducibility after Git
checkout; the exact prompt string and raw PNG are retained. No semantic art
edits were made.

`tools/champion_assets.py --prepare-master` reproduces the canonical master:
center crop `(2,2,1338,1171)` to exact 8:7, nearest-neighbor sample to 256x224,
collapse near-identical navy shades within twelve channel levels of RGB
`(17,26,61)` to that common color globally, then Pillow MEDIANCUT reduction to
90 colors without dithering, then nearest-neighbor
4x enlargement. Normal `Build.cmd --assets` validates the hashes, original raw
output, color ceiling and exact 4x grid before using the existing six-palette
BG1 converter. All lettering comes from the existing opaque project glyphs.

## Native scene contract

Only the champion branch of `showResult` loads the new scene. It uses the
existing screen-off transition, BG1 graphics/map addresses and palette banks
2..7. The winner uses the existing 64x80 portrait at VRAM `$4A00` and BG2
palette 1, anchored at tile `(21,7)`, inside the existing gold cursor frame.
The name, real P1/P2 round score and two-line ALL 11 / DEFEATED label occupy
the empty right column. The quote and truthful A/START: TITLE and
B: CHARACTER SELECT commands occupy the footer at rows 22, 24 and 26.
Only rows 22..27 receive a full navy panel, preserving the trophy base through
pixel row 175. The heading is centered on row 2.

Other result cards retain the v0.11 stage, portrait, text coordinates and
navigation. No combat, audio, Training boot/menu, Fighter64/Wave16 layout,
TRACE[0..122], ambient-cell or live DMA/OBJ behavior changes are included.
The native cartridge remains a 4 MiB NTSC FastROM LoROM image.

The final scene uses 330 BG1 tiles / 10,560 bytes, a 2,048-byte map and a
192-byte palette. Linked source blocks begin at `$E5:8000`, `$84:F800` and
`$9F:F8C0` respectively; each fits its 32 KiB LoROM bank. The maximum tile
index is 329, leaving the reserved ambient cells 960..967 untouched. The
generated set grows from 214 to 218 committed files: `champion.png` plus
`champion_tiles.bin`, `champion_map.bin` and `champion_pal.bin`.
`assets.h` and `data.asm` register the three new blocks.

The [preservation report](champion-preservation-report.json) compares every
pre-existing tracked asset, `src/hardware.asm` and `src/trace.asm` against
the clean base commit `68842a2b040fefc9070542fcf57284af5494e1dc`. Only the two
generated assembly/header metadata files change; all existing masters, menu
art, glyphs, palettes, fighter banks, portraits, stage data and audio bytes
are preserved. Three otherwise unchanged generated text files were restored
to their original LF line endings after the Windows generator ran.

## Focused verification

`tools/test_champion.py` boots the actual Snes9x ROM and uses only controller
input to win all eleven Arcade opponents. Losses continue the same opponent;
the probe verifies that only the eleventh win awards champion. It checks the
earlier result's original stage and layout, then the champion BG1 bytes/map,
entire unobscured trophy/office PPU region, exact portrait VRAM and rendered
portrait, opaque heading/name/score/quote/footer glyphs, stable waiting scene
and the A-to-title transition. `--exit start` and `--exit b` select alternative
exit proofs, each from a fresh controller-driven ladder. There are no emulated
memory writes, save states, GUI windows or audio devices.

`Build.cmd --assets` and the final `Build.cmd` complete successfully on this
child candidate, with unchanged version 0.11.0, checksum `218B`, ROM SHA256
`cd38f83519835855b2bf04273b86403a68637075c7a59222bd17b018014b4567`.
The [focused report](champion-ending-report.json) and captures
([ending](screenshots/champion/ending.png),
[earlier result](screenshots/champion/arcade-result.png),
[A-to-title](screenshots/champion/exit-a.png)) belong to that exact SHA.
The actual PPU trophy and portrait pixels agree with their decoded native
assets within two RGB channel levels. The scene remains stable while waiting
for input. The run uses Python 3.12.10, Pillow 13.0.0 and the pinned Snes9x
core, below-normal priority (`0x4000`), processors 14/15, no window and stdin
NUL; diagnostic logs stay under ignored `build/`. Only the A exit is exercised
in this focused capture; Start/B handling remains unchanged in `menuTick`.

The focused report and captures identify their exact child ROM. They do not
replace `Test.cmd`, pinned compatibility, extended release evidence or fresh
source verification after the parent merges this change. Historical reports
remain evidence for their recorded ROMs only. Human gameplay, physical
controller, full listening, likeness/consent and team/public-use gates remain
open; hardware support is unverified and `public_release_certified` is false.
