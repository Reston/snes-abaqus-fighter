"""Capture small native cross-up review clips from controller-only play.

This is a human-review aid rather than another release gate.  It reuses the
existing real-controller cross-up probe, recording the unmodified RGB frames
delivered by the libretro video callback.  The two emulator boots are kept
sequential because the Snes9x core is process-global.  No emulated memory or
save state is written by this script.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageSequence


ROOT = Path(__file__).resolve().parents[1]
ROM_PATH = ROOT / "dist" / "abaqus-after-hours.sfc"
MANIFEST_PATH = ROOT / "dist" / "manifest.json"
GIF_DIR = ROOT / "docs" / "screenshots" / "crossup"
REVIEW_PATH = ROOT / "docs" / "crossup-review.json"
FRAME_SIZE = (256, 224)
GIF_DURATION_MS = (20, 20, 10)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def signed16(value: int) -> int:
    return value - 0x10000 if value & 0x8000 else value


def process_contract() -> dict[str, Any]:
    """Describe the background runner inherited by this process."""

    priority_class: int | None = None
    process_affinity: list[int] = []
    api = None
    if os.name == "nt":
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.GetCurrentProcess.restype = ctypes.c_void_p
        api.GetPriorityClass.argtypes = [ctypes.c_void_p]
        api.GetPriorityClass.restype = ctypes.c_uint32
        process = api.GetCurrentProcess()
        priority_class = int(api.GetPriorityClass(process))
        process_mask = ctypes.c_size_t()
        system_mask = ctypes.c_size_t()
        api.GetProcessAffinityMask.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_size_t),
            ctypes.POINTER(ctypes.c_size_t),
        ]
        api.GetProcessAffinityMask.restype = ctypes.c_bool
        if api.GetProcessAffinityMask(
            process, ctypes.byref(process_mask), ctypes.byref(system_mask)
        ):
            mask = int(process_mask.value)
            process_affinity = [bit for bit in range(mask.bit_length()) if mask & (1 << bit)]

    contract = {
        "runner": "build/run_background.py",
        "stdin": "DEVNULL",
        "priority_class": priority_class,
        "priority_name": "BELOW_NORMAL" if priority_class == 0x4000 else None,
        "logical_processors": process_affinity,
        "controller_only": True,
        "gui_opened": False,
        "audio_device_opened": False,
        "audio_playback": False,
        "emulated_memory_writes": 0,
        "save_states": False,
        "sequential_boots": True,
        "max_active_emulators": 1,
    }
    if os.name == "nt":
        if priority_class != 0x4000:
            raise RuntimeError(
                f"capture must inherit BELOW_NORMAL priority, got {priority_class!r}"
            )
        if len(process_affinity) != 2:
            raise RuntimeError(
                f"capture must inherit the runner's two-CPU affinity, got {process_affinity!r}"
            )
    return contract


class RecordingEmulator:
    """Emulator subclass that only records callback frames and trace state."""

    instances: list["RecordingEmulator"] = []

    def __init__(self, base_class: type[Any], *args: Any, **kwargs: Any) -> None:
        self._base_class = base_class
        self.samples: list[dict[str, Any]] = []
        base_class.__init__(self, *args, **kwargs)
        self.__class__.instances.append(self)

    def state(self) -> dict[str, int]:
        return self._base_class.state(self)

    def tap(self, key: str, port: int = 0) -> dict[str, int]:
        return self._base_class.tap(self, key, port)

    def close(self) -> None:
        self._base_class.close(self)

    def run(self, n: int = 1, p1: Any = (), p2: Any = ()) -> dict[str, int]:
        result: dict[str, int] = {}
        for _ in range(n):
            result = self._base_class.run(self, 1, p1=p1, p2=p2)
            # Capture only settled live gameplay frames.  The image is the
            # exact RGB callback frame, with no annotation or resampling.
            if (
                self.frame is not None
                and result.get("screen") == 3
                and result.get("intro") == 0
            ):
                self.samples.append(
                    {
                        "image": self.frame.copy(),
                        "state": dict(result),
                        "host_frame": int(self.frames),
                    }
                )
        return result


def compact_state(state: dict[str, int]) -> dict[str, int]:
    fields = (
        "frame",
        "x1",
        "x2",
        "y1",
        "y2",
        "face1",
        "face2",
        "action1",
        "action2",
        "anim_frame1",
        "anim_frame2",
        "anim_tick1",
        "anim_tick2",
        "air_action1",
        "air_action2",
        "connected1",
        "connected2",
        "hp1",
        "hp2",
        "hurt1",
        "hurt2",
        "guard1",
        "guard2",
        "hitstop",
        "landing1",
        "landing2",
        "down_state1",
        "down_state2",
        "raw_keys1",
        "raw_keys2",
    )
    return {name: int(state.get(name, 0)) for name in fields}


def capture_case(inputs: Any, base_class: type[Any], port: int) -> tuple[dict[str, Any], RecordingEmulator]:
    """Run one existing cross-up case with one recording emulator boot."""

    RecordingEmulator.instances = []
    inputs.Emulator = lambda *args, **kwargs: RecordingEmulator(  # type: ignore[assignment]
        base_class, *args, **kwargs
    )
    try:
        result = inputs._cross_up_contact_case(port, key="a")
    finally:
        inputs.Emulator = base_class
    if len(RecordingEmulator.instances) != 1:
        raise RuntimeError(
            f"expected one sequential emulator boot for P{port + 1}, "
            f"saw {len(RecordingEmulator.instances)}"
        )
    recorder = RecordingEmulator.instances[0]
    if base_class._active_instance is not None:
        raise RuntimeError("cross-up helper left the process-global emulator active")
    return result, recorder


def trim_case(
    result: dict[str, Any], recorder: RecordingEmulator, port: int
) -> dict[str, Any]:
    attacker = str(port + 1)
    defender = str(2 - port)
    sign = 1 if port == 0 else -1
    direction = "right" if port == 0 else "left"
    samples = recorder.samples
    if not samples:
        raise RuntimeError(f"P{port + 1} cross-up produced no live PPU frames")

    def state_at(index: int) -> dict[str, int]:
        return samples[index]["state"]

    airborne = [
        index
        for index, sample in enumerate(samples)
        if signed16(int(sample["state"].get(f"y{attacker}", 0))) < 0
    ]
    if not airborne:
        raise RuntimeError(f"P{port + 1} cross-up capture has no airborne frame")
    first_airborne = airborne[0]
    crossed = [
        index
        for index in airborne
        if (
            int(state_at(index).get(f"x{attacker}", 0))
            - int(state_at(index).get(f"x{defender}", 0))
        )
        * sign
        > 0
    ]
    if not crossed:
        raise RuntimeError(f"P{port + 1} cross-up capture never crossed the defender")
    first_crossed = crossed[0]

    contact_field = f"connected{attacker}"
    contacts = [
        index
        for index, sample in enumerate(samples)
        if int(sample["state"].get(contact_field, 0)) == 2
    ]
    if not contacts:
        # The existing helper has already asserted contact.  Keep this guard
        # so the review artifact cannot silently become a jump-only clip.
        raise RuntimeError(f"P{port + 1} cross-up capture has no contact trace")
    first_contact = contacts[0]

    landed = [
        index
        for index in range(first_airborne + 1, len(samples))
        if signed16(int(samples[index]["state"].get(f"y{attacker}", 0))) == 0
        and int(samples[index]["state"].get(f"action{attacker}", 0)) == 0
        and int(samples[index]["state"].get(f"air_action{attacker}", 0)) == 0
    ]
    if not landed:
        raise RuntimeError(f"P{port + 1} cross-up capture has no settled landing")
    first_landed = landed[0]
    start = max(0, first_airborne - 8)
    end = min(len(samples), first_landed + 9)
    selected = samples[start:end]
    if len(selected) < 8:
        raise RuntimeError(f"P{port + 1} cross-up clip is unexpectedly short: {len(selected)}")
    if not (start <= first_crossed < end and start <= first_contact < end):
        raise RuntimeError(f"P{port + 1} cross-up evidence fell outside the trimmed clip")

    images = [sample["image"].convert("RGB") for sample in selected]
    if any(image.size != FRAME_SIZE for image in images):
        raise RuntimeError(f"P{port + 1} returned a non-native frame size")
    source_frame_hashes = [sha256_bytes(image.tobytes()) for image in images]
    trace = [compact_state(sample["state"]) for sample in selected]
    frame_numbers = [int(sample["state"].get("frame", 0)) for sample in selected]
    host_frames = [int(sample["host_frame"]) for sample in selected]

    def local_index(global_index: int) -> int:
        return global_index - start

    contact = result.get("contact") or state_at(first_contact)
    landed_state = state_at(first_landed)
    return {
        "side": f"P{port + 1}",
        "direction": f"{direction}-cross",
        "attacker": f"P{attacker}",
        "defender": f"P{defender}",
        "helper": "tools/test_inputs.py:_cross_up_contact_case",
        "helper_parameters": {"port": port, "key": "a", "guard": "", "delay": 0},
        "frames": len(images),
        "native_frame_numbers": frame_numbers,
        "host_video_callback_frames": host_frames,
        "source_rgb_sha256": source_frame_hashes,
        "trace": trace,
        "proof": {
            "first_airborne_clip_frame": local_index(first_airborne),
            "first_crossed_clip_frame": local_index(first_crossed),
            "first_contact_clip_frame": local_index(first_contact),
            "first_landed_clip_frame": local_index(first_landed),
            "takeoff_facing": int(state_at(first_airborne).get(f"face{attacker}", 0)),
            "landed_facing": int(landed_state.get(f"face{attacker}", 0)),
            "contact_trace": compact_state(contact),
            "helper_effect": result.get("effect"),
        },
        "gif_timing": {
            "source": "one image per consecutive native libretro video callback",
            "fixed_rate_inspection_sweep": True,
            "duration_ms_cycle": list(GIF_DURATION_MS),
            "average_duration_ms": sum(GIF_DURATION_MS) / len(GIF_DURATION_MS),
            "gif_centisecond_quantization": True,
            "note": "GIF timing is a review playback approximation; duplicate consecutive pixels may be coalesced by GIF encoding while retaining their duration; it does not claim in-game animation timing.",
        },
        "_images": images,
    }


def write_gif(path: Path, images: list[Image.Image]) -> tuple[int, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    durations = [GIF_DURATION_MS[index % len(GIF_DURATION_MS)] for index in range(len(images))]
    first, *rest = images
    first.save(
        path,
        format="GIF",
        save_all=True,
        append_images=rest,
        duration=durations,
        loop=0,
        disposal=1,
        optimize=True,
    )
    decoded_pixels: list[bytes] = []
    with Image.open(path) as decoded:
        if decoded.size != FRAME_SIZE:
            raise RuntimeError(f"{path} decoded at {decoded.size}, expected {FRAME_SIZE}")
        for frame in ImageSequence.Iterator(decoded):
            decoded_pixels.append(frame.convert("RGB").tobytes())
    decoded_count = len(decoded_pixels)
    if decoded_count > len(images):
        raise RuntimeError(
            f"{path} decoded {decoded_count} frames, source has {len(images)}"
        )
    # GIF may coalesce adjacent identical source frames.  Every decoded
    # composite must still be an exact source RGB frame; no quantized or
    # annotated replacement is acceptable for this review artifact.
    source_pixels = [image.tobytes() for image in images]
    source_index = 0
    for decoded_frame in decoded_pixels:
        if source_index == len(source_pixels) or source_pixels[source_index] != decoded_frame:
            raise RuntimeError(f"{path} decoded a pixel frame absent from the source callback frames")
        while source_index < len(source_pixels) and source_pixels[source_index] == decoded_frame:
            source_index += 1
    if source_index != len(source_pixels):
        raise RuntimeError(
            f"{path} dropped non-identical source frames while encoding: "
            f"{len(images) - source_index} remain"
        )
    return decoded_count, sha256_file(path)


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    rom_bytes = ROM_PATH.read_bytes()
    rom_sha = sha256_bytes(rom_bytes)
    if rom_sha != manifest.get("sha256"):
        raise RuntimeError(
            f"ROM does not match current manifest: {rom_sha} != {manifest.get('sha256')}"
        )
    version = str(manifest.get("version", ""))
    parts = version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts) or tuple(map(int, parts)) < (0, 15, 0):
        raise RuntimeError(f"cross-up review requires v0.15.0 or later, got {version}")

    host = process_contract()

    # Import only after the contract check so a rejected non-background run
    # cannot boot the core.  This is the same controller helper used by the
    # input suite; monkeypatching its Emulator symbol only wraps its run call.
    sys.path.insert(0, str(ROOT / "tools"))
    import emulator  # type: ignore
    import test_inputs  # type: ignore

    base_class = emulator.Emulator
    captures: list[dict[str, Any]] = []
    for port in (0, 1):
        result, recorder = capture_case(test_inputs, base_class, port)
        captures.append(trim_case(result, recorder, port))

    if base_class._active_instance is not None:
        raise RuntimeError("a core instance remained active after sequential captures")

    GIF_DIR.mkdir(parents=True, exist_ok=True)
    capture_records: list[dict[str, Any]] = []
    for capture, name in zip(captures, ("p1.gif", "p2.gif")):
        images = capture.pop("_images")
        gif_path = GIF_DIR / name
        decoded_count, gif_sha = write_gif(gif_path, images)
        capture["gif"] = str(gif_path.relative_to(ROOT)).replace("\\", "/")
        capture["gif_bytes"] = gif_path.stat().st_size
        capture["gif_sha256"] = gif_sha
        capture["decoded_gif_frames"] = decoded_count
        capture_records.append(capture)

    harness_paths = (
        "tools/make_crossup_review.py",
        "tools/test_inputs.py",
        "tools/emulator.py",
        "tools/test_stages.py",
        "build/run_background.py",
    )
    harness_sha = {
        path: sha256_file(ROOT / path)
        for path in harness_paths
    }
    core_path = ROOT / ".tools" / "core" / "snes9x_libretro.dll"
    core_bytes = core_path.read_bytes()
    report = {
        "status": "passed",
        "version": manifest["version"],
        "rom": str(ROM_PATH.relative_to(ROOT)).replace("\\", "/"),
        "rom_bytes": len(rom_bytes),
        "rom_sha256": rom_sha,
        "header_checksum": manifest.get("checksum"),
        "scope": "two native moving cross-up review captures from real controller input",
        "evidence_type": "visual review aid; not a release-scale gate",
        "controller_only": True,
        "audio": "callback capture is muted; no audio device or playback",
        "core": {
            "path": str(core_path.relative_to(ROOT)).replace("\\", "/"),
            "bytes": len(core_bytes),
            "sha256": sha256_bytes(core_bytes),
            "identity": "official Snes9x 1.63 libretro core",
        },
        "harness_sha256": harness_sha,
        "host_contract": host,
        "capture_contract": {
            "native_dimensions": list(FRAME_SIZE),
            "source": "PIL RGB frames delivered by the unmodified libretro video callback",
            "overlays": False,
            "art_or_frame_edits": False,
            "emulated_memory_writes": 0,
            "save_states": False,
            "boots": 2,
            "sequential_boots": True,
            "max_active_emulators": 1,
        },
        "captures": capture_records,
        "limitations": [
            "GIF playback uses a fixed inspection sweep and centisecond durations; it is not in-game animation timing.",
            "The clips show the current controller-driven neutral local-versus helper path, not every matchup, guard state, or stage.",
            "This visual aid does not replace native suites, human gameplay, physical-controller, likeness/consent, or public-use review.",
        ],
    }
    REVIEW_PATH.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "review": str(REVIEW_PATH),
                "rom_sha256": rom_sha,
                "captures": [
                    {
                        "side": item["side"],
                        "frames": item["frames"],
                        "gif_sha256": item["gif_sha256"],
                        "first_contact_clip_frame": item["proof"]["first_contact_clip_frame"],
                    }
                    for item in capture_records
                ],
                "host_contract": host,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
