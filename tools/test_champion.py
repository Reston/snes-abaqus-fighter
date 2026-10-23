"""Focused silent champion-ending proof through eleven real Arcade wins.

Only SNES controller actions drive this probe. VRAM/trace reads and actual
PPU frames prove the new scene. No memory writes, save states, native window,
or audio device. Run with the project's background launcher while gaming.
"""
from pathlib import Path
import argparse
import ctypes as C
import hashlib
import json
import os
import platform
import sys
import time

import PIL
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from emulator import Emulator, ROOT
import test_presentation as presentation


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check(ok, label, details=None):
    if not ok:
        raise AssertionError((label, details))


def host_contract():
    contract = {"python": platform.python_version(), "pillow": PIL.__version__,
                "gui_opened": False, "audio_device_opened": False}
    if os.name == "nt":
        kernel = C.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = C.c_void_p
        kernel.GetPriorityClass.argtypes = [C.c_void_p]
        kernel.GetProcessAffinityMask.argtypes = [C.c_void_p, C.POINTER(C.c_size_t), C.POINTER(C.c_size_t)]
        handle = kernel.GetCurrentProcess()
        process_mask, system_mask = C.c_size_t(), C.c_size_t()
        if not kernel.GetProcessAffinityMask(handle, C.byref(process_mask), C.byref(system_mask)):
            raise C.WinError(C.get_last_error())
        contract["priority_class"] = int(kernel.GetPriorityClass(handle))
        contract["logical_processors"] = [bit for bit in range(C.sizeof(C.c_size_t) * 8)
                                          if process_mask.value & (1 << bit)]
    return contract


def wait(e, screen, limit=600):
    for _ in range(limit // 10):
        if e.state()["screen"] == screen:
            e.run(15)
            return
        e.run(10)
    raise AssertionError(("screen did not arrive", screen, e.state()))


def press(e, key):
    e.tap(key)
    e.run(20)


def play_cpu(e):
    """Existing gameplay suite's controller-only close/guard/throw policy."""
    for _ in range(10000):
        s = e.state()
        if s["screen"] == 4:
            return
        forward = "right" if s["x1"] < s["x2"] else "left"
        back = "left" if forward == "right" else "right"
        distance = abs(s["x1"] - s["x2"]) // 16
        if s["intro"] or s["round_end"] or s["hitstop"]:
            e.run(1)
        elif s["action1"]:
            e.run(1, p1=[forward])
        elif s["action2"] and distance < 55:
            e.run(1, p1=[back, "down"] if 4 <= s["action2"] <= 6 else [back])
        elif distance > 25:
            e.run(1, p1=[forward])
        else:
            e.run(1, p1=[forward, 'x'])
            e.run(1, p1=[forward])
    raise AssertionError(("CPU match did not finish", e.state()))


def verify_background(e):
    generated = ROOT / "assets/generated"
    gfx = (generated / "champion_tiles.bin").read_bytes()
    tilemap = (generated / "champion_map.bin").read_bytes()
    palette = (generated / "champion_pal.bin").read_bytes()
    memory = presentation.vram_bytes(e)
    check(memory[:len(gfx)] == gfx, "Champion BG1 tiles reach VRAM exactly")
    check(memory[0x7000:0x7800] == tilemap, "Champion BG1 map reaches VRAM exactly")
    check(len(gfx) % 32 == 0 and len(gfx) // 32 < 896,
          "Champion BG1 stays below 896 tiles", len(gfx))
    check(len(gfx) < 32768 and len(tilemap) == 2048 and len(palette) == 192,
          "Champion scene assets fit individual LoROM banks and six palettes")
    entries = [int.from_bytes(tilemap[i:i+2], "little") for i in range(0, 1792, 2)]
    check(all(2 <= (entry >> 10) & 7 <= 7 for entry in entries),
          "Champion BG1 uses only palette banks 2 through 7")
    check(max(entry & 1023 for entry in entries) < 896,
          "Champion map cannot address reserved ambient tiles 960..967")
    colors = [presentation.snes_rgb(int.from_bytes(palette[i:i+2], "little"))
              for i in range(0, len(palette), 2)]
    expected = Image.new("RGB", (256, 224))
    for index, entry in enumerate(entries):
        offset = (entry & 1023) * 32
        pixels = presentation._tile_indices(gfx[offset:offset+32])
        bank = ((entry >> 10) & 7) - 2
        check(all(pixels), "Champion BG1 tiles are opaque")
        block = Image.new("RGB", (8, 8))
        block.putdata([colors[bank * 16 + value] for value in pixels])
        expected.paste(block, ((index % 32) * 8, (index // 32) * 8))
    # This is the entire unobscured trophy, plinth, skyline and keyboard area.
    crop = (0, 40, 160, 176)
    delta = presentation.image_delta(e.frame.crop(crop), expected.crop(crop))
    check(delta["max_channel_delta"] <= 3 and delta["pixels_over_16"] == 0,
          "Actual PPU trophy/office pixels match encoded BG1", delta)
    return {"tiles": len(gfx) // 32, "tile_bytes": len(gfx),
            "map_bytes": len(tilemap), "palette_bytes": len(palette),
            "palette_banks": [2, 3, 4, 5, 6, 7],
            "tile_sha256": sha(gfx), "map_sha256": sha(tilemap),
            "palette_sha256": sha(palette), "ppu_crop": list(crop), "ppu_delta": delta}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default="docs/champion-ending-report.json")
    parser.add_argument("--exit", choices=("a", "start", "b"), default="a")
    args = parser.parse_args()
    started = time.monotonic()
    rom = ROOT / "dist/abaqus-after-hours.sfc"
    report = {"scope": "focused controller-only champion ending; not a six-suite or release certification",
              "rom_sha256": sha(rom.read_bytes()), "status": "running",
              "core_sha256": sha((ROOT / ".tools/core/snes9x_libretro.dll").read_bytes()),
              "controller_only": True, "memory_writes": False, "save_states": False,
              "headless": True, "audio_device_opened": False,
              "host_contract": host_contract(), "ladder": []}
    path = ROOT / args.report
    path.parent.mkdir(parents=True, exist_ok=True)
    e = None
    try:
        e = Emulator()
        e.run(100)
        press(e, "l")  # Native title difficulty: Normal -> Easy.
        press(e, "a"); wait(e, 1)
        for _ in range(4):
            press(e, "right")
        press(e, "a"); wait(e, 2)
        press(e, "a"); wait(e, 3); e.run(180)
        check(e.state()["mode"] == 0, "Proof starts in native Arcade mode")
        for match in range(11):
            attempts = []
            for attempt in range(8):
                play_cpu(e)
                current = e.state()
                check(current["screen"] == 4, "Arcade match reaches a result", current)
                check(current["arcade"] == match, "Continue cannot skip a ladder opponent", current)
                attempts.append({"wins1": current["wins1"], "wins2": current["wins2"]})
                if current["wins1"] == 2:
                    break
                check(not current["champion"], "Losing an Arcade match cannot award champion")
                press(e, "a"); wait(e, 3)
            check(current["wins1"] == 2, "Player wins each of the eleven opponents", current)
            check(current["champion"] == (1 if match == 10 else 0),
                  "Only the eleventh Arcade victory awards champion", current)
            report["ladder"].append({"opponent": current["fighter_id2"],
                                     "arena": current["arena"], "attempts": attempts})
            print(f"Completed Arcade opponent {match + 1}/11", flush=True)
            if match < 10:
                if match == 0:
                    report["non_champion_result"] = {
                        "text": presentation.verify_result_font_bank(e, current),
                        "portrait": presentation.verify_large_portrait(e, current["fighter_id1"], 4, 9),
                    }
                    stage = (ROOT / f"assets/generated/stage{current['arena']}_tiles.bin").read_bytes()
                    check(presentation.vram_bytes(e)[:len(stage)] == stage,
                          "Non-champion result retains its original stage scene")
                    report["non_champion_result"]["stage_tiles_sha256"] = sha(stage)
                    report["non_champion_result"]["capture"] = str(e.shot("champion/arcade-result.png").relative_to(ROOT)).replace("\\", "/")
                press(e, "a"); wait(e, 3)
        e.run(20)
        current = e.state()
        check({match["opponent"] for match in report["ladder"]} ==
              set(range(12)) - {current["fighter_id1"]},
              "The ladder defeated all eleven distinct other fighters")
        check(all(match["arena"] == index % 3 for index, match in enumerate(report["ladder"])),
              "The controller-driven ladder follows all three native stages")
        report["champion_state"] = current
        report["capture"] = str(e.shot("champion/ending.png").relative_to(ROOT)).replace("\\", "/")
        report["background"] = verify_background(e)
        report["text"] = presentation.verify_result_font_bank(e, current)
        report["portrait"] = presentation.verify_large_portrait(e, current["fighter_id1"], 21, 7)
        before = e.frame.tobytes()
        e.run(60)
        check(e.state()["champion"] == 1 and e.frame.tobytes() == before,
              "Champion scene is stable while waiting for controller input")
        press(e, args.exit)
        wait(e, 1 if args.exit == "b" else 0)
        report["exit"] = {"key": args.exit, "screen": e.state()["screen"],
                          "capture": str(e.shot("champion/exit-" + args.exit + ".png").relative_to(ROOT)).replace("\\", "/")}
        report["frames"] = e.frames
        report["status"] = "passed"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = repr(error)
        if e is not None:
            report["last_state"] = e.state()
        raise
    finally:
        if e is not None:
            e.close()
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "rom_sha256": report["rom_sha256"],
                      "report": str(path)}))


if __name__ == "__main__":
    main()
