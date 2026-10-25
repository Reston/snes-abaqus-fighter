"""Prepare a self-contained Cloudflare static site around the native SNES ROM.

No native source, generated art, ROM, emulator cache or credentials are uploaded
by this command. Only build/cloudflare/site is the deployment directory.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import shutil
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build" / "cloudflare" / "site"
MAX_ASSET_BYTES = 25 * 1024 * 1024


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pinned_download(url: str, path: Path, expected: str) -> bytes:
    if path.is_file():
        data = path.read_bytes()
        if digest(data) == expected:
            return data
        raise ValueError(f"Cached dependency failed SHA-256 verification: {path.relative_to(ROOT)}")
    request = urllib.request.Request(url, headers={"User-Agent": "Abaqus-After-Hours"})
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read()
    if digest(data) != expected:
        raise ValueError(f"Downloaded dependency failed SHA-256 verification: {url}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def build() -> dict:
    manifest = json.loads((ROOT / "dist" / "manifest.json").read_text(encoding="utf-8"))
    rom_path = ROOT / "dist" / "abaqus-after-hours.sfc"
    rom = rom_path.read_bytes()
    if manifest.get("rom") != rom_path.name or len(rom) != manifest.get("bytes") or digest(rom) != manifest.get("sha256"):
        raise ValueError("Native ROM does not match dist/manifest.json; build the cartridge first")
    lock = json.loads((ROOT / "web" / "vendor-lock.json").read_text(encoding="utf-8"))
    cache = ROOT / ".tools" / "emulatorjs" / lock["emulatorjs_version"]
    jobs = [(name, lock["base_url"] + name, sha) for name, sha in lock["files"].items()]
    jobs.append(("LICENSE", lock["license"]["url"], lock["license"]["sha256"]))

    def fetch(job: tuple[str, str, str]) -> tuple[str, bytes]:
        name, url, sha = job
        return name, pinned_download(url, cache / name, sha)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        dependencies = dict(pool.map(fetch, jobs))

    # Only update the fixed build output. Preserve its directory so Windows
    # file watchers remain attached, and never follow symlinks or junctions.
    if OUTPUT.is_symlink() or (hasattr(OUTPUT, "is_junction") and OUTPUT.is_junction()):
        raise ValueError("Deployment output must be a regular build/cloudflare/site directory")
    if not (ROOT / "build").resolve().is_relative_to(ROOT.resolve()):
        raise ValueError("Build directory resolves outside this checkout")
    if not OUTPUT.resolve().is_relative_to((ROOT / "build").resolve()):
        raise ValueError("Deployment output resolves outside this checkout's build directory")
    if OUTPUT.exists():
        for entry in OUTPUT.rglob("*"):
            if entry.is_symlink() or (hasattr(entry, "is_junction") and entry.is_junction()):
                raise ValueError("Deployment output contains a symlink or junction")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    wanted = {"abaqus-after-hours.sfc", "poster.png", "release.json", "release.js", "licenses/project.txt"}
    for name in ["index.html", "style.css", "player.js", "credits.html", "404.html", "icon.svg", "_headers"]:
        shutil.copyfile(ROOT / "web" / name, OUTPUT / name)
        wanted.add(name)
    (OUTPUT / rom_path.name).write_bytes(rom)
    shutil.copyfile(ROOT / "docs/screenshots/menu-preview/presentation/title.png", OUTPUT / "poster.png")
    emulator_path = "emulator/" + lock["emulatorjs_version"] + "/"
    for name, data in dependencies.items():
        target = OUTPUT / ("licenses/EmulatorJS.txt" if name == "LICENSE" else emulator_path + name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        wanted.add(target.relative_to(OUTPUT).as_posix())
    for name in ["Snes9x", "PVSnesLib", "SNESMod"]:
        shutil.copyfile(ROOT / "licenses" / f"{name}.txt", OUTPUT / "licenses" / f"{name}.txt")
        wanted.add(f"licenses/{name}.txt")
    shutil.copyfile(ROOT / "LICENSE", OUTPUT / "licenses/project.txt")
    release = {
        "title": manifest["title"], "version": manifest["version"],
        "rom_sha256": manifest["sha256"], "rom_bytes": len(rom),
        "emulatorjs_version": lock["emulatorjs_version"], "emulator_path": emulator_path, "core": "snes9x",
        "vendor_sha256": lock["files"], "native_rom_unchanged": True,
    }
    (OUTPUT / "release.json").write_text(json.dumps(release, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / "release.js").write_text("window.ABAQUS_RELEASE = " + json.dumps(release) + ";\n", encoding="utf-8")
    for path in OUTPUT.rglob("*"):
        if path.is_file() and path.relative_to(OUTPUT).as_posix() not in wanted:
            path.unlink()
    files = [path for path in OUTPUT.rglob("*") if path.is_file()]
    oversized = [str(path.relative_to(OUTPUT)) for path in files if path.stat().st_size > MAX_ASSET_BYTES]
    if oversized:
        raise ValueError(f"Cloudflare's per-file limit exceeded: {oversized}")
    if digest(rom_path.read_bytes()) != manifest["sha256"]:
        raise ValueError("Native ROM changed while preparing the web player")
    summary = {"output": str(OUTPUT), "version": manifest["version"], "rom_sha256": manifest["sha256"],
               "files": len(files), "bytes": sum(path.stat().st_size for path in files)}
    print(json.dumps(summary, indent=2))
    return summary


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    try:
        build()
    except (OSError, ValueError, KeyError) as error:
        print(f"Web build failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
