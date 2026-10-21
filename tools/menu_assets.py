"""Small, code-authored menu plates for the native SNES interface.

The menu plates intentionally stay quiet.  The live C renderer owns the
cursor, labels and selected profile portrait; this module supplies a dark
royal-blue field, a few one-pixel rules, and enough breathing room for those
elements to remain readable on a CRT.  All lettering still comes from the
project's bitmap glyph callback.

Public contract::

    make_menu_images(root, stages, roster, text) -> {
        "title": RGB 256x224 image,
        "select": RGB 256x224 image,
        "arenas": RGB 256x224 image,
    }

``text`` has the signature ``text(image, xy, words, color, scale=1,
center=False)``.  The function does not write files or mutate its inputs.
"""

from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from PIL import Image, ImageDraw, ImageEnhance, ImageOps


Size = tuple[int, int]
TextFn = Callable[..., Any]
W, H = 256, 224

# The native converter has its own per-tile palette reduction.  Keeping menu
# art within this compact family prevents a card or rule from becoming noisy
# after conversion while preserving a little SNES-era warm/cool contrast.
INK = (4, 9, 25)
ROYAL = (8, 18, 50)
BLUE = (13, 31, 73)
BLUE_LINE = (38, 65, 112)
BLUE_SOFT = (24, 47, 93)
WHITE = (246, 242, 220)
MUTED = (154, 169, 197)
GOLD = (238, 190, 58)
GOLD_DARK = (126, 78, 24)


def _rgb_image(image: Image.Image, size: Size = (W, H)) -> Image.Image:
    """Return a detached RGB image at the native menu size."""

    return image.convert("RGB").resize(size, Image.Resampling.NEAREST)


def _gradient(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / float(H - 1)
        color = tuple(int(top[k] * (1.0 - t) + bottom[k] * t) for k in range(3))
        d.line((0, y, W - 1, y), fill=color)
    return im


def _quiet_backdrop(root: Path, amount: float = 0.10) -> Image.Image:
    """Use only a faint trace of the supplied title master, if present.

    The old generated backdrop is deliberately kept almost invisible.  The
    menus should read as a flat arcade interface rather than a photograph
    behind text, while the title still has a little depth when viewed on a
    modern display.
    """

    base = _gradient((14, 29, 70), (3, 8, 24))
    source_path = root / "assets" / "art" / "menu" / "title-backdrop.png"
    if not source_path.exists():
        return base
    try:
        source = Image.open(source_path).convert("RGB").resize((W, H), Image.Resampling.BILINEAR)
        source = ImageEnhance.Brightness(source).enhance(0.18)
        source = ImageEnhance.Color(source).enhance(0.35)
        return Image.blend(base, source, max(0.0, min(0.18, amount)))
    except (OSError, ValueError):
        return base


def _text(text_fn: TextFn, im: Image.Image, xy: tuple[int, int], words: str,
          color: tuple[int, int, int], scale: int = 1, center: bool = False,
          shadow: bool = False) -> None:
    """Draw a crisp glyph label, with a restrained one-pixel shadow."""

    if shadow:
        text_fn(im, (xy[0] + 1, xy[1] + 1), words, INK, scale=scale, center=center)
    text_fn(im, xy, words, color, scale=scale, center=center)


def _rule(im: Image.Image, xy: tuple[int, int, int, int], color=BLUE_LINE) -> None:
    ImageDraw.Draw(im).line(xy, fill=color, width=1)


def _title(root: Path, text_fn: TextFn) -> Image.Image:
    im = _quiet_backdrop(root, 0.08)
    d = ImageDraw.Draw(im)

    # A barely-there horizon and low band give the title a stable baseline;
    # native rows 20/22/24 remain open for the live menu labels.
    d.rectangle((0, 143, 255, 223), fill=(5, 11, 31))
    _rule(im, (18, 143, 237, 143), BLUE_LINE)
    _rule(im, (25, 205, 230, 205), BLUE_SOFT)

    _text(text_fn, im, (128, 31), "ABAQUS", GOLD, scale=4, center=True, shadow=True)
    _text(text_fn, im, (128, 73), "AFTER HOURS", WHITE, scale=2, center=True, shadow=True)
    _rule(im, (78, 96, 178, 96), GOLD)
    _text(text_fn, im, (128, 111), "OFFICE WORLD WARRIORS", MUTED, center=True)

    # These are simple wells, rather than separate cards.  drawTitle() writes
    # its rows on top of them and keeps the cursor legible in either state.
    for y in (155, 171, 187):
        d.rectangle((24, y, 231, y + 12), fill=ROYAL)
        _rule(im, (25, y, 230, y), BLUE_SOFT)
        _rule(im, (25, y + 12, 230, y + 12), INK)
    _text(text_fn, im, (128, 213), "PRESS START", MUTED, center=True)
    return im.convert("RGB")


def _portrait(item: Mapping[str, Any]) -> Image.Image:
    portrait = item.get("portrait")
    if isinstance(portrait, Image.Image):
        return portrait.convert("RGB").resize((32, 40), Image.Resampling.NEAREST)
    return Image.new("RGB", (32, 40), BLUE)


def _select(root: Path, roster: Sequence[Mapping[str, Any]], text_fn: TextFn) -> Image.Image:
    # A flat field lets the portraits and the native cursor do the work.
    im = _gradient((8, 19, 49), (3, 8, 24))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 255, 39), fill=INK)
    d.rectangle((175, 40, 255, 207), fill=(5, 12, 34))
    _rule(im, (8, 39, 167, 39), BLUE_LINE)
    _rule(im, (175, 40, 175, 207), BLUE_LINE)

    _text(text_fn, im, (8, 9), "SELECT FIGHTER", WHITE, scale=2, shadow=True)

    # Four by three, 40x48 cells.  The portrait remains inset by four pixels;
    # the native 5x6-tile cursor occupies the outer cell origin.
    for n in range(12):
        col, row = n % 4, n // 4
        x, y = 8 + col * 40, 48 + row * 48
        d.rectangle((x, y, x + 39, y + 47), fill=ROYAL, outline=BLUE_LINE)
        im.paste(_portrait(roster[n] if n < len(roster) else {}), (x + 4, y + 4))
    # Right portrait is filled by the native BG2 portrait DMA at (184,48).
    d = ImageDraw.Draw(im)
    d.rectangle((183, 47, 248, 129), fill=INK, outline=BLUE_LINE)
    _rule(im, (183, 131, 248, 131), BLUE_LINE)
    # Live name/special/footer rows have a clear, quiet surface underneath.
    _rule(im, (8, 198, 248, 198), BLUE_LINE)
    _rule(im, (8, 210, 248, 210), BLUE_LINE)
    return im.convert("RGB")


def _stage_preview(stage: Image.Image) -> Image.Image:
    source = _rgb_image(stage)
    # The arena picker uses complete, aspect-correct scene thumbnails.  The
    # old 224x48 crop threw away the sky, architecture and floor, and then
    # stretched the remaining strip across a caption card.  A 256x224 source
    # fits inside the inset 60x52 box, so every thumbnail keeps the authored
    # 8:7 geometry and remains recognizable after native tile quantization.
    fitted = ImageOps.contain(source, (60, 52), method=Image.Resampling.NEAREST)
    thumb = Image.new("RGB", (60, 52), ROYAL)
    thumb.paste(fitted, ((60 - fitted.width) // 2, (52 - fitted.height) // 2))
    return thumb


def _arenas(stages: Sequence[Image.Image], text_fn: TextFn) -> Image.Image:
    im = _gradient((9, 21, 52), (3, 8, 24))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 255, 35), fill=INK)
    _text(text_fn, im, (8, 7), "SELECT ARENA", WHITE, scale=2, shadow=True)
    _text(text_fn, im, (8, 25), "CHOOSE A LOCATION", MUTED, shadow=True)
    _rule(im, (8, 35, 247, 35), GOLD_DARK)

    # Three complete-scene rows line up with drawArenas()'s existing cursor:
    # x=8, y=40/96/152, width=240 and height=56.  Keeping that geometry lets
    # the gold native cursor frame each choice without covering the image.
    names = ("LAS CONDES", "EL CASTILLO", "LA OFICINA")
    subtitles = ("CITY GLASS", "PARTY PATIO", "LATE SHIFT")
    for i in range(3):
        y = 40 + i * 56
        d = ImageDraw.Draw(im)
        d.rectangle((8, y, 247, y + 55), fill=ROYAL, outline=BLUE_LINE)
        stage = stages[i] if i < len(stages) else Image.new("RGB", (W, H), BLUE)
        thumb = _stage_preview(stage)
        # The cursor's glyph 154 owns the first and last pixel rows of the
        # 56-pixel row.  Keep a two-pixel buffer so gold never crosses scene
        # detail when the native cursor is published over this plate.
        im.paste(thumb, (18, y + 2))
        d = ImageDraw.Draw(im)
        d.rectangle((17, y + 1, 78, y + 54), outline=INK)
        _rule(im, (88, y + 7, 88, y + 48), BLUE_SOFT)
        _text(text_fn, im, (100, y + 12), names[i], WHITE, shadow=True)
        _text(text_fn, im, (100, y + 31), subtitles[i], MUTED, shadow=True)

    # The native cursor owns the warm selection accent.  Keep the bottom
    # control row quiet and outside the three 56-pixel choices.
    _rule(im, (8, 210, 248, 210), BLUE_LINE)
    _text(text_fn, im, (128, 213), "UP / DOWN   A OK   B BACK", MUTED, center=True)
    return im.convert("RGB")


def make_menu_images(root: str | Path, stages: Sequence[Image.Image],
                     roster: Sequence[Mapping[str, Any]], text: TextFn) -> dict[str, Image.Image]:
    """Compose title, fighter-select and arena-select plates."""

    if not callable(text):
        raise TypeError("make_menu_images requires the project's pixel text callback")
    root_path = Path(root)
    return {
        "title": _title(root_path, text),
        "select": _select(root_path, roster, text),
        "arenas": _arenas(stages, text),
    }


__all__ = ["make_menu_images"]
