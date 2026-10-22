#!/usr/bin/env python3
"""Build a small offline reviewer for the generated native fighter strips.

The reviewer is deliberately separate from the emulator presentation gallery.
It reads the already generated 6144x80 RGBA strips, checks their native frame
contract, and gives an art reviewer a frame scrubber without inventing any
additional pixels.  ``--preview`` is safe to run while the native suites are
still in flight: it writes only the ignored ``build/`` draft and reports the
current suite identities instead of claiming release evidence.

Without ``--preview`` the six current native reports must all be complete and
must name the ROM in ``dist/manifest.json``.  The final page is then written to
``docs/ROSTER-REVIEW-v<version>.html`` with the twelve PNGs embedded as data
URLs, so it can be copied and reviewed offline.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html as html_lib
import io
import json
import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
FRAME_WIDTH = 96
FRAME_HEIGHT = 80
FRAME_COUNT = 64
ASSET_WIDTH = FRAME_WIDTH * FRAME_COUNT
ASSET_HEIGHT = FRAME_HEIGHT
BASELINE_Y = 78
DEFAULT_FIGHTER_ID = 11
REPORT_NAMES = (
    "test",
    "character-test",
    "presentation-test",
    "input-test",
    "stage-test",
    "training-test",
)


class ReviewError(RuntimeError):
    """A user-facing input or contract error while preparing the review."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReviewError(f"required manifest is missing: {path}") from exc
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReviewError(f"cannot read JSON manifest {path}: {exc}") from exc


def load_release_manifest(root: Path) -> tuple[dict[str, Any], str]:
    path = root / "dist" / "manifest.json"
    raw = path.read_bytes() if path.exists() else b""
    manifest = read_json(path)
    if not isinstance(manifest, dict):
        raise ReviewError(f"release manifest is not an object: {path}")
    required = ("version", "sha256", "checksum", "bytes")
    missing = [key for key in required if not manifest.get(key)]
    if missing:
        raise ReviewError(f"release manifest is missing {', '.join(missing)}")
    rom_sha = str(manifest["sha256"]).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", rom_sha):
        raise ReviewError("release manifest sha256 is not a 64-character digest")
    try:
        rom_bytes = int(manifest["bytes"])
    except (TypeError, ValueError) as exc:
        raise ReviewError("release manifest bytes is not an integer") from exc
    if rom_bytes <= 0:
        raise ReviewError("release manifest bytes must be positive")
    manifest["sha256"] = rom_sha
    manifest["bytes"] = rom_bytes
    return manifest, sha256_bytes(raw)


def parse_character_names(root: Path) -> list[str]:
    """Read the public names from the native C table, rather than duplicating it."""

    path = root / "src" / "characters.h"
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ReviewError(f"cannot read native character names {path}: {exc}") from exc
    match = re.search(
        r"characterNames\s*\[\s*12\s*\]\s*\[\s*12\s*\]\s*=\s*\{(.*?)\};",
        source,
        re.DOTALL,
    )
    if not match:
        raise ReviewError(f"native characterNames[12][12] table was not found in {path}")
    names = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', match.group(1))
    if len(names) != 12 or any(not name.strip() for name in names):
        raise ReviewError(f"native character name table must contain 12 names, found {len(names)}")
    return [bytes(name, "utf-8").decode("unicode_escape") for name in names]


def validate_character_manifest(root: Path, names: list[str]) -> tuple[str, dict[str, Any]]:
    path = root / "assets" / "generated" / "character-manifest.json"
    raw = path.read_bytes() if path.exists() else b""
    data = read_json(path)
    if not isinstance(data, list) or len(data) != len(names):
        raise ReviewError(f"character manifest must contain 12 entries: {path}")
    by_id: dict[int, dict[str, Any]] = {}
    for entry in data:
        if not isinstance(entry, dict):
            raise ReviewError(f"character manifest contains a non-object entry: {path}")
        try:
            fighter_id = int(entry["id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ReviewError(f"character manifest entry has no integer id: {path}") from exc
        if fighter_id in by_id or not 0 <= fighter_id < len(names):
            raise ReviewError(f"character manifest has duplicate or invalid id {fighter_id}")
        if str(entry.get("name", "")).upper() != names[fighter_id]:
            raise ReviewError(f"character manifest name does not match native id {fighter_id}")
        if entry.get("frame_count") != FRAME_COUNT:
            raise ReviewError(f"character manifest id {fighter_id} does not declare 64 frames")
        if entry.get("frame_canvas") != [FRAME_WIDTH, FRAME_HEIGHT]:
            raise ReviewError(f"character manifest id {fighter_id} does not declare a 96x80 frame")
        by_id[fighter_id] = entry
    if sorted(by_id) != list(range(len(names))):
        raise ReviewError("character manifest ids are not the complete 0..11 roster")
    return sha256_bytes(raw), {"entries": by_id, "path": path.relative_to(root).as_posix()}


def collect_assets(
    root: Path,
    names: list[str],
    preview: bool,
) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for fighter_id, name in enumerate(names):
        path = root / "assets" / "generated" / f"fighter{fighter_id:02d}.png"
        if not path.is_file():
            raise ReviewError(f"native fighter strip is missing: {path}")
        try:
            raw = path.read_bytes()
            with Image.open(io.BytesIO(raw)) as image:
                image.load()
                size = tuple(image.size)
                mode = image.mode
        except (OSError, ValueError) as exc:
            raise ReviewError(f"cannot decode native fighter strip {path}: {exc}") from exc
        if size != (ASSET_WIDTH, ASSET_HEIGHT):
            raise ReviewError(
                f"{path.name} must be {ASSET_WIDTH}x{ASSET_HEIGHT}, found {size[0]}x{size[1]}"
            )
        if mode != "RGBA":
            raise ReviewError(f"{path.name} must be RGBA, found {mode}")
        if size[0] // FRAME_WIDTH != FRAME_COUNT:
            raise ReviewError(f"{path.name} does not contain exactly 64 96px frames")
        digest = sha256_bytes(raw)
        absolute = path.resolve().as_posix()
        asset: dict[str, Any] = {
            "id": fighter_id,
            "name": name,
            "path": path.relative_to(root).as_posix(),
            "absolute_path": absolute,
            "sha256": digest,
            "width": size[0],
            "height": size[1],
            "frame_width": FRAME_WIDTH,
            "frame_height": FRAME_HEIGHT,
            "frame_count": FRAME_COUNT,
            # A preview intentionally points at the existing file so its
            # identity remains visible while the native suites run.  The
            # final page replaces this with a data URL below.
            "src": absolute if preview else "data:image/png;base64," + base64.b64encode(raw).decode("ascii"),
        }
        assets.append(asset)
    return assets


def report_state(path: Path, manifest: dict[str, Any], root: Path) -> dict[str, Any]:
    """Summarize one suite without hiding stale or incomplete evidence."""

    name = path.stem.removesuffix("-report")
    state: dict[str, Any] = {
        "name": name,
        "path": path.relative_to(root).as_posix(),
        "exists": path.is_file(),
        "status": "missing",
        "status_raw": None,
        "rom_sha256": None,
        "passed": None,
        "checks": None,
        "complete": False,
        "reason": "report is missing",
    }
    if not path.is_file():
        return state
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        state["status"] = "invalid"
        state["reason"] = f"cannot parse report: {exc}"
        return state
    if not isinstance(data, dict):
        state["status"] = "invalid"
        state["reason"] = "report is not an object"
        return state

    status_raw = data.get("status")
    rom_sha = str(data.get("rom_sha256", "")).lower() or None
    checks = data.get("checks")
    passed = data.get("passed")
    state.update(
        {
            "status_raw": status_raw,
            "rom_sha256": rom_sha,
            "passed": passed,
            "checks": len(checks) if isinstance(checks, list) else None,
        }
    )
    issues: list[str] = []
    if status_raw not in (None, "passed"):
        issues.append(f"status={status_raw!r}")
    if rom_sha != manifest["sha256"]:
        issues.append("ROM SHA does not match dist/manifest.json")
    if data.get("rom_bytes") != manifest["bytes"]:
        issues.append("ROM byte count does not match dist/manifest.json")
    if not isinstance(checks, list) or not checks:
        issues.append("checks are missing or empty")
    else:
        failed_checks = sum(
            1 for check in checks if not isinstance(check, dict) or check.get("passed") is not True
        )
        if failed_checks:
            issues.append(f"{failed_checks} failed or malformed checks")
    if isinstance(passed, bool) or not isinstance(passed, int):
        issues.append("passed count is not an integer")
    elif isinstance(checks, list) and passed != len(checks):
        issues.append("passed count does not equal checks count")
    state["complete"] = not issues
    if state["complete"]:
        state["status"] = "passed" if status_raw == "passed" else "passed (implicit)"
        state["reason"] = "matches the current release manifest"
    else:
        state["status"] = "pending"
        state["reason"] = "; ".join(issues)
    return state


def verification_summary(root: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        report_state(root / "docs" / f"{name}-report.json", manifest, root)
        for name in REPORT_NAMES
    ]


def esc(value: object, *, quote: bool = True) -> str:
    return html_lib.escape(str(value), quote=quote)


def build_html(
    *,
    manifest: dict[str, Any],
    manifest_sha256: str,
    character_manifest_sha256: str,
    assets: list[dict[str, Any]],
    reports: list[dict[str, Any]],
    preview: bool,
) -> str:
    all_suites_complete = all(report["complete"] for report in reports)
    if preview:
        if all_suites_complete:
            state_title = "PREVIEW - six native suites currently match"
            state_copy = (
                "This is an inspection draft. Run the final command after the release gates "
                "are intentionally accepted to create the docs artifact."
            )
        else:
            state_title = "PREVIEW - native suite verification pending"
            state_copy = (
                "The report identities below are read from disk while the current suites run. "
                "This draft is not release evidence and does not claim a verified ROM."
            )
    else:
        state_title = "VERIFIED - six native suites match the current ROM"
        state_copy = (
            "This final offline page embeds the exact generated strips after every current native "
            "suite matched the release manifest."
        )

    options = "".join(
        f'<option value="{fighter["id"]}"{" selected" if fighter["id"] == DEFAULT_FIGHTER_ID else ""}>'
        f'{esc(fighter["id"]):0>2} - {esc(fighter["name"])}</option>'
        for fighter in assets
    )
    report_rows: list[str] = []
    for report in reports:
        status_class = "ok" if report["complete"] else "pending"
        report_rom = report["rom_sha256"] or "-"
        report_rows.append(
            '<tr class="%s"><th scope="row">%s</th><td><span class="status-chip">%s</span>'
            '<small>%s</small></td><td><code>%s</code></td><td>%s / %s</td></tr>'
            % (
                status_class,
                esc(report["name"]),
                esc(report["status"].upper()),
                esc(report["reason"]),
                esc(report_rom),
                esc(report["passed"] if report["passed"] is not None else "-"),
                esc(report["checks"] if report["checks"] is not None else "-"),
            )
        )
    asset_rows: list[str] = []
    for asset in assets:
        display_path = asset["absolute_path"] if preview else asset["path"]
        asset_rows.append(
            '<tr><th scope="row">%02d</th><td>%s</td><td>%dx%d</td><td>%d</td>'
            '<td><code>%s</code></td><td><code>%s</code></td></tr>'
            % (
                asset["id"],
                esc(asset["name"]),
                asset["width"],
                asset["height"],
                asset["frame_count"],
                esc(asset["sha256"]),
                esc(display_path),
            )
        )

    runtime_roster = assets if preview else [
        {key: value for key, value in asset.items() if key != "absolute_path"}
        for asset in assets
    ]
    runtime = {
        "mode": "preview" if preview else "final",
        "manifest": {
            "version": manifest["version"],
            "rom_sha256": manifest["sha256"],
            "checksum": manifest["checksum"],
            "bytes": manifest["bytes"],
            "manifest_sha256": manifest_sha256,
            "character_manifest_sha256": character_manifest_sha256,
        },
        "reports": reports,
        "roster": runtime_roster,
    }
    runtime_json = json.dumps(runtime, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )
    version = esc(manifest["version"])
    page = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Abaqus: After Hours - native roster review v{version}</title>
<style>
:root {{
  color-scheme: light dark;
  --ink: var(--foreground, #17213a);
  --muted: var(--muted-foreground, #5a6880);
  --panel: var(--card, #f7f9fd);
  --panel-ink: var(--card-foreground, #17213a);
  --line: var(--border, #cad2e1);
  --accent: var(--primary, #1c376b);
  --accent-ink: var(--primary-foreground, #ffffff);
  --warning: var(--warning-surface, #fff3cc);
}}
* {{ box-sizing: border-box; }}
html {{ background: var(--background, #ffffff); color: var(--ink); }}
body {{ margin: 0; font: 14px/1.5 var(--font-sans, system-ui, sans-serif); }}
main {{ width: 100%; margin: 0; padding: 0; }}
h1 {{ margin: 0; font-size: clamp(21px, 4vw, 30px); letter-spacing: .02em; }}
h2 {{ margin: 0 0 8px; font-size: 17px; }}
h3 {{ margin: 0 0 7px; font-size: 15px; }}
p {{ margin: 0 0 12px; }}
.eyebrow {{ color: var(--muted); font-size: 12px; letter-spacing: .08em; text-transform: uppercase; }}
.intro {{ margin: 4px 0 18px; color: var(--muted); max-width: 780px; }}
.notice {{ margin: 16px 0; padding: 16px; border: 1px solid var(--line); border-radius: 10px; background: var(--warning); color: var(--panel-ink); }}
.notice strong {{ display: block; margin-bottom: 3px; }}
.identity, .review-card, .evidence, .asset-evidence {{ margin-top: 16px; padding: 16px; border: 1px solid var(--line); border-radius: 10px; background: var(--panel); color: var(--panel-ink); }}
.identity-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr)); gap: 10px; }}
.identity-item {{ min-width: 0; }}
.identity-item span {{ display: block; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .06em; }}
.identity-item code {{ display: block; margin-top: 2px; overflow-wrap: anywhere; }}
.toolbar {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin: 14px 0 16px; }}
.field {{ min-width: 0; }}
.field label, .check {{ display: block; margin-bottom: 5px; color: var(--muted); font-size: 12px; font-weight: 650; }}
select, input[type=range], button {{ width: 100%; font: inherit; }}
select, button {{ min-height: 36px; border: 1px solid var(--line); border-radius: 8px; padding: 7px 10px; background: var(--secondary, #eef2f9); color: var(--ink); }}
button {{ cursor: pointer; }}
button:hover, button:focus-visible {{ border-color: var(--accent); }}
.button-row {{ display: flex; flex-wrap: wrap; align-items: end; gap: 8px; }}
.button-row button {{ flex: 1 1 110px; width: auto; }}
button[aria-pressed=true] {{ border-color: transparent; background: var(--accent); color: var(--accent-ink); }}
.checks {{ display: flex; flex-wrap: wrap; align-items: end; gap: 13px; min-height: 36px; }}
.checks label {{ color: var(--ink); font-weight: 500; }}
.checks input {{ accent-color: var(--accent); }}
.frame-readout {{ display: flex; justify-content: space-between; gap: 12px; margin-top: 4px; color: var(--muted); font-size: 12px; }}
.frame-stage-wrap {{ overflow-x: auto; padding: 18px 10px 20px; }}
.frame-stage {{ position: relative; width: calc(96px * var(--stage-scale)); height: calc(80px * var(--stage-scale)); margin: 0 auto; background: #000008; box-shadow: 0 0 0 1px #55617a; --stage-scale: 1; }}
.frame-stage[data-scale="2"] {{ --stage-scale: 2; }}
.frame-stage canvas {{ display: block; width: 100%; height: 100%; image-rendering: pixelated; }}
.frame-stage canvas.flip {{ transform: scaleX(-1); }}
.guide {{ position: absolute; display: block; pointer-events: none; }}
.guide[hidden] {{ display: none; }}
.floor-guide {{ left: 0; right: 0; top: calc(78px * var(--stage-scale)); height: 1px; background: #ffd05b; box-shadow: 0 0 0 1px rgba(255,208,91,.25); }}
.frame-guide {{ inset: 0; border: 1px dashed rgba(255,255,255,.45); }}
.frame-caption {{ margin-top: 8px; text-align: center; color: var(--muted); font-size: 12px; }}
.status-line {{ min-height: 20px; margin-top: 9px; color: var(--muted); font-size: 12px; }}
details {{ margin: 16px 0; }}
summary {{ cursor: pointer; color: var(--muted); }}
.table-wrap {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
th, td {{ padding: 8px 7px; border-top: 1px solid var(--line); text-align: left; vertical-align: top; }}
th {{ white-space: nowrap; }}
td code, th code {{ overflow-wrap: anywhere; font: 11px/1.4 var(--font-mono, ui-monospace, monospace); }}
.suite-table .status-chip {{ display: inline-block; margin-bottom: 2px; }}
.suite-table small {{ display: block; color: var(--muted); max-width: 330px; }}
.suite-table tr.ok .status-chip {{ color: var(--success, #216e4e); }}
.suite-table tr.pending .status-chip {{ color: var(--destructive, #a32727); }}
details {{ margin-top: 14px; }}
summary {{ cursor: pointer; color: var(--muted); }}
.fineprint {{ margin-top: 18px; color: var(--muted); font-size: 12px; }}
@media (max-width: 560px) {{
  main {{ width: 100%; padding: 0; }}
  th, td {{ padding: 7px 5px; }}
}}
</style>
</head>
<body>
<main>
  <p class="eyebrow">Abaqus: After Hours / reviewer aid</p>
  <h1>Native roster frame review</h1>
  <p class="intro">Existing generated fighter strips at native pixels: 64 frames per fighter, each 96x80. Scrub or run a fixed-rate inspection sweep, flip the facing, and inspect the fixed floor baseline. The sweep does not reproduce in-game animation timing.</p>
  <section class="notice" aria-live="polite">
    <strong>{esc(state_title)}</strong>
    <span>{esc(state_copy)}</span>
  </section>
  <details><summary>Candidate identity</summary>
  <section class="identity" aria-labelledby="identity-title">
    <h2 id="identity-title">Candidate identity</h2>
    <div class="identity-grid">
      <div class="identity-item"><span>Version</span><code>v{version}</code></div>
      <div class="identity-item"><span>ROM SHA256</span><code>{esc(manifest["sha256"])}</code></div>
      <div class="identity-item"><span>Header checksum</span><code>{esc(manifest["checksum"])}</code></div>
      <div class="identity-item"><span>ROM size</span><code>{int(manifest["bytes"]):,} bytes</code></div>
      <div class="identity-item"><span>Source cartridge manifest SHA256</span><code>{esc(manifest_sha256)}</code></div>
      <div class="identity-item"><span>Character manifest SHA256</span><code>{esc(character_manifest_sha256)}</code></div>
    </div>
    <p class="fineprint">The source manifest is dist/manifest.json. The Windows package adds emulator pin metadata to its manifest; the cartridge SHA above identifies the same ROM.</p>
  </section></details>
  <section class="review-card" aria-labelledby="review-title">
    <h2 id="review-title">Frame inspector</h2>
    <div class="toolbar">
      <div class="field"><label for="fighter">Fighter</label><select id="fighter" aria-label="Fighter">{options}</select></div>
      <div class="field"><label for="group">Frame group</label><select id="group" aria-label="Frame group">
        <option value="0-15">Frames 0-15</option>
        <option value="16-31">Frames 16-31</option>
        <option value="32-47">Frames 32-47</option>
        <option value="48-63">Frames 48-63</option>
        <option value="all" selected>All frames (0-63)</option>
      </select></div>
      <div class="field"><label for="scale">Pixel scale</label><select id="scale" aria-label="Pixel scale"><option value="1">1x native</option><option value="2" selected>2x native</option></select></div>
      <div class="field button-row"><button id="play" type="button" aria-pressed="false" aria-label="Start fixed-rate inspection sweep">Run sweep</button><button id="first" type="button">First frame</button></div>
    </div>
    <div class="field"><label for="frame">Frame <output id="frame-number" for="frame">0</output> / 63</label><input id="frame" type="range" min="0" max="63" value="0" step="1" aria-label="Frame number"><div class="frame-readout"><span id="group-readout">All frames / individual scrub 0-63</span><span>native canvas 96x80 / floor y=78</span></div></div>
    <div class="checks"><label class="check"><input id="flip" type="checkbox"> Flip facing</label><label class="check"><input id="guides" type="checkbox" checked> Show native floor baseline + frame guides</label></div>
    <div class="frame-stage-wrap"><div id="stage" class="frame-stage" data-scale="1"><canvas id="frame-canvas" width="96" height="80" aria-label="Selected native fighter frame"></canvas><span class="guide floor-guide" aria-hidden="true"></span><span class="guide frame-guide" aria-hidden="true"></span></div></div>
    <p class="frame-caption" id="asset-caption">Loading Lars...</p>
    <p class="status-line" id="status-line" role="status">Loading the selected generated strip...</p>
  </section>
  <details><summary>Verification and asset hashes</summary>
  <section class="evidence" aria-labelledby="suite-title">
    <h2 id="suite-title">Native suite state</h2>
    <p class="fineprint">Each row is read from the named report on disk. A pending row can be stale or incomplete; the full ROM digest is shown so the page cannot quietly mix candidates.</p>
    <div class="table-wrap"><table class="suite-table"><thead><tr><th scope="col">Suite</th><th scope="col">State</th><th scope="col">Report ROM SHA256</th><th scope="col">Passed / checks</th></tr></thead><tbody>{''.join(report_rows)}</tbody></table></div>
  </section>
  <section class="asset-evidence" aria-labelledby="asset-title">
    <h2 id="asset-title">Generated strip identity</h2>
    <p class="fineprint">Every image below is an existing generated native strip. The review tool performs no art generation and does not rewrite the PNGs.</p>
    <div class="table-wrap"><table><thead><tr><th scope="col">ID</th><th scope="col">Native name</th><th scope="col">Strip</th><th scope="col">Frames</th><th scope="col">Asset SHA256</th><th scope="col">Source path</th></tr></thead><tbody>{''.join(asset_rows)}</tbody></table></div>
  </section>
  </details>
  <p class="fineprint">These are native generated asset frames, not emulator gameplay captures. Sequential source frame IDs can mix action ranges; the fixed-rate sweep is not in-game animation timing. Human likeness, motion, consent, and public-use approval remain pending. This reviewer has no audio.</p>
</main>
<script id="roster-data" type="application/json">{runtime_json}</script>
<script>
(() => {{
  const data = JSON.parse(document.getElementById('roster-data').textContent);
  const frameWidth = 96, frameHeight = 80;
  const groups = {{
    '0-15': [0, 15, 'Frames 0-15'],
    '16-31': [16, 31, 'Frames 16-31'],
    '32-47': [32, 47, 'Frames 32-47'],
    '48-63': [48, 63, 'Frames 48-63'],
    'all': [0, 63, 'All frames / individual scrub 0-63']
  }};
  const fighterSelect = document.getElementById('fighter');
  const groupSelect = document.getElementById('group');
  const scaleSelect = document.getElementById('scale');
  const frameInput = document.getElementById('frame');
  const frameNumber = document.getElementById('frame-number');
  const groupReadout = document.getElementById('group-readout');
  const playButton = document.getElementById('play');
  const firstButton = document.getElementById('first');
  const flipInput = document.getElementById('flip');
  const guidesInput = document.getElementById('guides');
  const stage = document.getElementById('stage');
  const canvas = document.getElementById('frame-canvas');
  const context = canvas.getContext('2d');
  const caption = document.getElementById('asset-caption');
  const statusLine = document.getElementById('status-line');
  const imageCache = new Map();
  let timer = null;
  let drawRequest = 0;

  function selectedAsset() {{
    return data.roster.find(asset => String(asset.id) === fighterSelect.value) || data.roster[0];
  }}
  function selectedBounds() {{
    const bounds = groups[groupSelect.value] || groups.all;
    return [bounds[0], bounds[1]];
  }}
  function setScale() {{ stage.dataset.scale = scaleSelect.value; }}
  function setGuides() {{ document.querySelectorAll('.guide').forEach(node => node.hidden = !guidesInput.checked); }}
  function updateReadout() {{
    const frame = Number(frameInput.value);
    frameNumber.value = String(frame);
    groupReadout.textContent = (groups[groupSelect.value] || groups.all)[2];
  }}
  function loadAsset(asset) {{
    if (imageCache.has(asset.id)) return imageCache.get(asset.id);
    const promise = new Promise((resolve, reject) => {{
      const image = new Image();
      image.onload = () => {{
        if (image.naturalWidth !== 6144 || image.naturalHeight !== 80) {{
          reject(new Error(asset.name + ' decoded as ' + image.naturalWidth + 'x' + image.naturalHeight));
          return;
        }}
        resolve(image);
      }};
      image.onerror = () => reject(new Error('could not load ' + asset.path));
      image.src = asset.src;
    }});
    imageCache.set(asset.id, promise);
    return promise;
  }}
  function draw() {{
    const request = ++drawRequest;
    const asset = selectedAsset();
    const frame = Number(frameInput.value);
    updateReadout();
    caption.textContent = asset.name + ' / frame ' + frame + ' / 96 x 80 native pixels';
    statusLine.textContent = 'Decoding ' + asset.path + '...';
    loadAsset(asset).then(image => {{
      if (request !== drawRequest) return;
      context.clearRect(0, 0, frameWidth, frameHeight);
      context.imageSmoothingEnabled = false;
      context.save();
      if (flipInput.checked) {{ context.translate(frameWidth, 0); context.scale(-1, 1); }}
      context.drawImage(image, frame * frameWidth, 0, frameWidth, frameHeight, 0, 0, frameWidth, frameHeight);
      context.restore();
      canvas.classList.toggle('flip', false);
      statusLine.textContent = 'Ready / 64 native frames / fixed-rate inspection sweep (not gameplay timing)';
    }}).catch(error => {{ if (request !== drawRequest) return; statusLine.textContent = 'Asset error: ' + error.message; console.error(error); }});
  }}
  function stop() {{
    if (timer !== null) window.clearInterval(timer);
    timer = null;
    playButton.textContent = 'Run sweep';
    playButton.setAttribute('aria-pressed', 'false');
  }}
  function tick() {{
    const [low, high] = selectedBounds();
    let frame = Number(frameInput.value) + 1;
    if (frame > high || frame < low) frame = low;
    frameInput.value = String(frame);
    draw();
  }}
  function start() {{
    if (timer !== null) return;
    playButton.textContent = 'Pause sweep';
    playButton.setAttribute('aria-pressed', 'true');
    timer = window.setInterval(tick, 170);
  }}
  fighterSelect.addEventListener('change', () => {{ stop(); frameInput.value = String(selectedBounds()[0]); draw(); }});
  groupSelect.addEventListener('change', () => {{
    stop(); const [low, high] = selectedBounds();
    frameInput.min = String(low); frameInput.max = String(high);
    frameInput.value = String(low); draw();
  }});
  scaleSelect.addEventListener('change', setScale);
  frameInput.addEventListener('input', draw);
  flipInput.addEventListener('change', draw);
  guidesInput.addEventListener('change', setGuides);
  playButton.addEventListener('click', () => timer === null ? start() : stop());
  firstButton.addEventListener('click', () => {{ stop(); frameInput.value = String(selectedBounds()[0]); draw(); }});
  document.addEventListener('visibilitychange', () => {{ if (document.hidden) stop(); }});
  setScale();
  setGuides();
  draw();
  console.log('Roster review ready: ' + data.roster.length + ' strips, ' + data.roster[0].frame_count + ' frames each, mode=' + data.mode);
}})();
</script>
</body>
</html>
'''
    return page


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preview",
        action="store_true",
        help="write the ignored build/roster-review-preview.html without requiring current suites",
    )
    args = parser.parse_args(argv)
    try:
        manifest, manifest_sha256 = load_release_manifest(ROOT)
        names = parse_character_names(ROOT)
        character_manifest_sha256, _ = validate_character_manifest(ROOT, names)
        assets = collect_assets(ROOT, names, args.preview)
        reports = verification_summary(ROOT, manifest)
        if not args.preview and not all(report["complete"] for report in reports):
            pending = ", ".join(report["name"] for report in reports if not report["complete"])
            raise ReviewError(
                "cannot create the final roster review until all six current-ROM reports pass "
                f"({pending} pending); use --preview for the ignored draft"
            )
        page = build_html(
            manifest=manifest,
            manifest_sha256=manifest_sha256,
            character_manifest_sha256=character_manifest_sha256,
            assets=assets,
            reports=reports,
            preview=args.preview,
        )
        target = ROOT / (
            Path("build") / "roster-review-preview.html"
            if args.preview
            else Path("docs") / f"ROSTER-REVIEW-v{manifest['version']}.html"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page, encoding="utf-8", newline="\n")
        print(
            json.dumps(
                {
                    "html": str(target),
                    "mode": "preview" if args.preview else "final",
                    "version": manifest["version"],
                    "rom_sha256": manifest["sha256"],
                    "roster": len(assets),
                    "frames_per_fighter": FRAME_COUNT,
                    "native_suites_complete": all(report["complete"] for report in reports),
                    "bytes": target.stat().st_size,
                },
                sort_keys=True,
            )
        )
        return 0
    except ReviewError as exc:
        print(f"make_roster_review: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
