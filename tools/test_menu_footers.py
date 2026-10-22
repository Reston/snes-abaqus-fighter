"""Bounded, silent native PPU/controller proof for the roster/arena hints.

Uses the pinned Snes9x libretro host without a window, audio device or game
memory writes. Outputs default to ignored build paths, not release evidence.
Run after Build.cmd --assets: python tools/test_menu_footers.py
For parent preservation, also pass --baseline-ref REF --baseline-rom PATH.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from emulator import Emulator, ROOT
import test_presentation as presentation
from test_champion import host_contract


ROSTER_HINT = "D-PAD SELECT A/START OK B BACK"
ARENA_HINT = "UP/DOWN A/START OK B BACK"
MODES = ("arcade", "versus", "training")


def verify_asset_preservation(baseline_ref: str) -> dict[str, object]:
    """Compare native binaries exactly and generated/source text after LF normalization."""
    paths = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", baseline_ref, "assets/generated"],
        cwd=ROOT, text=True).splitlines()
    presentation.check(len(paths) == 219, "baseline contains the exact 219 generated files", len(paths))
    tracked = subprocess.check_output(
        ["git", "ls-files", "assets/generated"], cwd=ROOT, text=True).splitlines()
    presentation.check(paths == tracked, "generated file inventory is unchanged")
    paths.append("tools/menu_assets.py")
    # One cat-file process avoids a shell and 220 separate Git invocations.
    blobs = subprocess.check_output(
        ["git", "cat-file", "--batch"], cwd=ROOT,
        input="".join(f"{baseline_ref}:{path}\n" for path in paths).encode())
    cursor = 0
    preserved = {}
    for path in paths:
        end = blobs.index(b"\n", cursor)
        header = blobs[cursor:end].split()
        presentation.check(len(header) == 3 and header[1] == b"blob",
                           "preservation reference resolves to a Git blob", path)
        size = int(header[2])
        original = blobs[end + 1:end + 1 + size]
        cursor = end + 2 + size
        actual = (ROOT / path).read_bytes()
        is_text = Path(path).suffix in (".asm", ".h", ".json", ".py")
        if is_text:
            actual, original = actual.replace(b"\r\n", b"\n"), original.replace(b"\r\n", b"\n")
        presentation.check(actual == original,
                           "regenerated asset/encoder matches parent with declared text comparison", path)
        preserved[path] = {"bytes": len(actual), "sha256": hashlib.sha256(actual).hexdigest(),
                           "comparison": "LF-normalized text" if is_text else "exact bytes"}
    return {"baseline_ref": baseline_ref, "generated_files": 219,
            "identical_generated_files": len(preserved) - 1, "files": preserved}


def menu_observations(rom: Path, directory: Path) -> dict[str, dict[str, object]]:
    """Collect all 60 roster choices and nine arena states using controllers."""
    directory.mkdir(parents=True, exist_ok=True)
    observed = {}

    def record(e: Emulator, key: str, bottom: int) -> None:
        assert e.frame is not None
        memory = presentation.vram_bytes(e)
        path = directory / f"{key}.png"
        e.frame.save(path)
        vram_path = directory / f"{key}.vram.bin"
        vram_path.write_bytes(memory)
        observed[key] = {
            "capture": path.resolve().relative_to(ROOT).as_posix(),
            "capture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "vram_capture": vram_path.resolve().relative_to(ROOT).as_posix(),
            "vram_sha256": hashlib.sha256(memory).hexdigest(),
            "preserved_pixel_bounds": [0, 0, 256, bottom],
            "pixels_sha256": hashlib.sha256(e.frame.crop((0, 0, 256, bottom)).tobytes()).hexdigest(),
            "bg1_tiles_and_map_sha256": hashlib.sha256(memory[:0x7800]).hexdigest(),
            "bg2_above_footer_sha256": hashlib.sha256(
                memory[presentation.BG2_MAP_BYTE:presentation.BG2_MAP_BYTE + bottom // 8 * 64]).hexdigest(),
        }

    for mode, name in enumerate(MODES):
        e = Emulator(rom)
        try:
            e.run(120)
            for _ in range(mode):
                presentation.press(e, "down")
            presentation.press(e, "a")
            presentation.wait_screen(e, presentation.SELECT)
            for scene in (("p1", "second") if mode else ("p1",)):
                field = "selected" if scene == "p1" else "selected2"
                for _ in range(12):
                    fighter = e.state()[field]
                    record(e, f"{name}-{scene}-{fighter:02}", 216)
                    presentation.press(e, "right")
                presentation.press(e, "start")
            presentation.wait_screen(e, presentation.ARENA)
            for arena in range(3):
                presentation.check(e.state()["arena"] == arena,
                                   "preservation probe visits each native arena row", name)
                record(e, f"{name}-arena-{arena}", 208)
                presentation.press(e, "down")
        finally:
            e.close()
    presentation.check(len(observed) == 69,
                       "native preservation covers every roster choice and arena in all modes", len(observed))
    return observed


def verify_native_preservation(baseline_rom: Path, directory: Path) -> dict[str, object]:
    baseline = menu_observations(baseline_rom, directory / "parent")
    candidate = menu_observations(ROOT / "dist/abaqus-after-hours.sfc", directory / "candidate")
    presentation.check(baseline.keys() == candidate.keys(), "parent/candidate native states match")
    proof = {}
    for key, original in baseline.items():
        current = candidate[key]
        # Compare actual RGB bytes as well as retaining their hashes for review.
        with Image.open(ROOT / original["capture"]) as parent, Image.open(ROOT / current["capture"]) as changed:
            bounds = tuple(current["preserved_pixel_bounds"])
            presentation.check(parent.crop(bounds).tobytes() == changed.crop(bounds).tobytes(),
                               "all actual native pixels above footer are exactly unchanged", key)
        for field in ("bg1_tiles_and_map_sha256", "bg2_above_footer_sha256"):
            presentation.check(original[field] == current[field],
                               "underlying native scene/cursor VRAM is exactly unchanged", {"scene": key, "field": field})
        proof[key] = {**current, "baseline": original}
    return {"baseline_rom_sha256": hashlib.sha256(baseline_rom.read_bytes()).hexdigest(),
            "roster_states": 60, "arena_states": 9, "pixel_difference_above_footer": 0,
            "capture_scope": "Retained baseline/candidate PNG and VRAM from controller-only runs; validation recomputes file bytes, preserved pixels and VRAM regions, not emulator execution.",
            "states": proof}


def verify_roster_footer(e: Emulator, label: str) -> dict[str, object]:
    x = presentation.centered_start(ROSTER_HINT)
    presentation.check(x >= 1 and x + len(ROSTER_HINT) <= 31,
                       "roster hint fits with a tile margin on both sides", {
                           "characters": len(ROSTER_HINT), "x": x,
                           "pixels": len(ROSTER_HINT) * 8,
                       })
    presentation.verify_menu_font_bank(e, [(27, x, ROSTER_HINT)], label)
    row = presentation.ui_row(e, 27)
    presentation.check(all((value & 0x3FF) == 0 for value in row[:x] +
                           row[x + len(ROSTER_HINT):]),
                       "roster footer keeps clear tile margins", label)

    # Compose the encoded select plate with the original transparent glyphs,
    # including their native shadow. This detects clipping in final PPU pixels.
    generated = ROOT / "assets/generated"
    with Image.open(generated / "select.png") as plate:
        expected = plate.convert("RGB").crop((0, 216, 256, 224))
    glyphs = (generated / "ui_tiles.bin").read_bytes()
    palette = (generated / "ui_pal.bin").read_bytes()
    memory = presentation.vram_bytes(e)
    for offset, character in enumerate(ROSTER_HINT):
        tile = ord(character)
        glyph = glyphs[tile * 32:(tile + 1) * 32]
        start = presentation.UI_TILE_VRAM_BYTE + tile * 32
        presentation.check(memory[start:start + 32] == glyph,
                           "roster hint uses the original native glyph bytes", {
                               "label": label, "character": character,
                           })
        for pixel, index in enumerate(presentation._tile_indices(glyph)):
            if index:
                color = int.from_bytes(palette[index * 2:index * 2 + 2], "little")
                expected.putpixel(((x + offset) * 8 + pixel % 8, pixel // 8),
                                  presentation.snes_rgb(color))
    assert e.frame is not None
    delta = presentation.image_delta(e.frame.crop((0, 216, 256, 224)), expected)
    presentation.check(delta["max_channel_delta"] <= 8,
                       "complete roster hint and margins reach the native PPU", {
                           "label": label, **delta,
                       })
    return {"text": ROSTER_HINT, "tile_x": x, "tile_row": 27, **delta}


def verify_arena_footer(e: Emulator) -> dict[str, object]:
    x = presentation.centered_start(ARENA_HINT)
    presentation.check(x >= 1 and x + len(ARENA_HINT) <= 31,
                       "arena hint fits with a tile margin on both sides", {
                           "text": ARENA_HINT, "tile_x": x,
                           "pixels": len(ARENA_HINT) * 8,
                       })
    presentation.verify_opaque_text_rows(e, [(27, x, ARENA_HINT)], "arena footer")
    generated = ROOT / "assets/generated"
    glyphs = (generated / "ui_tiles.bin").read_bytes()
    palette = (generated / "ui_pal.bin").read_bytes()
    memory = presentation.vram_bytes(e)
    # Compose all 64 cells independently of the candidate's actual BG2 map.
    # Opaque glyphs and panel margins must hide the old BG1 rule and lettering.
    expected = Image.new("RGB", (256, 16))
    seen = set()
    for row in (26, 27):
        wanted = [128] * 32
        if row == 27:
            wanted[x:x + len(ARENA_HINT)] = [256 + ord(c) for c in ARENA_HINT]
        presentation.check(presentation.ui_row(e, row) == [tile | 0x2000 for tile in wanted],
                           "arena footer owns only the two full BG2 panel rows", row)
        for cell, tile in enumerate(wanted):
            data = glyphs[tile * 32:(tile + 1) * 32]
            if tile not in seen:
                seen.add(tile)
                offset = presentation.UI_TILE_VRAM_BYTE + tile * 32
                presentation.check(memory[offset:offset + 32] == data and
                                   all(presentation._tile_indices(data)),
                                   "arena panel/glyph uses unchanged opaque native tile bytes", tile)
            expected.paste(presentation.tile_rgb(data, palette), (cell * 8, (row - 26) * 8))
    assert e.frame is not None
    delta = presentation.image_delta(e.frame.crop((0, 208, 256, 224)), expected)
    presentation.check(delta["max_channel_delta"] <= 8,
                       "entire arena panel and hint reach native PPU without BG1 bleed", delta)
    # Read only the original glyph literal; importing make_assets rebuilds assets.
    # Match every bright footer pixel independently of ui_tiles.bin and the map.
    source = ast.parse((ROOT / "tools/make_assets.py").read_text())
    glyphs = next(ast.literal_eval(node.value) for node in source.body
                  if isinstance(node, ast.Assign) and
                  any(isinstance(target, ast.Name) and target.id == "GLYPHS"
                      for target in node.targets))
    mask = Image.new("1", (256, 16))
    for offset, character in enumerate(ARENA_HINT):
        for y, row in enumerate(glyphs.get(character, [])):
            for x, bit in enumerate(row):
                if bit == "1":
                    mask.putpixel(((presentation.centered_start(ARENA_HINT) + offset) * 8 + x + 1,
                                   8 + y), 1)
    actual_mask = [int(max(pixel) > 100) for pixel in
                   e.frame.crop((0, 208, 256, 224)).convert("RGB").get_flattened_data()]
    presentation.check(actual_mask == list(mask.get_flattened_data()),
                       "arena PPU spells the explicit A/START OK hint in original glyphs")
    return {"text": ARENA_HINT, "tile_x": presentation.centered_start(ARENA_HINT),
            "tile_row": 27, "panel_pixel_bounds": [0, 208, 256, 224], **delta}


def capture(e: Emulator, directory: Path, name: str) -> dict[str, str]:
    presentation.check(e.frame is not None and e.frame.size == (256, 224),
                       "footer capture is an actual native 256x224 frame", name)
    assert e.frame is not None
    path = directory / name
    e.frame.save(path)
    return {"capture": path.resolve().relative_to(ROOT).as_posix(),
            "capture_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def boot_roster(mode: int) -> Emulator:
    e = Emulator()
    try:
        e.run(120)
        for _ in range(mode):
            presentation.press(e, "down")
        presentation.press(e, "a")
        presentation.wait_screen(e, presentation.SELECT)
        return e
    except BaseException:
        e.close()
        raise


def footer_captures(directory: Path) -> dict[str, object]:
    result = {}
    for mode, name in enumerate(MODES):
        e = boot_roster(mode)
        try:
            entry = {"p1": verify_roster_footer(e, name + " P1")}
            entry["p1"].update(capture(e, directory, name + "-p1.png"))
            presentation.press(e, "start")
            if mode:
                heading = "DUMMY" if mode == 2 else "PLAYER 2"
                presentation.verify_menu_font_bank(e, [(4, 23, heading)], heading)
                entry["second"] = verify_roster_footer(e, heading)
                entry["second"].update(capture(e, directory, name + "-second.png"))
                # P2 and DUMMY accept the second physical controller.
                presentation.press(e, "start", 1)
            presentation.wait_screen(e, presentation.ARENA)
            entry["arenas"] = []
            for arena in range(3):
                if arena:
                    presentation.press(e, "down")
                presentation.check(e.state()["arena"] == arena,
                                   "arena UP/DOWN hint matches native navigation", e.state())
                presentation.verify_arena_cursor(e, arena)
                presentation.verify_arena_plate(e, arena)
                footer = verify_arena_footer(e)
                footer.update(capture(e, directory, f"{name}-arena-{arena}.png"))
                entry["arenas"].append(footer)
            presentation.press(e, "up")
            presentation.check(e.state()["arena"] == 1,
                               "arena UP returns to the preceding row", e.state())
            result[name] = entry
        finally:
            e.close()
    return result


def controller_actions() -> list[dict[str, object]]:
    results = []
    # Both advertised confirmations, Back, and simultaneous priority. Each
    # scene must consume one action, including P2/DUMMY on either controller.
    cases = ((["a"], True), (["start"], True), (["b"], False),
             (["b", "a"], False), (["start", "b", "a"], True))
    for mode, name in enumerate(MODES):
        steps = [("p1", 0)]
        if mode:
            steps.extend((("second", 0), ("second", 1)))
        steps.append(("arena", 0))
        for scene, port in steps:
            for keys, confirms in cases:
                e = boot_roster(mode)
                try:
                    if scene != "p1":
                        presentation.press(e, "a")
                    if scene == "arena" and mode:
                        presentation.press(e, "a")
                    before = e.state()
                    e.run(12, **{"p1" if port == 0 else "p2": keys})
                    e.run(20)
                    after = e.state()
                    if scene == "arena":
                        wanted = presentation.FIGHT if confirms else presentation.SELECT
                    elif scene == "p1":
                        wanted = (presentation.SELECT if mode else presentation.ARENA) \
                            if confirms else presentation.TITLE
                    else:
                        wanted = presentation.ARENA if confirms else presentation.SELECT
                    presentation.check(after["screen"] == wanted,
                                       "footer actions preserve Start > B > A priority", {
                                           "mode": name, "scene": scene, "port": port,
                                           "keys": keys, "before": before, "after": after,
                                       })
                    if scene == "second" and not confirms:
                        presentation.verify_menu_font_bank(e, [(4, 23, "PLAYER 1")],
                                                           "Back returns once to P1")
                    elif scene == "p1" and mode and confirms:
                        heading = "DUMMY" if mode == 2 else "PLAYER 2"
                        presentation.verify_menu_font_bank(e, [(4, 23, heading)],
                                                           "confirm advances once")
                    results.append({"mode": name, "scene": scene, "port": port,
                                    "keys": keys, "screen": after["screen"]})
                finally:
                    e.close()
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "build/menu-footer-report.json")
    parser.add_argument("--captures", type=Path, default=ROOT / "build/menu-footer-captures")
    parser.add_argument("--baseline-ref", help="parent Git ref for exact 219-file/encoder preservation")
    parser.add_argument("--baseline-rom", type=Path, help="parent ROM for exact native-pixel preservation")
    args = parser.parse_args()
    args.captures.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    report = {"status": "failed", "emulator": "Official Snes9x 1.63 x64 libretro core",
              "scope": "Focused menu-footer PPU/controller proof; supplemental to the six native suites and release-scale gates",
              "controller_only": True, "memory_writes": False, "save_states": False,
              "host_contract": host_contract(),
              "harness_sha256": {
                  name: hashlib.sha256((ROOT / "tools" / name).read_bytes()).hexdigest()
                  for name in ("test_menu_footers.py", "test_presentation.py", "emulator.py",
                               "test_champion.py", "preservation.py")
              }}
    presentation.checks.clear()
    try:
        host = report["host_contract"]
        presentation.check(host.get("priority_class") == 0x4000 and
                           len(host.get("logical_processors", [])) == 2 and
                           host.get("gui_opened") is False and host.get("audio_device_opened") is False,
                           "focused proof stays silent and below normal on two logical CPUs", host)
        core = ROOT / ".tools/core/snes9x_libretro.dll"
        report["core_sha256"] = hashlib.sha256(core.read_bytes()).hexdigest()
        presentation.check(report["core_sha256"] ==
                           "f00db5bd97bbe0e80761e590449eb14716bd9ab5785a1b50725c55e10505c343",
                           "focused proof uses the pinned official Snes9x core")
        rom = (ROOT / "dist/abaqus-after-hours.sfc").read_bytes()
        report["rom_sha256"] = hashlib.sha256(rom).hexdigest()
        report["header_checksum"] = f"{int.from_bytes(rom[0x7FDE:0x7FE0], 'little'):04X}"
        manifest = json.loads((ROOT / "dist/manifest.json").read_text())
        presentation.check(len(rom) == 4 * 1024 * 1024 and
                           report["rom_sha256"] == manifest["sha256"],
                           "focused proof identifies the exact built 4 MiB native ROM")
        if args.baseline_ref:
            report["asset_preservation"] = verify_asset_preservation(args.baseline_ref)
        if args.baseline_rom:
            report["native_preservation"] = verify_native_preservation(args.baseline_rom, args.captures)
        report["captures"] = footer_captures(args.captures)
        report["controller_actions"] = controller_actions()
        report["status"] = "passed"
    except BaseException as exc:
        report["error"] = repr(exc)
        raise
    finally:
        report["checks"] = presentation.checks
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        args.report.write_text(json.dumps(report, indent=2) + "\n", newline="\n")
    print(json.dumps({key: report[key] for key in ("status", "rom_sha256", "elapsed_seconds")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
