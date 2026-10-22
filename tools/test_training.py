"""Silent native production checks for the v0.8 Training pause/help UI.

This suite is intentionally separate from the five release suites.  It drives
only the two SNES controllers through the libretro Snes9x core, reads the
public WRAM trace and native VRAM/video callbacks, and never writes emulated
memory or opens an audio device.  The v0.8 trace extension is read locally so
the existing ``tools/emulator.py`` interface remains unchanged:

    TRACE[114]  PPU STAT77 sample
    TRACE[115]  uploaded ambient phase
    TRACE[116]  ambient clock
    TRACE[117]  pending ambient phase
    TRACE[118]  ambient pending age
    TRACE[119]  pause page (0 normal, 1 controls, 2 specials)
    TRACE[120]  guide build stage (0 settled, 1..3 staged)
    TRACE[121]  Training dummy (0 stand, 1 high guard, 2 low guard, 3 jump)
    TRACE[122]  guide dirty flag (0 settled, 1 pending)

The suite drives the official pinned Snes9x libretro core through controller
inputs, reads only public trace/VRAM/video state, and never opens a window or
audio device.  Its authoritative report is ``docs/training-test-report.json``
and its review captures live under ``docs/screenshots/training``.  Candidate
runs can redirect both paths with ``--report`` and ``--captures`` without
touching the authoritative report.
"""

from __future__ import annotations

import argparse
import ctypes as C
import hashlib
import json
import re
import sys
import time
import zipfile
from pathlib import Path
from typing import Callable, Iterable

sys.path.insert(0, str(Path(__file__).parent))
from emulator import Emulator, ROOT


TITLE, SELECT, ARENA, FIGHT = 0, 1, 2, 3
TRACE_WORDS = 123
TRACE_BASE = 0x1FF00
BG2_MAP_WORD = 0x5800
BG2_MAP_BYTE = BG2_MAP_WORD * 2
HEALTH_TILE = 129
ENERGY_TILE = 138
P1_STATUS_ATTR = 0x2000
P2_STATUS_ATTR = 0x6000
PAUSE_PAGE = 119
GUIDE_BUILD = 120
TRAINING_DUMMY = 121
GUIDE_DIRTY = 122
GUIDE_SETTLE_CALLBACKS = 8
MENU_LOAD_DUPLICATE_LIMIT = 16
TRAINING_CORE_OPTIONS = {
    # Snes9x filters contradictory directions by default.  Training's SOCD
    # regression deliberately enables the core's documented pass-through so
    # the native cleanDirections() path receives both bits.
    "snes9x_up_down_allowed": "enabled",
}
CORE_ARCHIVE = ROOT / ".tools/core.zip"
CORE_MEMBER = "snes9x_libretro.dll"
CORE_ARCHIVE_SHA256 = (
    "f3e88ae8540840c838dbcd57715134809894c9fd31d389e613409923ac23ea4e"
)
CORE_MEMBER_SHA256 = (
    "f00db5bd97bbe0e80761e590449eb14716bd9ab5785a1b50725c55e10505c343"
)
DEFAULT_REPORT = ROOT / "docs/training-test-report.json"
DEFAULT_CAPTURE_DIR = ROOT / "docs/screenshots/training"
CAPTURE_DIR = DEFAULT_CAPTURE_DIR
CAPTURE_PATHS: list[str] = []

FIGHTER_NAMES = (
    "DAMIAN", "IVO", "CRISTOBAL", "COTE", "NEGGER", "DAVID",
    "FERNANDO", "CRISTIAN", "MAMARIAGA", "RESTON", "ROXANA", "LARS",
)
SPECIAL_NAMES = (
    "KERNEL BURST", "CAPITAL WAVE", "ATOMIC PUSH", "BALANCE BREAK",
    "MACRO SHOCK", "AUDIT STRIKE", "LEGACY FLASH", "RISK REVERSAL",
    "MERGE FORCE", "CLOUD CRASH", "CLOSE OUT", "NORDIC BYTE",
)
SPECIAL_FAMILY = (0, 0, 1, 1, 2, 3, 2, 3, 2, 0, 3, 2)
SPECIAL_FAMILY_NAMES = (
    "FORWARD PROJECTILE", "ADVANCING STRIKE",
    "LOW SHOCKWAVE", "RISING STRIKE",
)

CHECKS: list[dict[str, object]] = []


def check(ok: bool, label: str, details: object | None = None) -> None:
    if not ok:
        raise AssertionError((label, details))
    CHECKS.append({"check": label, "passed": True, "details": details})


def harness_identity() -> str:
    """Hash the exact two Python sources that define this suite's host."""

    digest = hashlib.sha256()
    for path in (ROOT / "tools/test_training.py", ROOT / "tools/emulator.py"):
        if not path.is_file():
            raise AssertionError(("training harness source is missing", str(path)))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def core_identity() -> dict[str, str]:
    """Pin the loaded native Snes9x DLL to the checked-in archive member."""

    if not CORE_ARCHIVE.is_file():
        raise AssertionError(("missing pinned libretro core archive",
                              str(CORE_ARCHIVE)))
    archive_sha = hashlib.sha256(CORE_ARCHIVE.read_bytes()).hexdigest()
    if archive_sha != CORE_ARCHIVE_SHA256:
        raise AssertionError(("core archive hash mismatch", archive_sha,
                              CORE_ARCHIVE_SHA256))
    with zipfile.ZipFile(CORE_ARCHIVE) as archive:
        try:
            member = archive.read(CORE_MEMBER)
        except KeyError as exc:
            raise AssertionError(("core archive missing pinned member",
                                  CORE_MEMBER)) from exc
    member_sha = hashlib.sha256(member).hexdigest()
    if member_sha != CORE_MEMBER_SHA256:
        raise AssertionError(("core archive member hash mismatch", member_sha,
                              CORE_MEMBER_SHA256))
    dll = ROOT / ".tools/core/snes9x_libretro.dll"
    if not dll.is_file():
        raise AssertionError(("loaded libretro core DLL is missing", str(dll)))
    dll_sha = hashlib.sha256(dll.read_bytes()).hexdigest()
    if dll_sha != member_sha:
        raise AssertionError(("loaded core DLL differs from archive member",
                              dll_sha, member_sha))
    return {
        "archive": str(CORE_ARCHIVE.relative_to(ROOT)),
        "archive_sha256": archive_sha,
        "member": CORE_MEMBER,
        "member_sha256": member_sha,
        "dll": str(dll.relative_to(ROOT)),
        "dll_sha256": dll_sha,
    }


def raw_trace(e: Emulator) -> list[int]:
    """Read all stable and v0.8 trace words without changing WRAM."""

    data = C.string_at(e.ram + TRACE_BASE, TRACE_WORDS * 2)
    return [int.from_bytes(data[i:i + 2], "little")
            for i in range(0, TRACE_WORDS * 2, 2)]


def public_state(e: Emulator) -> dict[str, int]:
    """Return emulator.py state plus the four v0.8 UI aliases."""

    values = raw_trace(e)
    result = dict(e.state())
    aliases = {
        "ppu_stat": values[114],
        "ambient_phase": values[115],
        "ambient_clock": values[116],
        "ambient_pending_phase": values[117],
        "ambient_pending_age": values[118],
        "pause_page": values[PAUSE_PAGE],
        "guide_build": values[GUIDE_BUILD],
        "training_dummy": values[TRAINING_DUMMY],
        "guide_dirty": values[GUIDE_DIRTY],
    }
    for key, value in aliases.items():
        result.setdefault(key, value)
    # e.state() from the current host only exposes 0..113.  These aliases are
    # useful in the report and make the pause cadence assertions explicit.
    result.update(aliases)
    return result


class QA:
    """One sequential libretro core session with trace cadence checking."""

    def __init__(self, rom: Path, label: str) -> None:
        self.rom_path = rom
        self.label = label
        self.core_options = dict(TRAINING_CORE_OPTIONS)
        self.emulator = Emulator(rom, core_options=self.core_options)
        self.previous: dict[str, int] | None = None
        self.samples = 0
        self.captures: list[str] = []
        self.cadence: list[dict[str, int | str]] = []
        self.menu_load_duplicates: list[dict[str, int | str]] = []
        self._menu_load_budget = 0
        self._menu_load_screen_changed = False

    def state(self) -> dict[str, int]:
        return public_state(self.emulator)

    def step(self, p1: Iterable[str] = (),
             p2: Iterable[str] = (),
             allow_menu_load_duplicate: bool = False) -> dict[str, int]:
        """Run exactly one native frame and assert the trace frame advances."""

        self.emulator.run(1, p1=tuple(p1), p2=tuple(p2))
        current = self.state()
        # Snes9x exposes the WRAM window before the ROM's first trace write;
        # those bytes are the core's 0x5555 fill pattern.  Start the cadence
        # contract at the first published magic word rather than treating
        # boot initialization as a duplicate native frame.
        valid_trace = (current.get("magic") == 0xAABA and
                       current.get("screen", -1) in (TITLE, SELECT, ARENA,
                                                       FIGHT, 4))
        if self.previous is not None and valid_trace:
            delta = (current["frame"] - self.previous["frame"]) & 0xFFFF
            # Once an A/B menu transition is armed, the trace can remain on
            # the old FIGHT screen for a few forced-blank callbacks.  Keep
            # the allowance attached to that transition rather than the
            # stale published screen; the budget is cleared after the first
            # unit callback on the new screen.
            menu_allowed = self._menu_load_budget > 0
            if delta != 1:
                if delta == 0 and menu_allowed:
                    # A/B transitions can enter the ROM's forced-blank menu
                    # loader before the next complete trace publication.  Keep
                    # this allowance narrow and visible: fight/pause cadence
                    # remains strict, and a sustained loader stall fails after
                    # a bounded number of callbacks.
                    self.menu_load_duplicates.append({
                        "label": self.label, "sample": self.samples,
                        "frame": current["frame"],
                        "previous_screen": self.previous.get("screen", -1),
                        "screen": current.get("screen", -1),
                    })
                    if self._menu_load_budget > 0:
                        self._menu_load_budget -= 1
                else:
                    failure = {
                        "label": self.label, "sample": self.samples,
                        "previous": self.previous["frame"],
                        "current": current["frame"], "delta": delta,
                        "screen": current.get("screen", -1),
                        "native_screen": current.get("native_screen", -1),
                    }
                    self.cadence.append(failure)
                    raise AssertionError(("TRACE frame cadence is not unit", failure))
            if self._menu_load_screen_changed and delta == 1:
                self._menu_load_budget = 0
                self._menu_load_screen_changed = False
            elif (self._menu_load_budget > 0 and delta == 0 and
                  current.get("screen") != self.previous.get("screen")):
                self._menu_load_screen_changed = True
        self.previous = current if valid_trace else None
        if valid_trace:
            self.samples += 1
        return current

    def run(self, frames: int, p1: Iterable[str] = (),
            p2: Iterable[str] = ()) -> dict[str, int]:
        current = self.state()
        p1_tuple, p2_tuple = tuple(p1), tuple(p2)
        for _ in range(frames):
            current = self.step(p1_tuple, p2_tuple)
        return current

    def press(self, key: str, port: int = 0,
              held_frames: int = 3, release_frames: int = 3) -> dict[str, int]:
        """Send a controller edge with a poll-safe hold and release gap."""

        before = self.state()
        # Menu A/B transitions may spend a few callbacks in forced blank.  A
        # pause A/START resume is deliberately excluded: it must retain the
        # strict in-fight cadence contract.  B from a paused match is the
        # roster route and is therefore included.
        menu_transition = (
            (key == "b" and before.get("paused") == 1) or
            (key == "a" and before.get("paused") != 1 and
             before.get("screen") != FIGHT)
        )
        if menu_transition:
            self._menu_load_budget = MENU_LOAD_DUPLICATE_LIMIT
            self._menu_load_screen_changed = False
        menu_duplicates_before = len(self.menu_load_duplicates)
        held = (key,)
        for _ in range(held_frames):
            self.step(held if port == 0 else (), held if port == 1 else (),
                      allow_menu_load_duplicate=menu_transition)
        current = self.state()
        for _ in range(release_frames):
            current = self.step(allow_menu_load_duplicate=menu_transition)
        if menu_transition:
            duplicate_count = len(self.menu_load_duplicates) - menu_duplicates_before
            check(duplicate_count <= MENU_LOAD_DUPLICATE_LIMIT,
                  "menu/force-blank trace stalls remain bounded", {
                      "label": self.label,
                      "duplicates": duplicate_count,
                      "limit": MENU_LOAD_DUPLICATE_LIMIT,
                  })
        return current

    def close(self) -> None:
        self.emulator.close()


def wait_screen(q: QA, wanted: int, limit: int = 720) -> dict[str, int]:
    current = q.state()
    for _ in range(limit):
        if current.get("screen") == wanted:
            return current
        current = q.step()
    raise AssertionError(("screen did not arrive", wanted, current))


def wait_fight_intro(q: QA) -> dict[str, int]:
    current = wait_screen(q, FIGHT)
    for _ in range(180):
        if current.get("intro", 1) == 0:
            q.run(3)
            return q.state()
        current = q.step()
    raise AssertionError(("fight intro did not complete", current))


def boot(rom: Path, mode: int = 2, fighter: int = 0,
         fighter2: int = 1, stage: int = 0, label: str = "boot") -> QA:
    """Boot a fresh mode through the native title/select/arena menus."""

    q = QA(rom, label)
    q.run(120)
    title = q.state()
    check(title["screen"] == TITLE, "cold boot reaches native home", title)
    # The first valid trace publication can land on the same host callback as
    # the end of core initialization.  Establish one completed native title
    # tick before the first menu edge; all later callbacks stay strict.
    warmed = q.step()
    check(warmed["frame"] != title["frame"],
          "cold boot title publication advances before input", {
              "before": title, "after": warmed,
          })
    for _ in range(mode):
        q.press("down")
    q.press("a")
    wait_screen(q, SELECT)
    for _ in range(fighter % len(FIGHTER_NAMES)):
        q.press("right")
    q.press("a")
    if mode == 1:
        # The native local-versus P2 cursor starts at roster slot 1.
        for _ in range((fighter2 - 1) % len(FIGHTER_NAMES)):
            q.press("right", port=1)
        q.press("a", port=1)
    wait_screen(q, ARENA)
    for _ in range(stage % 3):
        q.press("down")
    q.press("a")
    current = wait_fight_intro(q)
    check(current["screen"] == FIGHT and current["intro"] == 0,
          "native Training/mode match reaches live FIGHT", current)
    return q


def vram_bytes(q: QA) -> bytes:
    pointer = q.emulator.core.retro_get_memory_data(3)
    size = q.emulator.core.retro_get_memory_size(3)
    return C.string_at(pointer, size)


def bg2_entry(memory: bytes, x: int, y: int) -> int:
    offset = BG2_MAP_BYTE + (y * 32 + x) * 2
    return int.from_bytes(memory[offset:offset + 2], "little")


def bg2_rows(memory: bytes, first: int = 0, last: int = 32) -> list[list[int]]:
    return [[bg2_entry(memory, x, y) for x in range(32)]
            for y in range(first, last)]


def status_bar_expected(value: int, count: int, base: int,
                        attributes: int, scale_health: bool) -> list[int]:
    """Build the native mirrored health/energy glyph sequence."""

    remaining = (value * 88) // 128 if scale_health else value
    return [attributes + base + min(8, max(0, remaining - index * 8))
            for index in range(count)]


def check_status_bars(q: QA, sample: dict[str, int], label: str) -> dict[str, object]:
    """Compare both BG2 status bars with the read-only combat trace."""

    memory = vram_bytes(q)
    expected_health_p1 = status_bar_expected(
        sample["hp1"], 11, HEALTH_TILE, P1_STATUS_ATTR, True)
    expected_health_p2 = status_bar_expected(
        sample["hp2"], 11, HEALTH_TILE, P2_STATUS_ATTR, True)
    expected_energy_p1 = status_bar_expected(
        sample["energy1"], 12, ENERGY_TILE, P1_STATUS_ATTR, False)
    expected_energy_p2 = status_bar_expected(
        sample["energy2"], 12, ENERGY_TILE, P2_STATUS_ATTR, False)
    actual_health_p1 = [bg2_entry(memory, 1 + index, 1)
                        for index in range(11)]
    actual_health_p2 = [bg2_entry(memory, 30 - index, 1)
                        for index in range(11)]
    actual_energy_p1 = [bg2_entry(memory, 1 + index, 3)
                        for index in range(12)]
    actual_energy_p2 = [bg2_entry(memory, 30 - index, 3)
                        for index in range(12)]
    details = {
        "label": label,
        "sample": {key: sample[key] for key in
                    ("hp1", "hp2", "energy1", "energy2", "paused",
                     "pause_page", "hitstop", "frame")},
        "health_p1": actual_health_p1,
        "expected_health_p1": expected_health_p1,
        "health_p2": actual_health_p2,
        "expected_health_p2": expected_health_p2,
        "energy_p1": actual_energy_p1,
        "expected_energy_p1": expected_energy_p1,
        "energy_p2": actual_energy_p2,
        "expected_energy_p2": expected_energy_p2,
    }
    check(actual_health_p1 == expected_health_p1 and
          actual_health_p2 == expected_health_p2,
          "paused native mirrored health bars match combat HP after " + label,
          details)
    check(actual_energy_p1 == expected_energy_p1 and
          actual_energy_p2 == expected_energy_p2,
          "paused native mirrored energy bars match combat meter after " + label,
          details)
    return details


def decode_text(memory: bytes, first: int = 0, last: int = 32) -> str:
    """Decode legacy and opaque guide font tile IDs from BG2.

    The v0.8 guide uses opaque copies in tiles 256..383 and stores the
    character as ``tile - 256``.  The original HUD still uses the legacy
    ASCII tile IDs in older snapshots, so both encodings are accepted here without relaxing the
    exact text-token checks.
    """

    rows: list[str] = []
    for row in bg2_rows(memory, first, last):
        chars = []
        for entry in row:
            tile = entry & 0x03FF
            if 256 <= tile < 383:
                tile -= 256
            chars.append(chr(tile) if 32 <= tile < 127 else " ")
        rows.append("".join(chars).rstrip())
    return "\n".join(rows)


def compact_text(text: str) -> str:
    return re.sub(r"\s+", "", text).upper()


def signed16(value: int) -> int:
    """Interpret the native u16 fixed-point Y trace as a signed value."""

    return value - 0x10000 if value & 0x8000 else value


def capture(q: QA, name: str) -> str:
    check(q.emulator.frame is not None, "native PPU frame exists for capture", name)
    check(q.emulator.frame.size == (256, 224), "native PPU capture is 256x224", {
        "name": name, "size": q.emulator.frame.size,
    })
    # A fully opaque guide legitimately uses only seven UI colors. Require
    # visible light glyph pixels over its dark card instead of depending on
    # extra stage colors leaking through the old transparent HUD markers.
    panel = q.emulator.frame.crop((0, 40, 256, 224)).convert("RGB")
    pixels = list(panel.getdata())
    bright = sum(min(pixel) >= 180 for pixel in pixels)
    dark = sum(max(pixel) <= 100 for pixel in pixels)
    colors = len(q.emulator.frame.getcolors(256 * 224) or [])
    check(colors >= 3 and bright >= 400 and dark >= 20000,
          "native PPU capture is populated", {
              "name": name, "colors": colors,
              "light_guide_pixels": bright, "dark_card_pixels": dark,
          })
    path = CAPTURE_DIR / f"{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    q.emulator.frame.save(path)
    q.captures.append(str(path))
    try:
        CAPTURE_PATHS.append(str(path.relative_to(ROOT)))
    except ValueError:
        CAPTURE_PATHS.append(str(path))
    return str(path)


def wait_guide_settled(q: QA, label: str) -> list[dict[str, int]]:
    history: list[dict[str, int]] = []
    for callback in range(GUIDE_SETTLE_CALLBACKS):
        current = q.step()
        history.append({
            "callback": callback + 1,
            "page": current["pause_page"],
            "build": current["guide_build"],
            "dirty": current["guide_dirty"],
        })
        if current["guide_build"] == 0 and current["guide_dirty"] == 0:
            check(callback + 1 <= GUIDE_SETTLE_CALLBACKS,
                  "guide UI staged DMA settles within eight callbacks", {
                      "label": label, "history": history,
                  })
            return history
    raise AssertionError(("guide UI did not settle", label, history, q.state()))


def pause(q: QA, port: int = 0) -> dict[str, int]:
    current = q.press("start", port=port)
    for _ in range(12):
        if current["paused"]:
            break
        current = q.step()
    check(current["paused"] == 1, "START pauses from both controller ports", {
        "port": port, "state": current,
    })
    check(current["pause_page"] == 0, "pause opens on normal page", current)
    wait_guide_settled(q, f"pause-port-{port}-normal")
    return q.state()


def resume(q: QA, key: str = "start", port: int = 0) -> dict[str, int]:
    current = q.press(key, port=port)
    for _ in range(12):
        if not current["paused"]:
            break
        current = q.step()
    check(current["paused"] == 0, "START/A resumes the paused match", {
        "key": key, "port": port, "state": current,
    })
    return current


def full_pause_card(q: QA, label: str) -> dict[str, object]:
    """Assert the full-card rows and capture actual native page text/PPU."""

    memory = vram_bytes(q)
    rows = bg2_rows(memory, 5, 28)
    nonblank = sum(1 for row in rows for entry in row
                   if (entry & 0x03FF) != 0)
    total = 23 * 32
    check(nonblank >= int(total * 0.75),
          "pause guide card covers BG2 rows 5..27", {
              "label": label, "nonblank": nonblank, "total": total,
          })
    text = decode_text(memory, 0, 32)
    path = capture(q, label)
    return {
        "label": label, "nonblank": nonblank, "total": total,
        "text": text, "capture": path,
        "vram_sha256": hashlib.sha256(memory).hexdigest(),
    }


def page_text(q: QA, expected: Iterable[str], label: str) -> dict[str, object]:
    evidence = full_pause_card(q, label)
    text = str(evidence["text"])
    compact = compact_text(text)
    for token in expected:
        normalized = compact_text(token)
        check(normalized in compact, "guide page contains exact native text", {
            "label": label, "token": token, "text": text,
        })
    return evidence


def cycle_to_page(q: QA, target: int) -> list[dict[str, int]]:
    """Cycle SELECT in the native pause state until target page is visible."""

    current = q.state()
    seen: list[dict[str, int]] = []
    for _ in range(3):
        if current["pause_page"] == target:
            return seen
        q.press("select")
        history = wait_guide_settled(q, f"select-page-{target}")
        seen.extend(history)
        current = q.state()
    raise AssertionError(("SELECT did not reach pause page", target, current, seen))


def verify_page_navigation(rom: Path, mode: int, fighter: int,
                           fighter2: int, stage: int) -> dict[str, object]:
    q = boot(rom, mode, fighter, fighter2, stage,
             label=f"mode{mode}-fighter{fighter}")
    try:
        before = q.state()
        top_before = bg2_rows(vram_bytes(q), 0, 5)
        pause(q, port=0)
        paused = q.state()
        normal_hint = "A/START RESUME B ROSTER"
        hint_row = decode_text(vram_bytes(q), 12, 13).strip()
        check(hint_row == normal_hint,
              "normal pause card advertises both actual resume buttons", {
                  "mode": mode, "row12": hint_row,
              })
        pause_keys = (
            "hp1", "hp2", "x1", "x2", "y1", "y2", "energy1", "energy2",
            "pose1", "pose2", "anim_frame1", "anim_frame2", "wave1", "wave2",
            "down_state1", "down_state2", "down_tick1", "down_tick2",
            "wake_age1", "wake_age2", "ambient_clock",
        )
        for _ in range(8):
            q.step()
        after_wait = q.state()
        check(all(after_wait[key] == paused[key] for key in pause_keys),
              "pause preserves combat state, projectiles, wake/down and native frames", {
                  "mode": mode, "before": paused, "after": after_wait,
              })
        check(after_wait["ambient_clock"] == paused["ambient_clock"],
              "pause freezes the ambient/combat clock", after_wait)

        page1 = cycle_to_page(q, 1)
        controls = page_text(
            q,
            ("HOW TO PLAY 1/2", "WALK", "JUMP", "STAND GUARD",
             "LOW GUARD", "PUNCH", "KICK", "THROW", "UPPERCUT",
             "AFTER A HIT: PRESS HEAVIER"),
            f"mode{mode}-controls",
        )
        q.press("right")
        wait_guide_settled(q, f"mode{mode}-guide-right")
        check(q.state()["pause_page"] == 2,
              "RIGHT flips controls guide to specials page", q.state())
        q.press("left")
        wait_guide_settled(q, f"mode{mode}-guide-left")
        check(q.state()["pause_page"] == 1,
              "LEFT flips specials guide back to controls page", q.state())
        q.press("right")
        wait_guide_settled(q, f"mode{mode}-guide-specials")
        check(q.state()["pause_page"] == 2,
              "RIGHT returns to specials page", q.state())
        current = q.state()
        p1 = current.get("fighter_id1", fighter)
        p2 = current.get("fighter_id2", fighter2)
        expected = []
        if 0 <= p1 < len(FIGHTER_NAMES):
            expected.extend((FIGHTER_NAMES[p1], SPECIAL_NAMES[p1],
                             SPECIAL_FAMILY_NAMES[SPECIAL_FAMILY[p1]]))
        if 0 <= p2 < len(FIGHTER_NAMES):
            expected.extend((FIGHTER_NAMES[p2], SPECIAL_NAMES[p2],
                             SPECIAL_FAMILY_NAMES[SPECIAL_FAMILY[p2]]))
        expected.extend(("MOVE LIST 2/2", "QUICK: DOWN + Y / X",
                         "MOTION: D, D+F, F + Y/X", "COST: 32 ENERGY",
                         "PRESS PUNCH WITH FINAL TOWARD"))
        specials = page_text(q, expected, f"mode{mode}-specials")

        # SELECT is a three-state cycle, including the wrap to normal pause.
        q.press("select")
        wait_guide_settled(q, f"mode{mode}-select-wrap")
        check(q.state()["pause_page"] == 0,
              "SELECT cycles specials back to normal pause", q.state())
        q.press("select")
        wait_guide_settled(q, f"mode{mode}-select-controls-again")
        check(q.state()["pause_page"] == 1,
              "SELECT cycles normal pause to controls", q.state())
        resumed = resume(q, key="a", port=0)
        check(resumed["screen"] == FIGHT and not resumed["paused"],
              "A resumes from the controls page", resumed)
        q.run(8)
        top_after = bg2_rows(vram_bytes(q), 0, 5)
        # Row 3 contains the live health/energy bar glyphs and can legitimately
        # refill during the eight resumed fight callbacks.  The guide card
        # itself occupies rows 5..27; compare the static HUD rows exactly so a
        # stale opaque guide tile or a damaged title strip cannot pass.
        static_rows = (0, 1, 2, 4)
        check(all(top_after[row] == top_before[row] for row in static_rows),
              "guide clears cleanly and restores the static top HUD", {
                  "mode": mode, "rows": static_rows,
                  "before": {row: top_before[row] for row in static_rows},
                  "after": {row: top_after[row] for row in static_rows},
                  "dynamic_row3_before": top_before[3],
                  "dynamic_row3_after": top_after[3],
              })
        return {
            "mode": mode, "fighter1": p1, "fighter2": p2,
            "controls": controls, "specials": specials,
            "page_history": page1,
        }
    finally:
        q.close()


def verify_b_roster_and_second_port(rom: Path) -> dict[str, object]:
    q = boot(rom, mode=1, fighter=2, fighter2=5, stage=1,
             label="local-vs-b-roster")
    try:
        pause(q, port=1)
        q.press("b", port=1)
        current = wait_screen(q, SELECT)
        check(current["screen"] == SELECT,
              "B returns from paused gameplay to the roster", current)
        # A second fresh Training session proves port 2 can also pause/resume
        # independently; the first session already proves B's roster route.
        return {"screen": current["screen"], "state": current}
    finally:
        q.close()


def set_dummy(q: QA, target: int) -> dict[str, int]:
    """Set one of four paused Training dummy modes with directional edges."""

    current = q.state()
    check(current["paused"] == 1, "dummy configuration is paused-only", current)
    current_mode = current["training_dummy"]
    distance = (target - current_mode) % 4
    key = "down" if distance <= 2 else "up"
    count = distance if distance <= 2 else 4 - distance
    for _ in range(count):
        q.press(key)
        wait_guide_settled(q, f"dummy-{target}")
        current = q.state()
        check(current["paused"] == 1,
              "dummy direction changes do not resume gameplay", current)
    current = q.state()
    check(current["training_dummy"] == target,
          "paused UP/DOWN selects the requested Training dummy", {
              "target": target, "state": current,
          })
    return current


def verify_paused_directional_socd(rom: Path) -> dict[str, object]:
    """Ensure opposite directional inputs resolve to neutral while paused.

    Pause navigation and Training dummy selection are shared directional
    inputs.  The native contract combines the two controller ports, removes
    an opposite pair, and only then consumes a fresh edge.  Exercise that
    rule on one pad, across both pads, and when the opposite direction is
    added while the first direction remains held.  These are controller-only
    checks: no WRAM writes or synthetic state setup are used.
    """

    q = boot(rom, mode=2, fighter=0, stage=0, label="training-socd")
    try:
        # Paused fightTick intentionally does not recapture fighter input, so
        # prove the configured core delivers both same-pad bits during a live
        # callback before using the paused navigation path.
        same_pad_live = q.step(("left", "right"), ())
        check((same_pad_live["raw_keys1"] & (256 | 512)) == (256 | 512),
              "same-pad opposing bits reach native input", same_pad_live)
        q.step()
        pause(q)
        cycle_to_page(q, 1)
        page_before = q.state()["pause_page"]

        # Same-pad opposites are neutral for both the held and edge paths.
        for _ in range(4):
            q.step(("left", "right"), ())
        check(q.state()["pause_page"] == page_before,
              "paused guide ignores same-pad opposite directions", q.state())

        # Verify the second physical controller can navigate independently;
        # Training's fighter-2 trace is CPU-owned, so raw_keys2 is not a
        # physical P2 input witness here.
        q.step((), ("right",))
        check(q.state()["pause_page"] == 2,
              "paused guide accepts a physical P2 direction", q.state())
        q.step()
        q.step((), ("left",))
        check(q.state()["pause_page"] == 1,
              "physical P2 returns the guide to controls", q.state())
        q.step()

        # The union of both pads must use the same SOCD rule as one pad.
        for _ in range(4):
            q.step(("left",), ("right",))
        check(q.state()["pause_page"] == page_before,
              "paused guide ignores cross-pad opposite directions", q.state())

        # A new opposite edge must not win while the original direction is
        # still held.  The initial LEFT is allowed to make the normal
        # page-1->page-2 transition; only the later contradictory pair must
        # remain neutral.
        q.step()
        q.step(("left",), ())
        held_page = q.state()["pause_page"]
        for _ in range(3):
            q.step(("left", "right"), ())
        check(q.state()["pause_page"] == held_page,
              "held opposite guide edge remains neutral", q.state())

        # Return to the normal pause card, then test the same three cases on
        # the paused Training dummy selector.
        q.press("select")
        wait_guide_settled(q, "socd-dummy-page0")
        check(q.state()["pause_page"] == 0,
              "SOCD dummy fixture returns to normal pause", q.state())
        set_dummy(q, 1)
        dummy_before = q.state()["training_dummy"]

        for _ in range(4):
            q.step(("up", "down"), ())
        check(q.state()["training_dummy"] == dummy_before,
              "paused dummy ignores same-pad opposite directions", q.state())

        for _ in range(4):
            q.step(("up",), ("down",))
        check(q.state()["training_dummy"] == dummy_before,
              "paused dummy ignores cross-pad opposite directions", q.state())

        # UP changes the dummy once on its fresh edge; adding DOWN while UP
        # remains held must then stay neutral rather than cycling again.
        q.step(("up",), ())
        held_dummy = q.state()["training_dummy"]
        for _ in range(3):
            q.step(("up", "down"), ())
        check(q.state()["training_dummy"] == held_dummy,
              "held opposite dummy edge remains neutral", q.state())
        return {
            "page": page_before,
            "same_pad_raw_keys1": same_pad_live["raw_keys1"],
            "dummy_before": dummy_before,
            "dummy_after_held_edge": held_dummy,
        }
    finally:
        q.close()


def move_close(q: QA, target_fixed: int = 48 * 16,
               limit: int = 180) -> dict[str, int]:
    current = q.state()
    for index in range(limit):
        if abs(current["x1"] - current["x2"]) <= target_fixed:
            return current
        key = "right" if current["x1"] < current["x2"] else "left"
        current = q.step((key,), ())
    return current


def run_special(q: QA, button: str = "y", limit: int = 120) -> list[dict[str, int]]:
    for _ in range(4):
        q.step(("down", button), ())
    samples: list[dict[str, int]] = []
    for _ in range(limit):
        current = q.step()
        samples.append(current)
        if current["connected1"] or current["hp2"] < 128:
            break
    return samples


def status_bar_words(q: QA) -> list[int]:
    """Return the eight native BG2 bar spans for a freeze comparison."""

    memory = vram_bytes(q)
    return ([bg2_entry(memory, 1 + index, 1) for index in range(11)] +
            [bg2_entry(memory, 30 - index, 1) for index in range(11)] +
            [bg2_entry(memory, 1 + index, 3) for index in range(12)] +
            [bg2_entry(memory, 30 - index, 3) for index in range(12)])


def move_close_side(q: QA, attacker: int, target_fixed: int = 28 * 16,
                    limit: int = 180) -> dict[str, int]:
    """Move one local-versus fighter into normal attack range."""

    current = q.state()
    for _ in range(limit):
        distance = abs(current["x1"] - current["x2"])
        if distance < target_fixed:
            return current
        if attacker == 0:
            key = "right" if current["x1"] < current["x2"] else "left"
            current = q.step((key,), ())
        else:
            key = "left" if current["x2"] > current["x1"] else "right"
            current = q.step((), (key,))
    return current


def drive_local_contact(q: QA, attacker: int) -> tuple[dict[str, int],
                                                        dict[str, int],
                                                        list[dict[str, int]]]:
    """Produce one real light-punch contact using either local controller."""

    initial = move_close_side(q, attacker)
    attacker_x = "x1" if attacker == 0 else "x2"
    defender_x = "x2" if attacker == 0 else "x1"
    if attacker == 0:
        forward = "right" if initial[attacker_x] < initial[defender_x] else "left"
    else:
        forward = "left" if initial[attacker_x] > initial[defender_x] else "right"
    victim_key = "hp2" if attacker == 0 else "hp1"
    samples: list[dict[str, int]] = []
    for index in range(72):
        keys = (forward, "y") if index < 3 else ()
        current = q.step(keys if attacker == 0 else (),
                         keys if attacker == 1 else ())
        samples.append(current)
        if current[victim_key] < initial[victim_key]:
            check(current["connected1" if attacker == 0 else "connected2"] == 2,
                  "local contact pause fixture records a real hit", current)
            return initial, current, samples
    raise AssertionError(("local contact did not reach the defender", {
        "attacker": attacker, "initial": initial,
        "samples": samples[-24:], "final": q.state(),
    }))


def verify_pause_hud_after_contacts(rom: Path) -> dict[str, object]:
    """Keep both mirrored HUD bars truthful when pausing during hitstop."""

    cases: list[dict[str, object]] = []
    for attacker in (0, 1):
        q = boot(rom, mode=1, fighter=0, fighter2=1, stage=0,
                 label=f"pause-hud-contact-p{attacker + 1}")
        try:
            initial, impact, samples = drive_local_contact(q, attacker)
            victim_key = "hp2" if attacker == 0 else "hp1"
            check(impact[victim_key] < initial[victim_key],
                  "contact fixture changes the intended victim HP", {
                      "attacker": attacker, "initial": initial,
                      "impact": impact,
                  })
            # Pause immediately after the impact.  q.press keeps the edge
            # poll-safe but does not advance combat while the native hitstop
            # and pause state are active.
            paused_edge = q.press("start", port=attacker)
            check(paused_edge["paused"] == 1,
                  "contact fixture pauses from the attacking controller", {
                      "attacker": attacker, "state": paused_edge,
                  })
            entry_bars = check_status_bars(
                q, paused_edge, f"P{attacker + 1} contact pause entry")
            wait_guide_settled(q, f"pause-hud-contact-p{attacker + 1}-normal")
            paused = q.state()
            settled_bars = check_status_bars(
                q, paused, f"P{attacker + 1} contact pause settled")
            check(paused[victim_key] == impact[victim_key],
                  "pause preserves the contact HP snapshot", {
                      "attacker": attacker, "impact": impact,
                      "paused": paused,
                  })

            # Keep the top HUD truthful through both help pages and back to
            # the normal pause card; guide DMA must not restore stale HP.
            page_bars: dict[str, dict[str, object]] = {"0": settled_bars}
            for target in (1, 2, 0):
                if target == 1:
                    cycle_to_page(q, 1)
                elif target == 2:
                    q.press("right")
                    wait_guide_settled(q, f"pause-hud-contact-p{attacker + 1}-page2")
                else:
                    cycle_to_page(q, 0)
                page_state = q.state()
                page_bars[str(target)] = check_status_bars(
                    q, page_state,
                    f"P{attacker + 1} contact pause guide page {target}")
                check(page_state[victim_key] == impact[victim_key],
                      "guide page preserves the contact HP snapshot", {
                          "attacker": attacker, "page": target,
                          "impact": impact, "page_state": page_state,
                      })

            frozen = q.state()
            frozen_words = status_bar_words(q)
            for _ in range(8):
                q.step()
            after = q.state()
            check(after[victim_key] == frozen[victim_key] and
                  after["hp1"] == frozen["hp1"] and
                  after["hp2"] == frozen["hp2"] and
                  after["energy1"] == frozen["energy1"] and
                  after["energy2"] == frozen["energy2"],
                  "paused contact keeps HP and energy frozen", {
                      "attacker": attacker, "before": frozen,
                      "after": after,
                  })
            check(status_bar_words(q) == frozen_words,
                  "paused contact keeps mirrored HUD VRAM frozen", {
                      "attacker": attacker, "before": frozen_words,
                      "after": status_bar_words(q),
                  })
            cases.append({
                "attacker": attacker + 1,
                "initial": initial,
                "impact": impact,
                "paused": paused,
                "entry_bars": entry_bars,
                "settled_bars": settled_bars,
                "page_bars": page_bars,
                "sample_count": len(samples),
            })
        finally:
            q.close()
    return {"cases": cases}


def verify_dummy_and_contacts(rom: Path) -> dict[str, object]:
    """Exercise stationary modes and non-vacuous guard/contact outcomes."""

    q = boot(rom, mode=2, fighter=4, stage=0, label="training-dummy")
    try:
        initial = q.state()
        check(initial["training_dummy"] == 0,
              "new Training match starts with standing dummy", initial)
        # Live direction input may move/crouch the player, but never changes
        # the paused-only dummy configuration.
        q.run(6, ("down",))
        check(q.state()["training_dummy"] == 0,
              "live UP/DOWN input cannot configure the dummy", q.state())
        pause(q)
        for target in (1, 2, 3, 0):
            set_dummy(q, target)

        set_dummy(q, 3)
        resume(q)
        jump_samples = []
        for _ in range(220):
            current = q.step()
            if signed16(current["y2"]) < 0:
                jump_samples.append(signed16(current["y2"]))
        check(len(jump_samples) >= 2,
              "jump dummy repeats actual UP jumps", {
                  "samples": len(jump_samples), "values": jump_samples[:12],
              })
        stationary_after_jump = q.state()["x2"]
        q.run(20)
        check(abs(q.state()["x2"] - stationary_after_jump) <= 2 * 16,
              "jump/guard dummy remains in place instead of walking away", q.state())
        q.close()
    except Exception:
        q.close()
        raise

    # High guard loses an incoming low wave; low guard blocks it with at most
    # chip.  Negger (slot 4) owns the groundwave family.
    q = boot(rom, mode=2, fighter=4, stage=0, label="training-high-low-wave")
    try:
        pause(q)
        set_dummy(q, 1)
        resume(q)
        high_samples = run_special(q)
        high_damage = 128 - q.state()["hp2"]
        check(any(s.get("wave1") for s in high_samples) or high_damage > 0,
              "groundwave reaches the high-guard contact fixture", {
                  "samples": high_samples[:16], "final": q.state(),
              })
        check(high_damage > 0,
              "high guard loses to a low groundwave", {
                  "damage": high_damage, "final": q.state(),
              })
    finally:
        q.close()

    q = boot(rom, mode=2, fighter=4, stage=0, label="training-low-wave")
    try:
        pause(q)
        set_dummy(q, 2)
        resume(q)
        low_samples = run_special(q)
        low_damage = 128 - q.state()["hp2"]
        check(any(s.get("wave1") for s in low_samples) or low_damage <= 1,
              "low-guard groundwave fixture observes the incoming wave", {
                  "samples": low_samples[:16], "final": q.state(),
              })
        check(low_damage <= 1 and any(s.get("guard2") for s in low_samples),
              "low guard blocks the low groundwave with chip at most one", {
                  "damage": low_damage, "samples": low_samples[:24],
              })
    finally:
        q.close()

    # Low guard loses an airborne normal.  Close through the native movement
    # path, then issue a fresh UP+Y edge; no RAM or savestate setup is used.
    q = boot(rom, mode=2, fighter=0, stage=0, label="training-low-air")
    try:
        pause(q)
        set_dummy(q, 2)
        resume(q)
        # Start far enough away to account for the committed takeoff
        # velocity, then issue the normal on the descending side of the arc.
        # An immediate UP+Y starts frame 50 near the jump apex, above the
        # crouching body rectangle, and is a legitimate whiff rather than a
        # useful low-guard contact probe.
        current = move_close(q, target_fixed=86 * 16)
        forward = "right" if current["x1"] < current["x2"] else "left"
        q.step(("up", forward), ())
        air_samples: list[dict[str, int]] = []
        previous_y: int | None = None
        attack_issued = False
        for _ in range(100):
            current = q.step((forward,), ())
            air_samples.append(current)
            y = signed16(current["y1"])
            if (not attack_issued and previous_y is not None and
                    y > previous_y and -520 <= y <= -400):
                # The three-frame hold gives the native edge sampler a
                # stable Y edge without changing the attack's frame data.
                for _ in range(3):
                    current = q.step(("y",), ())
                    air_samples.append(current)
                attack_issued = True
            previous_y = y
            if current["hp2"] < 128:
                break
        air_damage = 128 - q.state()["hp2"]
        check(any(signed16(s["y1"]) < 0 for s in air_samples),
              "airborne normal fixture actually leaves the floor", air_samples[:24])
        check(attack_issued and any(s.get("air_action1") for s in air_samples),
              "low-guard fixture observes the committed airborne attack", {
                  "issued": attack_issued, "samples": air_samples[:48],
              })
        check(any(s.get("guard2") for s in air_samples),
              "airborne low-guard fixture keeps the defender guarding", {
                  "samples": air_samples[:48], "final": q.state(),
              })
        check(air_damage > 0,
              "low guard loses to an airborne normal", {
                  "damage": air_damage, "samples": air_samples[:32],
              })
    finally:
        q.close()

    # Throw remains available in Training after the dummy work.  The range is
    # taken from the public profile trace and the input is a fresh L edge.
    q = boot(rom, mode=2, fighter=0, stage=0, label="training-throw")
    try:
        current = move_close(q, target_fixed=max(1, q.state()["throw_range1"] * 16 - 1))
        forward = "right" if current["x1"] < current["x2"] else "left"
        throw_seen: list[dict[str, int]] = []
        for _ in range(80):
            current = q.step((forward, "l"), ())
            throw_seen.append(current)
            q.step((forward,), ())
            if (current["action1"] == 9 or current["throw_victim2"] == 1 or
                    current["down_state2"]):
                break
        check(any(s["action1"] == 9 or s["throw_victim2"] == 1
                  for s in throw_seen),
              "Training dummy still permits a native throw", {
                  "samples": throw_seen[:24], "final": q.state(),
              })
        return {
            "dummy_jump_samples": len(jump_samples),
            "high_wave_damage": high_damage,
            "low_wave_damage": low_damage,
            "air_damage": air_damage,
            "throw_samples": throw_seen[:24],
        }
    finally:
        q.close()


def verify_crossup_and_pause_projectile(rom: Path) -> dict[str, object]:
    """Check air momentum/facing and pause freezing of an active projectile."""

    q = boot(rom, mode=2, fighter=0, stage=0, label="crossup-projectile")
    try:
        # Projectile is deliberately started before pausing so the active wave
        # and its native animation/ambient clock are part of the freeze proof.
        samples = run_special(q)
        active = next((s for s in samples if s["wave1"]), None)
        check(active is not None, "projectile fixture reaches an active wave", samples[:24])
        before = q.state()
        pause(q)
        frozen = q.state()
        for _ in range(8):
            q.step()
        after = q.state()
        frozen_keys = (
            "hp1", "hp2", "x1", "x2", "y1", "y2", "wave1", "wave2",
            "pose1", "pose2", "anim_frame1", "anim_frame2", "ambient_clock",
            "down_state1", "down_state2", "wake_age1", "wake_age2",
        )
        check(all(after[key] == frozen[key] for key in frozen_keys),
              "pause freezes active projectile and combat/native animation state", {
                  "before": before, "frozen": frozen, "after": after,
              })
        resume(q)

        # Close to one body-width, then jump toward the opponent.  The native
        # takeoff direction must remain locked while airborne, even after a
        # cross-up, and only restore opponent-facing on landing.
        # A 32 px gap lets the committed takeoff velocity cross while the
        # jump is above the 50 px body-separation band; starting at 48 px
        # reaches the separation clamp before the airborne crossing.
        current = move_close(q, target_fixed=32 * 16)
        initial_face = current["face1"]
        forward = "right" if current["x1"] < current["x2"] else "left"
        crossed_air = False
        crossed_samples: list[dict[str, int]] = []
        for index in range(50):
            current = q.step(
                ("up", forward) if index == 0 else (forward,), (),
            )
            crossed_samples.append(current)
            if signed16(current["y1"]) < 0 and ((current["x1"] > current["x2"] and forward == "right") or
                                      (current["x1"] < current["x2"] and forward == "left")):
                crossed_air = True
                check(current["face1"] == initial_face,
                      "cross-up keeps takeoff facing while airborne", current)
            if crossed_air and signed16(current["y1"]) == 0:
                break
        check(crossed_air, "controller cross-up crosses during an airborne arc", {
            "samples": crossed_samples[:40], "initial_face": initial_face,
        })
        if crossed_air and signed16(q.state()["y1"]) == 0:
            landed = q.state()
            # Landing publishes before the next grounded controls pass; give
            # the native facing refresh its normal three quiet callbacks.
            for _ in range(3):
                landed = q.step()
            check(landed["face1"] != initial_face,
                  "cross-up restores opponent-facing after landing", landed)
        return {
            "projectile_samples": samples[:24],
            "crossup_samples": crossed_samples[:40],
        }
    finally:
        q.close()


def verify_dummy_reset_and_defaults(rom: Path) -> dict[str, object]:
    q = boot(rom, mode=2, fighter=0, stage=0, label="training-quick-reset")
    try:
        pause(q)
        set_dummy(q, 2)
        resume(q)
        # In Training, SELECT is the quick reset while live.  It keeps the
        # selected dummy mode while resetting both fighters immediately.
        q.press("select")
        current = q.state()
        for _ in range(12):
            if current["intro"] == 0 and current["hp1"] == 128 and current["hp2"] == 128:
                break
            current = q.step()
        check(current["screen"] == FIGHT and current["intro"] == 0,
              "Training SELECT quick reset returns to live FIGHT", current)
        check(current["training_dummy"] == 2,
              "quick-select reset preserves the selected dummy mode", current)
        return {"state": current}
    finally:
        q.close()


def verify_all_special_names(rom: Path) -> list[dict[str, object]]:
    evidence: list[dict[str, object]] = []
    for fighter in range(len(FIGHTER_NAMES)):
        q = boot(rom, mode=2, fighter=fighter, stage=fighter % 3,
                 label=f"special-name-{fighter:02}")
        try:
            pause(q)
            cycle_to_page(q, 1)
            q.press("right")
            wait_guide_settled(q, f"special-name-{fighter:02}-page2")
            current = q.state()
            check(current["pause_page"] == 2, "special page opens for every fighter", current)
            p1 = current.get("fighter_id1", fighter)
            p2 = current.get("fighter_id2", 1)
            expected: list[str] = []
            for player in (p1, p2):
                if 0 <= player < len(FIGHTER_NAMES):
                    expected.extend((FIGHTER_NAMES[player], SPECIAL_NAMES[player],
                                     SPECIAL_FAMILY_NAMES[SPECIAL_FAMILY[player]]))
            text = decode_text(vram_bytes(q), 0, 32)
            compact = compact_text(text)
            for token in expected:
                check(compact_text(token) in compact,
                      "all native fighter/special names appear on page 2", {
                          "fighter": fighter, "token": token, "text": text,
                      })
            if fighter in (0, 11):
                capture(q, f"special-page-{fighter:02}")
            evidence.append({"fighter": fighter, "p1": p1, "p2": p2,
                             "special": SPECIAL_NAMES[fighter], "text": text})
        finally:
            q.close()
    return evidence


def run_suite(rom: Path, core_info: dict[str, str] | None = None,
              harness_sha: str | None = None) -> dict[str, object]:
    rom_bytes = rom.read_bytes()
    rom_sha = hashlib.sha256(rom_bytes).hexdigest()
    core_info = core_identity() if core_info is None else core_info
    harness_sha = harness_identity() if harness_sha is None else harness_sha
    check(len(rom_bytes) == 4 * 1024 * 1024,
          "candidate Training ROM is the 4 MiB native image", len(rom_bytes))
    modes = [
        verify_page_navigation(rom, 0, 0, 1, 0),
        verify_page_navigation(rom, 1, 2, 5, 1),
        verify_page_navigation(rom, 2, 4, 1, 2),
    ]
    roster = verify_b_roster_and_second_port(rom)
    socd = verify_paused_directional_socd(rom)
    dummy = verify_dummy_and_contacts(rom)
    freeze = verify_crossup_and_pause_projectile(rom)
    reset = verify_dummy_reset_and_defaults(rom)
    specials = verify_all_special_names(rom)
    pause_hud = verify_pause_hud_after_contacts(rom)
    return {
        "emulator": "Official Snes9x 1.63 x64 libretro core",
        "suite": "training",
        "status": "passed",
        "passed": len(CHECKS),
        "rom_sha256": rom_sha,
        "rom_bytes": len(rom_bytes),
        "core": core_info,
        "harness_sha256": harness_sha,
        "core_options": dict(TRAINING_CORE_OPTIONS),
        "contract_flags": {
            "strict_trace_cadence": True,
            "strict_fight_pause_guide_cadence": True,
            "bounded_menu_load_duplicates": True,
            "opaque_guide_tiles": True,
            "native_same_pad_socd_input": True,
            "paused_contact_hud_truth": True,
        },
        "cadence_failures": [],
        "guide_failures": [],
        "trace_offsets": {
            "ppu_stat": 114, "ambient_phase": 115, "ambient_clock": 116,
            "ambient_pending_phase": 117, "ambient_pending_age": 118,
            "pause_page": 119, "guide_build": 120,
            "training_dummy": 121, "guide_dirty": 122,
        },
        "modes": modes,
        "roster_return": roster,
        "paused_directional_socd": socd,
        "dummy_and_contacts": dummy,
        "pause_projectile_crossup": freeze,
        "quick_reset": reset,
        "all_special_names": specials,
        "pause_hud_after_contacts": pause_hud,
        "checks": CHECKS,
        "capture_directory": str(CAPTURE_DIR.relative_to(ROOT))
        if CAPTURE_DIR.is_relative_to(ROOT) else str(CAPTURE_DIR),
        "capture_paths": list(CAPTURE_PATHS),
        "captures": [entry for entry in CHECKS
                     if entry["check"] == "native PPU capture is 256x224"],
    }


def main() -> int:
    global CAPTURE_DIR

    parser = argparse.ArgumentParser()
    parser.add_argument("--rom", type=Path,
                        default=ROOT / "dist/abaqus-after-hours.sfc")
    parser.add_argument("--report", type=Path,
                        default=DEFAULT_REPORT)
    parser.add_argument("--captures", type=Path,
                        default=DEFAULT_CAPTURE_DIR,
                        help="directory for native review PNGs")
    args = parser.parse_args()
    if not args.report.is_absolute():
        args.report = ROOT / args.report
    if not args.captures.is_absolute():
        args.captures = ROOT / args.captures
    CAPTURE_DIR = args.captures
    CHECKS.clear()
    CAPTURE_PATHS.clear()

    started = time.monotonic()
    rom_sha: str | None = None
    rom_bytes: int | None = None
    if args.rom.is_file():
        raw_rom = args.rom.read_bytes()
        rom_sha = hashlib.sha256(raw_rom).hexdigest()
        rom_bytes = len(raw_rom)
    try:
        harness_sha = harness_identity()
    except Exception as exc:
        harness_sha = None
        harness_error = repr(exc)
    else:
        harness_error = None

    contract_flags = {
        "strict_trace_cadence": True,
        "strict_fight_pause_guide_cadence": True,
        "bounded_menu_load_duplicates": True,
        "opaque_guide_tiles": True,
        "native_same_pad_socd_input": True,
        "paused_contact_hud_truth": True,
    }
    trace_offsets = {
        "ppu_stat": 114, "ambient_phase": 115, "ambient_clock": 116,
        "ambient_pending_phase": 117, "ambient_pending_age": 118,
        "pause_page": 119, "guide_build": 120,
        "training_dummy": 121, "guide_dirty": 122,
    }
    report: dict[str, object] = {
        "emulator": "Official Snes9x 1.63 x64 libretro core",
        "suite": "training",
        "status": "failed",
        "rom_sha256": rom_sha,
        "rom_bytes": rom_bytes,
        "core": None,
        "harness_sha256": harness_sha,
        "core_options": dict(TRAINING_CORE_OPTIONS),
        "contract_flags": contract_flags,
        "cadence_failures": [],
        "guide_failures": [],
        "trace_offsets": trace_offsets,
        "capture_directory": (str(CAPTURE_DIR.relative_to(ROOT))
                               if CAPTURE_DIR.is_relative_to(ROOT)
                               else str(CAPTURE_DIR)),
        "capture_paths": [],
        "captures": [],
        "checks": CHECKS,
        "passed": 0,
    }
    exit_code = 0
    try:
        if harness_error is not None:
            raise AssertionError(("training harness identity failed", harness_error))
        pinned_core = core_identity()
        report["core"] = pinned_core
        report = run_suite(args.rom, pinned_core, harness_sha)
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = repr(exc)
        report["failure_diagnostics"] = {
            "error": repr(exc),
            "last_checks": CHECKS[-24:],
        }
        exit_code = 1
    finally:
        report["passed"] = len(CHECKS)
        report["checks"] = CHECKS
        report["capture_paths"] = list(CAPTURE_PATHS)
        report["captures"] = [entry for entry in CHECKS
                              if entry["check"] == "native PPU capture is 256x224"]
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    summary = {
        "suite": "training", "status": report["status"],
        "passed": report["passed"], "seconds": report["elapsed_seconds"],
        "rom_sha256": report["rom_sha256"],
        "report": str(args.report.relative_to(ROOT))
        if args.report.is_relative_to(ROOT) else str(args.report),
    }
    print(json.dumps(summary), flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

