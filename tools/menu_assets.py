"""Code-authored native menu plates for Abaqus: After Hours.

The native menu renderer owns its tile conversion and dynamic text.  This
module only composes the three 256x224 RGB plates that sit behind that UI.
The deliberately small layout leaves the dynamic fighter profile, cursor,
menu mode, and arena cursor areas clear for ``src/game.c``.

Public contract::

    make_menu_images(root, stages, roster, text) -> {
        "title": RGB 256x224 image,
        "select": RGB 256x224 image,
        "arenas": RGB 256x224 image,
    }

``text`` is the project's pixel glyph callback with the signature
``text(image, xy, words, color, scale=1, center=False)``.  Pillow is the only
runtime dependency beyond the Python standard library.
"""

from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps


Size = tuple[int, int]
TextFn = Callable[..., Any]

W, H = 256, 224

# Fixed arcade palette.  Keep these colours below the native converter's six
# local palette groups so the plates remain legible after tile quantization.
NAVY_0 = (5, 10, 31)
NAVY_1 = (10, 17, 49)
NAVY_2 = (17, 28, 67)
NAVY_3 = (31, 46, 91)
CYAN = (83, 226, 218)
CYAN_DARK = (29, 118, 141)
MAGENTA = (229, 64, 145)
MAGENTA_DARK = (105, 31, 104)
GOLD = (255, 219, 91)
GOLD_LIGHT = (255, 241, 163)
ORANGE = (255, 133, 52)
ORANGE_DARK = (168, 57, 35)
WHITE = (244, 247, 234)
MUTED = (145, 178, 196)
STEEL = (88, 116, 151)
BLACK = (3, 5, 17)


def _rgb_image(image: Image.Image, size: Size = (W, H)) -> Image.Image:
    """Return a detached RGB image at the native menu size."""

    return image.convert("RGB").resize(size, Image.Resampling.NEAREST)


def _alpha_rect(im: Image.Image, box: tuple[int, int, int, int], fill: tuple[int, int, int, int]) -> None:
    """Draw one RGBA rectangle while keeping the plate itself RGB."""

    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle(box, fill=fill)
    im.paste(overlay.convert("RGB"), (0, 0), overlay)


def _alpha_line(im: Image.Image, xy: tuple[int, int, int, int], fill: tuple[int, int, int, int], width: int = 1) -> None:
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).line(xy, fill=fill, width=width)
    im.paste(overlay.convert("RGB"), (0, 0), overlay)


def _fallback_backdrop() -> Image.Image:
    """Small deterministic fallback used when the master is absent in a test."""

    im = Image.new("RGB", (W, H), NAVY_0)
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / max(1, H - 1)
        c = tuple(int(NAVY_2[k] * (1.0 - t) + NAVY_0[k] * t) for k in range(3))
        d.line((0, y, W - 1, y), fill=c)
    d.polygon([(0, 168), (26, 145), (43, 163), (70, 135), (104, 166), (144, 140), (184, 164), (221, 134), (256, 157), (256, 224), (0, 224)], fill=(25, 36, 78))
    for x, top, width in ((12, 174, 16), (42, 160, 13), (75, 170, 21), (115, 151, 17), (151, 170, 15), (184, 153, 23), (219, 166, 16)):
        d.rectangle((x, top, x + width, 211), fill=(11, 21, 48))
        for wx in range(x + 3, x + width - 1, 5):
            d.rectangle((wx, top + 6, wx + 1, top + 8), fill=ORANGE_DARK)
    return im


def _load_title_backdrop(root: Path) -> Image.Image:
    path = Path(root) / "assets" / "art" / "menu" / "title-backdrop.png"
    if not path.exists():
        return _fallback_backdrop()

    source = Image.open(path).convert("RGB")
    # The generated master is intentionally wider than the SNES aspect ratio.
    # A slightly high crop keeps the Andes and the sunset band while retaining
    # a calm, dark center for the code-authored logo.
    return ImageOps.fit(source, (W, H), method=Image.Resampling.LANCZOS, centering=(0.5, 0.43))


def _darken(im: Image.Image, brightness: float = 0.65, saturation: float = 0.85) -> Image.Image:
    out = ImageEnhance.Color(im).enhance(saturation)
    return ImageEnhance.Brightness(out).enhance(brightness)


def _pixel_text(text_fn: TextFn, im: Image.Image, xy: tuple[int, int], words: str, color: tuple[int, int, int], scale: int = 1, center: bool = False, shadow: tuple[int, int, int] | None = None, shadow_offset: tuple[int, int] = (1, 1)) -> None:
    """Render a crisp pixel label with an optional one-pixel extrusion."""

    if shadow is not None:
        sx, sy = shadow_offset
        text_fn(im, (xy[0] + sx, xy[1] + sy), words, shadow, scale=scale, center=center)
    text_fn(im, xy, words, color, scale=scale, center=center)


def _corner_marks(im: Image.Image, box: tuple[int, int, int, int], color: tuple[int, int, int]) -> None:
    """Add four one-pixel arcade registration marks around a panel."""

    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(im)
    d.line((x0, y0, x0 + 7, y0), fill=color)
    d.line((x0, y0, x0, y0 + 4), fill=color)
    d.line((x1 - 7, y0, x1, y0), fill=color)
    d.line((x1, y0, x1, y0 + 4), fill=color)
    d.line((x0, y1, x0 + 7, y1), fill=color)
    d.line((x0, y1 - 4, x0, y1), fill=color)
    d.line((x1 - 7, y1, x1, y1), fill=color)
    d.line((x1, y1 - 4, x1, y1), fill=color)


def _draw_title(root: Path, text_fn: TextFn) -> Image.Image:
    im = _darken(_load_title_backdrop(root), 0.72, 0.78)
    d = ImageDraw.Draw(im)

    # The darkened center makes the gold logo and the live menu rows readable
    # on a CRT while leaving the warm Andes rim visible around it.
    _alpha_rect(im, (0, 19, 255, 128), (4, 8, 34, 112))
    _alpha_rect(im, (0, 142, 255, 223), (4, 8, 30, 224))
    _alpha_rect(im, (15, 145, 240, 204), (9, 16, 45, 190))
    d = ImageDraw.Draw(im)

    # Small corner labels frame the title without competing with the menu.
    _pixel_text(text_fn, im, (8, 8), "SANTIAGO / 199X", CYAN, shadow=BLACK)
    _pixel_text(text_fn, im, (193, 8), "ABAQUS", MUTED, shadow=BLACK)
    _alpha_line(im, (8, 19, 248, 19), (83, 226, 218, 155), 1)

    # Original slanted, extruded wordmark treatment.  The glyphs remain the
    # project's authored pixel glyphs, so no desktop font is pulled into ROM.
    # Scale five makes the mark read as the title-screen anchor at 256 pixels;
    # a warm orange lower pass and gold upper pass create the gradient while
    # the offset magenta pass provides the arcade cabinet-style extrusion.
    d.polygon([(43, 27), (219, 27), (228, 34), (222, 41), (37, 41)], fill=MAGENTA_DARK)
    d.polygon([(40, 24), (216, 24), (225, 31), (219, 38), (34, 38)], fill=ORANGE_DARK)
    _pixel_text(text_fn, im, (128, 27), "ABAQUS", ORANGE, scale=5, center=True, shadow=MAGENTA_DARK, shadow_offset=(3, 4))
    _pixel_text(text_fn, im, (128, 23), "ABAQUS", GOLD_LIGHT, scale=5, center=True)
    _alpha_line(im, (65, 67, 191, 67), (255, 133, 52, 255), 2)
    _alpha_line(im, (82, 70, 175, 70), (83, 226, 218, 255), 1)
    _pixel_text(text_fn, im, (128, 78), "AFTER HOURS", WHITE, scale=2, center=True, shadow=MAGENTA_DARK, shadow_offset=(1, 2))
    _pixel_text(text_fn, im, (128, 100), "OFFICE WORLD WARRIORS", CYAN, center=True, shadow=BLACK)

    # Three clean slots correspond to the dynamic rows written by showTitle.
    # Their interior stays untextured so the cursor and menu labels remain
    # crisp when the plate is reduced into six local BG palettes.
    for i in range(3):
        y0 = 155 + i * 16
        d.rectangle((26, y0, 230, y0 + 13), fill=NAVY_1, outline=NAVY_3)
        d.line((27, y0, 229, y0), fill=(53, 81, 125))
        d.line((27, y0 + 12, 229, y0 + 12), fill=(8, 13, 37))
        d.rectangle((28, y0 + 2, 31, y0 + 10), fill=CYAN_DARK if i != 1 else MAGENTA_DARK)
    _corner_marks(im, (15, 145, 240, 204), CYAN_DARK)
    _alpha_line(im, (16, 208, 239, 208), (229, 64, 145, 190), 1)
    _pixel_text(text_fn, im, (128, 214), "ORIGINAL HOMEBREW", MUTED, center=True, shadow=BLACK)
    return im.convert("RGB")


def _roster_portrait(item: Mapping[str, Any]) -> Image.Image:
    portrait = item.get("portrait")
    if isinstance(portrait, Image.Image):
        return portrait.convert("RGB").resize((32, 40), Image.Resampling.NEAREST)
    return Image.new("RGB", (32, 40), NAVY_2)


def _draw_select(root: Path, roster: Sequence[Mapping[str, Any]], text_fn: TextFn) -> Image.Image:
    # A dark, low-contrast title plate gives all twelve individual portraits a
    # shared world without making the cards fight the player profile panel.
    im = _darken(_load_title_backdrop(root), 0.30, 0.48)
    d = ImageDraw.Draw(im)
    _alpha_rect(im, (0, 0, 255, 39), (5, 10, 33, 232))
    _alpha_rect(im, (0, 40, 171, 223), (5, 10, 31, 88))
    _alpha_rect(im, (176, 0, 255, 223), (5, 10, 34, 238))
    d = ImageDraw.Draw(im)

    # Pixel grid in the left field and the angular right profile divider.
    for x in range(8, 173, 40):
        d.line((x, 44, x, 194), fill=(20, 39, 69))
    for y in range(48, 193, 48):
        d.line((8, y, 168, y), fill=(20, 39, 69))
    d.line((172, 40, 172, 205), fill=MAGENTA_DARK, width=2)
    d.line((175, 40, 175, 205), fill=CYAN_DARK)

    _pixel_text(text_fn, im, (8, 8), "SQUAD SELECT", GOLD_LIGHT, scale=2, shadow=ORANGE_DARK, shadow_offset=(1, 2))
    _pixel_text(text_fn, im, (177, 10), "PROFILE", CYAN, shadow=BLACK)
    _pixel_text(text_fn, im, (177, 25), "TEAM ABAQUS", MUTED, shadow=BLACK)
    _alpha_line(im, (8, 37, 165, 37), (255, 133, 52, 230), 1)
    _alpha_line(im, (181, 37, 249, 37), (83, 226, 218, 190), 1)

    # Fixed 4x3 card grid: 38x46 frames, portrait at +4,+4.  The native
    # cursor can land on each frame without covering its neighbor.
    for n in range(12):
        col, row = n % 4, n // 4
        x, y = 8 + col * 40, 48 + row * 48
        accent = CYAN if n % 3 else MAGENTA
        # The 40x48 cell is deliberately one pixel larger than the 38x46
        # framed card.  This leaves the native 5x6-tile cursor outside the
        # card at the exact cell origin while the portrait starts at +4,+4.
        d.rectangle((x + 1, y + 1, x + 38, y + 46), fill=(8, 14, 39), outline=STEEL)
        d.rectangle((x + 2, y + 2, x + 37, y + 45), outline=accent)
        d.rectangle((x + 3, y + 3, x + 36, y + 44), outline=(39, 58, 90))
        im.paste(_roster_portrait(roster[n] if n < len(roster) else {}), (x + 4, y + 4))
        # Tiny number tab is readable even with no dynamic name under the card.
        d = ImageDraw.Draw(im)
        d.rectangle((x + 3, y + 40, x + 12, y + 44), fill=NAVY_0)
        _pixel_text(text_fn, im, (x + 4, y + 40), str(n + 1).zfill(2), GOLD, shadow=BLACK)

    # Large portrait slot: deliberately an empty dark navy outline.  The
    # parent C renderer fills this exact 64x80 area with the selected fighter's
    # native portrait tiles after the dynamic profile is known.
    d = ImageDraw.Draw(im)
    d.rectangle((183, 47, 248, 129), fill=(7, 13, 39), outline=CYAN_DARK)
    d.rectangle((185, 49, 246, 127), outline=STEEL)
    d.line((185, 50, 196, 50), fill=CYAN)
    d.line((185, 50, 185, 62), fill=CYAN)
    d.line((235, 127, 246, 127), fill=MAGENTA)
    d.line((246, 116, 246, 127), fill=MAGENTA)
    # Dynamic text bands are intentionally blank inside the right panel;
    # src/game.c owns the name at y=136, family at y=152, power at y=168, and
    # speed at y=184.  Rules sit only between those rows, never underneath a
    # glyph baseline.
    for y in (148, 164, 180):
        d.line((180, y, 250, y), fill=(31, 47, 81))

    # Full-width rows are reserved for dynamic special and input footer text.
    _alpha_rect(im, (7, 198, 249, 207), (5, 10, 31, 245))
    _alpha_rect(im, (7, 210, 249, 223), (5, 10, 31, 245))
    _alpha_line(im, (8, 198, 248, 198), (255, 133, 52, 230), 1)
    _alpha_line(im, (8, 210, 248, 210), (83, 226, 218, 190), 1)
    return im.convert("RGB")


def _stage_preview(stage: Image.Image) -> Image.Image:
    source = stage.convert("RGB")
    # A shallow crop makes each card read as a cinematic strip while retaining
    # the hard-edged native stage art instead of introducing blur.
    preview = ImageOps.fit(source, (224, 48), method=Image.Resampling.NEAREST, centering=(0.5, 0.58))
    preview = ImageEnhance.Brightness(preview).enhance(0.72)
    preview = ImageEnhance.Contrast(preview).enhance(1.08)
    return preview


def _draw_arenas(stages: Sequence[Image.Image], text_fn: TextFn) -> Image.Image:
    im = Image.new("RGB", (W, H), NAVY_0)
    d = ImageDraw.Draw(im)
    # Angular navy field with a subtle cyan/magenta scanline rhythm.
    for y in range(H):
        c = (7 + y // 24, 13 + y // 28, 35 + y // 12)
        d.line((0, y, 255, y), fill=c)
    for x in range(-224, 256, 24):
        d.line((x, 0, x + 68, 224), fill=(11, 28, 57))
    _alpha_rect(im, (0, 0, 255, 36), (5, 10, 33, 238))
    _alpha_rect(im, (0, 205, 255, 223), (5, 10, 31, 245))
    _pixel_text(text_fn, im, (8, 8), "ARENA SELECT", GOLD_LIGHT, scale=2, shadow=ORANGE_DARK, shadow_offset=(1, 2))
    _pixel_text(text_fn, im, (239, 10), "CL", CYAN, shadow=BLACK, center=True)
    _alpha_line(im, (8, 36, 247, 36), (229, 64, 145, 210), 1)

    names = ("LAS CONDES", "EL CASTILLO", "LA OFICINA")
    tags = ("SANTIAGO / CL", "SANTIAGO / CL", "ABAQUS HQ / CL")
    accents = (CYAN, MAGENTA, GOLD)
    for i in range(3):
        y = 48 + i * 56
        accent = accents[i]
        d = ImageDraw.Draw(im)
        d.rectangle((15, y - 1, 240, y + 48), fill=NAVY_1, outline=(35, 57, 94))
        d.rectangle((16, y, 239, y + 47), outline=accent)
        stage = stages[i] if i < len(stages) else Image.new("RGB", (W, H), NAVY_2)
        im.paste(_stage_preview(stage), (16, y))
        # Dark left caption well preserves the image while making the name and
        # location tag legible at native resolution.
        _alpha_rect(im, (20, y + 4, 120, y + 43), (5, 10, 31, 195))
        d = ImageDraw.Draw(im)
        d.line((21, y + 5, 21, y + 42), fill=accent, width=2)
        _pixel_text(text_fn, im, (27, y + 10), names[i], WHITE, shadow=BLACK)
        _pixel_text(text_fn, im, (27, y + 26), tags[i], accent, shadow=BLACK)
        # Preview corner ticks echo the selection cursor without hardcoding its
        # live state; drawArenas can highlight the active row above this plate.
        d.line((226, y + 4, 235, y + 4), fill=accent)
        d.line((235, y + 4, 235, y + 11), fill=accent)

    # Cursor landing strip and dynamic footer are kept open for native UI.
    for i in range(3):
        y = 40 + i * 56
        d = ImageDraw.Draw(im)
        d.rectangle((8, y, 38, y + 7), fill=NAVY_0, outline=CYAN_DARK if i != 1 else MAGENTA_DARK)
        d.line((10, y + 1, 36, y + 1), fill=STEEL)
    _alpha_line(im, (8, 205, 248, 205), (83, 226, 218, 180), 1)
    _pixel_text(text_fn, im, (128, 214), "UP / DOWN  A TO FIGHT", MUTED, center=True, shadow=BLACK)
    return im.convert("RGB")


def make_menu_images(root: str | Path, stages: Sequence[Image.Image], roster: Sequence[Mapping[str, Any]], text: TextFn) -> dict[str, Image.Image]:
    """Compose title, fighter-select, and arena-select plates.

    ``stages`` should contain the three native 256x224 stage previews and
    ``roster`` should contain dictionaries with a 32x40 ``portrait`` image.
    The function never writes files or mutates caller-owned images.
    """

    if not callable(text):
        raise TypeError("make_menu_images requires the project's pixel text callback")
    root_path = Path(root)
    return {
        "title": _draw_title(root_path, text),
        "select": _draw_select(root_path, roster, text),
        "arenas": _draw_arenas(stages, text),
    }


__all__ = ["make_menu_images"]
