"""Original code-authored arcade menus for the native SNES interface.

The title uses original slanted bitmap lettering. Character selection puts a
Natural Earth world silhouette above a six-by-two roster, with the existing
64x80 profile and 32x40 portraits retained. The live C renderer owns player
markers, names, controls and confirmation. Arena landmark crops stay intact.

Public contract::

    make_menu_images(root, stages, roster, text) -> {
        "title": RGB 256x224 image,
        "select": RGB 256x224 image,
        "arenas": RGB 256x224 image,
    }

``text`` has the signature ``text(image, xy, words, color, scale=1,
center=False)``.  The function does not write files or mutate its inputs.
"""

import hashlib
import json
from pathlib import Path
import struct
from typing import Any, Callable, Mapping, Sequence

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


Size = tuple[int, int]
TextFn = Callable[..., Any]
W, H = 256, 224

# The native converter has its own per-tile palette reduction.  Keeping menu
# art within this compact family prevents a card or rule from becoming noisy
# after conversion while preserving a little SNES-era warm/cool contrast.
INK = (15, 12, 10)
ROYAL = (35, 28, 21)
BLUE = (48, 36, 25)
BLUE_LINE = (113, 83, 45)
BLUE_SOFT = (68, 51, 31)
WHITE = (255, 240, 206)
MUTED = (190, 165, 123)
GOLD = (244, 189, 81)
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


def _world(root: Path, size: Size, land, ocean, shore) -> Image.Image:
    """Rasterize the retained public-domain land data, never an invented map."""
    folder = root / "assets/art/menu/classic-v1"
    source = (folder / "world-land.geojson").read_bytes()
    metadata = json.loads((folder / "source.json").read_bytes())
    if hashlib.sha256(source).hexdigest() != metadata["sha256"]:
        raise ValueError("Classic menu world source differs from its recorded hash")
    data = json.loads(source)
    if data.get("type") != "FeatureCollection" or len(data["features"]) != 127:
        raise ValueError("Unexpected Natural Earth land inventory")
    im = Image.new("RGB", size, ocean)
    d = ImageDraw.Draw(im)
    width, height = size
    def project(point):
        longitude, latitude = point[:2]
        return (round((longitude + 180) / 360 * (width - 1)),
                round((85 - latitude) / 145 * (height - 1)))
    for x in range(0, width, max(1, width // 12)):
        d.line((x, 0, x, height - 1), fill=BLUE_SOFT)
    for y in range(0, height, max(1, height // 5)):
        d.line((0, y, width - 1, y), fill=BLUE_SOFT)
    for feature in data["features"]:
        geometry = feature["geometry"]
        if geometry["type"] == "Polygon":
            polygons = [geometry["coordinates"]]
        elif geometry["type"] == "MultiPolygon":
            polygons = geometry["coordinates"]
        else:
            raise ValueError("Land must contain polygon geometry")
        for polygon in polygons:
            for index, ring in enumerate(polygon):
                d.polygon([project(point) for point in ring],
                          fill=land if index == 0 else ocean,
                          outline=shore if index == 0 else None)
    return im


def _arcade_word(im: Image.Image, text_fn: TextFn, words: str,
                 y: int, scale: int, top=WHITE, bottom=GOLD) -> None:
    """Original glyphs with a pixel slant, warm gradient and short extrusion."""
    height = 7 * scale
    slant = height // 4
    mask = Image.new("L", (len(words) * 6 * scale + slant + 8, height + 8))
    flat = Image.new("L", mask.size)
    text_fn(flat, (2, 2), words, 255, scale=scale)
    for row in range(height + 4):
        offset = max(0, (height + 1 - row) // 4)
        mask.paste(flat.crop((0, row, flat.width - offset, row + 1)), (offset, row))
    x = (W - mask.width) // 2
    outline = mask.filter(ImageFilter.MaxFilter(3))
    for dx, dy in ((4, 5), (3, 4), (2, 3)):
        im.paste((139, 48, 28), (x + dx, y + dy), outline)
    im.paste(INK, (x, y), outline)
    color = Image.new("RGB", mask.size)
    d = ImageDraw.Draw(color)
    for row in range(mask.height):
        t = min(1.0, max(0.0, (row - 2) / max(1, height - 1)))
        rgb = tuple(round(top[k] * (1 - t) + bottom[k] * t) for k in range(3))
        d.line((0, row, color.width - 1, row), fill=rgb)
    im.paste(color, (x, y), mask)


def _title(root: Path, text_fn: TextFn) -> Image.Image:
    im = _gradient((37, 29, 19), (11, 10, 9))
    im.paste(_world(root, (224, 90), (61, 46, 27), (28, 23, 17), (94, 70, 36)), (16, 16))
    _arcade_word(im, text_fn, "ABAQUS", 25, 5, (255, 246, 187), (239, 146, 40))
    _arcade_word(im, text_fn, "AFTER HOURS", 75, 2, WHITE, GOLD)
    _text(text_fn, im, (128, 114), "OFFICE FIGHTERS", MUTED, center=True)
    _rule(im, (48, 133, 207, 133), GOLD_DARK)
    # Plain live mode rows at 18/20/22 evoke the console title menu.
    _rule(im, (48, 187, 207, 187), BLUE_SOFT)
    _rule(im, (8, 210, 247, 210), BLUE_LINE)
    return im


def _portrait(item: Mapping[str, Any]) -> Image.Image:
    portrait = item.get("portrait")
    if isinstance(portrait, Image.Image):
        return portrait.convert("RGB").resize((32, 40), Image.Resampling.NEAREST)
    return Image.new("RGB", (32, 40), BLUE)


def _select(root: Path, roster: Sequence[Mapping[str, Any]], text_fn: TextFn) -> Image.Image:
    im = _gradient((33, 27, 20), (12, 10, 9))
    d = ImageDraw.Draw(im)
    _arcade_word(im, text_fn, "PLAYER SELECT", 3, 2)
    im.paste(_world(root, (160, 56), (124, 94, 48), (30, 25, 18), (187, 145, 73)), (88, 32))
    d.rectangle((7, 23, 72, 104), outline=BLUE_LINE)
    _rule(im, (88, 92, 247, 92), BLUE_LINE)
    # Six by two, 40x56 cells. The 12px top inset reserves a separate badge
    # row, so the 1P/2P labels never cover the retained 32x40 portrait pixels.
    for n in range(12):
        col, row = n % 6, n // 6
        x, y = 8 + col * 40, 104 + row * 56
        d.rectangle((x, y, x + 39, y + 55), fill=ROYAL, outline=BLUE_LINE)
        im.paste(_portrait(roster[n] if n < len(roster) else {}), (x + 4, y + 12))
    return im


ARENA_PREVIEW_CROPS = (
    (0, 64, 256, 192),  # Current Las Condes: 140 sign, entrance and paving seam.
    (0, 64, 256, 192),  # Current El Castillo: patio gathering, garden and grass.
    (0, 64, 256, 192),  # Current La Oficina: skyline, desks and carpet seam.
)


def _stage_preview(stage: Image.Image, stage_index: int) -> Image.Image:
    source = _rgb_image(stage)
    # Whole scenes at 60 pixels wide turn fine pixel textures into scattered
    # samples. Give each location a wider, aspect-correct landmark view and
    # average the source pixels before the SNES palette conversion. Every crop
    # is exactly 2:1, matching the 104x52 destination without stretching.
    landmark = source.crop(ARENA_PREVIEW_CROPS[stage_index])
    return landmark.resize((104, 52), Image.Resampling.BOX)


def native_stage_previews(root: str | Path, ui_palette, prepared=None) -> list[Image.Image]:
    """Use current converted BG1 bytes, including its 16px camera gutters.

    Menu generation runs before the final stage install on a clean build.
    Rebuild those deterministic payloads in memory instead of reading stale
    generated PNGs or the historical cartoon-stage masters.
    """
    from stage_depth_assets import stage_payload, colors
    root = Path(root)
    records = json.loads((root / 'assets/art/stages/depth-v1/stages.json').read_bytes())
    if records.get('schema') != 1 or records.get('scope') != 'stage-depth-v1':
        raise ValueError('unknown current arena-preview stage source')
    if [r['id'] for r in records['stages']] != [0, 1, 2]:
        raise ValueError('arena previews require all three current stages')
    result = []
    for record in records['stages']:
        payload, _, metadata = stage_payload(root, record, ui_palette, prepared)
        name = 'stage' + str(record['id'])
        gfx, raw_map, raw_palette = (payload[name + suffix] for suffix in ('_tiles.bin', '_map.bin', '_pal.bin'))
        if len(raw_map) != 4096 or len(raw_palette) != 192 or len(gfx) > 0x7000:
            raise ValueError('current preview exceeds its native BG1 contract')
        entries = struct.unpack('<2048H', raw_map)
        palette = colors(raw_palette)
        viewport = Image.new('RGB', (256, 224))
        cache = {}
        for y in range(28):
            for x in range(32):
                column = x + 2  # center viewport x16..271 of the 288px scene
                entry = entries[(column // 32) * 1024 + y * 32 + column % 32]
                if entry not in cache:
                    if entry == 0 and gfx[:32] == bytes(32):
                        # The five HUD-covered top rows deliberately use the
                        # transparent tile in map palette zero.
                        cache[entry] = Image.new('RGB', (8, 8))
                        viewport.paste(cache[entry], (x * 8, y * 8))
                        continue
                    index, bank = entry & 1023, ((entry >> 10) & 7) - 2
                    if not (0 <= bank < 6 and (index + 1) * 32 <= len(gfx)):
                        raise ValueError('current arena preview references an invalid tile or palette')
                    tile = gfx[index * 32:(index + 1) * 32]
                    pixels = []
                    for yy in range(8):
                        row = 7 - yy if entry & 0x8000 else yy
                        for xx in range(8):
                            bit = xx if entry & 0x4000 else 7 - xx
                            value = sum(((tile[(plane // 2) * 16 + row * 2 + plane % 2] >> bit) & 1) << plane
                                        for plane in range(4))
                            pixels.append(palette[bank * 16 + value])
                    image = Image.new('RGB', (8, 8))
                    image.putdata(pixels)
                    cache[entry] = image
                viewport.paste(cache[entry], (x * 8, y * 8))
        if metadata['viewport'] != [16, 0, 272, 224]:
            raise ValueError('review arena crop for a changed native viewport')
        result.append(viewport)
    return result


def _arenas(stages: Sequence[Image.Image], text_fn: TextFn) -> Image.Image:
    im = _gradient((33, 27, 20), (12, 10, 9))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 255, 35), fill=INK)
    _text(text_fn, im, (8, 7), "SELECT ARENA", WHITE, scale=2, shadow=True)
    _text(text_fn, im, (8, 25), "CHOOSE A LOCATION", MUTED, shadow=True)
    _rule(im, (8, 35, 247, 35), GOLD_DARK)

    # Three landmark-preview rows line up with drawArenas()'s existing cursor:
    # x=8, y=40/96/152, width=240 and height=56.  Keeping that geometry lets
    # the gold native cursor frame each choice without covering the image.
    names = ("LAS CONDES", "EL CASTILLO", "LA OFICINA")
    subtitles = ("GLASS LOBBY", "GARDEN PATIO", "TRADING DESKS")
    for i in range(3):
        y = 40 + i * 56
        d = ImageDraw.Draw(im)
        d.rectangle((8, y, 247, y + 55), fill=ROYAL, outline=BLUE_LINE)
        stage = stages[i] if i < len(stages) else Image.new("RGB", (W, H), BLUE)
        thumb = _stage_preview(stage, i)
        # The cursor's glyph 154 owns the first and last pixel rows of the
        # 56-pixel row.  Keep a two-pixel buffer so gold never crosses scene
        # detail when the native cursor is published over this plate.
        im.paste(thumb, (18, y + 2))
        d = ImageDraw.Draw(im)
        d.rectangle((17, y + 1, 122, y + 54), outline=INK)
        _rule(im, (130, y + 7, 130, y + 48), BLUE_SOFT)
        _text(text_fn, im, (140, y + 12), names[i], WHITE, shadow=True)
        _text(text_fn, im, (140, y + 31), subtitles[i], MUTED, shadow=True)

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
