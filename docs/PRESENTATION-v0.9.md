# Presentation corrections

This pass follows the user's live v0.8.1 review: clipped selection faces,
Damian's likeness, narrow arena crops, and scenery showing through HUD and
result lettering.

Selection portraits now share one head-anchored composition at 32x40 and
64x80. The source window is contained with nearest-neighbor sampling and a
small background margin. It no longer fills the target by cutting off the
source's left and right edges. `character-manifest.json` records the source
crop, head anchor, padding and scale as `portrait_framing`.

The arena picker retains its native three-row cursor contract at x8..247,
y40..95 plus 56 pixels per row. Each complete stage image fits inside a
60x52 thumbnail at x18..77, y42..93 plus 56 pixels per row. The gold cursor
does not touch the scene pixels. Location names and short captions occupy a
separate text column.

The text defect was a BG2 tile transparency error. Writing an ASCII glyph
replaces the solid panel tile at that map cell; transparent holes then reveal
BG1. FIGHT and RESULT now select the existing opaque glyphs 256..383, whose
background pixels use UI palette index 1. Title, roster and arena menu text
retain the original ASCII bank. Round marker tiles 147/148 also use the opaque
panel background. VRAM allocation, transfer sizes and all Fighter/Wave trace
offsets remain unchanged.

The presentation suite checks the actual PPU frame against decoded native
portrait tiles and palettes for all twelve selections. It compares complete
32x40 grid portraits, arena interiors and thumbnails, cursor/map geometry,
and HUD/result glyph cells. Exact portrait VRAM/map assertions remain in
place. Test captures are generated silently; image-content checks supplement
the existing gameplay, roster, input, stage and Training suites.

Damian's versioned art sources and immutable revision contract retain his
established palette, physical scale and animation order. The other eleven
fighters' native pose banks remain fixed. Native visual acceptance does not
substitute for the user's likeness review or public-use approval.
