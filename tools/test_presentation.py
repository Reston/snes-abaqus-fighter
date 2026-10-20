"""Silent, headless presentation checks for the v0.4 native menus and arenas.

This suite drives the actual cartridge through the official Snes9x libretro
core.  It checks title/select/arena state transitions, the four-by-three roster
navigation contract, selected portrait updates, and all three fight stages.
Frames are captured from the core's video callback for human review; no window
or audio device is opened and the host never writes emulated memory.

Run after the 4 MiB animation native build with::

    python tools/test_presentation.py
"""

from __future__ import annotations

import ctypes as C
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from emulator import Emulator, ROOT


TITLE, SELECT, ARENA, FIGHT = 0, 1, 2, 3
NAMES = (
    "DAMIAN", "IVO", "CRISTOBAL", "COTE", "NEGGER", "DAVID",
    "FERNANDO", "CRISTIAN", "MAMARIAGA", "RESTON", "ROXANA", "LARS",
)
STAGES = ("las-condes", "el-castillo", "la-oficina")
PORTRAIT_VRAM_WORD = 0x4A00
PORTRAIT_VRAM_BYTE = PORTRAIT_VRAM_WORD * 2
PORTRAIT_BYTES = 64 * 80 // 2
BG2_MAP_WORD = 0x5800
BG2_MAP_BYTE = BG2_MAP_WORD * 2
PORTRAIT_MAP_X = 23
PORTRAIT_MAP_Y = 6
PORTRAIT_TILE_BASE = 160
PORTRAIT_MAP_PALETTE = 1
checks: list[dict[str, object]] = []


def check(ok: bool, label: str, details: object | None = None) -> None:
    if not ok:
        raise AssertionError((label, details))
    checks.append({"check": label, "passed": True, "details": details})


def state(e: Emulator) -> dict[str, int]:
    return e.state()


def press(e: Emulator, key: str, port: int = 0) -> None:
    e.tap(key, port)
    e.run(20)


def wait_screen(e: Emulator, wanted: int, max_frames: int = 600) -> None:
    for _ in range(max_frames // 10):
        if state(e)["screen"] == wanted:
            e.run(10)
            return
        e.run(10)
    raise AssertionError(("screen did not arrive", wanted, state(e)))


def frame_digest(e: Emulator) -> str:
    check(e.frame is not None, "video callback produced a native frame")
    return hashlib.sha256(e.frame.tobytes()).hexdigest()


def capture(e: Emulator, name: str) -> Path:
    check(e.frame is not None, "capture has a native video frame", name)
    check(e.frame.size == (256, 224), "capture uses the SNES 256x224 frame", {
        "name": name, "size": e.frame.size,
    })
    check(len(e.frame.getcolors(256 * 224) or []) > 12,
          "capture is a populated presentation frame", name)
    path = ROOT / "docs/screenshots/presentation" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    e.frame.save(path)
    return path


def vram_bytes(e: Emulator) -> bytes:
    """Read the core's VRAM callback without modifying emulated memory."""

    pointer = e.core.retro_get_memory_data(3)
    size = e.core.retro_get_memory_size(3)
    return C.string_at(pointer, size)


def verify_large_portrait(e: Emulator, fighter: int) -> dict[str, object]:
    """Verify the selected 64x80 portrait transfer and its BG2 map anchor.

    The profile image is a native 8x10 tile block at VRAM word $4A00.  A
    whole-block comparison catches stale portraits that can look plausible in
    a generic frame digest, while the map check proves the renderer points
    BG2 at tile 160 with palette 1 at the documented (23,6) anchor.
    """

    memory = vram_bytes(e)
    expected_path = ROOT / "assets/generated" / f"portrait{fighter:02}_tiles.bin"
    check(expected_path.exists(), "native large portrait asset exists", {
        "fighter": fighter, "path": str(expected_path),
    })
    expected = expected_path.read_bytes()
    check(len(expected) == PORTRAIT_BYTES,
          "large portrait asset is an 8x10 tile block", {
              "fighter": fighter, "bytes": len(expected),
          })
    actual = memory[PORTRAIT_VRAM_BYTE:PORTRAIT_VRAM_BYTE + PORTRAIT_BYTES]
    check(actual == expected, "selected large portrait reaches BG2 VRAM exactly", {
        "fighter": fighter, "vram_word": hex(PORTRAIT_VRAM_WORD),
        "sha256": hashlib.sha256(actual).hexdigest(),
    })

    map_offset = BG2_MAP_BYTE + (PORTRAIT_MAP_Y * 32 + PORTRAIT_MAP_X) * 2
    entry = int.from_bytes(memory[map_offset:map_offset + 2], "little")
    tile = entry & 0x03FF
    palette = (entry >> 10) & 0x07
    check(tile == PORTRAIT_TILE_BASE and palette == PORTRAIT_MAP_PALETTE,
          "profile map anchor selects tile 160 with palette 1", {
              "fighter": fighter, "x": PORTRAIT_MAP_X, "y": PORTRAIT_MAP_Y,
              "entry": hex(entry), "tile": tile, "palette": palette,
          })
    return {"asset": str(expected_path), "sha256": hashlib.sha256(actual).hexdigest(),
            "map_entry": entry, "tile": tile, "palette": palette}


def optional_portrait_trace(e: Emulator, selected: int) -> None:
    """Validate optional trace aliases when the native UI exposes one."""

    values: list[tuple[str, int]] = []
    current = state(e)
    for key in (
        "portrait_id", "portrait", "hover_portrait", "select_portrait",
        "selected_portrait", "portrait_slot",
    ):
        if key in current:
            values.append((key, int(current[key])))
    for key, value in values:
        check(value == selected, "selection trace exposes the hovered portrait", {
            "field": key, "selected": selected, "value": value,
        })


def title_and_select() -> dict[str, object]:
    e = Emulator()
    try:
        e.run(120)
        check(state(e)["screen"] == TITLE, "cold boot reaches the redesigned home screen")
        title_path = capture(e, "title.png")
        initial_title = frame_digest(e)
        press(e, "r")
        check(state(e)["screen"] == TITLE, "title difficulty cycling keeps the home screen")
        check(frame_digest(e) != initial_title, "title difficulty state changes the rendered menu")
        press(e, "a")
        wait_screen(e, SELECT)

        check(state(e)["selected"] == 0, "roster opens on the first fighter")
        select_digests: dict[int, str] = {0: frame_digest(e)}
        portrait_paths: dict[str, str] = {"00": str(capture(e, "select-00.png"))}
        portrait_vram: dict[str, dict[str, object]] = {
            "00": verify_large_portrait(e, 0),
        }
        optional_portrait_trace(e, 0)

        # Horizontal movement covers every card and its wrap.  The expected
        # 4x3 visual grid is then exercised with +/-4 vertical steps.
        for expected in range(1, 12):
            press(e, "right")
            check(state(e)["selected"] == expected,
                  "roster horizontal navigation reaches slot " + str(expected + 1), {
                      "selected": state(e)["selected"],
                  })
            select_digests[expected] = frame_digest(e)
            portrait_paths[f"{expected:02}"] = str(capture(e, f"select-{expected:02}.png"))
            portrait_vram[f"{expected:02}"] = verify_large_portrait(e, expected)
            optional_portrait_trace(e, expected)
        press(e, "right")
        check(state(e)["selected"] == 0, "roster horizontal navigation wraps")

        press(e, "down")
        check(state(e)["selected"] == 4, "roster down moves one four-card row")
        select_digests[4] = frame_digest(e)
        press(e, "down")
        check(state(e)["selected"] == 8, "roster down reaches the third four-card row")
        press(e, "down")
        check(state(e)["selected"] == 0, "roster down wraps after the third row")
        press(e, "up")
        check(state(e)["selected"] == 8, "roster up wraps to the third row")
        press(e, "up")
        check(state(e)["selected"] == 4, "roster up moves one four-card row")
        press(e, "up")
        check(state(e)["selected"] == 0, "roster up returns to the first row")

        check(len(portrait_vram) == 12,
              "every fighter hover refreshes its exact large portrait block", {
                  "fighters": len(portrait_vram),
              })
        check(len(set(select_digests.values())) == len(select_digests),
              "each fighter hover has a distinct rendered large-profile state", {
                  "fighters": len(select_digests),
              })

        press(e, "a")
        wait_screen(e, ARENA)
        check(state(e)["arena"] == 0, "arena select opens on Las Condes")
        arena_paths: dict[str, str] = {}
        arena_digests: list[str] = []
        for index, stage in enumerate(STAGES):
            if index:
                press(e, "down")
            check(state(e)["arena"] == index, "arena cursor reaches row " + str(index + 1), {
                "arena": state(e)["arena"],
            })
            arena_digests.append(frame_digest(e))
            arena_paths[stage] = str(capture(e, f"arena-{index}.png"))
        press(e, "down")
        check(state(e)["arena"] == 0, "arena cursor wraps after the third row")
        return {
            "title": str(title_path), "portraits": portrait_paths,
            "portrait_vram": portrait_vram,
            "arena_select": arena_paths, "arena_digests": arena_digests,
        }
    finally:
        e.close()


def fight_stage_captures() -> dict[str, str]:
    captures: dict[str, str] = {}
    digests: dict[str, str] = {}
    for stage_index, stage in enumerate(STAGES):
        e = Emulator()
        try:
            e.run(120)
            press(e, "a")
            wait_screen(e, SELECT)
            press(e, "a")
            wait_screen(e, ARENA)
            for _ in range(stage_index):
                press(e, "down")
            press(e, "a")
            wait_screen(e, FIGHT)
            for _ in range(160):
                if state(e)["intro"] == 0:
                    break
                e.run(1)
            check(state(e)["intro"] == 0, "stage fight intro completes", {
                "stage": stage,
            })
            e.run(3)
            path = capture(e, f"stage-{stage_index}.png")
            captures[stage] = str(path)
            digests[stage] = frame_digest(e)
        finally:
            e.close()
    check(len(captures) == 3, "all three stage captures are saved", captures)
    check(len(set(digests.values())) == 3,
          "the three stage fights render distinct native architecture plates", digests)
    return captures


def main() -> int:
    started = time.time()
    report: dict[str, object] = {
        "emulator": "Official Snes9x 1.63 x64 libretro core",
        "rom_sha256": None, "rom_bytes": None, "status": "failed",
        "checks": checks, "captures": {},
    }
    try:
        manifest = json.loads((ROOT / "dist/manifest.json").read_text())
        report["rom_sha256"] = manifest.get("sha256")
        report["rom_bytes"] = manifest.get("bytes")
        check(manifest.get("bytes") == 4 * 1024 * 1024,
              "presentation build uses the 4 MiB animation ROM", manifest)
        report["captures"] = {
            "menus": title_and_select(),
            "stages": fight_stage_captures(),
        }
        report["status"] = "passed"
    except Exception as exc:
        report["error"] = repr(exc)
        raise
    finally:
        report["passed"] = len(checks)
        report["elapsed_seconds"] = round(time.time() - started, 2)
        (ROOT / "docs/presentation-test-report.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
    print(json.dumps({"status": report["status"], "passed": report["passed"],
                      "seconds": report["elapsed_seconds"],
                      "report": "docs/presentation-test-report.json"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
