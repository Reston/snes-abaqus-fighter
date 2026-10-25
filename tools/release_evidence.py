"""Strict, read-only validation for the current technical release evidence.

The native package and the technical audit use the same checks so that a ZIP
cannot pass one gate while the other accepts a different interpretation of
the long-running evidence, including the sixth native Training suite.  This
module never starts an emulator; it only reads JSON, hashes files, and checks
the committed source relationship used by the fresh-build report.
"""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from typing import Any


EXTRA_REPORTS: dict[str, str] = {
    "matchups": "docs/matchup-test-report.json",
    "independent_combat": "docs/compatibility-combat-test-report.json",
    "endurance": "docs/endurance-test-report.json",
    "fresh_build": "docs/fresh-build-test-report.json",
}

# Training is a native suite and therefore has an authoritative committed
# report of its own.  Candidate runs may use build/training-test-report.json,
# but that ignored file is deliberately excluded from release validation.
TRAINING_REPORT = "docs/training-test-report.json"

FIGHTERS = 12
STAGES = 3
MATCHUP_POLICIES = ("ground_combo_special", "jump_guard_throw_mix")
MATCHUP_CASES = FIGHTERS * FIGHTERS * len(MATCHUP_POLICIES)
MATCHUP_FRAMES = 600
INDEPENDENT_CASES = 48
INDEPENDENT_FRAMES = 600
INDEPENDENT_TOTAL_FRAMES = INDEPENDENT_CASES * INDEPENDENT_FRAMES
HOUR_SECONDS = 3600.0
ROM_BYTES = 4 * 1024 * 1024
GENERATED_ASSET_COUNT = 226

EXPECTED_NATIVE_CORE = {
    "archive_sha256": "f3e88ae8540840c838dbcd57715134809894c9fd31d389e613409923ac23ea4e",
    "member_sha256": "f00db5bd97bbe0e80761e590449eb14716bd9ab5785a1b50725c55e10505c343",
    "dll_sha256": "f00db5bd97bbe0e80761e590449eb14716bd9ab5785a1b50725c55e10505c343",
}
EXPECTED_INDEPENDENT_CORE = {
    "archive_sha256": "cb1211ae6b6838ed60beb7cc8ae5ad8074327733f1042ccc8baba32a62c6d18c",
    "dll_sha256": "f2aac1ddb314a001467a26b56604020f0a29c3a4dd1658b072884ace75343cf4",
}

TRAINING_CORE_OPTIONS = {"snes9x_up_down_allowed": "enabled"}
TRAINING_CONTRACT_FLAGS = (
    "strict_trace_cadence",
    "strict_fight_pause_guide_cadence",
    "bounded_menu_load_duplicates",
    "opaque_guide_tiles",
    "native_same_pad_socd_input",
    "paused_contact_hud_truth",
)
TRAINING_TRACE_OFFSETS = {
    "ppu_stat": 114,
    "ambient_phase": 115,
    "ambient_clock": 116,
    "ambient_pending_phase": 117,
    "ambient_pending_age": 118,
    "pause_page": 119,
    "guide_build": 120,
    "training_dummy": 121,
    "guide_dirty": 122,
}
TRAINING_SPECIAL_NAMES = (
    "KERNEL BURST", "CAPITAL WAVE", "ATOMIC PUSH", "BALANCE BREAK",
    "MACRO SHOCK", "AUDIT STRIKE", "LEGACY FLASH", "RISK REVERSAL",
    "MERGE FORCE", "CLOUD CRASH", "CLOSE OUT", "NORDIC BYTE",
)
TRAINING_SPECIAL_FAMILY_NAMES = (
    "FORWARD PROJECTILE", "ADVANCING STRIKE",
    "LOW SHOCKWAVE", "RISING STRIKE",
)
TRAINING_SPECIAL_FAMILIES = (0, 0, 1, 1, 2, 3, 2, 3, 2, 0, 3, 2)

BASE_COVERAGE_KEYS = frozenset({
    "attack", "air", "throw", "guard", "special", "down", "wake",
    "round_progress", "three_stages", "six_normal_actions", "real_damage",
})
MODE_COVERAGE_KEYS = {
    "0": BASE_COVERAGE_KEYS | {"arcade_ladder", "champion", "champion_restart"},
    "1": BASE_COVERAGE_KEYS | {"menu_roster"},
    "2": BASE_COVERAGE_KEYS | {"menu_roster", "training_reset"},
}

NTSC_NATIVE_FPS_MIN = 59.0
NTSC_NATIVE_FPS_MAX = 61.0

STRICT_ENDURANCE_FLAGS = (
    "strict_live_cadence",
    "strict_stable_fight_native_timing",
    "strict_resident_spc_fifo",
    "strict_ambient_cadence",
    "strict_trace_bounds",
    "strict_oam_bounds",
    "strict_video_geometry",
    "strict_video_fps",
    "strict_pcm_callback",
    "strict_trace_magic",
)

# Inputs which can alter the cartridge, generated data or candidate evidence
# policy. Captured reports/document outputs can follow the source freeze.
SOURCE_INPUT_EXACT = {
    "Build.cmd",
    "Test.cmd",
    "Play.cmd",
    "tools/setup.ps1",
    "tools/build.py",
    "tools/make_assets.py",
    "tools/fighter_assets.py",
    "tools/portrait_assets.py",
    "tools/menu_assets.py",
    "tools/test_classic_menu.py",
    "tools/menu_preview_checks.py",
    "tools/test_menu_preview.py",
    "tools/champion_assets.py",
    "tools/stage_assets.py",
    "tools/stage_sources.py",
    "tools/stage_cartoon.py",
    "tools/effect_assets.py",
    "tools/victory_music.py",
    "tools/audio_assets.py",
    "tools/synthesize_announcements.ps1",
    "tools/preservation.py",
    "tools/expansion_contracts.py",
    "tools/walking_assets.py",
    "tools/pose_revision_assets.py",
    "tools/v024_contracts.py",
    "tools/v025_contracts.py",
    "tools/v029_contracts.py",
    "tools/test_v029_contracts.py",
    "tools/collate_pacing_floor_25.py",
    "tools/test_pacing_floor_25.py",
    "tools/contact_geometry.py",
    "tools/stage_test_contract.py",
    "tools/stage_depth_assets.py",
    "tools/asset_transaction.py",
    "tools/asset_cache.py",
    "tools/native_artifacts.py",
    "tools/candidate_sources.py",
    "tools/play_flow_media.py",
    "tools/play_flow_counterfactual.py",
    "tools/test_play_flow_counterfactual.py",
    "tools/test_play_flow_long_26.py",
    "tools/test_session_limit_26.py",
    "tools/test_long_session_guards.py",
    "tools/verify_play_flow_26.py",
    "tools/test_verification_runner_guards.py",
    "tools/v026_contracts.py",
    "tools/collate_play_flow_26.py",
    "tools/check_play_flow_native_26.py",
    "tools/test_play_flow_26.py",
    "tools/test_feedback_26.py",
    "tools/test_arena_preview_26.py",
    "tools/test_menu_repeat_26.py",
    "tools/test_music_26.py",
    "tools/test_confirm_26.py",
    "tools/test_normal_guide_26.py",
    "tools/test_throw_feedback_26.py",
    "tools/test_training_best_26.py",
    "tools/test_local_session_26.py",
    "tools/test_roster_hints_26.py",
    "tools/test_motion_26.py",
    "tools/test_stage_pipeline_26.py",
    "tools/test_native_build_26.py",
    "tools/test_launcher_26.py",
    "tools/test_asset_transaction.py",
    "tools/test_asset_cache.py",
    "tools/test_native_artifacts.py",
    "tools/test_candidate_sources.py",
    "tools/test_play_flow_media.py",
    "tools/test_play_flow_collation.py",
    "tools/test_play_flow_stress_26.py",
    "tools/make_play_flow_review_26.py",
    "tools/check_authoring_guards.py",
    "tools/release_evidence.py",
    "tools/play.ps1",
    "tools/validate_cartridge.ps1",
}
SOURCE_INPUT_PREFIXES = ("src/", "assets/", "dist/")

Recorder = Callable[[bool, str, Any], None]


class EvidenceError(AssertionError):
    """Raised when a release report is missing or fails a release gate."""


def _record(recorder: Recorder | None, label: str, details: Any = None) -> None:
    if recorder is not None:
        recorder(True, label, details)


def require(condition: bool, label: str, details: Any = None,
            recorder: Recorder | None = None) -> None:
    if not condition:
        raise EvidenceError((label, details))
    _record(recorder, label, details)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().lower()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _sha_constants(path: Path, names: tuple[str, ...]) -> dict[str, str]:
    """Read pinned hashes from a test script without importing or running it."""

    require(path.is_file(), "pinned-core source script exists", str(path))
    text = path.read_text(encoding="utf-8")
    values: dict[str, str] = {}
    for name in names:
        match = re.search(
            rf"(?ms)^\s*{re.escape(name)}\s*=\s*(?:\(\s*)?[\"']([0-9A-Fa-f]{{64}})[\"']",
            text,
        )
        require(match is not None, "pinned-core source hash constant exists",
                {"file": str(path), "name": name})
        values[name] = match.group(1).lower()
    return values


def _validate_pinned_core_sources(root: Path,
                                  recorder: Recorder | None) -> None:
    native = _sha_constants(
        root / "tools/test_endurance.py",
        ("CORE_ARCHIVE_SHA256", "CORE_MEMBER_SHA256"),
    )
    require(native == {
        "CORE_ARCHIVE_SHA256": EXPECTED_NATIVE_CORE["archive_sha256"],
        "CORE_MEMBER_SHA256": EXPECTED_NATIVE_CORE["member_sha256"],
    }, "native core source pins are the release pins", native, recorder)
    independent = _sha_constants(
        root / "tools/test_compatibility.py",
        ("CORE_ARCHIVE_SHA256", "CORE_DLL_SHA256"),
    )
    require(independent == {
        "CORE_ARCHIVE_SHA256": EXPECTED_INDEPENDENT_CORE["archive_sha256"],
        "CORE_DLL_SHA256": EXPECTED_INDEPENDENT_CORE["dll_sha256"],
    }, "independent core source pins are the release pins", independent, recorder)


def _validate_core_identity(core: Any, expected: dict[str, str],
                            label: str,
                            recorder: Recorder | None) -> None:
    require(isinstance(core, dict), label + " identity exists", core, recorder)
    for field, digest in expected.items():
        actual = str(core.get(field, "")).lower()
        require(actual == digest, label + " " + field, actual, recorder)


def _harness_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for relative in ("tools/longrun_host.py", "tools/test_endurance.py"):
        path = root / relative
        require(path.is_file(), "endurance harness source exists", relative)
        digest.update(path.read_bytes())
    return digest.hexdigest()


def load_report(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    require(path.is_file(), "release evidence report exists", relative)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EvidenceError(("release evidence report is valid JSON", relative,
                              repr(error))) from error
    require(isinstance(value, dict), "release evidence report is an object", relative)
    return value


def training_report_path(root: Path) -> Path:
    """Return the authoritative committed Training report path.

    The test driver can redirect candidate output under ``build`` while
    developing a run. Release evidence must come from the
    committed ``docs`` report, so there is intentionally no build fallback.
    """

    path = root / TRAINING_REPORT
    require(path.is_file(), "native Training evidence report exists", TRAINING_REPORT)
    return path


def _training_harness_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for relative in ("tools/test_training.py", "tools/emulator.py"):
        path = root / relative
        require(path.is_file(), "Training harness source exists", relative)
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise EvidenceError((label, value))
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise EvidenceError((label, value)) from error


def _finite_float(value: Any, label: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise EvidenceError((label, value)) from error
    if not math.isfinite(parsed):
        raise EvidenceError((label, value))
    return parsed


def _exact_rom(report: dict[str, Any], rom_sha256: str, label: str,
               recorder: Recorder | None) -> None:
    require(report.get("status") == "passed", label + " passed", report.get("status"), recorder)
    nested = report.get("rom")
    if nested is not None:
        require(isinstance(nested, dict), label + " ROM identity object", nested, recorder)
        require(str(nested.get("sha256", "")).lower() == rom_sha256,
                label + " matches the exact current ROM", nested.get("sha256"), recorder)
        require(_int(nested.get("bytes", 0), label + " ROM byte count") == ROM_BYTES,
                label + " ROM byte count", nested.get("bytes"), recorder)
    else:
        actual = str(report.get("rom_sha256", "")).lower()
        require(actual == rom_sha256, label + " matches the exact current ROM", actual, recorder)
        if "rom_bytes" in report:
            require(_int(report.get("rom_bytes", 0), label + " ROM byte count") == ROM_BYTES,
                    label + " ROM byte count", report.get("rom_bytes"), recorder)


def _matchup_key(item: dict[str, Any]) -> tuple[int, int, str]:
    return (_int(item.get("fighter1"), "matchup fighter1"),
            _int(item.get("fighter2"), "matchup fighter2"),
            str(item.get("policy")))


def validate_matchups(report: dict[str, Any], rom_sha256: str,
                      recorder: Recorder | None = None) -> dict[str, Any]:
    label = "native matchup sweep"
    _exact_rom(report, rom_sha256, label, recorder)
    require(report.get("scope") == "controller-only ordered 12x12 local-VS matchup sweep",
            label + " scope", report.get("scope"), recorder)
    require(_int(report.get("matchup_count_requested", 0), label + " requested count") == MATCHUP_CASES,
            label + " has 288 requested cases", report.get("matchup_count_requested"), recorder)
    require(_int(report.get("completed_matchups", 0), label + " completed count") == MATCHUP_CASES,
            label + " completed all cases", report.get("completed_matchups"), recorder)
    require(_int(report.get("frames_per_matchup", 0), label + " frames") == MATCHUP_FRAMES,
            label + " uses 600 native frames per case", report.get("frames_per_matchup"), recorder)
    require(_int(report.get("ordered_pair_count", 0), label + " ordered pair count") == FIGHTERS * FIGHTERS,
            label + " covers all 144 ordered pairs", report.get("ordered_pair_count"), recorder)
    require(report.get("full_ordered_matrix") is True,
            label + " is the full ordered matrix", report.get("full_ordered_matrix"), recorder)
    require(tuple(report.get("policies", ())) == MATCHUP_POLICIES,
            label + " has both deterministic policies", report.get("policies"), recorder)

    results = report.get("results")
    require(isinstance(results, list) and len(results) == MATCHUP_CASES,
            label + " contains 288 result records",
            len(results) if isinstance(results, list) else results, recorder)
    expected = {(p1, p2, policy)
                for p1 in range(FIGHTERS)
                for p2 in range(FIGHTERS)
                for policy in MATCHUP_POLICIES}
    seen: set[tuple[int, int, str]] = set()
    stage_values: set[int] = set()
    for index, item in enumerate(results):
        require(isinstance(item, dict), label + " result is an object", index, recorder)
        key = _matchup_key(item)
        require(key in expected, label + " result belongs to the ordered matrix", key, recorder)
        require(key not in seen, label + " has no duplicate case", key, recorder)
        seen.add(key)
        stage = _int(item.get("stage"), label + " stage")
        stage_values.add(stage)
        require(stage in range(STAGES), label + " stage is native", stage, recorder)
        require(_int(item.get("frames", 0), label + " case frame count") == MATCHUP_FRAMES,
                label + " case has 600 frames", {"index": index, "frames": item.get("frames")}, recorder)
        require(item.get("passed") is True, label + " case passed", key, recorder)
        cadence = item.get("cadence")
        require(isinstance(cadence, dict), label + " cadence record exists", key, recorder)
        for field, expected_value in (
            ("observed_frames", MATCHUP_FRAMES),
            ("trace_delta_min", 1), ("trace_delta_max", 1),
            ("trace_non_one_deltas", 0), ("host_delta_min", 1),
            ("host_delta_max", 1), ("host_non_one_deltas", 0),
        ):
            require(_int(cadence.get(field), label + " cadence field") == expected_value,
                    label + " strict unit cadence", {"case": key, "field": field,
                                                       "value": cadence.get(field)}, recorder)
        require(cadence.get("passed") is True, label + " cadence passed", key, recorder)
    require(seen == expected, label + " has every ordered pair and policy", len(seen), recorder)
    require(stage_values == set(range(STAGES)), label + " covers all three stages", stage_values, recorder)
    stage_counts = report.get("stages")
    require(isinstance(stage_counts, dict) and set(stage_counts) == {"0", "1", "2"},
            label + " stage summary covers all three locations", stage_counts, recorder)
    require(all(_int(stage_counts[key], label + " stage summary") > 0 for key in ("0", "1", "2")) and
            sum(_int(stage_counts[key], label + " stage summary") for key in ("0", "1", "2")) == MATCHUP_CASES,
            label + " stage summary totals 288 cases", stage_counts, recorder)

    host = report.get("host_contract")
    require(isinstance(host, dict), label + " host contract exists", host, recorder)
    for field in ("controller_only", "trace_read_only"):
        require(host.get(field) is True, label + " host contract " + field, host.get(field), recorder)
    for field in ("emulated_memory_writes", "savestate_calls"):
        require(_int(host.get(field, -1), label + " host contract field") == 0,
                label + " host contract " + field, host.get(field), recorder)
    for field in ("frontend_window_created", "audio_device_opened"):
        require(host.get(field) is False, label + " host contract " + field, host.get(field), recorder)

    replays = report.get("replays")
    require(isinstance(replays, list) and len(replays) == 4,
            label + " has four deterministic replay records",
            len(replays) if isinstance(replays, list) else replays, recorder)
    expected_replays = {
        (0, 1, 1, "ground_combo_special"),
        (1, 0, 1, "ground_combo_special"),
        (4, 6, 2, "jump_guard_throw_mix"),
        (6, 4, 2, "jump_guard_throw_mix"),
    }
    replay_keys: set[tuple[int, int, int, str]] = set()
    for replay in replays:
        require(isinstance(replay, dict), label + " replay is an object", replay, recorder)
        key = (_int(replay.get("fighter1"), "replay fighter1"),
               _int(replay.get("fighter2"), "replay fighter2"),
               _int(replay.get("stage"), "replay stage"),
               str(replay.get("policy")))
        replay_keys.add(key)
        require(replay.get("passed") is True and replay.get("same_trace_sha256") is True,
                label + " deterministic replay passed", key, recorder)
        digest = str(replay.get("trace_sha256", ""))
        require(len(digest) == 64, label + " replay has a trace digest", key, recorder)
    require(replay_keys == expected_replays,
            label + " has the four prescribed deterministic replays", replay_keys, recorder)
    return {"cases": len(results), "replays": len(replays), "stages": sorted(stage_values)}


def _independent_key(item: dict[str, Any]) -> tuple[int, int, int, str]:
    return (_int(item.get("fighter1"), "independent fighter1"),
            _int(item.get("fighter2"), "independent fighter2"),
            _int(item.get("stage"), "independent stage"),
            str(item.get("policy")))


def validate_independent_combat(report: dict[str, Any], rom_sha256: str,
                                recorder: Recorder | None = None) -> dict[str, Any]:
    label = "independent combat sweep"
    _exact_rom(report, rom_sha256, label, recorder)
    require(report.get("pinned_core") is True, label + " uses the pinned core", report.get("pinned_core"), recorder)
    require(not report.get("errors"), label + " has no reported errors", report.get("errors"), recorder)
    matrix = report.get("matrix")
    require(isinstance(matrix, dict), label + " matrix exists", matrix, recorder)
    require(_int(matrix.get("fighters", 0), label + " fighter count") == FIGHTERS,
            label + " covers all twelve fighters", matrix.get("fighters"), recorder)
    require(_int(matrix.get("stages", 0), label + " stage count") == STAGES,
            label + " covers all three stages", matrix.get("stages"), recorder)
    require(tuple(matrix.get("policies", ())) == MATCHUP_POLICIES,
            label + " has both deterministic policies", matrix.get("policies"), recorder)
    require(_int(matrix.get("full_case_count", 0), label + " full case count") == INDEPENDENT_CASES,
            label + " defines 48 cases", matrix.get("full_case_count"), recorder)
    require(_int(matrix.get("requested_frames_per_case", 0), label + " frames per case") == INDEPENDENT_FRAMES,
            label + " uses 600 frames per case", matrix.get("requested_frames_per_case"), recorder)
    require(_int(matrix.get("selected_case_count", 0), label + " selected case count") == INDEPENDENT_CASES,
            label + " ran all 48 cases", matrix.get("selected_case_count"), recorder)
    require(_int(matrix.get("selected_frames", 0), label + " selected frames") == INDEPENDENT_TOTAL_FRAMES,
            label + " ran 28,800 independent frames", matrix.get("selected_frames"), recorder)

    cases = report.get("cases")
    require(isinstance(cases, list) and len(cases) == INDEPENDENT_CASES,
            label + " contains 48 result records",
            len(cases) if isinstance(cases, list) else cases, recorder)
    neighbors = [(fighter, (fighter + 1) % FIGHTERS) for fighter in range(FIGHTERS)]
    pairs = neighbors + [(p2, p1) for p1, p2 in neighbors]
    expected = {(p1, p2, (index * len(MATCHUP_POLICIES) + policy_index) % STAGES, policy)
                for index, (p1, p2) in enumerate(pairs)
                for policy_index, policy in enumerate(MATCHUP_POLICIES)}
    seen: set[tuple[int, int, int, str]] = set()
    for index, item in enumerate(cases):
        require(isinstance(item, dict), label + " case is an object", index, recorder)
        key = _independent_key(item)
        require(key in expected, label + " case belongs to the prescribed matrix", key, recorder)
        require(key not in seen, label + " has no duplicate case", key, recorder)
        seen.add(key)
        require(_int(item.get("frames", 0), label + " case frame count") == INDEPENDENT_FRAMES,
                label + " case has 600 frames", key, recorder)
        require(item.get("passed") is True, label + " case passed", key, recorder)
        cadence = item.get("cadence")
        require(isinstance(cadence, dict), label + " cadence exists", key, recorder)
        for field, expected_value in (
            ("trace_frames", INDEPENDENT_FRAMES),
            ("trace_delta_min", 1), ("trace_delta_max", 1),
            ("trace_non_one_deltas", 0), ("video_callbacks", INDEPENDENT_FRAMES),
            ("video_delta_min", 1), ("video_delta_max", 1),
            ("video_non_one_deltas", 0),
        ):
            require(_int(cadence.get(field), label + " cadence field") == expected_value,
                    label + " strict unit cadence", {"case": key, "field": field,
                                                       "value": cadence.get(field)}, recorder)
        require(cadence.get("passed") is True, label + " cadence passed", key, recorder)
        audio = item.get("audio")
        require(isinstance(audio, dict) and _int(audio.get("samples", 0), label + " PCM samples") > 0 and
                _int(audio.get("energy", 0), label + " PCM energy") > 0 and
                0 < _int(audio.get("peak", 0), label + " PCM peak") < 32767,
                label + " PCM callback is healthy", {"case": key, "audio": audio}, recorder)
    require(seen == expected, label + " has every prescribed P1/P2 case", len(seen), recorder)
    host = report.get("host_contract")
    require(isinstance(host, dict), label + " host contract exists", host, recorder)
    for field in ("emulated_memory_writes", "savestate_calls"):
        require(_int(host.get(field, -1), label + " host contract field") == 0,
                label + " host contract " + field, host.get(field), recorder)
    for field in ("audio_device_opened", "frontend_window_created", "pcm_callback_capture_only"):
        require(host.get(field) is (field == "pcm_callback_capture_only"),
                label + " host contract " + field, host.get(field), recorder)
    _validate_core_identity(report.get("core"), EXPECTED_INDEPENDENT_CORE,
                            label + " pinned independent core", recorder)
    return {"cases": len(cases), "frames": INDEPENDENT_TOTAL_FRAMES}


def _training_hex_digest(value: Any, label: str,
                         recorder: Recorder | None) -> None:
    digest = str(value).lower()
    require(re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
            label + " is a SHA-256 digest", value, recorder)


def _training_state(value: Any, label: str,
                    recorder: Recorder | None,
                    screen: int | None = None) -> dict[str, Any]:
    require(isinstance(value, dict), label + " state exists", value, recorder)
    require(_int(value.get("magic", -1), label + " magic") == 0xAABA,
            label + " publishes the native trace magic", value.get("magic"), recorder)
    if screen is not None:
        require(_int(value.get("screen", -1), label + " screen") == screen,
                label + " screen", value.get("screen"), recorder)
    for field in ("fighter_id1", "fighter_id2"):
        fighter = _int(value.get(field, -1), label + " " + field)
        require(0 <= fighter < FIGHTERS, label + " fighter identity", fighter, recorder)
    return value


def _training_bar_record(value: Any, label: str,
                         recorder: Recorder | None) -> None:
    require(isinstance(value, dict), label + " bar record exists", value, recorder)
    sample = value.get("sample")
    require(isinstance(sample, dict), label + " sample exists", sample, recorder)
    require(_int(sample.get("paused", 0), label + " sample paused") == 1,
            label + " sample is paused", sample.get("paused"), recorder)
    require(_int(sample.get("pause_page", -1), label + " sample page") in (0, 1, 2) and
            _int(sample.get("hitstop", -1), label + " sample hitstop") >= 0,
            label + " sample pause metadata", sample, recorder)
    for field in ("hp1", "hp2", "energy1", "energy2"):
        _int(sample.get(field, -1), label + " sample " + field)
    for meter in ("health", "energy"):
        for side in ("p1", "p2"):
            actual = value.get(meter + "_" + side)
            expected = value.get("expected_" + meter + "_" + side)
            require(isinstance(actual, list) and len(actual) > 0,
                    label + " " + meter + " " + side + " samples", actual, recorder)
            require(actual == expected,
                    label + " " + meter + " " + side + " matches expected HUD",
                    {"actual": actual, "expected": expected}, recorder)


def _validate_training_modes(report: dict[str, Any],
                             recorder: Recorder | None) -> None:
    label = "native Training mode coverage"
    modes = report.get("modes")
    require(isinstance(modes, list) and len(modes) == 3,
            label + " contains modes 0, 1 and 2", modes, recorder)
    seen: set[int] = set()
    for mode in modes:
        require(isinstance(mode, dict), label + " mode record is an object", mode, recorder)
        mode_id = _int(mode.get("mode", -1), label + " mode id")
        require(mode_id in (0, 1, 2) and mode_id not in seen,
                label + " has a unique valid mode id", mode_id, recorder)
        seen.add(mode_id)
        for field in ("fighter1", "fighter2"):
            fighter = _int(mode.get(field, -1), label + " " + field)
            require(0 <= fighter < FIGHTERS,
                    label + " fighter identity", {"mode": mode_id, field: fighter}, recorder)
        for page in ("controls", "specials"):
            card = mode.get(page)
            card_label = label + " mode " + str(mode_id) + " " + page
            require(isinstance(card, dict), card_label + " card exists", card, recorder)
            require(card.get("label") == f"mode{mode_id}-{page}",
                    card_label + " label", card.get("label"), recorder)
            total = _int(card.get("total", 0), card_label + " total")
            nonblank = _int(card.get("nonblank", 0), card_label + " nonblank")
            require(total > 0 and nonblank == total,
                    card_label + " is fully populated", {"total": total, "nonblank": nonblank}, recorder)
            require(isinstance(card.get("text"), str) and card["text"].strip(),
                    card_label + " text exists", card.get("text"), recorder)
            _training_hex_digest(card.get("vram_sha256"), card_label + " VRAM digest", recorder)
        history = mode.get("page_history")
        require(isinstance(history, list) and len(history) > 0,
                label + " page history exists", history, recorder)
        for entry in history:
            require(isinstance(entry, dict), label + " page history record", entry, recorder)
            page = _int(entry.get("page", -1), label + " page history page")
            build = _int(entry.get("build", -1), label + " page history build")
            dirty = _int(entry.get("dirty", -1), label + " page history dirty")
            require(page in (0, 1, 2) and 0 <= build <= 3 and dirty in (0, 1),
                    label + " page history values", entry, recorder)
    require(seen == {0, 1, 2}, label + " covers all three modes", seen, recorder)


def _validate_training_pause_hud(report: dict[str, Any],
                                 recorder: Recorder | None) -> None:
    label = "native Training mirrored pause HUD"
    evidence = report.get("pause_hud_after_contacts")
    require(isinstance(evidence, dict), label + " evidence exists", evidence, recorder)
    cases = evidence.get("cases")
    require(isinstance(cases, list) and len(cases) == 2,
            label + " has both attacker-side cases", cases, recorder)
    attackers: set[int] = set()
    for case in cases:
        require(isinstance(case, dict), label + " case is an object", case, recorder)
        attacker = _int(case.get("attacker", 0), label + " attacker")
        require(attacker in (1, 2) and attacker not in attackers,
                label + " covers a unique P1/P2 attacker", attacker, recorder)
        attackers.add(attacker)
        initial = _training_state(case.get("initial"), label + " initial", recorder, screen=3)
        impact = _training_state(case.get("impact"), label + " impact", recorder, screen=3)
        paused = _training_state(case.get("paused"), label + " paused", recorder, screen=3)
        require(_int(initial.get("paused", -1), label + " initial pause") == 0 and
                _int(impact.get("paused", -1), label + " impact pause") == 0 and
                _int(paused.get("paused", -1), label + " paused flag") == 1,
                label + " transitions into pause after contact", case, recorder)
        require((initial.get("hp1"), initial.get("hp2")) !=
                (impact.get("hp1"), impact.get("hp2")),
                label + " records real contact damage", case, recorder)
        for field in ("hp1", "hp2", "energy1", "energy2"):
            require(paused.get(field) == impact.get(field),
                    label + " freezes " + field, {
                        "impact": impact.get(field), "paused": paused.get(field),
                    }, recorder)
        for phase in ("entry_bars", "settled_bars"):
            _training_bar_record(case.get(phase), label + " " + phase, recorder)
        page_bars = case.get("page_bars")
        require(isinstance(page_bars, dict) and set(page_bars) == {"0", "1", "2"},
                label + " covers guide pages 0, 1 and 2", page_bars, recorder)
        for page, bars in page_bars.items():
            _training_bar_record(bars, label + " guide page " + page, recorder)
        require(_int(case.get("sample_count", 0), label + " sample count") > 0,
                label + " has pause samples", case.get("sample_count"), recorder)
    require(attackers == {1, 2}, label + " covers both controller sides", attackers, recorder)


def validate_training_evidence(root: Path, rom_sha256: str,
                               recorder: Recorder | None = None) -> dict[str, Any]:
    """Validate the authoritative native Training report for the current ROM."""

    label = "native Training suite"
    report = load_report(root, TRAINING_REPORT)
    _exact_rom(report, rom_sha256, label, recorder)
    require(report.get("suite") == "training", label + " suite identity", report.get("suite"), recorder)
    checks = report.get("checks")
    require(isinstance(checks, list) and len(checks) > 0,
            label + " has non-empty checks", checks, recorder)
    passed = _int(report.get("passed", -1), label + " passed count")
    require(passed == len(checks) and passed > 0,
            label + " passed count covers every check", {
                "passed": passed, "checks": len(checks),
            }, recorder)
    for index, item in enumerate(checks):
        require(isinstance(item, dict) and item.get("passed") is True,
                label + " check passed", index, recorder)

    training_pins = _sha_constants(
        root / "tools/test_training.py", ("CORE_ARCHIVE_SHA256", "CORE_MEMBER_SHA256"))
    require(training_pins == {
        "CORE_ARCHIVE_SHA256": EXPECTED_NATIVE_CORE["archive_sha256"],
        "CORE_MEMBER_SHA256": EXPECTED_NATIVE_CORE["member_sha256"],
    }, label + " source core pins are the release pins", training_pins, recorder)
    _validate_core_identity(report.get("core"), EXPECTED_NATIVE_CORE,
                            label + " pinned native core", recorder)
    harness = str(report.get("harness_sha256", "")).lower()
    require(harness == _training_harness_sha256(root),
            label + " harness matches current test sources", harness, recorder)
    require(report.get("core_options") == TRAINING_CORE_OPTIONS,
            label + " core options are pinned", report.get("core_options"), recorder)

    flags = report.get("contract_flags")
    require(isinstance(flags, dict) and set(flags) == set(TRAINING_CONTRACT_FLAGS),
            label + " contract flag schema", flags, recorder)
    require(all(flags[name] is True for name in TRAINING_CONTRACT_FLAGS),
            label + " contract flags are complete", flags, recorder)
    for field in ("cadence_failures", "guide_failures"):
        failures = report.get(field)
        require(isinstance(failures, list) and failures == [],
                label + " " + field, failures, recorder)
    require(report.get("trace_offsets") == TRAINING_TRACE_OFFSETS,
            label + " trace offsets are stable", report.get("trace_offsets"), recorder)

    _validate_training_modes(report, recorder)

    specials = report.get("all_special_names")
    require(isinstance(specials, list) and len(specials) == FIGHTERS,
            label + " includes all twelve special-name records", specials, recorder)
    seen_specials: set[int] = set()
    for item in specials:
        require(isinstance(item, dict), label + " special-name record", item, recorder)
        fighter = _int(item.get("fighter", -1), label + " special fighter")
        require(fighter in range(FIGHTERS) and fighter not in seen_specials,
                label + " special-name fighter IDs", fighter, recorder)
        seen_specials.add(fighter)
        require(item.get("special") == TRAINING_SPECIAL_NAMES[fighter],
                label + " special-name mapping", item, recorder)
        for field in ("p1", "p2"):
            value = _int(item.get(field, -1), label + " special " + field)
            require(0 <= value < FIGHTERS,
                    label + " special fighter selection", {field: value}, recorder)
        require(isinstance(item.get("text"), str) and item["text"].strip(),
                label + " special page text", item, recorder)
        require(TRAINING_SPECIAL_FAMILY_NAMES[TRAINING_SPECIAL_FAMILIES[fighter]]
                in item["text"],
                label + " special family text", item, recorder)
    require(seen_specials == set(range(FIGHTERS)),
            label + " covers every fighter special", seen_specials, recorder)

    dummy = report.get("dummy_and_contacts")
    require(isinstance(dummy, dict), label + " dummy/contact evidence exists", dummy, recorder)
    require(_int(dummy.get("dummy_jump_samples", 0), label + " dummy jump samples") > 0,
            label + " records real dummy jumps", dummy.get("dummy_jump_samples"), recorder)
    for field, expected in (("high_wave_damage", 24), ("low_wave_damage", 1),
                            ("air_damage", 8)):
        require(_int(dummy.get(field, -1), label + " " + field) == expected,
                label + " " + field, dummy.get(field), recorder)
    throws = dummy.get("throw_samples")
    require(isinstance(throws, list) and len(throws) > 0,
            label + " records a native throw", throws, recorder)
    for sample in throws:
        state = _training_state(sample, label + " throw sample", recorder, screen=3)
        require(_int(state.get("action1", 0), label + " throw action1") != 0 or
                _int(state.get("action2", 0), label + " throw action2") != 0,
                label + " throw sample reaches an action", state, recorder)

    socd = report.get("paused_directional_socd")
    require(isinstance(socd, dict), label + " paused directional SOCD evidence", socd, recorder)
    require(_int(socd.get("page", -1), label + " SOCD page") == 1 and
            _int(socd.get("same_pad_raw_keys1", -1), label + " SOCD raw bits") == 768 and
            _int(socd.get("dummy_before", -1), label + " SOCD dummy before") == 1 and
            _int(socd.get("dummy_after_held_edge", -1), label + " SOCD dummy after") == 1,
            label + " same-pad opposite directions stay neutral", socd, recorder)

    freeze = report.get("pause_projectile_crossup")
    require(isinstance(freeze, dict), label + " projectile/cross-up evidence", freeze, recorder)
    projectile = freeze.get("projectile_samples")
    require(isinstance(projectile, list) and len(projectile) > 0,
            label + " samples an active projectile", projectile, recorder)
    for sample in projectile:
        _training_state(sample, label + " projectile sample", recorder, screen=3)
    require(any(_int(sample.get("wave1", 0), label + " wave1") > 0 or
                _int(sample.get("wave2", 0), label + " wave2") > 0
                for sample in projectile),
            label + " observes an active wave", projectile, recorder)
    crossup = freeze.get("crossup_samples")
    require(isinstance(crossup, list) and len(crossup) > 0,
            label + " samples an airborne cross-up", crossup, recorder)
    for sample in crossup:
        _training_state(sample, label + " cross-up sample", recorder, screen=3)
    require(any(_int(sample.get("y1", 0), label + " cross-up y1") != 0
                for sample in crossup) and
            any(_int(sample.get("landing1", 0), label + " cross-up landing") != 0
                for sample in crossup) and
            len({_int(sample.get("face2", -1), label + " cross-up face2")
                 for sample in crossup}) > 1,
            label + " observes airborne arc, landing and facing restoration", crossup, recorder)

    quick = report.get("quick_reset")
    require(isinstance(quick, dict), label + " quick reset evidence", quick, recorder)
    quick_state = _training_state(quick.get("state"), label + " quick reset", recorder, screen=3)
    require(_int(quick_state.get("intro", -1), label + " quick reset intro") == 0 and
            _int(quick_state.get("training_dummy", -1), label + " quick reset dummy") == 2,
            label + " preserves live Training reset", quick_state, recorder)

    roster = report.get("roster_return")
    require(isinstance(roster, dict), label + " roster return evidence", roster, recorder)
    require(_int(roster.get("screen", -1), label + " roster return screen") == 1,
            label + " returns to roster", roster, recorder)
    roster_state = _training_state(roster.get("state"), label + " roster return", recorder, screen=1)
    require(_int(roster_state.get("selected", -1), label + " roster selected") in range(FIGHTERS) and
            _int(roster_state.get("selected2", -1), label + " roster selected2") in range(FIGHTERS),
            label + " roster selections remain valid", roster_state, recorder)

    _validate_training_pause_hud(report, recorder)
    _validate_training_capture_inventory(report, root, recorder)
    return {"checks": passed, "report": TRAINING_REPORT, "modes": 3,
            "captures": len(report["capture_paths"])}


def _validate_training_capture_inventory(report: dict[str, Any], root: Path,
                                         recorder: Recorder | None = None) -> None:
    """The smaller CPU card has its own native-geometry check, outside guides."""
    label = "native Training suite"
    captures = report.get("captures")
    require(isinstance(captures, list) and len(captures) == 8,
            label + " has eight native review captures", captures, recorder)
    for index, capture in enumerate(captures):
        require(isinstance(capture, dict) and
                capture.get("check") == "native PPU capture is 256x224" and
                capture.get("passed") is True,
                label + " capture record", index, recorder)
        details = capture.get("details")
        require(isinstance(details, dict) and details.get("size") == [256, 224],
                label + " capture geometry", details, recorder)
    capture_paths = report.get("capture_paths")
    version = tuple(map(int, load_report(root, "dist/manifest.json")["version"].split(".")))
    expected_paths = len(captures) + (version >= (0, 17, 0))
    require(isinstance(capture_paths, list) and len(capture_paths) == expected_paths and
            all(isinstance(path, str) and path for path in capture_paths),
            label + " capture paths", capture_paths, recorder)
    if version >= (0, 17, 0):
        names = [f"mode{mode}-{page}" for mode in range(3)
                 for page in ("controls", "specials")] + ["special-page-00", "special-page-11"]
        require([item.get("details", {}).get("name") for item in captures] == names,
                label + " fixed guide capture inventory", captures, recorder)
        expected = ["docs/screenshots/training/" + name + ".png"
                    for name in ["training-cpu-card", *names]]
        require([path.replace("\\", "/") for path in capture_paths] == expected,
                label + " fixed guide and CPU card paths", capture_paths, recorder)
        geometry = [item for item in report.get("checks", []) if isinstance(item, dict) and
                    item.get("check") == "CPU normal-card capture is a native 256x224 PPU frame"]
        require(len(geometry) == 1 and geometry[0].get("passed") is True,
                label + " CPU card native geometry proof", geometry, recorder)


def _strict_flags(value: Any, label: str, recorder: Recorder | None) -> None:
    require(isinstance(value, dict), label + " flags exist", value, recorder)
    for flag in STRICT_ENDURANCE_FLAGS:
        require(value.get(flag) is True, label + " " + flag, value.get(flag), recorder)


def _mode_audio_video(mode: dict[str, Any], label: str,
                      native_fps: float, target_frames: int,
                      expected_coverage: frozenset[str],
                      recorder: Recorder | None) -> None:
    require(mode.get("status") == "passed", label + " passed", mode.get("status"), recorder)
    require(mode.get("uninterrupted_session") is True,
            label + " uninterrupted session", mode.get("uninterrupted_session"), recorder)
    require(_int(mode.get("core_boots", 0), label + " boots") == 1,
            label + " has one core boot", mode.get("core_boots"), recorder)
    require(_int(mode.get("core_unloads", 0), label + " unloads") == 1,
            label + " has one core unload", mode.get("core_unloads"), recorder)
    require(_int(mode.get("core_reboots", -1), label + " reboots") == 0,
            label + " has zero core reboots", mode.get("core_reboots"), recorder)
    require(_int(mode.get("target_live_frames", 0), label + " target") >= target_frames,
            label + " target meets native-hour frame count", mode.get("target_live_frames"), recorder)
    require(_int(mode.get("live_frames", 0), label + " live frames") >= target_frames,
            label + " completed the native-hour live frame count", mode.get("live_frames"), recorder)
    require(_int(mode.get("native_frame_wraps", 0), label + " frame wraps") >= 3,
            label + " crossed three native frame wraps", mode.get("native_frame_wraps"), recorder)
    require(mode.get("coverage_required") is True,
            label + " requires full coverage", mode.get("coverage_required"), recorder)
    required = mode.get("required_coverage")
    require(isinstance(required, dict) and
            set(required) == set(expected_coverage),
            label + " required coverage schema", required, recorder)
    require(all(value is True for value in required.values()),
            label + " required coverage is complete", required, recorder)
    require(_int(mode.get("stable_fight_lag_increments", -1), label + " stable fight lag") == 0,
            label + " has zero stable FIGHT lag", mode.get("stable_fight_lag_increments"), recorder)
    for field, description in (
        ("cadence_failures", "cadence failures"),
        ("native_timing_failures", "native timing failures"),
        ("ambient_failures", "ambient failures"),
        ("spc_fifo_failures", "SPC FIFO failures"),
        ("ppu_overflow_frames", "PPU overflow frames"),
    ):
        failures = mode.get(field)
        require(isinstance(failures, list) and failures == [],
                label + " " + description, failures, recorder)
    require(_int(mode.get("video_samples", 0), label + " video samples") > 0 and
            _int(mode.get("video_nonblank_samples", 0), label + " nonblank video") > 0 and
            mode.get("video_geometry") == [256, 224],
            label + " video callback is healthy", {
                "samples": mode.get("video_samples"),
                "nonblank": mode.get("video_nonblank_samples"),
                "geometry": mode.get("video_geometry"),
            }, recorder)
    require(_int(mode.get("audio_samples", 0), label + " audio samples") > 0 and
            _int(mode.get("audio_nonzero_batches", 0), label + " nonzero PCM") > 0 and
            _finite_float(mode.get("audio_sample_rate", 0), label + " audio rate") > 0,
            label + " PCM callback is healthy", {
                "samples": mode.get("audio_samples"),
                "nonzero": mode.get("audio_nonzero_batches"),
                "rate": mode.get("audio_sample_rate"),
            }, recorder)
    worker_fps = _finite_float(mode.get("video_fps", 0), label + " video FPS")
    require(abs(worker_fps - native_fps) <= 1e-6,
            label + " video FPS matches native timing", {"worker": worker_fps, "native": native_fps}, recorder)
    require(str(mode.get("rom_sha256", "")).lower() != "",
            label + " reports its ROM hash", mode.get("rom_sha256"), recorder)


def validate_endurance(report: dict[str, Any], rom_sha256: str,
                       recorder: Recorder | None = None,
                       root: Path | None = None) -> dict[str, Any]:
    label = "endurance gate"
    if root is None:
        root = Path(__file__).resolve().parents[1]
    training_cpu = tuple(map(int, load_report(root, 'dist/manifest.json')['version'].split('.'))) >= (0, 17, 0)
    _validate_pinned_core_sources(root, recorder)
    _exact_rom(report, rom_sha256, label, recorder)
    require(report.get("suite") == "endurance", label + " suite identity", report.get("suite"), recorder)
    native_fps = _finite_float(report.get("native_fps", 0), label + " native FPS")
    require(NTSC_NATIVE_FPS_MIN < native_fps < NTSC_NATIVE_FPS_MAX,
            label + " native FPS is NTSC-rate", native_fps, recorder)
    target_frames = math.ceil(native_fps * HOUR_SECONDS)
    reported_target = _int(report.get("target_live_frames_per_mode", 0), label + " target frames")
    require(reported_target >= target_frames, label + " target meets ceil(native_fps*3600)",
            {"reported": reported_target, "required": target_frames}, recorder)
    aggregate_flags = report.get("contract_flags")
    _strict_flags(aggregate_flags, label + " aggregate", recorder)
    require(aggregate_flags.get("worker_video_fps_match") is True,
            label + " aggregate worker FPS match", aggregate_flags.get("worker_video_fps_match"), recorder)
    benchmark_flags = report.get("benchmark_contract")
    if benchmark_flags is None and isinstance(report.get("benchmark"), dict):
        benchmark_flags = report["benchmark"].get("contract_flags", report["benchmark"].get("benchmark_contract"))
    _strict_flags(benchmark_flags, label + " benchmark", recorder)
    modes = report.get("modes")
    require(isinstance(modes, dict) and set(modes) == {"0", "1", "2"},
            label + " has all three modes", modes, recorder)
    _validate_core_identity(report.get("core"), EXPECTED_NATIVE_CORE,
                            label + " aggregate native core", recorder)
    harness = str(report.get("harness_sha256", "")).lower()
    require(len(harness) == 64, label + " harness identity is recorded", harness, recorder)
    expected_harness = _harness_sha256(root)
    require(harness == expected_harness,
            label + " harness matches current source", harness, recorder)
    for key in ("0", "1", "2"):
        mode = modes[key]
        require(isinstance(mode, dict), label + " mode is an object", key, recorder)
        _exact_rom(mode, rom_sha256, label + " mode " + key, recorder)
        _validate_core_identity(mode.get("core"), EXPECTED_NATIVE_CORE,
                                label + " mode " + key + " native core", recorder)
        coverage = MODE_COVERAGE_KEYS[key]
        if key == '2' and training_cpu:
            coverage = coverage | {'training_cpu_hour', 'training_cpu_roster'}
            require(_int(mode.get('training_cpu_live_frames', 0), label + ' CPU Training frames') >= reported_target,
                    label + ' CPU Training completes a native live hour', mode.get('training_cpu_live_frames'), recorder)
            rosters = mode.get('rosters')
            require(isinstance(rosters, list) and all(isinstance(row, dict) for row in rosters) and
                    {row.get('fighter2') for row in rosters} == set(range(FIGHTERS)),
                    label + ' CPU Training covers all twelve opponent profiles', rosters, recorder)
        _mode_audio_video(mode, label + " mode " + key, native_fps,
                          reported_target, coverage, recorder)
    totals = report.get("total_frames_per_mode")
    require(isinstance(totals, dict) and all(_int(totals.get(key, 0), label + " total frames") >= reported_target
                                             for key in ("0", "1", "2")),
            label + " total frames meet the target", totals, recorder)
    return {"native_fps": native_fps, "target_live_frames_per_mode": reported_target,
            "modes": 3}


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=root, stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, errors="replace")
    if result.returncode:
        raise EvidenceError(("git command succeeded", args, result.stderr[-1000:]))
    return result.stdout.strip()


def _source_input(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    # These are package outputs, not cartridge inputs.  They are intentionally
    # ignored so running package.py after the fresh source build does not make
    # its own checksum or release ZIP look like a source mutation.
    if normalized == "dist/release-sha256.txt" or (
            normalized.startswith("dist/") and normalized.lower().endswith(".zip")):
        return False
    return normalized in SOURCE_INPUT_EXACT or any(
        normalized.startswith(prefix) for prefix in SOURCE_INPUT_PREFIXES)


def _validate_fresh_source(root: Path, report: dict[str, Any],
                           recorder: Recorder | None) -> None:
    commit = str(report.get("source_commit", ""))
    tree = str(report.get("source_tree", "")).lower()
    require(len(commit) >= 7, "fresh build records a source commit", commit, recorder)
    resolved = _git(root, "rev-parse", "--verify", "--end-of-options", f"{commit}^{{commit}}")
    actual_tree = _git(root, "rev-parse", f"{resolved}^{{tree}}").lower()
    require(tree == actual_tree, "fresh source tree matches source commit", {"expected": tree, "actual": actual_tree}, recorder)
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", resolved, "HEAD"],
                              cwd=root, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(ancestor.returncode == 0, "fresh source commit is an ancestor of release HEAD", resolved, recorder)
    changed = [line for line in _git(root, "diff", "--name-only", resolved, "--").splitlines() if line]
    untracked = []
    status = _git(root, "status", "--porcelain", "--untracked-files=all")
    for line in status.splitlines():
        if line.startswith("?? "):
            untracked.append(line[3:])
    source_changes = [path for path in changed + untracked if _source_input(path)]
    require(not source_changes, "fresh source inputs unchanged since source commit", source_changes, recorder)
    _record(recorder, "fresh source commit/tree provenance", {"commit": resolved, "tree": actual_tree})


def validate_fresh_build(report: dict[str, Any], rom_sha256: str,
                         root: Path, recorder: Recorder | None = None) -> dict[str, Any]:
    label = "fresh committed-source build"
    _exact_rom(report, rom_sha256, label, recorder)
    require(str(report.get("rebuilt_rom_sha256", "")).lower() == rom_sha256,
            label + " rebuilt ROM matches the exact current ROM", report.get("rebuilt_rom_sha256"), recorder)
    require(_int(report.get("build_exit_code", -1), label + " build exit") == 0,
            label + " build succeeded", report.get("build_exit_code"), recorder)
    host = report.get("host_contract")
    require(isinstance(host, dict), label + " host contract exists", host, recorder)
    for field in ("gui_opened", "emulator_launched", "pre_extracted_tools_reused", "build_intermediates_reused"):
        require(host.get(field) is False, label + " host contract " + field, host.get(field), recorder)
    environment = report.get("build_environment")
    require(isinstance(environment, dict), label + " build environment exists", environment, recorder)
    selected_sdk = str(environment.get("selected_sdk", "")).replace("\\", "/")
    require(selected_sdk == ".tools/sdk/pvsneslib", label + " uses a fresh source-local SDK extraction", selected_sdk, recorder)
    require(_int(environment.get("sdk_files", 0), label + " SDK file count") > 0 and
            len(str(environment.get("sdk_tree_sha256", ""))) == 64,
            label + " records the extracted pinned SDK tree", environment, recorder)
    for field in ("source_local_sdk_reused", "pre_extracted_sdk_reused", "source_archive_contains_cache"):
        if field in host:
            require(host[field] is False, label + " host contract " + field, host[field], recorder)
        if field in environment:
            require(environment[field] is False, label + " build environment " + field, environment[field], recorder)
    generated = report.get("generated_assets")
    require(isinstance(generated, list) and len(generated) == GENERATED_ASSET_COUNT,
            label + f" has exactly {GENERATED_ASSET_COUNT} generated assets", len(generated) if isinstance(generated, list) else generated, recorder)
    require(_int(report.get("generated_assets_verified", 0), label + " generated count") == GENERATED_ASSET_COUNT,
            label + f" verified exactly {GENERATED_ASSET_COUNT} generated assets", report.get("generated_assets_verified"), recorder)
    names: set[str] = set()
    for item in generated:
        require(isinstance(item, dict), label + " generated asset record", item, recorder)
        name = str(item.get("file", "")).replace("\\", "/")
        digest = str(item.get("sha256", ""))
        suffix = Path(name).suffix.lower()
        expected_comparison = (
            "LF-normalized text" if suffix in {".asm", ".h", ".json"}
            else "exact bytes"
        )
        comparison = item.get("comparison")
        require(name.startswith("assets/generated/") and name not in names and
                len(digest) == 64 and comparison == expected_comparison,
                label + " generated asset provenance record", item, recorder)
        generated_path = root / name
        payload = generated_path.read_bytes() if generated_path.is_file() else b""
        if comparison == "LF-normalized text":
            payload = payload.replace(b"\r\n", b"\n")
        require(generated_path.is_file() and sha256_bytes(payload) == digest,
                label + " generated asset matches the current checkout", name, recorder)
        names.add(name)
    require(report.get("symbols_equal_after_source_path_normalization") is True,
            label + " linker symbols match after source path normalization",
            report.get("symbols_equal_after_source_path_normalization"), recorder)
    _validate_fresh_source(root, report, recorder)
    return {"generated_assets": len(generated), "source_commit": report.get("source_commit"),
            "source_tree": report.get("source_tree")}


def validate_release_evidence(root: Path, rom_sha256: str,
                              recorder: Recorder | None = None) -> dict[str, dict[str, Any]]:
    reports = {key: load_report(root, relative) for key, relative in EXTRA_REPORTS.items()}
    summaries = {
        "matchups": validate_matchups(reports["matchups"], rom_sha256, recorder),
        "independent_combat": validate_independent_combat(reports["independent_combat"], rom_sha256, recorder),
        "endurance": validate_endurance(reports["endurance"], rom_sha256,
                                         recorder, root),
        "fresh_build": validate_fresh_build(reports["fresh_build"], rom_sha256, root, recorder),
        "training": validate_training_evidence(root, rom_sha256, recorder),
    }
    return summaries
