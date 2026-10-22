"""Deterministic hardware preparation of the original champion ending art.

No semantic artwork is authored here. Retain the built-in imagegen output and
exact prompt; crop to 8:7, sample at native resolution, reduce to 90 colors,
and store that native grid as a four-times RGB master.
"""
from pathlib import Path
import argparse
import hashlib
import json

from PIL import Image

RAW = "assets/art/menu/source-champion-v1/champion-raw-v1.png"
PROMPT = "assets/art/menu/source-champion-v1/generation-v1.json"
MASTER = "assets/art/menu/champion-ending-v1.png"
PROVENANCE = "assets/art/menu/champion-ending-v1.json"
RAW_SHA256 = "5de9abb1669e5c2c9a1c7ad40ae119c4e7392e4a55be72432bf0d3f627bfb62e"
CROP = (2, 2, 1338, 1171)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha256(path: Path) -> str:
    """Git stores JSON as LF; preserve the prompt while accepting host EOLs."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def prepare_native(root: Path) -> Image.Image:
    path = root / RAW
    if sha256(path) != RAW_SHA256:
        raise ValueError("Champion raw image does not match the retained original")
    with Image.open(path) as source:
        if source.mode != "RGB" or source.size != (1340, 1174):
            raise ValueError("Champion raw image must be the original RGB 1340x1174 output")
        native = source.crop(CROP).resize((256, 224), Image.Resampling.NEAREST)
    # The generated quiet field has tiny RGB variations, which otherwise
    # consume every BG1 tile as a unique pattern. Collapse only near-navy
    # palette shades globally; contours, trophy planes and composition stay
    # in place. This is hardware palette cleanup, not a painted art edit.
    navy = (17, 26, 61)
    native.putdata([navy if max(abs(pixel[k] - navy[k]) for k in range(3)) <= 12
                    else pixel for pixel in native.get_flattened_data()])
    return native.quantize(colors=90, method=Image.Quantize.MEDIANCUT,
                           dither=Image.Dither.NONE).convert("RGB")


def prepare_master(root: Path) -> None:
    native = prepare_native(root)
    master = root / MASTER
    native.resize((1024, 896), Image.Resampling.NEAREST).save(master)
    generation = json.loads((root / PROMPT).read_text(encoding="utf-8"))
    provenance = {
        "asset": MASTER, "version": "v1", "mode": "built-in imagegen",
        "purpose": "Original Office Champion ending; native integration concept accepted, human review pending",
        "raw_output_path": RAW, "raw_output_sha256": RAW_SHA256,
        "raw_output_default_path": "C:/Users/user/.codex/generated_images/01a160f4-3e59-7980-b2d2-8db765944eeb/exec-900efced-cd60-44b2-84c3-aa49d46849b2.png",
        "exact_generation_record": PROMPT, "generation_record_sha256": text_sha256(root / PROMPT),
        "generation_record_hash_comparison": "LF-normalized text; exact prompt string retained",
        "prompt": generation["prompt"], "transparent_background": False,
        "processing": {
            "source_size": [1340, 1174], "center_aspect_crop_xyxy": list(CROP),
            "cropped_size": [1336, 1169], "aspect": "8:7",
            "native_size": [256, 224], "native_resampling": "nearest-neighbor",
            "navy_palette_cleanup": {"rgb": [17, 26, 61], "max_channel_distance": 12,
                                     "operation": "collapse near-identical navy colors globally before quantization"},
            "palette": "Pillow MEDIANCUT, 90 colors, no dithering",
            "master_size": [1024, 896], "master_upscale": "4x nearest-neighbor",
            "semantic_edits": False,
        },
        "selected_final": {"path": MASTER, "sha256": sha256(master),
                           "size": [1024, 896], "mode": "RGB",
                           "colors": len(native.getcolors(256 * 224))},
        "review": {"native_integration_concept_accepted": True,
                   "human_art_approval": "pending", "public_release_certified": False},
    }
    (root / PROVENANCE).write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")


def load_champion(root: Path) -> Image.Image:
    """Validate retained provenance and return the unchanged native grid."""
    record = json.loads((root / PROVENANCE).read_text(encoding="utf-8"))
    if text_sha256(root / PROMPT) != record["generation_record_sha256"]:
        raise ValueError("Champion exact generation record changed")
    if sha256(root / MASTER) != record["selected_final"]["sha256"]:
        raise ValueError("Champion master hash changed")
    with Image.open(root / MASTER) as source:
        if source.mode != "RGB" or source.size != (1024, 896):
            raise ValueError("Champion master must be opaque RGB 1024x896")
        if source.getcolors(90) is None:
            raise ValueError("Champion master exceeds 90 colors")
        native = source.resize((256, 224), Image.Resampling.NEAREST)
        if source.tobytes() != native.resize(source.size, Image.Resampling.NEAREST).tobytes():
            raise ValueError("Champion master must preserve the exact 4x native grid")
    if native.tobytes() != prepare_native(root).tobytes():
        raise ValueError("Champion master does not reproduce from the retained raw output")
    return native


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-master", action="store_true")
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    if args.prepare_master:
        prepare_master(project)
    load_champion(project)
