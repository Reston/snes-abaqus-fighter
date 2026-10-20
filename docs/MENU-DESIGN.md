# Menu design

The menu plates use a quiet, original 16-bit presentation.  They are built
from flat royal-blue and navy fields, the project's existing bitmap glyphs,
one-pixel rules, and a single warm gold selection accent.  The visual goal is
the clear rhythm of a classic arcade fighter: the player should find the mode,
fighter, arena, and confirmation prompt immediately.  The plates do not copy
commercial game artwork or fonts.

`tools/menu_assets.py` owns only the background plates.  The native renderer
in `src/game.c` owns live text, selection cursors, and the 64x80 profile
portrait.  `make_menu_images(root, stages, roster, text)` continues to return
the three RGB 256x224 images expected by `tools/make_assets.py`.

## Home

The title plate keeps the wordmark in the upper half and leaves the lower band
quiet for the existing live rows at tile rows 20, 22, and 24.  The generator
uses the supplied title backdrop only as a very faint tonal trace; the screen
reads as a flat navy interface on a CRT.  The native `drawTitle()` should keep
the three mode rows in their existing positions and use the existing project
glyphs for their labels.  A small `A START   B BACK` hint may remain at the
bottom center.

## Fighter select

The grid is a four-by-three set of 40x48 cells:

| Element | Native pixel rectangle |
| --- | --- |
| Grid cell | `x=8+40*column`, `y=48+48*row`, `40x48` |
| Card portrait | cell origin plus `(4,4)`, `32x40` |
| Native cursor lane | cell origin, `5x6` tiles, outside the portrait |
| Profile portrait frame | `x=183..248`, `y=47..129` |
| Profile portrait DMA | `x=184`, `y=48`, `64x80`, BG2 palette 1 |
| Live fighter name | `x=176`, tile row 17 (`y=136`) |
| Full-width footer separators | `y=198` and `y=210` rules |

The card borders use low-contrast blue.  The live native cursor should be the
only strong accent: gold or the existing single warm cursor treatment.  Do not
add card numbers, family badges, POWER/SPEED blocks, multi-color corner marks,
or a second technical panel.  The parent C pass may show a small `PLAYER 1`
or `PLAYER 2` heading above the profile area, but the selected name should
remain the first piece of information below the large portrait.

The integrated native UI places that player heading at pixel `(184,32)` and
keeps only the selected name below the portrait. Family, power, speed and
special-move labels are omitted. Cursor tiles use one gold accent, and text
uses transparent glyphs with a one-pixel navy shadow. The title footer reads
`PRESS START`; the arena heading has no extra right-side hint.

The v0.5.1 live fight clears the intro hint at tile rows 26-27 when combat
begins, on pause and on Training reset. This restores the bottom sixteen native
pixels to the arena. A dedicated 128-byte dirty-region upload handles the clear.
The result panel shows `P1  0 - 0  P2` at row 15 with the actual round wins;
the fighter quote moves to row 17, retaining actions at rows 19 and 21.

Horizontal movement remains one card at a time.  Up and down move by four
entries, preserving the natural 4x3 reading order.

## Arena select

The three stage cards are aligned to the existing native cursor:

| Element | Native pixel rectangle |
| --- | --- |
| Stage card | `x=16`, `y=48+56*arena`, `224x48` |
| Native cursor lane | `x=8`, `y=40+56*arena`, `240x56` |
| Footer rule | `y=205` |

Each card is an unblurred shallow crop of the authored stage plate with a
single dark caption strip along its bottom edge.  The caption names are
`LAS CONDES`, `EL CASTILLO`, and `LA OFICINA`.  A thin blue frame keeps the
three choices separate, while the live cursor supplies the warm accent.  The
footer may read `UP / DOWN   A OK   B BACK` in the project glyphs.

## Native conversion notes

All generated plates are RGB 256x224 and remain within a compact navy, royal,
cream, muted-blue, and gold family.  This keeps the six local 15-color tile
palettes stable through the existing converter.  No menu asset writes files
at import time; previews are produced only by the normal `Build.cmd --assets`
pipeline.  The title master and its source prompt remain in
`assets/art/menu/` for provenance, even though the current layout intentionally
uses the master at very low opacity.
