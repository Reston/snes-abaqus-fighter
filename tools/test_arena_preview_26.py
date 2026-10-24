"""Bind arena thumbnails to current compiled scenery and both native PPUs."""
import ast
import ctypes as C
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from PIL import Image, ImageDraw
from emulator import Emulator, ROOT
from play_flow_media import inventory as media_inventory
import menu_assets
import test_inputs as inputs
import test_presentation as presentation
import test_compatibility as compatibility
from test_play_flow_26 import source_hashes
from test_champion import host_contract
from stage_depth_assets import colors
from release_evidence import EXPECTED_NATIVE_CORE, EXPECTED_INDEPENDENT_CORE

CHECKS = []
OUT = ROOT / 'docs/screenshots/play-flow-v026'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(ok, label, details=None):
    CHECKS.append({'check': label, 'passed': bool(ok), 'details': details})
    if not ok:
        raise AssertionError((label, details))


def decode_native(gfx, tilemap, palette):
    """Independent per-pixel SNES bitplane/map decode of x16..271."""
    entries = struct.unpack('<2048H', tilemap)
    rgb = colors(palette)
    image = Image.new('RGB', (256, 224))
    pixels = image.load()
    for y in range(224):
        for x in range(256):
            world_x = x + 16
            column = world_x // 8
            entry = entries[(column // 32) * 1024 + (y // 8) * 32 + column % 32]
            tile, bank = entry & 1023, (entry >> 10) & 7
            xx, yy = world_x % 8, y % 8
            if entry & 0x4000:
                xx = 7 - xx
            if entry & 0x8000:
                yy = 7 - yy
            offset = tile * 32 + yy * 2
            value = ((gfx[offset] >> (7 - xx)) & 1) | (((gfx[offset + 1] >> (7 - xx)) & 1) << 1)
            value |= (((gfx[offset + 16] >> (7 - xx)) & 1) << 2) | (((gfx[offset + 17] >> (7 - xx)) & 1) << 3)
            pixels[x, y] = (0, 0, 0) if value == 0 else rgb[(bank - 2) * 16 + value]
    return image


def reencode_menu(stages):
    """Execute only frozen pure encoding functions, with an isolated sink."""
    source = ROOT / 'tools/make_assets.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    glyphs = next(node.value for node in tree.body if isinstance(node, ast.Assign) and
                  any(isinstance(target, ast.Name) and target.id == 'GLYPHS' for target in node.targets))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and
                 node.name in ('text', 'color15', 'palbytes', 'tile', 'background')]
    payload = {}
    with tempfile.TemporaryDirectory(prefix='arena-reencode-', dir=ROOT / 'build') as directory:
        namespace = {'Image': Image, 'ImageDraw': ImageDraw, 'struct': struct, 'OUT': Path(directory),
                     'GLYPHS': ast.literal_eval(glyphs), 'asset': lambda name, data: payload.update({name + '.bin': bytes(data)})}
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), 'exec'), namespace)
        authored = menu_assets._arenas(stages, namespace['text'])
        native = namespace['background']('arenas', authored)
    for name, raw in payload.items():
        require((ROOT / 'assets/generated' / name).read_bytes() == raw,
                'arena binary is reproduced from current native stage pixels', {'file': name, 'sha256': sha(raw)})
    expected = Image.open(ROOT / 'assets/generated/arenas.png').convert('RGB')
    require(native.tobytes() == expected.tobytes(), 'arena preview PNG is exactly the current binary conversion')
    return {'payload': {name: sha(raw) for name, raw in payload.items()}, 'png_sha256': sha((ROOT / 'assets/generated/arenas.png').read_bytes())}


class AccuracyAdapter:
    def __init__(self):
        self.host = compatibility.Probe()
        self.ram, self.core = self.host.ram, self.host.core

    @property
    def frame(self):
        return self.host.frame_image.resize((256, 224), Image.Resampling.NEAREST).convert('RGB')

    def run(self, count=1, p1=(), p2=()):
        self.host.run(count, p1, p2)
        return inputs.trace(self)

    def close(self):
        self.host.close()


def native_case(stage, independent, expected):
    e = AccuracyAdapter() if independent else Emulator(core_options=inputs.MENU_CORE_OPTIONS)
    try:
        e.run(120)
        inputs.menu_arena(e, 1)
        for _ in range(stage):
            inputs.menu_press(e, ['down'], port=1)
        e.run(15)
        require(inputs.trace(e)['screen'] == 2 and inputs.trace(e)['arena'] == stage,
                'both-core controller menus reach the selected arena row', [stage, independent])
        presentation.verify_arena_cursor(e, stage)
        plate = presentation.verify_arena_plate(e, stage)
        path = OUT / f'arena-current-{stage}-{"accuracy" if independent else "snes9x"}.png'
        e.frame.save(path)
        inputs.menu_press(e, ['a'], port=1)
        e.run(140)
        require(inputs.trace(e)['screen'] == 3 and inputs.trace(e)['arena'] == stage,
                'selected preview loads its actual current stage', [stage, independent])
        memory = presentation.vram_bytes(e)
        generated = ROOT / 'assets/generated'
        gfx = (generated / f'stage{stage}_tiles.bin').read_bytes()
        tilemap = (generated / f'stage{stage}_map.bin').read_bytes()
        palette = (generated / f'stage{stage}_pal.bin').read_bytes()
        require(memory[:len(gfx)] == gfx and memory[0x7000:0x8000] == tilemap,
                'preview scenery payloads are the exact BG1 bytes uploaded in native play', [stage, independent])
        native = decode_native(memory[:len(gfx)], memory[0x7000:0x8000], palette)
        require(native.tobytes() == expected.tobytes(),
                'current thumbnail source matches an independent decode of native stage VRAM', [stage, independent])
        require(menu_assets.ARENA_PREVIEW_CROPS[stage] == (0, 64, 256, 192),
                'landmark crop avoids the hidden HUD rows and retains its 2:1 aspect', stage)
        return {'stage': stage, 'independent': independent, 'plate': plate,
                'capture': path.relative_to(ROOT).as_posix(), 'capture_sha256': sha(path.read_bytes()),
                'source_pixels_sha256': sha(native.tobytes()),
                'stage_payload_sha256': {'gfx': sha(gfx), 'map': sha(tilemap), 'palette': sha(palette)}}
    finally:
        e.close()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / 'dist/manifest.json').read_bytes())
    source = source_hashes()
    started = time.monotonic()
    report = {'status': 'failed', 'version': manifest['version'], 'rom_sha256': manifest['sha256'],
              'source_sha256': source, 'checks': CHECKS, 'host_contract': host_contract(),
              'controller_only': True, 'memory_writes': False, 'save_states': False, 'cases': []}
    try:
        require(sha((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()) == manifest['sha256'], 'preview proof identifies the exact current cartridge')
        for path, pin in ((ROOT / '.tools/core/snes9x_libretro.dll', EXPECTED_NATIVE_CORE),
                          (compatibility.CORE_PATH, EXPECTED_INDEPENDENT_CORE)):
            require(sha(Path(path).read_bytes()).lower() == pin['dll_sha256'].lower(), 'actual expanded preview core matches its pin', str(path))
        report['independent_core'] = compatibility.verify_manifest_and_pinned_core()
        palette = colors((ROOT / 'assets/generated/ui_pal.bin').read_bytes())
        stages = menu_assets.native_stage_previews(ROOT, palette)
        require(len(stages) == 3 and all(im.size == (256, 224) for im in stages), 'all current preview sources have native viewport dimensions')
        report['reproduction'] = reencode_menu(stages)
        for independent in (False, True):
            for stage in range(3):
                report['cases'].append(native_case(stage, independent, stages[stage]))
                print(json.dumps({'stage': stage, 'accuracy': independent, 'status': 'passed'}), flush=True)
        require(source_hashes() == source, 'preview source and harness remain fixed throughout proof')
        report['captures'] = media_inventory(ROOT, 'previews')
        report['status'] = 'passed'
    except Exception as error:
        report['error'] = repr(error)
        raise
    finally:
        report['check_count'] = len(CHECKS)
        report['presentation_checks'] = len(presentation.checks)
        report['elapsed_seconds'] = round(time.monotonic() - started, 3)
        (ROOT / 'docs/play-flow-v026-previews-report.json').write_bytes((json.dumps(report, indent=2) + '\n').encode())
        print(json.dumps({k: report[k] for k in ('status', 'check_count', 'elapsed_seconds')}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
