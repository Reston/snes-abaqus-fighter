"""Original native pixel effects, authored on the existing 128x32 OBJ sheet.

No source illustration is altered. The named 16x16 cells retain the current
tile layout. Lower cells x80/x96 supply light contacts without growing VRAM,
the palette or the single impact OAM entry. Projectiles and shadows stay exact.
"""
from PIL import Image, ImageDraw


def make_effect_sheet():
    image = Image.new('P', (128, 32), 0)
    d = ImageDraw.Draw(image)

    # Strong strike: substantial first contact, expanding split rays, embers.
    # Cream core / gold body / orange tips remain legible on all three stages.
    for phase, radius in enumerate((5, 7, 6, 4)):
        cx, cy = phase * 16 + 8, 8
        if phase < 3:
            outer = [(cx, cy-radius), (cx+1, cy-2),
                     (cx+radius, cy-radius+1), (cx+3, cy),
                     (cx+radius, cy+radius-1), (cx+1, cy+2),
                     (cx, cy+radius), (cx-1, cy+2),
                     (cx-radius, cy+radius-1), (cx-3, cy),
                     (cx-radius, cy-radius+1), (cx-1, cy-2)]
            d.polygon(outer, fill=13)
            d.polygon([(cx, cy-radius+1), (cx+2, cy-1),
                       (cx+radius-1, cy), (cx+2, cy+1),
                       (cx, cy+radius-1), (cx-2, cy+1),
                       (cx-radius+1, cy), (cx-2, cy-1)], fill=3)
            if phase < 2:
                d.rectangle((cx-1, cy-2, cx+1, cy+2), fill=2)
                d.line((cx-2, cy, cx+2, cy), fill=12)
            else:
                d.rectangle((cx-1, cy-1, cx+1, cy+1), fill=0)
        else:
            for dx, dy in ((-5,-4), (4,-5), (-3,5), (5,3)):
                d.line((cx+dx, cy+dy, cx+dx//2, cy+dy//2), fill=3)
                d.point((cx+dx, cy+dy), fill=13)

    # High projectile: three breathing cores with a directional trailing edge.
    for phase in range(3):
        x = 64 + phase * 16
        top = (4, 3, 4)[phase]
        d.polygon([(x,7), (x+5,top+1), (x+10,top),
                   (x+14,6), (x+15,8), (x+12,12),
                   (x+6,13-top//3), (x+3,10), (x,11), (x+2,8)], fill=4)
        d.ellipse((x+6,top+2,x+13,11), fill=2)
        d.line((x+1,7+phase%2,x+8,7+phase%2), fill=3)
        d.point((x+13,6), fill=12)

    # Guard: hollow cyan brace opening toward the attacker, then a wider arc.
    # The center stays transparent; no damage burst or screen flash on a block.
    for phase in range(2):
        x = phase * 16
        inset = 3 if phase == 0 else 1
        d.arc((x+inset,16+inset,x+15-inset,31-inset),
              220, 500, fill=4, width=2)
        d.arc((x+inset+2,18+inset,x+13-inset,29-inset),
              250, 470, fill=2)
        d.line((x+3,18,x+1,16), fill=4)
        d.line((x+3,29,x+1,31), fill=4)

    # Low projectile: grounded amber crest, animated from heel to leading tip.
    for phase in range(3):
        x = 32 + phase * 16
        crest = (6, 9, 7)[phase]
        d.polygon([(x,29), (x+3,26), (x+4,29), (x+crest,19),
                   (x+crest+1,24), (x+12,21+phase),
                   (x+15,28), (x+14,30), (x+2,30)], fill=13)
        d.polygon([(x+3,29), (x+crest,23), (x+crest,27),
                   (x+12,25), (x+14,29)], fill=3)
        d.line((x+6,29,x+12,27), fill=2)

    # Light contact: a tight amber diamond and two separated fading flecks.
    # Native cells 426/428 were blank; all pixels fit their own 16x16 cell.
    x = 80
    d.polygon([(x+8,20), (x+9,23), (x+12,24), (x+9,25),
               (x+8,28), (x+7,25), (x+4,24), (x+7,23)], fill=13)
    d.line((x+8,22,x+8,26), fill=3)
    d.line((x+6,24,x+10,24), fill=3)
    d.point((x+8,24), fill=2)
    d.line((x+2,20,x+4,22), fill=3)
    d.line((x+11,27,x+13,29), fill=13)
    x = 96
    for a, b in (((x+2,19), (x+4,21)), ((x+11,27), (x+13,29))):
        d.line((*a, *b), fill=13)
        d.point(b, fill=3)
    d.line((x+7,23,x+8,24), fill=3)

    # Left half of one shallow contact ellipse. The native renderer places
    # adjacent mirrored halves at floor-1: its dark center touches the feet,
    # with no detached pair of ovals below the fighter. Keep the same two
    # 16x16 OAM entries, below the low waves' last fetch line (198).
    # Four painted scanlines keep the contact ellipse shallow.
    for y in range(4):
        for x in range(16):
            radius=((x-15.5)/16)**2+((y-1.5)/2.0)**2
            if radius<=1:image.putpixel((112+x,16+y),11 if radius>.72 else 8)
    return image
