# Menu direction

The v0.4 menu plates use a shared native arcade language: deep navy panels,
warm gold and orange title lettering, cyan/magenta selection accents, chrome
registration marks, and compact pixel-authored labels. The imagery is tied to
the game's setting through a stylized Santiago evening skyline and the Andes,
while the selection and arena screens keep the same low-contrast field behind
the readable UI.

`tools/menu_assets.py` owns only the three 256x224 RGB plates returned by
`make_menu_images(root, stages, roster, text)`. The native C renderer remains
responsible for dynamic state:

- Title menu rows at y=160, 176, and 192, with the cursor at x=7.
- Four-by-three fighter cells beginning at x=8, y=48, with 40x48 spacing.
  Each cell has a 38x46 framed card at (+1,+1) and a 32x40 portrait at
  (+4,+4), leaving the native 5x6-tile cursor outside the cell origin.
- The selected fighter's 64x80 portrait slot at x=184, y=48.
- Dynamic fighter name, style, stats, special name, and input footer.
- Three arena cards beginning at x=16, y=48, with 56-pixel vertical spacing.
- The arena cursor strip at x=8, y=40 plus 56 pixels per row.

The generated master is `assets/art/menu/title-backdrop.png`; its complete
built-in imagegen prompt, provenance, dimensions, SHA-256, and crop policy are
in `assets/art/menu/prompts.json`. Generated imagery contains no readable
text, so all words in the final plates use the project's authored glyph
callback and remain deterministic for the SNES tile pipeline.

The title master is intentionally kept at 1536x1024 as an art source. The
module crops it to 256x224 and applies a restrained dark overlay before
composing the code-authored logo and clean menu wells. The stage previews use
nearest-neighbor crops from the existing native stage images; no new stage
photography or commercial game art is introduced.
