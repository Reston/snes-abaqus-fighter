"""Deterministic, head-safe framing for the select-screen portraits.

The fighter masters are full-body illustrations whose first idle figure is not
an ordinary portrait crop.  ``ImageOps.fit`` on a guessed upper-body rectangle
can crop a profile nose or the side of a head when the source is wide.  This
module keeps one source crop for both native portrait sizes, chooses that crop
from the upper silhouette, and uses contain-style nearest-neighbour scaling on
an opaque navy backdrop.

The helper deliberately does not alter a fighter master.  The caller passes
the already extracted idle RGBA figure and receives RGB 32x40 and 64x80
portraits plus framing metadata suitable for a generated-manifest regression
check.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw


PORTRAIT_SIZE = (32, 40)
PORTRAIT_LARGE_SIZE = (64, 80)
NAVY_BACKDROP = (4, 15, 38)

# The top silhouette is a stable, source-independent head anchor for the
# authored idle figures.  The wider portrait window is taken below it, so the
# complete crown/face/ear is retained while lower legs and spare arms may be
# dropped.  A little extra width is reserved on each side for a profile nose
# and hair edge; the face direction in the authored masters is right-facing.
HEAD_ANCHOR_FRACTION = 0.16
PORTRAIT_CROP_FRACTION = 0.56
HEAD_MARGIN_FRACTION = 0.045


def _alpha_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    """Return a non-empty alpha box, rejecting an unusable transparent source."""

    rgba = image.convert("RGBA")
    box = rgba.getchannel("A").getbbox()
    if not box:
        raise ValueError("portrait source has no opaque pixels")
    return box


def _upper_anchor(image: Image.Image, fraction: float = HEAD_ANCHOR_FRACTION):
    """Find the head anchor from the highest opaque silhouette rows.

    The extracted idle figures are tightly cropped, so the top 16 percent is
    the crown/face region before the hands and torso widen the silhouette.  A
    bbox rather than a fixed source coordinate keeps this usable for masters
    with different canvas sizes and body proportions.
    """

    rgba = image.convert("RGBA")
    width, height = rgba.size
    rows = max(1, min(height, round(height * fraction)))
    box = rgba.getchannel("A").crop((0, 0, width, rows)).getbbox()
    if not box:
        box = _alpha_bbox(rgba)
    left, top, right, bottom = box
    return (left, top, right, bottom)


def _composition_box(image: Image.Image):
    """Choose one source crop that contains the complete upper head region."""

    rgba = image.convert("RGBA")
    width, height = rgba.size
    head_left, head_top, head_right, head_bottom = _upper_anchor(rgba)

    # Keep the output aspect exactly 32:40 (and therefore 64:80).  The crop is
    # tall enough to show shoulders/upper jacket but does not spend portrait
    # pixels on the full-body stance.
    crop_height = max(head_bottom + 1, round(height * PORTRAIT_CROP_FRACTION))
    crop_height = min(height, crop_height)
    crop_width = max(1, round(crop_height * PORTRAIT_SIZE[0] / PORTRAIT_SIZE[1]))

    # Very broad top silhouettes can still be the result of a hand crossing
    # the head.  Increase the source window only as needed to keep the authored
    # head anchor inside it; never solve a wide source by clipping its edge.
    head_width = head_right - head_left
    safety = max(2, round(width * HEAD_MARGIN_FRACTION))
    needed_width = head_width + safety * 2
    if needed_width > crop_width:
        crop_width = min(width, needed_width)
        crop_height = min(height,
                           max(crop_height,
                               round(crop_width * PORTRAIT_SIZE[1] /
                                     PORTRAIT_SIZE[0])))
        crop_width = max(crop_width,
                         round(crop_height * PORTRAIT_SIZE[0] /
                               PORTRAIT_SIZE[1]))
        crop_width = min(width, crop_width)

    # Bias a few source pixels toward the face/nose while retaining both sides
    # of the top silhouette.  This is deliberately bounded, so it cannot make
    # the head safe on one side by clipping it on the other.
    anchor_x = (head_left + head_right) / 2.0 + width * 0.035
    left = round(anchor_x - crop_width / 2.0)
    left = max(0, min(left, width - crop_width))

    # Recenter to include the complete head anchor with its margin.  The second
    # clamp is important for Reston/David-style profiles near the right edge.
    if left > head_left - safety:
        left = head_left - safety
    if left + crop_width < head_right + safety:
        left = head_right + safety - crop_width
    left = max(0, min(left, width - crop_width))

    top = 0
    right = left + crop_width
    bottom = crop_height
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise ValueError(f"invalid portrait composition box {(left, top, right, bottom)}")

    # The top silhouette is the conservative head contract.  If this fails,
    # refuse to emit a portrait instead of silently clipping an authored face.
    if left > head_left or right < head_right:
        raise ValueError(
            f"portrait crop would clip head anchor {(head_left, head_top, head_right, head_bottom)}"
        )
    return (left, top, right, bottom), (head_left, head_top, head_right, head_bottom)


def _rasterize(source: Image.Image, crop_box, size, backdrop):
    """Contain a shared crop into a native portrait using nearest pixels."""

    rgba = source.convert("RGBA").crop(crop_box)
    # Leave a small, deliberate navy margin around the head.  The available
    # content box keeps the crop ratio intact, so small and large portraits
    # remain the same composition at different native scales.
    margin_x = max(1, round(size[0] * 0.03125))
    margin_y = max(1, round(size[1] * 0.025))
    available = (max(1, size[0] - margin_x * 2),
                 max(1, size[1] - margin_y * 2))
    scale = min(available[0] / rgba.width, available[1] / rgba.height)
    figure_size = (max(1, round(rgba.width * scale)),
                   max(1, round(rgba.height * scale)))
    figure = rgba.resize(figure_size, Image.Resampling.NEAREST)
    result = Image.new("RGB", size, tuple(backdrop))
    offset = ((size[0] - figure.width) // 2,
              (size[1] - figure.height) // 2)
    result.paste(figure, offset, figure.getchannel("A"))
    return result, {
        "content_box": [offset[0], offset[1],
                         offset[0] + figure.width, offset[1] + figure.height],
        "padding": [offset[0], offset[1],
                     size[0] - offset[0] - figure.width,
                     size[1] - offset[1] - figure.height],
        "scale": scale,
    }


def build_portrait_pair(source: Image.Image,
                        *,
                        backdrop=NAVY_BACKDROP,
                        full_head=False):
    """Return both native sizes and framing for an idle figure or head master.

    ``source`` may be any RGBA extracted idle figure.  Both portraits use the
    exact same source crop and composition anchor.  The result dictionary is
    intentionally serializable except for the two PIL images, making it easy
    for the parent asset pipeline to attach ``framing`` to its manifest entry.
    """

    rgba = source.convert("RGBA")
    # A separately authored and pinned head master already contains the entire
    # portrait composition. Do not apply the full-body crop to it.
    if full_head:
        crop_box = head_box = _alpha_bbox(rgba)
    else:
        crop_box, head_box = _composition_box(rgba)
    left, top, right, bottom = crop_box
    head_left, head_top, head_right, head_bottom = head_box
    small, small_render = _rasterize(rgba, crop_box, PORTRAIT_SIZE, backdrop)
    large, large_render = _rasterize(rgba, crop_box, PORTRAIT_LARGE_SIZE, backdrop)
    metadata = {
        "schema": 1,
        "source_size": list(rgba.size),
        "source_alpha_box": list(_alpha_bbox(rgba)),
        "crop_box": list(crop_box),
        "head_anchor_box": list(head_box),
        "head_margin_source": {
            "left": head_left - left,
            "top": head_top - top,
            "right": right - head_right,
            "bottom": bottom - head_bottom,
        },
        "target_sizes": [list(PORTRAIT_SIZE), list(PORTRAIT_LARGE_SIZE)],
        "render": {"small": small_render, "large": large_render},
        "backdrop_rgb": list(backdrop),
        "resampling": "nearest",
        "shared_composition": True,
        "head_clipped": False,
        "source_figure": ("registered_head_master" if full_head
                          else "legacy_idle_frame0"),
    }
    return {
        "small": small,
        "large": large,
        "metadata": metadata,
    }


def build_roster_portraits(root: Path, output: Path):
    """Build an ignored review set from all current legacy idle masters.

    This CLI helper imports the existing extractor but does not modify the
    production generator or generated assets.  It is useful for visual review
    while the parent integrates ``build_portrait_pair`` into fighter_assets.
    """

    root = Path(root).resolve()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    tools_dir = Path(__file__).resolve().parent
    import sys
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    from fighter_assets import SLUGS, extract_atlas

    records = []
    sheet = Image.new("RGB", (4 * 96, 3 * 112), NAVY_BACKDROP)
    draw = ImageDraw.Draw(sheet)
    for fighter, slug in enumerate(SLUGS):
        atlas = root / f"assets/art/characters/{fighter:02}-{slug}/atlas.png"
        figures, _ = extract_atlas(atlas)
        pair = build_portrait_pair(figures[0])
        pair["small"].save(output / f"portrait{fighter:02}.png")
        pair["large"].save(output / f"portrait{fighter:02}-large.png")
        pair["small"].save(output / f"portrait{fighter:02}-thumbnail.png")
        x = (fighter % 4) * 96 + 16
        y = (fighter // 4) * 112 + 4
        sheet.paste(pair["large"], (x, y))
        draw.text(((fighter % 4) * 96 + 2, y + 82), f"{fighter:02} {slug}", fill=(255, 255, 255))
        records.append({"id": fighter, "slug": slug, **pair["metadata"]})
    sheet.save(output / "portrait-review.png")
    (output / "portrait-framing.json").write_text(
        json.dumps({"schema": 1, "portraits": records}, indent=2) + "\n",
        encoding="utf-8")
    return records


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--output", type=Path,
                        default=Path("build/portrait-review"))
    args = parser.parse_args(argv)
    build_roster_portraits(args.root, args.output)


if __name__ == "__main__":
    main()
