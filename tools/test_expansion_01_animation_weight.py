"""Controller-only native animation proof; no WRAM writes, saves or audio device.

Record the integration base before editing with --record-base, then run normally.
The ignored base recording compares every non-animation Fighter byte and public
combat trace on identical physical inputs. --base-rom/--base-symbols allow a
fresh reviewer to reproduce it. All video comes from the actual libretro PPU.
"""
from __future__ import annotations

import argparse
import ctypes as C
import hashlib
import json
import re
import sys
import subprocess
import time
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import Emulator, ROOT
from test_inputs import trace, signed16

OUT = ROOT / "docs/expansion-01-report.json"
SHOTS = ROOT / "docs/screenshots/expansion-01"
BASE = ROOT / "build/expansion-01-base-proof.json"
checks = []


def check(ok, label, detail=None):
    if not ok:
        raise AssertionError((label, detail))
    checks.append({"check": label, "passed": True, "details": detail})


def symbols(path):
    return {name: int(value, 16) for value, name in
            re.findall(r"^([0-9a-fA-F]{6,8})\s+(\S+)\s*$",
                       path.read_text(encoding="utf-8"), re.M)}


def address(table, name):
    return table.get(name, table.get("_" + name))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def boot(rom, fighter):
    e = Emulator(rom=rom)
    e.run(120)

    def press(key, port=0):
        e.tap(key, port)
        e.run(20)

    def screen(wanted):
        for _ in range(60):
            if trace(e)["screen"] == wanted:
                e.run(10)
                return
            e.run(10)
        raise AssertionError(("boot screen", wanted, trace(e)))

    press("down")  # Local Versus: both actual controller ports.
    press("a")
    screen(1)
    for _ in range(fighter):
        press("right")
    press("a")
    for _ in range((fighter - trace(e)["selected2"]) % 12):
        press("right", 1)
    press("a", 1)
    screen(2)
    press("a")
    screen(3)
    for _ in range(180):
        if not trace(e)["intro"]:
            break
        e.run(1)
    e.run(3)
    check(trace(e)["fighter_id1"] == fighter and
          trace(e)["fighter_id2"] == fighter, "controller selects mirror roster", fighter)
    return e


class Probe:
    def __init__(self, e, fighter, table, base=False):
        self.e, self.fighter, self.base = e, fighter, base
        self.fighter_offset = address(table, "fighters") - 0x7E0000
        self.oam_offset = address(table, "oamMemory") - 0x7E0000
        self.game_hash = hashlib.sha256()
        self.lag_address = address(table, "lag_frame_counter")
        self.vblank_address = address(table, "snes_vblank_count")
        self.native_previous = self.native_timing()
        self.native_failures = []
        self.lag_increments = 0
        self.rows = []
        self.drops, self.overflow, self.bad_payload, self.geometry = [], [], [], []
        self.uploads = Counter()
        self.frames = [set(), set()]
        self.clips = {}
        self.previous = trace(e)
        self.previous_payload = None
        self.lookup = {}
        for bank, suffix in enumerate(("", "b", "c", "d", "e", "f", "g", "h")):
            data = (ROOT / f"assets/generated/fighter{fighter:02}{suffix}.bin").read_bytes()
            for index in range(8):
                self.lookup[data[index * 3840:(index + 1) * 3840]] = bank * 8 + index

    def native_timing(self):
        return tuple(int.from_bytes(C.string_at(self.e.ram + offset, 2), "little")
                     for offset in (self.lag_address, self.vblank_address))

    def step(self, p1=(), p2=(), label="", film=False):
        before = self.previous
        self.e.run(1, p1=p1, p2=p2)
        s = trace(self.e)
        native = self.native_timing()
        lag_delta = (native[0] - self.native_previous[0]) & 65535
        vblank_delta = (native[1] - self.native_previous[1]) & 65535
        self.lag_increments += lag_delta
        if lag_delta or vblank_delta != 1:
            self.native_failures.append({"label": label, "frame": s["frame"],
                                         "lag_delta": lag_delta, "vblank_delta": vblank_delta})
        self.native_previous = native
        ram = C.string_at(self.e.ram + self.fighter_offset, 128)
        # The only exempt bytes are animFrame, oldFrame, animState, animTick.
        self.game_hash.update(ram[:44] + ram[48:108] + ram[112:])
        self.game_hash.update(json.dumps({k: v for k, v in s.items()
                                         if not k.startswith("anim_")},
                                        sort_keys=True).encode("utf-8"))
        if ((s["frame"] - before["frame"]) & 65535) != 1:
            self.drops.append({"label": label, "before": before["frame"], "after": s["frame"]})
        row = {"label": label, **{k: s[k] for k in (
            "frame", "action1", "action2", "anim_frame1", "anim_frame2",
            "anim_state1", "anim_state2", "anim_tick1", "anim_tick2",
            "landing1", "landing2", "down_state1", "down_state2", "down_tick1",
            "down_tick2", "y1", "y2", "paused", "hitstop", "hp1", "hp2", "round_end", "intro")}}
        row["tick1"], row["tick2"] = ram[17], ram[81]
        row["startup1"], row["startup2"] = ram[24], ram[88]
        row["active_end1"], row["active_end2"] = ram[63], ram[127]
        row["action_end1"], row["action_end2"] = ram[62], ram[126]
        row["vy1"] = int.from_bytes(ram[4:6], "little", signed=True)
        row["vy2"] = int.from_bytes(ram[68:70], "little", signed=True)
        if not self.base:
            raw = C.string_at(self.e.core.retro_get_memory_data(3),
                              self.e.core.retro_get_memory_size(3))
            payloads = tuple(b"".join(raw[0xC000 + port * 0x1400 + n * 512:
                                             0xC000 + port * 0x1400 + n * 512 + 384]
                                      for n in range(10)) for port in range(2))
            changed = 0 if self.previous_payload is None else sum(
                payloads[p] != self.previous_payload[p] for p in range(2))
            self.uploads[changed] += 1
            self.previous_payload = payloads
            oam = C.string_at(self.e.ram + self.oam_offset, 544)
            stat = C.string_at(self.e.ram + 0x1FF00 + 114 * 2, 2)
            if int.from_bytes(stat, "little") & 0xC0:
                self.overflow.append((label, s["frame"], list(stat)))
            for port in range(2):
                suffix = port + 1
                frame = s[f"anim_frame{suffix}"]
                if not 0 <= frame < 64:
                    self.bad_payload.append((label, port, frame))
                actual = self.lookup.get(payloads[port])
                row[f"uploaded{suffix}"] = actual
                if actual is None:
                    self.bad_payload.append((label, port, "non-native or torn frame"))
                self.frames[port].add(actual)
                # Exact 30-piece canvas: no offset, stretching, palette or scale changes.
                x = (s[f"x{suffix}"] >> 4) - 48
                y = 201 + (signed16(s[f"y{suffix}"]) >> 4) - 80
                face = s[f"face{suffix}"]
                for index in range(30):
                    slot = port * 32 + index
                    px, py, tile, attr = oam[slot * 4:slot * 4 + 4]
                    high = (oam[512 + slot // 4] >> ((slot & 3) * 2)) & 3
                    want_x = x + ((5 - index % 6) if not face else index % 6) * 16
                    want_y = y + index // 6 * 16
                    if (px | ((high & 1) << 8)) != (want_x & 511) or py != (want_y & 255):
                        self.geometry.append((label, port, index, px, py, want_x, want_y))
                    if high & 2 != 2 or ((attr >> 1) & 7) != port:
                        self.geometry.append((label, port, "size/palette", high, attr))
            if film and self.fighter in (0, 9, 11):
                images = self.clips.setdefault(label, [])
                if len(images) < 145:
                    images.append((self.e.frame.copy(), dict(row)))
        self.rows.append(row)
        self.previous = s
        return s

    def run(self, n, p1=(), p2=(), label="", film=False):
        for _ in range(n):
            self.step(p1, p2, label, film)

    def close(self):
        for _ in range(180):
            s = trace(self.e)
            if abs(s["x1"] - s["x2"]) < min(s["throw_range1"], s["throw_range2"]) * 16:
                return
            self.step(["right"], ["left"], "close")
        raise AssertionError("controller could not close fighters")


def scenario(rom, fighter, table, base):
    e = boot(rom, fighter)
    p = Probe(e, fighter, table, base)
    try:
        p.run(110, label="idle", film=True)
        p.run(40, ["right"], ["left"], "walk-forward", True)
        p.run(40, ["left"], ["right"], "walk-back", True)
        p.run(18, label="walk-settle", film=True)
        p.run(12, ["down"], ["down"], "crouch", True)
        p.run(16, label="crouch-return", film=True)
        p.run(3, ["up"], ["up"], "jump", True)
        p.run(82, label="jump", film=True)
        p.run(3, ["up"], ["up"], "landing-cancel", True)
        for _ in range(100):
            if trace(e)["landing1"] == 1:
                break
            p.step(label="landing-cancel", film=True)
        check(trace(e)["landing1"] == 1, "controller jump reaches landing release boundary", fighter)
        p.step(label="landing-cancel", film=True)
        p.run(3, ["y"], ["y"], "landing-cancel", True)
        p.run(45, label="landing-cancel", film=True)
        for key in ("y", "x", "b", "a"):
            p.run(3, [key], [key], "normal-" + key, True)
            p.run(42, label="normal-" + key, film=True)
        p.run(3, ["down", "y"], ["down", "y"], "special", True)
        p.run(95, label="special", film=True)
        p.run(3, ["up"], ["up"], "air-kick", True)
        p.run(6, label="air-kick", film=True)
        p.run(3, ["a"], ["a"], "air-kick", True)
        p.run(65, label="air-kick", film=True)
        for port in (0, 1):
            p.close()
            p.run(8)
            s = trace(e)
            forward = "right" if s[f"face{port+1}"] else "left"
            p.run(3, [forward, "x"] if port == 0 else [],
                  [forward, "x"] if port == 1 else [], "throw-" + str(port), True)
            p.run(110, label="throw-" + str(port), film=True)
        p.close()
        p.run(5)
        p.run(3, ["down", "a"], [], "sweep", True)
        p.run(100, label="sweep", film=True)
        # Pause freezes requested pose clocks, then physical Start resumes.
        p.run(3, ["start"], label="pause")
        p.run(18, label="pause")
        p.run(3, p2=["start"], label="resume")
        p.run(12, label="resume")
        if fighter in (0, 2, 4, 5):
            for index in range(600):
                phase = index % 150
                keys = (["right"] if phase < 38 else ["right", "x"] if phase < 44
                        else ["up", "x"] if phase < 50 else ["down", "a"] if phase < 80
                        else ["down", "y"] if phase < 110 else [])
                p.step(keys, label="stress")
        return p
    finally:
        e.close()


def visual_checks(p):
    fighter, rows = p.fighter, p.rows
    check(not p.drops, "one native tick per callback", {"fighter": fighter, "failures": p.drops[:4]})
    check(not p.native_failures, "SDK counters show zero lag and one vblank per callback",
          {"fighter": fighter, "lag_increments": p.lag_increments, "failures": p.native_failures[:4]})
    check(not p.overflow, "STAT77 OBJ overflow stays clear", {"fighter": fighter, "failures": p.overflow[:4]})
    check(not p.bad_payload, "both ports display intact approved 64-frame payloads", {"fighter": fighter, "failures": p.bad_payload[:4]})
    check(not p.geometry, "both ports retain exact canvas scale, palette and floor pivot", {"fighter": fighter, "failures": p.geometry[:4]})
    check(not p.uploads[2], "no callback replaces both actor pages", {"fighter": fighter, "uploads": dict(p.uploads)})
    for port in (1, 2):
        def frames(label):
            return [r[f"anim_frame{port}"] for r in rows if r["label"] == label]
        idle = Counter(frames("idle"))
        check(set(idle) == {16, 17, 18, 19} and idle[16] > idle[17],
              "idle breath holds its guard longer than inhale", {"fighter": fighter, "port": port, "holds": dict(idle)})
        jump = [r for r in rows if r["label"] == "jump"]
        landing = [r for r in jump if r[f"landing{port}"]]
        settle = [r for r in jump if r[f"anim_state{port}"] == 15]
        check(landing and all(r[f"anim_frame{port}"] == 31 for r in landing),
              "landing plants compression at actual floor", {"fighter": fighter, "port": port})
        check({28, 19}.issubset({r[f"anim_frame{port}"] for r in settle}) and
              all(r[f"y{port}"] == 0 for r in settle),
              "landing releases through crouch and guard with fixed grounding", {"fighter": fighter, "port": port})
        walk = Counter(frames("walk-forward"))
        check(set(walk) == {20, 21, 22, 23}, "distance-driven forward gait keeps all four poses", {"fighter": fighter, "port": port, "holds": dict(walk)})
        back = Counter(frames("walk-back"))
        check(set(back) == {24, 25, 26, 27}, "distance-driven backward gait keeps all four poses", {"fighter": fighter, "port": port, "holds": dict(back)})
        cancel = [r for r in rows if r["label"] == "landing-cancel"]
        settle_index = next((i for i, r in enumerate(cancel) if r[f"anim_state{port}"] == 15), None)
        check(settle_index is not None and any(r[f"action{port}"] == 1
              for r in cancel[settle_index + 1:settle_index + 5]),
              "physical punch immediately interrupts visual landing release", {"fighter": fighter, "port": port})
        for key in ("x", "a"):
            seq = [r for r in rows if r["label"] == "normal-" + key and r[f"action{port}"]]
            active = [r for r in seq if r[f"startup{port}"] <= r[f"tick{port}"] < r[f"active_end{port}"]]
            expect = 6 if key == "x" else 7
            check(active and all(r[f"anim_frame{port}"] == expect for r in active),
                  "strong contact art remains aligned to native active window", {"fighter": fighter, "port": port, "key": key})
            check(32 in [r[f"anim_frame{port}"] for r in seq if r[f"tick{port}"] >= r[f"active_end{port}"]],
                  "strong recovery reclaims guard before action expires", {"fighter": fighter, "port": port, "key": key})
        thrown = [r for r in rows if r["label"] == "throw-" + str(2 - port)]
        check({1, 2, 3, 4, 5}.issubset({r[f"down_state{port}"] for r in thrown}),
              "actual opposing throw traverses complete downed flow", {"fighter": fighter, "port": port})
        floor = [r[f"anim_frame{port}"] for r in thrown if r[f"down_state{port}"] == 3]
        check({59, 14}.issubset(set(floor)), "ground impact settles into prone hold", {"fighter": fighter, "port": port})
        rise = [r[f"anim_frame{port}"] for r in thrown if r[f"down_state{port}"] == 4]
        check({62, 63}.issubset(set(rise)), "get-up plants hand before upright wake guard", {"fighter": fighter, "port": port})
        paused = [r for r in rows if r["paused"]]
        check(paused and len({(r[f"anim_frame{port}"], r[f"anim_tick{port}"]) for r in paused}) == 1,
              "pause freezes weighted animation", {"fighter": fighter, "port": port})
    sweep = [r for r in rows if r["label"] == "sweep" and r["down_state2"] == 2]
    check(sweep and all(r["anim_frame2"] == (60 if r["vy2"] < 0 else 61) for r in sweep),
          "knockdown launch and fall follow actual velocity", {"fighter": fighter})
    freeze = [(a, b) for a, b in zip(rows, rows[1:]) if a["hitstop"] > 1 and
              a["label"] == b["label"] and not a["paused"] and not a["round_end"]
              and not b["round_end"] and not a["intro"] and not b["intro"]]
    check(freeze and all((a["anim_frame1"], a["anim_tick1"], a["anim_frame2"], a["anim_tick2"]) ==
                        (b["anim_frame1"], b["anim_tick1"], b["anim_frame2"], b["anim_tick2"]) for a, b in freeze),
          "real throw/hit hitstop freezes both weighted clocks", {"fighter": fighter, "samples": len(freeze)})


def save_clips(p):
    result = []
    for label in ("idle", "walk-forward", "walk-back", "jump", "normal-x", "normal-a", "throw-0", "sweep"):
        images = p.clips.get(label, [])
        if not images:
            continue
        path = SHOTS / f"fighter{p.fighter:02}-{label}.gif"
        # GIF stores centiseconds. Cumulative rounding preserves native elapsed
        # time with 10/20ms holds instead of silently truncating 17ms to 10ms.
        native_ms = 1000 / 60.098811862348406
        durations = [10 * (round((i + 1) * native_ms / 10) - round(i * native_ms / 10))
                     for i in range(len(images))]
        images[0][0].save(path, save_all=True, append_images=[im for im, _ in images[1:]],
                          duration=durations, loop=0, optimize=False)
        # A labelled native-frame strip makes holds and stage changes inspectable.
        chosen = []
        old = None
        for im, r in images:
            identity = (r["anim_frame1"], r["anim_frame2"])
            if identity != old:
                chosen.append((im, r))
                old = identity
        chosen = chosen[:16]
        sheet = Image.new("RGB", (4 * 256, ((len(chosen) + 3) // 4) * 248), (15, 22, 37))
        draw = ImageDraw.Draw(sheet)
        for index, (im, r) in enumerate(chosen):
            x, y = index % 4 * 256, index // 4 * 248
            sheet.paste(im, (x, y))
            draw.text((x + 4, y + 225), f"tick {r['frame']} / request {r['anim_frame1']},{r['anim_frame2']}", fill="white")
        sheet.save(path.with_suffix(".png"))
        result.append({"gif": str(path.relative_to(ROOT)).replace("\\", "/"),
                       "strip": str(path.with_suffix(".png").relative_to(ROOT)).replace("\\", "/"),
                       "frames": len(images), "native_fps": 60.098811862348406,
                       "gif_note": "10/20ms quantized GIF holds approximate native timing",
                       "strip_note": "Request labels describe read-only trace; actor DMA may trail by one frame."})
    return result


def preservation(table, baseline_symbols):
    """Audit retained encoded art, linker RAM and LoROM section sizes."""
    listing = subprocess.run(["git", "ls-tree", "-r", "610537d", "--", "assets/generated"],
                             cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8").stdout
    changed, manifest = [], []
    for line in listing.splitlines():
        meta, name = line.split("\t", 1)
        expected = meta.split()[2]
        data = (ROOT / name).read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if blob != expected:
            changed.append(name)
        manifest.append(name + ":" + hashlib.sha256(data).hexdigest())
    check(not changed and len(manifest) == 219, "all 219 generated assets match integration base", changed)
    result = {"unchanged_generated_assets": len(manifest),
              "generated_asset_manifest_sha256": hashlib.sha256("\n".join(manifest).encode()).hexdigest()}
    if baseline_symbols.exists():
        old = symbols(baseline_symbols)
        old_ram = {n: a for n, a in old.items() if a < 0x2000 or 0x7E0000 <= a < 0x800000}
        ram = {n: a for n, a in table.items() if a < 0x2000 or 0x7E0000 <= a < 0x800000}
        check(ram == old_ram, "all RAM/direct-page symbol addresses and names match base", len(ram))
        result["unchanged_ram_direct_page_symbols"] = len(ram)
        old_start = next(a for n, a in old.items() if n.startswith("SECTIONSTART_.animateFighter"))
        old_end = next(a for n, a in old.items() if n.startswith("SECTIONEND_.animateFighter"))
        result["base_animation_code_bytes"] = old_end - old_start
    section_bytes, crossings, occupied = 0, [], {}
    for name, start in table.items():
        if not name.startswith("SECTIONSTART_"):
            continue
        end = table.get(name.replace("SECTIONSTART_", "SECTIONEND_"))
        if end is None or start & 65535 < 0x8000:
            continue
        if 0x7E0000 <= start < 0x800000:
            continue
        size = end - start
        section_bytes += size
        if (start & 65535) + size > 0x10000:
            crossings.append(name)
        bank = (start >> 16) & 127
        occupied[bank] = occupied.get(bank, 0) + size
        if name.startswith("SECTIONSTART_.animateFighter"):
            result["animation_code_bytes"] = size
            result["animation_code_address"] = f"{start:06X}"
            result["animation_bank"] = bank
    check(not crossings, "all linker ROM sections fit their 32 KiB LoROM banks", crossings)
    result.update({"linked_rom_section_bytes": section_bytes,
                   "rom_bytes_outside_linked_sections": 4194304 - section_bytes,
                   "occupied_rom_banks": len(occupied), "wholly_unoccupied_rom_banks": 128 - len(occupied),
                   "animation_bank_unoccupied_bytes": 32768 - occupied[result["animation_bank"]]})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record-base", action="store_true")
    parser.add_argument("--base-rom", type=Path)
    parser.add_argument("--base-symbols", type=Path)
    parser.add_argument("--skip-preservation", action="store_true",
                        help="Combined integration may intentionally change assets; retain native animation checks.")
    parser.add_argument("--fighters", default="0,1,2,3,4,5,6,7,8,9,10,11")
    args = parser.parse_args()
    rom = args.base_rom if args.record_base and args.base_rom else ROOT / "dist/abaqus-after-hours.sfc"
    sym = args.base_symbols if args.record_base and args.base_symbols else ROOT / "dist/abaqus-after-hours.sym"
    table = symbols(sym)
    SHOTS.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    fighters = [int(n) for n in args.fighters.split(",")]
    results, clips = [], []
    baseline = None if args.record_base else json.loads(BASE.read_text(encoding="utf-8")) if BASE.exists() else None
    for fighter in fighters:
        p = scenario(rom, fighter, table, args.record_base)
        result = {"fighter": fighter, "callbacks": len(p.rows), "non_animation_sha256": p.game_hash.hexdigest()}
        if not args.record_base:
            visual_checks(p)
            if baseline is not None:
                old = next(r for r in baseline["fighters"] if r["fighter"] == fighter)
                check(result == old, "every non-animation Fighter byte and combat trace matches base", result)
            result.update({"requested_and_uploaded_frames": [sorted(x) for x in p.frames],
                           "actor_page_changes_per_callback": dict(p.uploads), "cadence_failures": p.drops,
                           "sdk_lag_increments": p.lag_increments, "native_timing_failures": p.native_failures,
                           "obj_overflow_failures": p.overflow, "geometry_failures": p.geometry,
                           "payload_failures": p.bad_payload})
            clips.extend(save_clips(p))
        results.append(result)
        print(f"fighter {fighter:02}: {len(p.rows)} native callbacks", flush=True)
    retained = None if args.record_base or args.skip_preservation else preservation(
        table, args.base_symbols or ROOT / "build/expansion-01-base.sym")
    report = {"schema": "abaqus-expansion-01-animation-weight/v1", "status": "passed",
              "rom_sha256": digest(rom), "symbol_sha256": digest(sym),
              "core_sha256": digest(ROOT / ".tools/core/snes9x_libretro.dll"),
              "harness_sha256": digest(Path(__file__)), "elapsed_seconds": round(time.monotonic() - started, 3),
              "source_sha256": {name: digest(ROOT / name) for name in ("src/game.c", "src/animation_weight.h")},
              "controller_only": True, "memory_writes": False, "save_states": False,
              "gui": False, "audio_playback": False, "base_comparison": baseline is not None,
              "fighters": results, "clips": clips, "preservation": retained,
              "passed_checks": len(checks), "checks": checks}
    if baseline:
        report["base_rom_sha256"] = baseline["rom_sha256"]
    target = BASE if args.record_base else OUT
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {target}; {len(checks)} focused checks", flush=True)


if __name__ == "__main__":
    main()
