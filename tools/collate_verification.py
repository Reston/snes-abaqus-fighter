#!/usr/bin/env python3
"""Collate the current technical verification evidence without running tests.

This is the source-controlled replacement for the temporary finalization helper
used by the v0.13 candidate.  It reads ``dist/manifest.json`` for the current
candidate identity, delegates gate logic to the existing read-only validators,
and writes one concise verification record only after every required evidence
input passes.  It never builds a package and never canonicalizes or rewrites an
input report.  Use ``--check`` to run the same validation without writing the
summary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from collections.abc import Mapping
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import package
import preservation
from release_evidence import EXTRA_REPORTS, validate_release_evidence


NATIVE_SUITES = (
    ("gameplay", "docs/test-report.json", None),
    ("characters", "docs/character-test-report.json", None),
    ("presentation", "docs/presentation-test-report.json", None),
    ("inputs", "docs/input-test-report.json", None),
    ("stages", "docs/stage-test-report.json", None),
    ("training", "docs/training-test-report.json", "training"),
)

CHAMPION_ROUTES = (
    ("a", "docs/champion-ending-report.json"),
    ("start", "docs/champion-ending-start-report.json"),
    ("b", "docs/champion-ending-back-report.json"),
)

HUMAN_GATES_OPEN = (
    "gameplay and balance",
    "full listening",
    "physical controllers",
    "likeness and consent",
    "team and public use",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def read_json(root: Path, path: str, label: str) -> Any:
    return package.read_json(root / path, label)


def require(condition: bool, message: str, details: Any = None) -> None:
    package.require(condition, message, details)


def load_manifest(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = read_json(root, "dist/manifest.json", "release manifest")
    require(isinstance(manifest, Mapping), "Release manifest must be an object")
    for field in ("version", "sha256", "checksum", "bytes"):
        require(field in manifest, "Release manifest is missing " + field)
    version = str(manifest["version"])
    rom_sha = str(manifest["sha256"]).lower()
    require(len(rom_sha) == 64 and all(char in "0123456789abcdef" for char in rom_sha),
            "Release manifest ROM SHA256 is invalid", rom_sha)
    try:
        rom_bytes = int(manifest["bytes"])
    except (TypeError, ValueError) as error:
        raise package.PackageError("Release manifest byte count is invalid") from error
    require(rom_bytes > 0, "Release manifest byte count must be positive")
    current = dict(manifest)
    current["version"] = version
    current["sha256"] = rom_sha
    current["bytes"] = rom_bytes
    return current, {
        "version": version,
        "rom_sha256": rom_sha,
        "checksum": str(manifest["checksum"]),
        "bytes": rom_bytes,
    }


def validate_cartridge(root: Path, manifest: Mapping) -> dict[str, Any]:
    path = root / "dist/abaqus-after-hours.sfc"
    require(path.is_file(), "Current native cartridge is missing", relative(root, path))
    raw = path.read_bytes()
    digest = sha256_bytes(raw)
    require(len(raw) == manifest["bytes"], "Current native cartridge byte count differs from manifest",
            {"actual": len(raw), "expected": manifest["bytes"]})
    require(digest == manifest["sha256"], "Current native cartridge differs from manifest",
            {"actual": digest, "expected": manifest["sha256"]})
    return {"file": relative(root, path), "bytes": len(raw), "sha256": digest}


def validate_native_suites(root: Path, manifest: Mapping) -> tuple[dict[str, Any], int]:
    suites: dict[str, Any] = {}
    total = 0
    for label, report_name, suite in NATIVE_SUITES:
        report = read_json(root, report_name, label)
        require(isinstance(report, Mapping), f"{label} report must be an object")
        package.validate_suite(report, label, manifest["sha256"], suite)
        require(report.get("rom_bytes") == manifest["bytes"],
                f"{label} report byte count must match the current manifest")
        checks = report["checks"]
        passed = int(report["passed"])
        suites[label] = {
            "report": report_name,
            "status": report.get("status", "passed"),
            "passed": passed,
            "checks": len(checks),
            "elapsed_seconds": report.get("elapsed_seconds"),
        }
        total += passed
    return suites, total


def validate_independent_smoke(root: Path, manifest: Mapping) -> dict[str, Any]:
    report_name = "docs/compatibility-test-report.json"
    report = read_json(root, report_name, "independent compatibility smoke")
    require(isinstance(report, Mapping), "Independent compatibility smoke must be an object")
    rom = report.get("rom", {})
    require(report.get("status") == "passed" and isinstance(rom, Mapping) and
            rom.get("sha256") == manifest["sha256"] and rom.get("bytes") == manifest["bytes"],
            "Independent compatibility smoke must match the current ROM")
    require(not report.get("errors"), "Independent compatibility smoke contains errors",
            report.get("errors"))
    checks = report.get("checks", {})
    return {
        "status": report["status"],
        "report": report_name,
        "rom_sha256": rom["sha256"],
        "bytes": rom["bytes"],
        "scope": report.get("scope"),
        "check_sections": sorted(checks) if isinstance(checks, Mapping) else [],
        "core": report.get("core"),
        "host_contract": report.get("host_contract"),
    }


def summarize_release_evidence(root: Path, manifest: Mapping) -> dict[str, Any]:
    """Run the existing release-scale validators and attach their source paths."""

    summaries = validate_release_evidence(root, manifest["sha256"])
    result: dict[str, Any] = {}
    for key, summary in summaries.items():
        report_path = EXTRA_REPORTS.get(key)
        entry = dict(summary)
        if report_path is not None:
            entry["report"] = report_path
        result[key] = entry
    return result


def summarize_champion(root: Path, manifest: Mapping) -> dict[str, Any]:
    package.validate_champion_evidence(root, manifest)
    routes: dict[str, Any] = {}
    for key, report_name in CHAMPION_ROUTES:
        report = read_json(root, report_name, "champion route")
        ladder = report.get("ladder", [])
        routes[key] = {
            "report": report_name,
            "status": report.get("status"),
            "exit": report.get("exit"),
            "ladder_opponents": len(ladder) if isinstance(ladder, list) else None,
            "capture": report.get("capture"),
        }
    audio_name = "docs/champion-audio-report.json"
    audio = read_json(root, audio_name, "champion audio")
    listening_name = f"docs/audio-listening-v{manifest['version']}.json"
    # validate_champion_evidence checks this transitively; keep this explicit
    # so a future validator refactor cannot silently drop the listening gate.
    package.validate_listening_record(root, manifest)
    listening = read_json(root, listening_name, "current listening record")
    return {
        "routes": routes,
        "audio": {
            "report": audio_name,
            "status": audio.get("status"),
            "checks": len(audio.get("checks", [])),
            "human_listening_approved": audio.get("human_listening_approved"),
        },
        "listening": {
            "record": listening_name,
            "status": listening.get("status"),
            "archive": listening.get("archive"),
            "source_report": listening.get("source_report"),
            "source_report_sha256": listening.get("source_report_sha256"),
            "human_listening_approved": listening.get("human_listening_approved"),
        },
    }


def summarize_menu_and_authoring(root: Path, manifest: Mapping) -> dict[str, Any]:
    menu_name = "docs/menu-footer-report.json"
    menu = read_json(root, menu_name, "menu footer evidence")
    package.validate_menu_evidence(menu, root, manifest)
    authoring_name = "docs/authoring-guards-report.json"
    authoring = read_json(root, authoring_name, "authoring guard evidence")
    package.validate_authoring_evidence(authoring, root, manifest)
    return {
        "menu": {
            "report": menu_name,
            "status": menu.get("status"),
            "checks": len(menu.get("checks", [])),
            "controller_actions": len(menu.get("controller_actions", [])),
            "native_states": len(menu.get("native_preservation", {}).get("states", {})),
        },
        "authoring": {
            "report": authoring_name,
            "status": authoring.get("status"),
            "runs": len(authoring.get("runs", [])),
            "source_commit": authoring.get("source_commit"),
            "tests_per_run": [run.get("tests") for run in authoring.get("runs", [])],
        },
    }


def summarize_preservation(root: Path, manifest: Mapping, source_commit: str) -> dict[str, Any]:
    version = str(manifest["version"])
    policy = preservation.POLICIES.get(version)
    require(isinstance(policy, Mapping), "No approved preservation policy for current version", version)
    report_name = f"docs/preservation-v{version}.json"
    report = read_json(root, report_name, "current preservation report")
    require(isinstance(report, Mapping), "Current preservation report must be an object")
    try:
        preservation.validate_report(root, dict(report), dict(manifest), source_commit)
    except (ValueError, OSError, KeyError) as error:
        raise package.PackageError(f"Current preservation report is stale or incomplete: {error}") from error
    return {
        "report": report_name,
        "status": report.get("status"),
        "baseline_commit": policy["baseline_commit"],
        "baseline_version": policy["baseline_version"],
        "baseline_rom_sha256": policy["baseline_rom_sha256"],
        "allowed_changed": sorted(policy["allowed_changed"]),
        "allowed_added": sorted(policy["allowed_added"]),
        "generated_assets_total": report.get("generated_assets_total"),
        "existing_assets_preserved": report.get("existing_assets_preserved"),
        "generated_assets_modified": report.get("generated_assets_modified"),
        "generated_assets_added": report.get("generated_assets_added"),
        "native_assembly_preserved": report.get("native_assembly_preserved"),
        "source_freeze": report.get("source_freeze"),
    }


def collate(root: Path = ROOT) -> dict[str, Any]:
    manifest, identity = load_manifest(root)
    cartridge = validate_cartridge(root, manifest)
    native_suites, native_checks_total = validate_native_suites(root, manifest)
    independent_smoke = validate_independent_smoke(root, manifest)
    release_evidence = summarize_release_evidence(root, manifest)
    fresh_name = EXTRA_REPORTS["fresh_build"]
    fresh = read_json(root, fresh_name, "fresh source rebuild")
    require(isinstance(fresh, Mapping), "Fresh source rebuild report must be an object")
    source_commit = str(fresh["source_commit"])
    source_tree = str(fresh["source_tree"])
    supplemental = summarize_menu_and_authoring(root, manifest)
    champion = summarize_champion(root, manifest)
    preservation_summary = summarize_preservation(root, manifest, source_commit)
    return {
        "version": identity["version"],
        "rom_sha256": identity["rom_sha256"],
        "rom_bytes": identity["bytes"],
        "checksum": identity["checksum"],
        "status": "passed",
        "scope": "Current native emulator candidate verification; human review gates remain open.",
        "cartridge": cartridge,
        "source_commit": source_commit,
        "source_tree": source_tree,
        "source_rebuild": {
            "report": fresh_name,
            "generated_assets": len(fresh.get("generated_assets", [])),
            "generated_assets_verified": fresh.get("generated_assets_verified"),
            "symbols_equal_after_source_path_normalization": fresh.get(
                "symbols_equal_after_source_path_normalization"
            ),
            "elapsed_seconds": fresh.get("elapsed_seconds"),
        },
        "native_suites": native_suites,
        "native_checks_total": native_checks_total,
        "independent_smoke": independent_smoke,
        "release_evidence": release_evidence,
        "supplemental_evidence": supplemental,
        "champion_evidence": champion,
        # Keep the compact historical field names alongside the grouped
        # records so release notes can consume this generic summary without
        # knowing which candidate version produced it.
        "champion_routes": champion["routes"],
        "champion_audio": champion["audio"],
        "listening_record": champion["listening"],
        "menu_evidence": supplemental["menu"],
        "authoring_evidence": supplemental["authoring"],
        "preservation": preservation_summary,
        "public_release_certified": False,
        "human_gates": list(HUMAN_GATES_OPEN),
        "human_gates_open": list(HUMAN_GATES_OPEN),
        "original_hardware": "unverified; outside the first emulator-release support scope",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate and print a compact result without writing the verification JSON",
    )
    args = parser.parse_args(argv)
    try:
        summary = collate(ROOT)
        if args.check:
            print(json.dumps({
                "status": summary["status"],
                "version": summary["version"],
                "rom_sha256": summary["rom_sha256"],
                "native_checks_total": summary["native_checks_total"],
                "source_commit": summary["source_commit"],
                "source_tree": summary["source_tree"],
            }, sort_keys=True))
            return 0
        target = ROOT / f"docs/verification-v{summary['version']}.json"
        target.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(json.dumps({
            "status": summary["status"],
            "verification": relative(ROOT, target),
            "version": summary["version"],
            "rom_sha256": summary["rom_sha256"],
            "native_checks_total": summary["native_checks_total"],
            "source_commit": summary["source_commit"],
            "source_tree": summary["source_tree"],
        }, sort_keys=True))
        return 0
    except (package.PackageError, ValueError, KeyError, OSError, TypeError) as error:
        print(f"collate_verification: error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
