"""Controller-only, capture-only native proof of stage depth and victory life.

No save states, emulated memory writes, window or audio device. WRAM, VRAM,
OAM, callback PPU pixels and cadence are observations of the actual cartridge.
Run with the cached Python; output belongs only to expansion 08.
"""
from __future__ import annotations

import ctypes as C
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import Emulator, ROOT
from test_stages import (boot_stage, TRACE_DEFAULTS, stage_trace, vram_bytes,
                         oam_memory, oam_entry, scanline_budget, actor_contract)
from test_compatibility import Probe, verify_manifest_and_pinned_core

OUT = ROOT / "docs/screenshots/expansion-08"
REPORT = ROOT / "docs/expansion-08-report.json"
checks = []


def check(condition, message, details=None):
    if not condition:
        raise AssertionError((message, details))
    checks.append({"check": message, "passed": True, "details": details})


def digest(data):
    return hashlib.sha256(data).hexdigest()


def symbols(data):
    return {name: int(address, 16) for address, name in
            re.findall(r"^([0-9a-fA-F]{8}) (\S+)$", data, re.M)}


SYMS = symbols((ROOT / "dist/abaqus-after-hours.sym").read_text(encoding="utf-8"))


def ram(e, name, size=1):
    return C.string_at(e.ram + (SYMS[name] & 0x1ffff), size)


def word(e, name):
    return int.from_bytes(ram(e, name, 2), "little", signed=True)


def table(e):
    data = ram(e, "stageDepthTable", 10)
    offsets = [int.from_bytes(data[i:i+2], "little") for i in (1, 4, 7)]
    return data, [value - 512 if value >= 256 else value for value in offsets]


def tick(e, p1=(), p2=(), cadence=None):
    previous = e.state()
    e.run(1, p1, p2)
    current = stage_trace(e, TRACE_DEFAULTS)
    delta = (current["frame"] - previous["frame"]) & 65535
    if cadence is not None:
        cadence.append(delta)
        if delta != 1:
            raise AssertionError(("native cadence", previous, current, p1, p2))
    check(current["ppu_stat"] & 0xc0 == 0, "STAT77 has no range/time overflow")
    video_memory = vram_bytes(e)
    previous_vram = getattr(e, "_depth_previous_vram", None)
    if previous_vram is not None:
        if video_memory[0x7800:0x7900] != previous_vram[0x7800:0x7900]:
            check(video_memory[0xc000:0xe800] == previous_vram[0xc000:0xe800],
                  "native ambient upload yields to actor pose DMA")
            check(video_memory[0xb000:0xb800] == previous_vram[0xb000:0xb800],
                  "native ambient upload yields to interface/guide DMA")
    e._depth_previous_vram = video_memory
    return current


def gif(frames, name, step=4, duration_ms=None):
    selected = frames[::step]
    path = OUT / name
    selected[0].save(path, save_all=True, append_images=selected[1:],
                     duration=duration_ms or round(1000 * step / 60.098811862348406),
                     loop=0, disposal=2)
    return str(path.relative_to(ROOT)).replace("\\", "/")


def static_shift(reference, shifted, offset, rect):
    x0, y0, x1, y1 = rect
    expected = reference.crop((x0 + offset, y0, x1 + offset, y1))
    return expected.tobytes() == shifted.crop(rect).tobytes()


def resources():
    base = symbols(subprocess.check_output(
        ["git", "show", "610537d:dist/abaqus-after-hours.sym"], cwd=ROOT).decode("utf-8"))
    old_ram = {k: v for k, v in base.items() if 0x7e0000 <= v < 0x800000
               and not k.startswith("SECTION")}
    changes = [{"symbol": k, "before": hex(v), "after": hex(SYMS.get(k, 0))}
               for k, v in old_ram.items() if SYMS.get(k) != v]
    owned = {k: hex(SYMS[k]) for k in ("stageDepthTable", "stageDepthFar",
             "stageDepthNear", "stageVictoryTick", "stageVictoryPhase")}
    check(SYMS["fighters"] == base["fighters"] and SYMS["waves"] == base["waves"],
          "Fighter64/Wave16 base addresses remain exact")
    check(SYMS["stageDepthTable"] == base["roundUiPending"] + 1,
          "sixteen feature bytes append after existing game globals", owned)
    check(SYMS["stageDepthTable"] >> 16 == 0x7e,
          "HDMA source is in its declared WRAM bank")
    # Exact native art/palette/SPC and all non-owned generated outputs remain.
    changed = subprocess.check_output(["git", "diff", "610537d", "--name-only",
                                      "--", "assets/generated"], cwd=ROOT).decode().splitlines()
    check(set(changed) == {"assets/generated/stage-dynamics.json",
                          *[f"assets/generated/stage{i}_ambient.bin" for i in range(3)]},
          "generated changes are restricted to owned ambient outputs", changed)
    sections = []
    for name, start in SYMS.items():
        if not name.startswith("SECTIONSTART_") or start < 0x800000:
            continue
        end = SYMS.get(name.replace("SECTIONSTART_", "SECTIONEND_"))
        if end is not None:
            check(start >> 15 == (end - 1) >> 15,
                  "native ROM section fits its 32 KiB LoROM bank", name)
            sections.append((start, end))
    used = sum(end - start for start, end in sections)
    feature_sections = {name: SYMS[name.replace("SECTIONSTART_", "SECTIONEND_")] - start
                        for name, start in SYMS.items()
                        if name.startswith("SECTIONSTART_.stageDepth")}
    return {"new_state_bytes": 16, "new_symbols": owned,
            "existing_ram_symbols": len(old_ram), "ram_address_changes": changes,
            "feature_code_sections": feature_sections,
            "linked_section_bytes": used, "rom_capacity_bytes": 4194304}


def run_stage(stage):
    e = boot_stage(stage, TRACE_DEFAULTS, mode=1)
    cadence = []
    result = {"stage": stage}
    try:
        for _ in range(6):
            tick(e, cadence=cadence)
        reference = e.frame.copy()
        data, offsets = table(e)
        check(offsets == [0, 0, 0], "centered fighters give neutral stage bands")
        check(sum(data[::3][:3]) == 224 and data[-1] == 0,
              "HDMA covers exactly 224 lines with a terminating record")
        check(all(0 < value < 128 for value in data[::3][:3]),
              "HDMA records transfer once at each band boundary")
        motion = []
        directions = []
        for direction, count in (("left", 72), ("right", 118)):
            for _ in range(count):
                tick(e, [direction], [direction], cadence)
                motion.append(e.frame.copy())
            for _ in range(5):
                tick(e, cadence=cadence)
            data, offsets = table(e)
            far, near, floor = offsets
            check((far < 0 and near < 0) if direction == "left" else (far > 0 and near > 0),
                  "both camera directions produce signed parallax", offsets)
            check(abs(far) < abs(near) and floor == 0,
                  "distant and near scenery have distinct rates above the fixed floor", offsets)
            check(static_shift(reference, e.frame, near, (12, 88, 244, 96)),
                  "actual PPU scenery pixels match the near-band horizontal displacement", offsets)
            check(static_shift(reference, e.frame, 0, (12, 216, 244, 224)),
                  "actual PPU floor stays fixed beneath feet and shadows")
            for rect in ((0, 0, 112, 24), (160, 0, 256, 24)):
                check(reference.crop(rect).tobytes() == e.frame.crop(rect).tobytes(),
                      "BG2 names/health stay pixel-exact while BG1 scrolls", rect)
            actor_contract(e, expected_floor=201)
            path = OUT / f"stage{stage}-{direction}.png"
            e.frame.save(path)
            directions.append({"direction": direction, "offsets": offsets,
                               "focus_positions": [e.state()["x1"], e.state()["x2"]],
                               "screenshot": str(path.relative_to(ROOT)).replace("\\", "/")})
        result["camera"] = directions
        result["motion_gif"] = gif(motion, f"stage{stage}-parallax.gif")

        # Pause both the live scene and the opaque staged Controls guide.
        tick(e, ["start"], cadence=cadence)
        for _ in range(8):
            tick(e, cadence=cadence)
        before = (ram(e, "stageDepthTable", 10), ram(e, "ambientClock", 2),
                  vram_bytes(e)[0x7800:0x7900])
        for _ in range(32):
            tick(e, ["left"], ["right"], cadence)
        check(e.state()["paused"] == 1, "movement does not dismiss pause")
        check(before == (ram(e, "stageDepthTable", 10), ram(e, "ambientClock", 2),
                         vram_bytes(e)[0x7800:0x7900]),
              "pause freezes camera table, ambient clock and native tiles")
        tick(e, ["select"], cadence=cadence)
        for _ in range(12):
            tick(e, cadence=cadence)
        frozen = e.frame.tobytes()
        for _ in range(24):
            tick(e, cadence=cadence)
        check(e.frame.tobytes() == frozen, "completed opaque Controls guide is pixel-stable")
        e.frame.save(OUT / f"stage{stage}-guide.png")
        tick(e, ["start"], cadence=cadence)
        for _ in range(8):
            tick(e, cadence=cadence)

        # Observe all authored phases on the native tile stream and pixels.
        phase_images = {}
        source = (ROOT / f"assets/generated/stage{stage}_ambient.bin").read_bytes()
        initial_oam = oam_memory(e)
        peak_sprites = peak_tiles = 0
        for _ in range(150):
            s = tick(e, cadence=cadence)
            phase = s["ambient_phase"]
            actual = vram_bytes(e)[0x7800:0x7900]
            check(actual == source[phase*256:(phase+1)*256],
                  "uploaded ambient telemetry identifies exact native VRAM bytes")
            if s["ambient_pending_phase"] == 255:
                phase_images.setdefault(phase, e.frame.copy())
            budget = scanline_budget(oam_memory(e))
            peak_sprites = max(peak_sprites, budget["max_sprites"])
            peak_tiles = max(peak_tiles, budget["max_tiles"])
        check(set(phase_images) == set(range(4)), "four distinct ambient phases reach the PPU")
        # One callback can trail VRAM telemetry; collect visibly stable phase
        # frames below by allowing the request to settle for two quiet ticks.
        near = table(e)[1][1]
        manifest = json.loads((ROOT / "assets/generated/stage-dynamics.json").read_text(encoding="utf-8"))
        cells = manifest["stages"][stage]["cells"]
        for phase in range(4):
            for _ in range(100):
                s = tick(e, cadence=cadence)
                if s["ambient_phase"] == phase and (s["ambient_clock"] & 15) >= 5:
                    phase_images[phase] = e.frame.copy()
                    break
            e.frame.save(OUT / f"stage{stage}-ambient{phase}.png")
        changes = []
        for phase in (1, 2, 3):
            count = 0
            for cell in cells:
                # All authored cells are above the fixed floor. The initial
                # far-band exception is the Las Condes tree's first row.
                offset = table(e)[1][0] if cell["native_y"] < table(e)[0][0] else near
                rect = (cell["native_x"]-offset, cell["native_y"],
                        cell["native_x"]+8-offset, cell["native_y"]+8)
                count += sum(a != b for a, b in zip(phase_images[0].crop(rect).get_flattened_data(),
                                                   phase_images[phase].crop(rect).get_flattened_data()))
            check(count > 0, "ambient phase changes actual feature pixels", [phase, count])
            changes.append(count)
        check(oam_memory(e)[256:] == initial_oam[256:],
              "ambient activity adds no OBJ entries or changes shadow geometry")
        result["ambient"] = {"visible_changed_pixels": changes,
                              "gif": gif([phase_images[i] for i in range(4)],
                                         f"stage{stage}-ambient.gif", step=1, duration_ms=267)}

        # Ordinary controller attacks earn a real KO, with no gameplay writes.
        saw_hitstop = False
        for index in range(2200):
            s = e.state()
            distance = abs(s["x1"] - s["x2"]) // 16
            if distance > 24:
                keys = ["right" if s["x1"] < s["x2"] else "left"]
            else:
                keys = ["down", "x"] if index % 40 < 2 else []
            s = tick(e, keys, cadence=cadence)
            if s["hitstop"] > 1:
                tick(e, cadence=cadence)
                # A contact sample may have advanced once before hitstop began.
                frozen_clock = ram(e, "ambientClock", 2)
                frozen_tiles = vram_bytes(e)[0x7800:0x7900]
                frozen_camera = ram(e, "stageDepthFar", 4)
                tick(e, cadence=cadence)
                check((ram(e, "ambientClock", 2), vram_bytes(e)[0x7800:0x7900],
                       ram(e, "stageDepthFar", 4)) ==
                      (frozen_clock, frozen_tiles, frozen_camera),
                      "hitstop freezes normal ambient bytes and tracked camera")
                saw_hitstop = True
            if e.state()["round_end"]:
                break
        controller_ko_frames = index + 1
        check(e.state()["hp2"] == 0 and e.state()["wins1"] == 1,
              "real face-button controller route earns a round victory", e.state())
        check(saw_hitstop, "victory route observed native contact hitstop")
        frozen_clock = ram(e, "ambientClock", 2)
        victory_frames = []
        victory_phases = set()
        requests = []
        for index in range(124):
            s = tick(e, cadence=cadence)
            check(ram(e, "ambientClock", 2) == frozen_clock,
                  "normal ambient clock stays frozen during victory reaction")
            victory_frames.append(e.frame.copy())
            elapsed = ram(e, "stageVictoryTick")[0]
            if 16 <= elapsed <= 80:
                victory_phases.add(s["ambient_phase"])
            requests.append([elapsed, s["ambient_phase"], s["ambient_pending_phase"]])
            if index == 45:
                tick(e, ["start"], cadence=cadence)
                for _ in range(6):
                    tick(e, cadence=cadence)
                paused_tick = ram(e, "stageVictoryTick")
                paused_patch = vram_bytes(e)[0x7800:0x7900]
                for _ in range(20):
                    tick(e, cadence=cadence)
                check((ram(e, "stageVictoryTick"), vram_bytes(e)[0x7800:0x7900]) ==
                      (paused_tick, paused_patch), "pause also freezes the separate victory policy")
                tick(e, ["start"], cadence=cadence)
                tick(e, cadence=cadence)
        check(victory_phases == set(range(4)), "all four bounded victory phases reach native VRAM")
        visible_victory_frames = {digest(image.crop((0, 40, 256, 120)).tobytes())
                                  for image in victory_frames[18:75]}
        check(len(visible_victory_frames) >= 4,
              "victory reaction changes actual PPU scenery above the actors",
              len(visible_victory_frames))
        check(ram(e, "stageVictoryTick")[0] == 96 and
              vram_bytes(e)[0x7800:0x7900] == source[:256],
              "victory stops after 96 samples with source-identical ambient neutral")
        result["victory"] = {"controller_frames_to_ko": controller_ko_frames,
                              "phases": sorted(victory_phases),
                              "gif": gif(victory_frames, f"stage{stage}-victory.gif"),
                              "samples": requests}
        # Natural round progression resets only the new bounded presentation.
        for _ in range(100):
            s = tick(e, cadence=cadence)
            if s["intro"]:
                break
        check(s["intro"] > 0 and ram(e, "stageVictoryTick")[0] == 0,
              "ordinary next-round transition resets victory policy")
        check(word(e, "stageDepthFar") == 0 and word(e, "stageDepthNear") == 0,
              "next round restores neutral camera for reset fighter positions")
        check(peak_sprites <= 32 and peak_tiles <= 34,
              "native OBJ scanline budget remains within hardware limits",
              {"sprites": peak_sprites, "tiles": peak_tiles})
        result["cadence"] = {"frames": len(cadence), "deltas": sorted(set(cadence))}
        result["obj_peak"] = {"sprites": peak_sprites, "tiles": peak_tiles}
        return result
    finally:
        e.close()


def stress_stage(stage):
    """Both pads drive existing low waves plus moving/jumping actor uploads."""
    e = boot_stage(stage, TRACE_DEFAULTS, mode=1, fighter=4, fighter2=6)
    cadence = []
    waves = simultaneous = 0
    peak_sprites = peak_tiles = 0
    try:
        for index in range(720):
            phase = index % 120
            if phase < 4:
                p1 = p2 = ["down"]
            elif phase < 6:
                p1 = p2 = ["down", "y"]
            elif 65 <= phase < 67:
                p1 = p2 = ["up"]
            elif 70 <= phase < 90:
                p1, p2 = ["right"], ["left"]
            elif 90 <= phase < 110:
                p1, p2 = ["left"], ["right"]
            else:
                p1 = p2 = []
            s = tick(e, p1, p2, cadence)
            waves += int(bool(s["wave1"] or s["wave2"]))
            simultaneous += int(bool(s["wave1"] and s["wave2"]))
            budget = scanline_budget(oam_memory(e))
            peak_sprites = max(peak_sprites, budget["max_sprites"])
            peak_tiles = max(peak_tiles, budget["max_tiles"])
        check(simultaneous > 0, "two controller-driven low waves coexist under HDMA", simultaneous)
        check(peak_sprites <= 32 and peak_tiles <= 34,
              "two-wave/jump stress preserves hardware OBJ scanline limits",
              {"sprites": peak_sprites, "tiles": peak_tiles})
        return {"stage": stage, "frames": len(cadence), "deltas": sorted(set(cadence)),
                "wave_frames": waves, "two_wave_frames": simultaneous,
                "obj_peak_sprites": peak_sprites, "obj_peak_tiles": peak_tiles}
    finally:
        e.close()


def independent_stage(stage):
    """Accuracy-core PPU displacement and freeze, without touching its shared report."""
    e = Probe()
    cadence = []
    frames = 0
    try:
        def run(count=1, p1=(), p2=(), measure=True):
            nonlocal frames
            for _ in range(count):
                before = e.state()["frame"]
                e.run(1, p1, p2)
                frames += 1
                if measure:
                    after = e.state()
                    delta = (after["frame"] - before) & 65535
                    cadence.append(delta)
                    check(delta == 1, "Accuracy core preserves native stage cadence")
                    status = e.trace_words()[114]
                    check(status & 0xc0 == 0, "Accuracy core STAT77 has no OBJ overflow")

        def press(key, port=0):
            e.run(3, [key] if port == 0 else (), [key] if port == 1 else ())
            e.run(23)

        run(120, measure=False)
        press("down")
        press("a")
        press("a")
        press("a", 1)
        for _ in range(stage):
            press("down")
        press("a")
        while e.state()["intro"]:
            e.run(1)
        run(8)
        check(e.state()["screen"] == 3 and e.state()["mode"] == 1,
              "Accuracy core reaches Local VS through ordinary controllers")
        reference = e.frame_image.copy()
        scale = reference.width // 256
        shifts = []
        for direction, count in (("left", 72), ("right", 118)):
            run(count, [direction], [direction])
            run(5)
            near = word(e, "stageDepthNear")
            rect = (12 * scale, 88, 244 * scale, 96)
            check(static_shift(reference, e.frame_image, near * scale, rect),
                  "Accuracy PPU has exact position-driven near-band displacement", near)
            rect = (12 * scale, 216, 244 * scale, 224)
            check(static_shift(reference, e.frame_image, 0, rect),
                  "Accuracy PPU floor stays fixed")
            e.frame_image.save(OUT / f"stage{stage}-accuracy-{direction}.png")
            shifts.append({"direction": direction, "near_scroll": near})
        press("start")
        frozen = (ram(e, "stageDepthTable", 10), ram(e, "ambientClock", 2))
        run(48, ["left"], ["right"])
        check(e.state()["paused"] == 1 and frozen ==
              (ram(e, "stageDepthTable", 10), ram(e, "ambientClock", 2)),
              "Accuracy core freezes stage camera and ambient clock while paused")
        press("start")
        run(600)
        return {"stage": stage, "callback_dimensions": list(reference.size),
                "camera": shifts, "measured_frames": len(cadence),
                "cadence_deltas": sorted(set(cadence))}
    finally:
        e.close()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"feature": "08-stage-depth", "status": "running",
              "rom_sha256": digest((ROOT / "dist/abaqus-after-hours.sfc").read_bytes()),
              "core_sha256": digest((ROOT / ".tools/core/snes9x_libretro.dll").read_bytes()),
              "input_policy": "physical controllers only; no WRAM writes/save states",
              "audio_policy": "headless capture only; no audio output device"}
    try:
        report["resources"] = resources()
        report["stages"] = [run_stage(stage) for stage in range(3)]
        report["stress"] = [stress_stage(stage) for stage in range(3)]
        report["accuracy_core"] = verify_manifest_and_pinned_core()
        report["independent_stages"] = [independent_stage(stage) for stage in range(3)]
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = repr(exc)
        raise
    finally:
        report["checks"] = checks
        report["passed_checks"] = len(checks)
        REPORT.write_bytes((json.dumps(report, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"status": report["status"], "checks": len(checks),
                      "rom_sha256": report["rom_sha256"]}))


if __name__ == "__main__":
    main()
