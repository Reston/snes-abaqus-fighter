# Fighter proportion contract

The runtime treats every fighter as a **96x80 native canvas**. The canvas is
six 16x16 OBJ pieces wide and five pieces high. Every pose for one fighter is
rendered with one scale chosen from that fighter's source atlas; a wide kick or
an extended arm cannot silently shrink the whole fighter for one animation.

The source art remains free to use different pose silhouettes. Crouches,
jumps, attacks, victory poses, and knockouts can have different opaque bounds,
but they share the same floor pivot and native canvas. The asset manifest
records the source scale and effective standing height so visual review can
distinguish intentional pose variation from a changed fighter scale.

## Native transfer layout

Each 96-pixel row contains twelve 8x8 tiles (384 bytes). The SNES OBJ page is
16 tiles wide, so the renderer advances 512 bytes to the next row and leaves
128 bytes of padding at the right edge. A pose is therefore 10 source rows,
3,840 streamed bytes, and 5,120 bytes in its padded VRAM page.

| Resource | Address / range | Contract |
| --- | --- | --- |
| Actor 0 frame page | VRAM word `$6000` | tile base 0 |
| Actor 1 frame page | VRAM word `$6A00` | tile base 160 |
| Actor 0 OAM block | bytes `0..127` | 30 live 16x16 entries + 2 pad slots |
| Actor 1 OAM block | bytes `128..255` | 30 live 16x16 entries + 2 pad slots |
| Shadows/effects | byte `256` and above | outside both actor blocks |

The two actor pages are contiguous but are not interleaved. Actor 1's fourth
and fifth tile rows cross OBJ tile number 255, so the renderer writes the
9th tile-number bit in each entry's OAM attribute byte. The high OAM table also
keeps each sprite's 16x16 size bit set and writes the ninth X bit from the
signed screen coordinate. This lets the 96-pixel body pass the left or right
edge while the gameplay position remains centered on the same pivot.

OBJSEL is configured for 8×8 small / 16×16 large sprites. Actor pieces,
shadows and effects select the large size. The renderer computes packed X9
fields once per actor and uses paired tile/attribute stores; actor 1's ninth
tile bit remains separate from the size and X9 fields.

The renderer streams at most one pose per vblank. A second actor may therefore
show its previous pose for one video frame while its combat state continues;
the transfer is bounded at 3,840 bytes per frame and the row stride remains
the 512-byte OBJ hardware page.

Pose-bank pointer selection and offset arithmetic are prepared during active
display. The blanking interval then performs the queued transfer directly,
so its final rows do not spill into visible scanlines. Interface updates also
cache unchanged health, meter, wins and timer values.
