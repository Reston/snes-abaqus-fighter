"""Refresh ROM rectangles from final native pixels; never changes source art.

Run after make_assets.py, before build.py. The preview, manifest native hash,
and decoded eight SNES banks must agree. --check rejects a stale header.
--overlays writes offline diagnostics only; no debug UI enters the cartridge.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 1
ACTIVE = (5, 6, 7, 8, 13, 15, 50, 53, 1, 2, 4)
SUFFIX = ('', 'b', 'c', 'd', 'e', 'f', 'g', 'h')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def decode_pose(raw):
    require(len(raw) == 3840, 'Incomplete native pose')
    ids = bytearray(96 * 80)
    for ty in range(10):
        for tx in range(12):
            start = (ty * 12 + tx) * 32
            for y in range(8):
                planes = [raw[start + (b // 2) * 16 + y * 2 + b % 2] for b in range(4)]
                for x in range(8):
                    ids[(ty * 8 + y) * 96 + tx * 8 + x] = sum(
                        ((planes[b] >> (7 - x)) & 1) << b for b in range(4))
    return bytes(ids)


def bounds(points, pad=0):
    require(bool(points), 'Empty geometry region')
    xs, ys = zip(*points)
    return [max(1, min(xs) - pad), max(1, min(ys) - pad),
            min(95, max(xs) + 1 + pad), min(78, max(ys) + 1 + pad)]


def quantile(values, q):
    values = sorted(values)
    return values[round((len(values) - 1) * q)]


def derive(points, frame, super_family=None):
    """Two stable body bands and a distal strike; no per-pixel runtime test.

    Trim each body band's outer fifth of x mass, retaining head/torso/legs
    without making an extended glove/boot a remote hurt box. Two pixels of
    bounded forgiveness surround distal strikes. Art still requires review:
    silhouette analysis cannot infer an artist's intended anatomical joint.
    """
    box = bounds(points)
    top, bottom = box[1], box[3]
    height = bottom - top
    split = top + max(4, round(height * .60))
    body = []
    for lo, hi in ((top, split), (split, bottom)):
        xs = [x for x, y in points if lo <= y < hi]
        left, right = quantile(xs, .20), quantile(xs, .80) + 1
        # A core band may lean with its frame; do not follow a remote limb.
        center = quantile(xs, .50)
        left, right = max(left, center - 13), min(right, center + 14)
        body.append([max(1, left - 1), lo, min(95, right + 1), hi])
    kind = 'kick' if frame in (7, 8, 53) else 'punch'
    if frame == 13 or (frame == 2 and super_family == 'SUPER_RISE'):
        kind = 'rise'
    elif frame in (1, 2, 4, 15):
        kind = 'body'
    low = top + round(height * (.05 if kind == 'rise' else .16))
    high = top + round(height * (.64 if kind == 'rise' else (.98 if kind == 'kick' else .70)))
    candidates = [(x, y) for x, y in points if low <= y < high]
    tip = max(x for x, y in candidates)
    distal = [(x, y) for x, y in candidates if x >= tip - (12 if kind in ('kick', 'body') else 9)]
    strike = bounds(distal, 2)
    # Only air A can acquire the rear region, with the original 16px cap.
    rear_points = [(x, y) for x, y in points if 32 <= x < 48 and y >= top + height * .48]
    rear = bounds(rear_points, 2) if frame == 53 and rear_points else [0, 0, 0, 0]
    if rear[2]:
        rear[0], rear[2] = max(32, rear[0]), min(48, rear[2])
    return body + [strike, rear]


def generate(root=ROOT):
    manifest_path = root / 'assets/generated/character-manifest.json'
    manifest = json.loads(manifest_path.read_bytes())
    require(len(manifest) == 12, 'Expected complete roster manifest')
    dependencies = {'assets/generated/character-manifest.json': sha(manifest_path.read_bytes().replace(b'\r\n', b'\n'))}
    profiles_path=root/'src/super_moves.h'
    profiles_raw=profiles_path.read_bytes().replace(b'\r\n',b'\n')
    profile_block=re.search(r'const SuperProfile superProfiles\[12\]=\{(.*?)\n\};',profiles_raw.decode(),re.S)
    require(profile_block is not None,'Missing twelve-super profile inventory')
    super_families=re.findall(r'\{\s*(SUPER_\w+)\s*,',profile_block[1])
    require(len(super_families)==12 and set(super_families)<={'SUPER_VOLLEY','SUPER_RUSH','SUPER_RISE'},
            'Unknown super family; audit its active geometry')
    dependencies['src/super_moves.h']=sha(profiles_raw)
    roster = []
    for fighter, entry in enumerate(manifest):
        require(entry['id'] == fighter and entry['frame_count'] == 64, 'Roster order/frame count mismatch')
        path = root / f'assets/generated/fighter{fighter:02d}.png'
        image = Image.open(path).convert('RGBA')
        require(image.size == (6144, 80), 'Unexpected native preview canvas')
        dependencies[path.relative_to(root).as_posix()] = sha(path.read_bytes())
        banks = []
        for suffix in SUFFIX:
            bank = root / f'assets/generated/fighter{fighter:02d}{suffix}.bin'
            raw = bank.read_bytes()
            require(len(raw) == 30720, 'Native pose bank size mismatch')
            dependencies[bank.relative_to(root).as_posix()] = sha(raw)
            banks.append(raw)
        poses = []
        for frame in range(64):
            ids = decode_pose(banks[frame // 8][(frame % 8) * 3840:(frame % 8 + 1) * 3840])
            meta = entry['frames'][frame]
            require(sha(ids) == meta['pixels_sha256'], f'{fighter}/{frame}: native bank/manifest mismatch')
            preview = image.crop((frame * 96, 0, (frame + 1) * 96, 80))
            require(bytes(bool(a) for a in preview.getchannel('A').get_flattened_data()) == bytes(bool(i) for i in ids),
                    f'{fighter}/{frame}: preview/native silhouette mismatch')
            points = [(x, y) for y in range(80) for x in range(96) if ids[y * 96 + x]]
            require(bounds(points) == meta['native_box'], f'{fighter}/{frame}: manifest bounds mismatch')
            family=super_families[fighter] if meta.get('source_kind')=='super-v1' else None
            poses.append(derive(points, frame, family))
        roster.append(poses)
    payload = {'schema': SCHEMA, 'algorithm': 'two-body-bands-distal-strike-v1',
               'dependencies': dependencies, 'poses': roster}
    digest = sha(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode())
    lines = ['/* Generated by tools/contact_geometry.py; DO NOT hand edit. */',
             f'/* Native pixels / manifest / rectangles SHA256: {digest} */',
             'const u8 contactGeometryDigest[32]={' + ','.join(str(v) for v in bytes.fromhex(digest)) + '};',
             'const ContactPose contactPoses[768]={']
    for fighter, poses in enumerate(roster):
        lines.append('  /* fighter %02d */' % fighter)
        for frame, regions in enumerate(poses):
            lines.append('    {' + ','.join('{' + ','.join(map(str, r)) + '}' for r in regions) + '}, /* %d */' % frame)
    lines += ['};', '']
    payload['digest'] = digest
    return '\n'.join(lines).encode(), payload


def world(rect, x=0, y=0, face=1):
    l, t, r, b = rect
    return [x + (l - 48 if face else 48 - r) * 16, y + (t - 78) * 16,
            x + (r - 48 if face else 48 - l) * 16, y + (b - 78) * 16]


def overlap(a, b):
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def overlay_pair(root, data, fighter, frame, defender_frame, gap16, face=1, ay=0):
    """The runtime's actual evaluated rectangles, with fixed-point labels."""
    sheet = Image.open(root / f'assets/generated/fighter{fighter:02d}.png').convert('RGBA')
    im = Image.new('RGB', (256, 128), (25, 30, 42))
    d = ImageDraw.Draw(im)
    origin = (92, 109)
    a = data['poses'][fighter][frame]
    b = data['poses'][fighter][defender_frame]
    for pose, x, y, facing, regions in ((frame, 0, ay, face, a), (defender_frame, gap16 if face else -gap16, 0, 1-face, b)):
        raster = sheet.crop((pose*96, 0, (pose+1)*96, 80))
        if not facing:
            raster = raster.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        im.paste(raster, (origin[0]+x//16-48, origin[1]+y//16-78), raster)
        for r in regions[:2]:
            q = world(r, x, y, facing)
            d.rectangle((origin[0]+q[0]//16, origin[1]+q[1]//16,
                         origin[0]+(q[2]-1)//16, origin[1]+(q[3]-1)//16), outline='#4bdf9e')
    strike = world(a[2], 0, ay, face)
    d.rectangle((origin[0]+strike[0]//16, origin[1]+strike[1]//16,
                 origin[0]+(strike[2]-1)//16, origin[1]+(strike[3]-1)//16), outline='#ff7864')
    hit = any(overlap(strike, world(r, gap16 if face else -gap16, 0, 1-face)) for r in b[:2])
    d.text((5, 3), f'{fighter:02d} frame {frame}/{defender_frame} gap {gap16}/16', fill='white')
    d.text((5, 16), f'{"OVERLAP" if hit else "MISS"} | green hurt / red strike', fill='white')
    return im, hit


def overlays(root, data, directory):
    directory.mkdir(parents=True, exist_ok=True)
    # Preserve a review surface for EVERY final pose, including the three
    # new super slots and all jump/landing/startup/recovery hurt silhouettes.
    # Orange is stored candidate geometry, not an assertion of eligibility:
    # canHit's temporal/action gates still decide when it can be evaluated.
    for fighter in range(12):
        atlas = Image.open(root / f'assets/generated/fighter{fighter:02d}.png').convert('RGBA')
        full = Image.new('RGB', (8*192, 8*104+24), (25, 30, 42))
        draw = ImageDraw.Draw(full)
        draw.text((4, 4), 'Green: hurt. Orange: stored strike candidate; action/phase/pulse gates apply. Violet: air A rear only.', fill='white')
        for frame in range(64):
            for facing in (0, 1):
                raster = atlas.crop((frame*96, 0, (frame+1)*96, 80))
                if not facing:
                    raster = raster.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                ox, oy = (frame % 8)*192+(1-facing)*96, (frame//8)*104+44
                full.paste(raster, (ox, oy), raster)
                for i, rect in enumerate(data['poses'][fighter][frame]):
                    l, t, r, b = rect
                    if l == r:
                        continue
                    if not facing:
                        l, r = 96-r, 96-l
                    draw.rectangle((ox+l, oy+t, ox+r-1, oy+b-1), outline=('#4bdf9e', '#4bdf9e', '#e8ae65', '#a8a3ff')[i])
            draw.text(((frame % 8)*192+4, (frame//8)*104+28), f'{fighter:02d} / frame {frame}', fill='white')
        full.save(directory / f'{fighter:02d}-all64-regions.png')
    # Full roster, both facings, representative high/low/air/rise/rush poses.
    sheet = Image.new('RGB', (6*192, 12*112), (25, 30, 42))
    d = ImageDraw.Draw(sheet)
    for fighter in range(12):
        atlas = Image.open(root / f'assets/generated/fighter{fighter:02d}.png').convert('RGBA')
        for col, frame in enumerate((5, 7, 8, 13, 50, 53)):
            for facing in (0, 1):
                raster = atlas.crop((frame*96, 0, (frame+1)*96, 80))
                if not facing:
                    raster = raster.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                ox, oy = col*192+(1-facing)*96, fighter*112+24
                sheet.paste(raster, (ox, oy), raster)
                for i, rect in enumerate(data['poses'][fighter][frame]):
                    if rect[0] == rect[2]:
                        continue
                    l, t, r, b = rect
                    if not facing:
                        l, r = 96-r, 96-l
                    d.rectangle((ox+l, oy+t, ox+r-1, oy+b-1), outline=('#4bdf9e', '#4bdf9e', '#ff7864', '#a8a3ff')[i])
            d.text((col*192+4, fighter*112+4), f'{fighter:02d} / {frame}', fill='white')
    sheet.save(directory / 'roster-pose-regions.png')
    pairs = Image.new('RGB', (512, 12*128), (25, 30, 42))
    records = []
    for fighter in range(12):
        a = data['poses'][fighter][5][2]
        body = data['poses'][fighter][16][:2]
        # Last exact fixed-point boundary across either body band.
        limits = [world(a)[2] - world(b, face=0)[0] for b in body
                  if world(a)[1] < world(b)[3] and world(a)[3] > world(b)[1]]
        require(bool(limits), 'Jab has no vertically plausible standing target')
        boundary = max(limits)
        for col, gap in enumerate((boundary, boundary-16)):
            im, hit = overlay_pair(root, data, fighter, 5, 16, gap)
            require(hit == bool(col), 'Boundary overlay disagrees with strict contact')
            pairs.paste(im, (col*256, fighter*128))
        records.append({'fighter': fighter, 'attack_frame': 5, 'hurt_frame': 16,
                        'edge_touch_miss_gap_12_4': boundary, 'one_pixel_overlap_gap_12_4': boundary-16})
    pairs.save(directory / 'exact-contact-boundaries.png')
    (directory / 'boundaries.json').write_text(json.dumps(records, indent=2)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--overlays', type=Path)
    args = parser.parse_args()
    header, data = generate(args.root)
    target = args.root / 'build/contact_geometry_data.h'
    if args.check:
        require(target.is_file() and target.read_bytes() == header, 'Stale/missing contact header; regenerate after final native art')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(header)
        (target.parent / 'contact-geometry.json').write_text(json.dumps(data, indent=2)+'\n')
    if args.overlays:
        overlays(args.root, data, args.overlays)
    print(json.dumps({'status': 'passed', 'digest': data['digest'], 'rom_table_bytes': 12320,
                      'poses': 768, 'header': str(target), 'check': args.check}))


if __name__ == '__main__':
    main()
