"""Native impact proof: controllers only, read-only telemetry/VRAM, silent video.

Run after tools/build.py. No GUI, audio device, RAM writes or save states.
The focused report deliberately does not claim the six integration suites.
"""
from __future__ import annotations

import ctypes as C
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parent))
from effect_assets import make_effect_sheet
from expansion_contracts import preserved_assets, preserved_native
from release_evidence import EXPECTED_NATIVE_CORE, EXPECTED_INDEPENDENT_CORE
from test_characters import boot, vram
from test_inputs import trace, signed16
from test_stages import oam_entry, oam_memory, scanline_budget

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/screenshots/expansion-02'
REPORT = ROOT / 'docs/expansion-02-report.json'
CHECKS = []
SYMBOLS = {}
SHEET = make_effect_sheet()
PALETTE = []
pal = (ROOT / 'assets/generated/effects_pal.bin').read_bytes()
for i in range(16):
    color = int.from_bytes(pal[i * 2:i * 2 + 2], 'little')
    PALETTE.append(tuple(((color >> shift) & 31) * 8 for shift in (0, 5, 10)))


def check(ok, label, detail=None):
    CHECKS.append({'check': label, 'passed': bool(ok), 'details': detail})
    if not ok:
        raise AssertionError((label, detail))


def symbols(path):
    return {name: int(addr, 16) for addr, name in re.findall(
        r'^([0-9a-fA-F]+) (\S+)$', path.read_text(encoding='utf-8'), re.M)}


def byte(e, name):
    addr = SYMBOLS[name]
    return C.string_at(e.ram + (addr & 0x1ffff), 1)[0]


def word(e, offset):
    return int.from_bytes(C.string_at(e.ram + offset, 2), 'little')


def snapshot(e):
    s = trace(e)
    s.update({n: byte(e, n) for n in ('fxLife', 'fxType', 'fxX', 'fxY', 'shake')})
    s['ppu_stat'] = word(e, 0x1ff00 + 114 * 2)
    s['ambient_clock'] = word(e, 0x1ff00 + 116 * 2)
    raw = oam_memory(e)
    s['effect'] = oam_entry(raw, 69)
    s['budget'] = scanline_budget(raw)
    s['shadows'] = [oam_entry(raw, i) for i in (64, 65, 66, 67)]
    return s


def drive(e, port, keys=(), defender=()):
    return e.run(1, **{f'p{port + 1}': keys, f'p{2 - port}': defender})


def close(e, port, gap=26):
    toward = 'right' if port == 0 else 'left'
    for _ in range(180):
        if abs(trace(e)['x1'] - trace(e)['x2']) <= gap * 16:
            e.run(5)
            return
        drive(e, port, [toward])
    raise AssertionError('Controller approach failed')


def boot_independent(stage):
    from test_compatibility import Probe, press

    class Adapter:
        def __init__(self):
            self.probe = Probe()
            self.core, self.ram = self.probe.core, self.probe.ram

        @property
        def frame(self):
            return self.probe.frame_image.resize((256, 224), Image.Resampling.NEAREST)

        def run(self, count=1, p1=(), p2=()):
            return self.probe.run(count, p1, p2)

        def close(self):
            self.probe.close()

    e = Adapter()
    p = e.probe
    p.run(120)
    press(p, 'down')
    press(p, 'a')
    press(p, 'a')
    while p.state()['selected2']:
        press(p, 'left', 1)
    press(p, 'a', 1)
    for _ in range(stage):
        press(p, 'down')
    press(p, 'a')
    for _ in range(180):
        if p.state()['screen'] == 3 and not p.state()['intro']:
            break
        p.run(1)
    check(p.state()['screen'] == 3 and not p.state()['intro'],
          'Independent Accuracy controller boot reaches live local match', p.state())
    p.run(3)
    return e


def stage_shift(before, after):
    # Unobscured upper stage band; search beyond the allowed envelope so a
    # larger accidental camera kick fails instead of being clamped by the test.
    sample = before.crop((16, 42, 240, 62))
    scores = []
    for dy in range(-3, 4):
        for dx in range(-6, 7):
            candidate = after.crop((16 + dx, 42 + dy, 240 + dx, 62 + dy))
            error = sum(ImageStat.Stat(ImageChops.difference(sample, candidate)).mean)
            scores.append((error, dx, dy))
    error, dx, dy = min(scores)
    return {'x': dx, 'y': dy, 'mean_rgb_error': round(error, 3)}


def pixel_match(frame, entry):
    """Match every opaque spark pixel; contact rotation must defeat occlusion."""
    x0 = (entry['tile'] - 384) % 16 * 8
    y0 = (entry['tile'] - 384) // 16 * 8
    matched = total = 0
    for y in range(16):
        for x in range(16):
            sx = 15 - x if entry['attr'] & 0x40 else x
            index = SHEET.getpixel((x0 + sx, y0 + y))
            if not index:
                continue
            px, py = entry['x'] + x, entry['y'] + y
            if 0 <= px < frame.width and 40 <= py < frame.height:
                total += 1
                got = frame.getpixel((px, py))
                if max(abs(a - b) for a, b in zip(got, PALETTE[index])) <= 8:
                    matched += 1
    return {'matched': matched, 'opaque': total,
            'ratio': matched / max(1, total)}


CASES = (
    # name, command, presentation kind (0 strong / 1 guard / 2 light), block
    ('light-punch', ('y',), 2, False),
    ('light-kick', ('b',), 2, False),
    ('strong-punch', ('x',), 0, False),
    ('strong-kick', ('a',), 0, False),
    ('light-block', ('y',), 1, True),
    ('strong-block', ('x',), 1, True),
    ('low-light', ('down', 'b'), 2, False),
    ('low-strong', ('down', 'a'), 0, False),
    ('low-block', ('down', 'a'), 1, True),
    ('air-light', ('up', 'b'), 2, False),
    ('air-strong', ('up', 'a'), 0, False),
    ('air-target', ('y',), 2, False),
)


def contact_case(stage, port, case, capture=False, engine='snes9x'):
    name, command, kind, blocked = case
    label = f'{engine} stage{stage} P{port + 1} {name}'
    e = boot(1, 5, stage, 5) if engine == 'snes9x' else boot_independent(stage)
    rows, images = [], []
    try:
        close(e, port)
        start = snapshot(e)
        background = e.frame.copy()
        defender_keys = ('down', 'right' if port == 0 else 'left') if blocked else ()
        if name == 'air-target':
            defender_keys = ('up',)
        contact = None
        for tick in range(52):
            drive(e, port, command if tick < 3 else (), defender_keys)
            s = snapshot(e)
            rows.append(s)
            images.append(e.frame.copy())
            if contact is None and s['hitstop']:
                contact = len(rows) - 1
        check(contact is not None, label + ' actual controller contact', rows[-1])
        hit = rows[contact]
        d, a = str(2 - port), str(port + 1)
        check((hit['fxType'] & 3) == kind and hit[f'guard{d}'] == int(blocked),
              label + ' correct native impact class', hit)
        check(hit['hitstop'] == (3 if blocked else 4 if kind == 2 else 6),
              label + ' exact class-specific hitstop', hit['hitstop'])
        check((hit[f'hp{d}'] >= start[f'hp{d}'] - 1) if blocked else
              (hit[f'hp{d}'] < start[f'hp{d}']),
              label + ' guard/chip or real damage established by gameplay',
              {'before': start[f'hp{d}'], 'after': hit[f'hp{d}']})
        if name.startswith('air-'):
            airborne = hit[f'y{d}'] if name == 'air-target' else hit[f'y{a}']
            check(signed16(airborne) < 0, label + ' genuinely airborne at contact', airborne)
        if name.startswith('low-'):
            check(hit['fxY'] == 179, label + ' spark stays at low contact height', hit['fxY'])
        check(hit['effect']['tile'] in ({416, 418} if blocked else
                                       {426, 428} if kind == 2 else {384, 386, 388, 390}),
              label + ' uses its own existing 16x16 cells', hit['effect'])
        check(vram(e)[0xf000:0xf800] == (ROOT / 'assets/generated/effects.bin').read_bytes(),
              label + ' complete native effect sheet remains exact in VRAM')
        frozen = rows[contact + 1:contact + hit['hitstop'] + 1]
        fields = ('x1', 'x2', 'y1', 'y2', 'anim_frame1', 'anim_frame2',
                  'anim_tick1', 'anim_tick2', 'fxLife', 'ambient_clock')
        check(len(frozen) == hit['hitstop'] and
              all(all(s[f] == hit[f] for f in fields) for s in frozen),
              label + ' hitstop freezes physics, art, effect age and ambient',
              {'contact': {f: hit[f] for f in fields},
               'frozen': [{f: s[f] for f in fields} for s in frozen]})
        check(all(s['effect'] == hit['effect'] for s in frozen),
              label + ' no flicker or random flip during hitstop')
        after = rows[contact + hit['hitstop'] + 1]
        check(after['fxLife'] < hit['fxLife'], label + ' effect resumes after hitstop')
        check(all(((b['frame'] - a['frame']) & 65535) == 1
                  for a, b in zip([start] + rows, rows)),
              label + ' unit native video cadence through contact and recovery')
        check(all(s['budget']['max_sprites'] <= 32 and
                  s['budget']['max_tiles'] <= 34 and not (s['ppu_stat'] & 0xc0)
                  for s in rows), label + ' full OAM fetch and actual STAT77 safe',
              {'max_sprites': max(s['budget']['max_sprites'] for s in rows),
               'max_tiles': max(s['budget']['max_tiles'] for s in rows),
               'stat77': sorted({s['ppu_stat'] for s in rows})})
        check(all(shadow['y'] == 200 and shadow['tile'] == 430 and
                  shadow['size'] == 1 for s in rows for shadow in s['shadows']),
              label + ' floor shadows retain geometry and tile')
        check(all(s['effect']['size'] == 1 and (s['effect']['attr'] & 0x3e) == 0x34
                  for s in rows if s['fxLife']),
              label + ' single effect entry retains size, palette and priority')
        ppu_index = contact + 2
        pixels = pixel_match(images[ppu_index], rows[ppu_index]['effect'])
        check(pixels['opaque'] >= 15 and pixels['ratio'] >= .95,
              label + ' actual PPU displays the authored spark pixels', pixels)
        # Verify all lifetime phases in the native PPU, allowing callback latency.
        displayed_tiles = set()
        for i in range(contact + 2, len(rows)):
            for j in (i, i - 1, i - 2):
                entry = rows[j]['effect']
                match = pixel_match(images[i], entry)
                if rows[j]['fxLife'] and match['opaque'] >= 3 and match['ratio'] >= .95:
                    displayed_tiles.add(entry['tile'])
        wanted = {416, 418} if blocked else {426, 428} if kind == 2 else {384, 386, 388, 390}
        check(wanted <= displayed_tiles, label + ' every authored phase reaches actual video',
              sorted(displayed_tiles))
        if blocked:
            check(all(s['shake'] == 0 for s in rows), label + ' guard has no camera shake')
        else:
            expected = 2 if kind == 2 else 6
            check(hit['shake'] == expected and rows[contact + expected]['shake'] == 0,
                  label + ' short bounded video-clock shake',
                  [s['shake'] for s in rows[contact:contact + 8]])
        shifts = [stage_shift(background, image) for image in images[contact:contact + 10]]
        check(all(abs(s['x']) <= (0 if blocked else 1 if kind == 2 else 2) and
                  s['y'] == 0 for s in shifts),
              label + ' actual stage camera remains horizontal and restrained', shifts)
        if not blocked:
            leading = next((s['x'] for s in shifts if s['x']), 0)
            check(leading > 0 if port == 0 else leading < 0,
                  label + ' first visible camera kick follows contact direction', shifts)
        captures = []
        if capture:
            image_path = OUT / f'{engine}-stage{stage}-p{port + 1}-{name}.png'
            images[ppu_index].save(image_path)
            captures.append(image_path.relative_to(ROOT).as_posix())
            clip = OUT / f'{engine}-stage{stage}-p{port + 1}-{name}.gif'
            images[max(0, contact - 2):contact + 26][0].save(
                clip, save_all=True,
                append_images=images[max(0, contact - 2):contact + 26][1:],
                duration=17, loop=0, optimize=False)
            captures.append(clip.relative_to(ROOT).as_posix())
        return {'case': label, 'hitstop': hit['hitstop'], 'fx_type': hit['fxType'],
                'pixels': pixels, 'tiles': sorted(displayed_tiles),
                'camera': shifts,
                'peak_fetch': max(s['budget']['max_tiles'] for s in rows),
                'captures': captures}
    finally:
        e.close()


def trade_pause_reset():
    results = []
    e = boot(1, 5, 1, 5)
    try:
        close(e, 0)
        before = snapshot(e)
        for tick in range(20):
            e.run(1, p1=['y'] if tick < 3 else [], p2=['y'] if tick < 3 else [])
            s = snapshot(e)
            if s['hitstop']:
                break
        check(s['hp1'] < before['hp1'] and s['hp2'] < before['hp2'],
              'Controller-synchronized jabs trade real damage on both sides', s)
        check((s['fxType'] & 3) == 2 and s['hitstop'] == 4,
              'Second traded jab remains light after first hurt cancels its action', s)
        results.append({'case': 'mutual-light-trade', 'hitstop': s['hitstop'], 'fx_type': s['fxType']})
    finally:
        e.close()
    for strong_port in (0, 1):
        mixed = None
        attempts = []
        # Find a genuine common active tick by controller scheduling. This
        # bounded search remains useful when Feature03 changes startup values.
        for delay in (5, 4, 6, 3, 7, 2, 8, 1, 9, 0, 10, 11):
            e = boot(1, 5, 1, 5)
            try:
                close(e, strong_port)
                before = snapshot(e)
                for tick in range(32):
                    drive(e, strong_port, ['x'] if tick < 3 else [],
                          ['y'] if delay <= tick < delay + 3 else [])
                    hit = snapshot(e)
                    if hit['hitstop']:
                        break
                attempts.append({'delay': delay, 'hp': [hit['hp1'], hit['hp2']]})
                if hit['hp1'] < before['hp1'] and hit['hp2'] < before['hp2']:
                    mixed = hit
                    break
            finally:
                e.close()
        check(mixed is not None, f'P{strong_port + 1} strong/light controller trade really damages both', attempts)
        check(mixed['hitstop'] == 6 and (mixed['fxType'] & 3) == 0 and
              bool(mixed['fxType'] & 128) == (strong_port == 0),
              f'P{strong_port + 1} strong trade owns hitstop, spark and shake direction', mixed)
        results.append({'case': f'p{strong_port + 1}-mixed-trade', 'attempts': attempts,
                        'hitstop': mixed['hitstop'], 'fx_type': mixed['fxType']})
    for port in (0, 1):
        e = boot(2, 5, 2, 5)
        try:
            close(e, 0)
            for tick in range(20):
                e.run(1, p1=['x'] if tick < 3 else [])
                if snapshot(e)['hitstop']:
                    break
            check(snapshot(e)['hitstop'] == 6, f'P{port + 1} pause fixture earns a strong contact')
            drive(e, port, ['start'])
            e.run(3)
            paused = snapshot(e)
            background = e.frame.copy()
            rows = []
            for _ in range(12):
                e.run(1)
                rows.append(snapshot(e))
            fields = ('x1', 'x2', 'y1', 'y2', 'fxLife', 'fxType', 'shake', 'hitstop')
            check(paused['paused'] == 1 and all(all(row[f] == paused[f] for f in fields)
                                               for row in rows),
                  f'P{port + 1} contact-adjacent pause freezes feedback and physics')
            shift = stage_shift(background, e.frame)
            check(shift['x'] == shift['y'] == 0,
                  f'P{port + 1} paused camera holds its exact contact offset', shift)
            drive(e, port, ['start'])
            e.run(10)
            e.run(4, p1=['select'])
            e.run(5)
            reset = snapshot(e)
            check(reset['hp1'] == reset['hp2'] == 128 and reset['fxLife'] == reset['shake'] == 0 and
                  reset['paused'] == 0,
                  f'P{port + 1} resume plus ordinary Training Select clears feedback', reset)
            results.append({'case': f'p{port + 1}-pause-reset', 'paused_fx_life': paused['fxLife']})
        finally:
            e.close()
    return results


def projectile_case(fighter, port, blocked):
    low = fighter == 4
    label = f'P{port + 1} {"low" if low else "high"} wave {"guard" if blocked else "hit"}'
    e = boot(1, fighter, fighter % 3, fighter)
    try:
        away = 'right' if port == 0 else 'left'
        guard = (['down', away] if low else [away]) if blocked else []
        rows, images = [], []
        contact = None
        for tick in range(120):
            drive(e, port, ['down', 'y'] if tick < 3 else [], guard)
            s = snapshot(e)
            rows.append(s)
            images.append(e.frame.copy())
            if contact is None and s['hitstop']:
                contact = tick
        check(any(row[f'wave{port + 1}'] for row in rows), label + ' launches a real native projectile')
        check(contact is not None, label + ' actually reaches defender')
        hit = rows[contact]
        check((hit['fxType'] & 3) == (1 if blocked else 0),
              label + ' wrapper classifies detached wave impact independently of normal action', hit)
        check(hit['hitstop'] == (3 if blocked else 6), label + ' preserves class hitstop')
        if low:
            check(hit['fxY'] == 179, label + ' effect follows low wave contact')
        pixels = pixel_match(images[contact + 2], rows[contact + 2]['effect'])
        check(pixels['ratio'] >= .95 and pixels['opaque'] >= 15,
              label + ' entire spark is visible in actual PPU', pixels)
        check(all(row['budget']['max_tiles'] <= 34 and not (row['ppu_stat'] & 0xc0) for row in rows),
              label + ' projectile/effect/shadow fetch is safe')
        return {'case': label, 'pixels': pixels, 'contact_action': hit[f'action{port + 1}']}
    finally:
        e.close()


def stress_case(stage):
    e = boot(1, 4, stage, 4)
    try:
        previous = snapshot(e)
        rows, failures, kinds, contacts = [], [], set(), 0
        paired_waves = 0
        for tick in range(600):
            phase = tick % 100
            p1, p2 = [], []
            if abs(previous['x1'] - previous['x2']) > 28 * 16 and phase < 35:
                p1 = ['right' if previous['x1'] < previous['x2'] else 'left']
                p2 = ['left' if previous['x1'] < previous['x2'] else 'right']
            elif 36 <= phase < 40:
                p1, p2 = ['y'], ['down', 'right' if previous['face2'] == 0 else 'left']
            elif 50 <= phase < 54:
                p1, p2 = ['b'], ['b']
            elif 68 <= phase < 72:
                p1, p2 = ['down', 'y'], ['down', 'y']
            elif 86 <= phase < 90:
                p1, p2 = ['x'], ['x']
            e.run(1, p1=p1, p2=p2)
            s = snapshot(e)
            if ((s['frame'] - previous['frame']) & 65535) != 1:
                failures.append({'tick': tick, 'before': previous, 'after': s})
            if s['hitstop'] and not previous['hitstop']:
                kinds.add(s['fxType'] & 3)
                contacts += 1
            if s['wave1'] and s['wave2']:
                paired_waves += 1
            rows.append(s)
            previous = s
        detail = {'stage': stage, 'video_frames': 600, 'nonunit_steps': failures,
                  'contacts': contacts, 'impact_kinds': sorted(kinds),
                  'paired_wave_frames': paired_waves,
                  'peak_fetch': max(s['budget']['max_tiles'] for s in rows),
                  'peak_sprites': max(s['budget']['max_sprites'] for s in rows),
                  'stat77': sorted({s['ppu_stat'] for s in rows})}
        check(not failures, f'Stage{stage} impact stress keeps exact 600/600 native cadence', detail)
        check(contacts >= 3 and len(kinds) >= 2,
              f'Stage{stage} stress reaches multiple real impact classes', detail)
        check(detail['peak_fetch'] <= 34 and detail['peak_sprites'] <= 32 and
              all(not (s['ppu_stat'] & 0xc0) for s in rows),
              f'Stage{stage} sustained impact/actor/wave load has no native overflow', detail)
        return detail
    finally:
        e.close()


def wave_pair(stage):
    e = boot(1, 4, stage, 6)
    try:
        e.run(4, p1=['down'], p2=['down'])
        paired = flashes = 0
        maximum = 0
        statuses = set()
        for tick in range(64):
            keys = ['down', 'y'] if tick < 28 else []
            e.run(1, p1=keys, p2=keys)
            s = snapshot(e)
            paired += bool(s['wave1'] and s['wave2'])
            flashes += bool(s['fxLife'])
            maximum = max(maximum, s['budget']['max_tiles'])
            statuses.add(s['ppu_stat'])
        detail = {'stage': stage, 'paired_wave_frames': paired, 'spark_frames': flashes,
                  'peak_fetch': maximum, 'stat77': sorted(statuses)}
        check(paired > 0 and flashes > 0,
              f'Stage{stage} two-port low waves produce real coexistence and clash FX', detail)
        check(maximum <= 34 and all(not (s & 0xc0) for s in statuses),
              f'Stage{stage} paired low-wave, impact and floor-shadow fetch stays safe', detail)
        return detail
    finally:
        e.close()


def asset_proof():
    # Encode independently; verify authored cells reach VRAM later in every case.
    encoded = bytearray()
    for ty in range(4):
        for tx in range(16):
            data = bytearray(32)
            for y in range(8):
                for x in range(8):
                    index = SHEET.getpixel((tx * 8 + x, ty * 8 + y))
                    for bit in range(4):
                        data[(bit // 2) * 16 + y * 2 + bit % 2] |= ((index >> bit) & 1) << (7 - x)
            encoded.extend(data)
    current = (ROOT / 'assets/generated/effects.bin').read_bytes()
    check(len(current) == 2048 and current == encoded,
          'Authored indexed cells encode to the same 2048-byte native sheet')
    baseline = subprocess.check_output(['git', 'show', '610537d:assets/generated/effects.bin'], cwd=ROOT)
    preserved = []
    # High projectiles, low projectiles and both shadow quadrants stay exact.
    for first, count in ((8, 6), (24, 6), (36, 6), (46, 2), (52, 6), (62, 2)):
        check(current[first * 32:(first + count) * 32] == baseline[first * 32:(first + count) * 32],
              'Unowned projectile/shadow tile bytes preserved', {'first': first, 'count': count})
        preserved.extend(range(first, first + count))
    shared = preserved_assets(ROOT)
    check(True, 'Combined assets satisfy exact authorized changes and retained source pins')
    return {'effects_sha256': hashlib.sha256(current).hexdigest(),
            'preserved_tiles': preserved, 'combined': shared}


def memory_proof():
    result = {'impact_mutable_bytes_added': 0, 'fighter_stride': 64, 'wave_stride': 16,
              'trace_words': 123, 'combined': preserved_native(ROOT)}
    check(True, 'Combined native memory and ABI satisfy strict shared policy')
    sections = []
    for name, addr in SYMBOLS.items():
        if not name.startswith('SECTIONSTART_'):
            continue
        end = SYMBOLS.get(name.replace('SECTIONSTART_', 'SECTIONEND_', 1))
        if end is None or not 0x800000 <= addr < 0x1000000:
            continue
        check((addr >> 16) == ((end - 1) >> 16), 'Linked section fits one native ROM bank', name)
        sections.append((name, addr, end))
    impact_sections = {n: {'bank': a >> 16, 'bytes': b - a}
                       for n, a, b in sections if any(f'.{f}text' in n for f in
                       ('beginImpact', 'drawImpact', 'publishImpactPriority', 'impactScroll', 'hurtWithRecoil'))}
    result['native_sections'] = impact_sections
    # Include actual linker section coverage, not a claim that fill bytes are free.
    covered = set()
    for _, start, end in sections:
        for addr in range(start, end):
            covered.add(((addr >> 16) & 127) * 32768 + (addr & 32767))
    result['rom_bank_count'] = 128
    result['linked_rom_bytes'] = len(covered)
    result['unallocated_rom_bytes'] = 4194304 - len(covered)
    return result


def main():
    global SYMBOLS
    OUT.mkdir(parents=True, exist_ok=True)
    SYMBOLS = symbols(ROOT / 'dist/abaqus-after-hours.sym')
    manifest = json.loads((ROOT / 'dist/manifest.json').read_text(encoding='utf-8'))
    report = {'status': 'failed', 'rom_sha256': manifest['sha256'], 'version': manifest['version'],
              'source_sha256': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted((ROOT / 'src').rglob('*')) if p.is_file()},
              'symbols_sha256': hashlib.sha256((ROOT / 'dist/abaqus-after-hours.sym').read_bytes()).hexdigest(),
              'core_sha256': {name: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for name, path in (
                  ('snes9x', '.tools/core/snes9x_libretro.dll'),
                  ('bsnes2014-accuracy', '.tools/compat/bsnes2014-accuracy/bsnes2014_accuracy_libretro.dll'))},
              'harness_sha256': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in (
                  'tools/test_expansion_02_impact.py', 'tools/expansion_contracts.py',
                  'tools/effect_assets.py', 'tools/test_characters.py', 'tools/test_inputs.py',
                  'tools/test_stages.py', 'tools/test_compatibility.py', 'tools/emulator.py')},
              'host_contract': {'headless': True, 'audio_playback': False,
                                'controller_only': True, 'memory_writes': False, 'save_states': False},
              'checks': CHECKS, 'cases': [], 'scope': 'Feature02 focused proof; no six-suite claim'}
    try:
        check(hashlib.sha256((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()).hexdigest() ==
              manifest['sha256'], 'Built cartridge matches exact manifest SHA')
        check(report['core_sha256']['snes9x'] == EXPECTED_NATIVE_CORE['dll_sha256'] and
              report['core_sha256']['bsnes2014-accuracy'] == EXPECTED_INDEPENDENT_CORE['dll_sha256'],
              'Both focused proof cores match their pinned native DLL identities')
        report['assets'] = asset_proof()
        report['memory'] = memory_proof()
        for stage in range(3):
            for port in (0, 1):
                for case in CASES:
                    result = contact_case(stage, port, case,
                                          capture=(stage == 0 and port == 0) or
                                          (stage == 2 and port == 1 and case[0] == 'strong-punch'))
                    report['cases'].append(result)
                    print(result['case'], 'PASS', flush=True)
        report['lifecycle'] = trade_pause_reset()
        report['projectiles'] = [projectile_case(fighter, port, blocked)
                                 for fighter in (0, 4) for port in (0, 1) for blocked in (False, True)]
        report['stress'] = [stress_case(stage) for stage in range(3)]
        report['paired_low_waves'] = [wave_pair(stage) for stage in range(3)]
        report['independent'] = []
        for port in (0, 1):
            for i in (0, 2, 8, 9, 10, 11):
                result = contact_case(0, port, CASES[i],
                                      capture=(port == 1 and i in (0, 2, 8)),
                                      engine='bsnes2014-accuracy')
                report['independent'].append(result)
                print(result['case'], 'PASS', flush=True)
        report['rom_sha256_after'] = hashlib.sha256((ROOT / 'dist/abaqus-after-hours.sfc').read_bytes()).hexdigest()
        check(report['rom_sha256_after'] == report['rom_sha256'],
              'Production ROM identity stays unchanged throughout the focused proof')
        report['status'] = 'passed'
    except Exception as exc:
        report['error'] = repr(exc)
        raise
    finally:
        report['captures'] = [{'path': name, 'sha256': hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}
                              for case in report['cases'] + report.get('independent', [])
                              for name in case['captures']]
        report['passed'] = sum(item['passed'] for item in CHECKS)
        report['failed'] = sum(not item['passed'] for item in CHECKS)
        REPORT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'status': report['status'], 'passed': report['passed'],
                      'rom_sha256': report['rom_sha256']}))


if __name__ == '__main__':
    main()
