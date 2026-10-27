"""Focused authoring-contract mutations; run normally and with python -O.

Fixtures stay under ignored build/. No emulator, source art, generated payload,
release report or tool cache is changed. make_assets has top-level generation,
so its actual function definitions are compiled without running that entrypoint.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
from pathlib import Path
import random
import shutil
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import fighter_assets as fighters
from release_evidence import SOURCE_INPUT_EXACT
from stage_sources import load_stage_sources


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


class AuthoringGuards(unittest.TestCase):
    def setUp(self):
        container = ROOT / 'build/authoring-guards'
        container.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix='mutation-', dir=container)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def stage_fixture(self):
        directory = self.root / 'assets/art/stages'
        directory.mkdir(parents=True, exist_ok=True)
        native = Image.new('RGB', (256, 224))
        native.putdata([(x % 3 * 80, 16, 32) for y in range(224) for x in range(256)])
        native.resize((1024, 896), Image.Resampling.NEAREST).save(directory / 'master.png')
        write_json(directory / 'provenance.json', {'mode': 'built-in imagegen'})
        (directory / 'raw.png').write_bytes(b'retained original output')
        record = {'id': 0, 'name': 'fixture'}
        for role, name in (('master', 'master.png'), ('provenance', 'provenance.json'),
                           ('raw_source', 'raw.png')):
            record[role] = {'file': f'assets/art/stages/{name}',
                            'sha256': sha((directory / name).read_bytes())}
        manifest = {'schema': 2, 'style_contract': {'native_canvas': [256, 224],
                                                   'master_canvas': [1024, 896]},
                    'stages': [{**copy.deepcopy(record), 'id': i} for i in range(3)]}
        write_json(directory / 'stages.json', manifest)
        return directory, manifest

    def save_stage(self, directory, manifest, role=None):
        if role:
            for record in manifest['stages']:
                descriptor = record[role]
                descriptor['sha256'] = sha((self.root / descriptor['file']).read_bytes())
        write_json(directory / 'stages.json', manifest)

    def native_fixture(self):
        frames = [bytes([i % 16]) * (96 * 80) for i in range(64)]
        palette = [(i * 8, i * 8, i * 8) for i in range(16)]
        hashes = fighters._native_frame_hashes(frames)
        palette_bytes = fighters._palette_bytes(palette)
        block = {'frame_hashes': hashes,
                 'frame_hashes_sha256': fighters._frame_hash_summary(hashes),
                 'palette_hex': palette_bytes.hex(), 'palette_sha256': sha(palette_bytes),
                 'uniform_scale': .25, 'physical_scale': .25}
        expected = {**block, 'palette_bytes': palette_bytes}
        return frames, palette, block, expected

    def authoring_functions(self):
        path = ROOT / 'tools/make_assets.py'
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                     and node.name != 'asset']
        namespace = {'Image': Image, 'struct': struct, 'hashlib': hashlib,
                     'math': math, 'random': random.Random(7), 'OUT': self.root,
                     'asset': mock.Mock()}
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), namespace)
        return namespace

    def test_production_authoring_guards_are_not_removable(self):
        for name in sorted(SOURCE_INPUT_EXACT):
            if not name.endswith('.py'):
                continue
            with self.subTest(file=name):
                tree = ast.parse((ROOT / name).read_text(encoding='utf-8'))
                self.assertEqual([node.lineno for node in ast.walk(tree)
                                  if isinstance(node, ast.Assert)], [])

    def test_real_selected_stage_and_baseline_contracts(self):
        self.assertEqual([entry['id'] for entry in load_stage_sources(ROOT)], [0, 1, 2])
        baseline = fighters._load_native_baseline(ROOT)
        self.assertEqual([entry['slug'] for entry in baseline.values()], list(fighters.SLUGS))

    def test_stage_fixture_is_valid(self):
        self.stage_fixture()
        selected = load_stage_sources(self.root)
        self.assertEqual([entry['image'].size for entry in selected], [(256, 224)] * 3)

    def test_stage_schema_canvas_and_order_mutations(self):
        directory, original = self.stage_fixture()
        mutations = [('schema', 3), ('native_canvas', [255, 224]),
                     ('master_canvas', [1024, 895]), ('ids', [0, 2, 1])]
        for key, value in mutations:
            with self.subTest(field=key):
                manifest = copy.deepcopy(original)
                if key == 'schema':
                    manifest[key] = value
                elif key == 'ids':
                    for record, identifier in zip(manifest['stages'], value):
                        record['id'] = identifier
                else:
                    manifest['style_contract'][key] = value
                self.save_stage(directory, manifest)
                with self.assertRaises(AssertionError):
                    load_stage_sources(self.root)

    def test_stage_hashes_and_containment(self):
        directory, original = self.stage_fixture()
        for role in ('master', 'provenance', 'raw_source'):
            with self.subTest(role=role, mutation='hash'):
                manifest = copy.deepcopy(original)
                manifest['stages'][0][role]['sha256'] = '0' * 64
                self.save_stage(directory, manifest)
                with self.assertRaises(AssertionError) as error:
                    load_stage_sources(self.root)
                self.assertEqual(error.exception.args[0][0], role)
            with self.subTest(role=role, mutation='escape'):
                manifest = copy.deepcopy(original)
                source = self.root / manifest['stages'][0][role]['file']
                outside = directory.parent / source.name
                outside.write_bytes(source.read_bytes())
                manifest['stages'][0][role]['file'] = f'assets/art/stages/../{source.name}'
                self.save_stage(directory, manifest)
                with self.assertRaises(AssertionError) as error:
                    load_stage_sources(self.root)
                self.assertEqual(error.exception.args[0], (role, outside.resolve()))

    def test_stage_provenance_mode(self):
        directory, manifest = self.stage_fixture()
        write_json(directory / 'provenance.json', {'mode': 'unreviewed replacement'})
        self.save_stage(directory, manifest, 'provenance')
        with self.assertRaises(AssertionError) as error:
            load_stage_sources(self.root)
        self.assertEqual(error.exception.args, (0,))

    def test_stage_shape_grid_and_color_mutations(self):
        directory, manifest = self.stage_fixture()
        images = [('mode', Image.new('RGBA', (1024, 896))),
                  ('canvas', Image.new('RGB', (512, 448)))]
        with Image.open(directory / 'master.png') as source:
            off_grid = source.copy()
        off_grid.putpixel((1, 1), (255, 255, 255))
        images.append(('4x grid', off_grid))
        for count in (1, 2, 91, 92):
            native = Image.new('RGB', (256, 224))
            native.putdata([(i % count, 16, 32) for i in range(256 * 224)])
            images.append((f'{count} colors', native.resize((1024, 896), Image.Resampling.NEAREST)))
        for name, image in images:
            with self.subTest(mutation=name):
                image.save(directory / 'master.png')
                self.save_stage(directory, manifest, 'master')
                with self.assertRaises(AssertionError):
                    load_stage_sources(self.root)

    def test_fighter_source_descriptors(self):
        directory = self.root / 'assets/art/characters/01-ivo'
        directory.mkdir(parents=True)
        source = directory / 'atlas.png'
        source.write_bytes(b'pinned individual fighter source')
        relative = source.relative_to(self.root).as_posix()
        descriptor = {'file': relative, 'sha256': sha(source.read_bytes())}
        self.assertEqual(fighters._resolve_checked_source(self.root, directory, descriptor, 'legacy'), source)
        outside = directory.parent / 'outside.png'
        outside.write_bytes(source.read_bytes())
        invalid = [None, {**descriptor, 'file': str(source)},
                   {**descriptor, 'file': ''}, {**descriptor, 'sha256': 'short'},
                   {**descriptor, 'sha256': '0' * 64},
                   {**descriptor, 'file': relative.replace('atlas.png', 'missing.png')},
                   {**descriptor, 'file': relative.replace('atlas.png', '../outside.png')}]
        for value in invalid:
            with self.subTest(descriptor=value), self.assertRaises(AssertionError):
                fighters._resolve_checked_source(self.root, directory, value, 'legacy')

    def test_immutable_baseline_mutation(self):
        data = json.loads((ROOT / fighters.NATIVE_BASELINE_PATH).read_text())
        data['frame_count'] = 63
        path = self.root / fighters.NATIVE_BASELINE_PATH
        write_json(path, data)
        with self.assertRaisesRegex(AssertionError, 'Native roster baseline hash changed'):
            fighters._load_native_baseline(self.root)
        # Re-pin only this isolated fixture to reach the inner shape guard.
        with mock.patch.object(fighters, 'NATIVE_BASELINE_SHA256', sha(path.read_bytes())):
            with self.assertRaises(AssertionError):
                fighters._load_native_baseline(self.root)

    def test_unapproved_revision_mutations(self):
        # Ivo now has an explicitly registered likeness revision. Exercise
        # the same rejection against Cristobal's still-unregistered slot.
        fighter_id, slug = 2, 'cristobal'
        self.assertNotIn(fighter_id, fighters.NATIVE_REVISION_REGISTRY)
        directory = self.root / 'assets/art/characters/02-cristobal'
        directory.mkdir(parents=True)
        self.assertIsNone(fighters._load_revision_sources(self.root, fighter_id, slug, directory, {}))
        (directory / 'atlas-v4.png').write_bytes(b'unapproved art')
        with self.assertRaisesRegex(AssertionError, 'no approved revision slot'):
            fighters._load_revision_sources(self.root, fighter_id, slug, directory, {})
        relative = fighters.NATIVE_REVISION_REGISTRY[9]['contract_file']
        path = self.root / relative
        contract = json.loads((ROOT / relative).read_text())
        contract['schema'] = 99
        write_json(path, contract)
        with self.assertRaisesRegex(AssertionError, 'contract hash is not allowlisted'):
            fighters._load_revision_sources(self.root, 9, 'reston', path.parent, {})

    def test_airborne_provenance(self):
        path = self.root / 'airborne.json'
        for valid in ({'atlas': {'path': 'source.png'}, 'prompt': 'original prompt'},
                      {'output': {'path': 'source.png'}, 'generation': {'full_prompt': 'original prompt'}}):
            write_json(path, valid)
            self.assertEqual(fighters._load_airborne_provenance(path), valid)
        for invalid in ([], {}, {'atlas': {'path': 'source.png'}}, {'prompt': 'missing source'}):
            write_json(path, invalid)
            with self.subTest(metadata=invalid), self.assertRaises(AssertionError):
                fighters._load_airborne_provenance(path)

    def test_registered_source_version(self):
        baseline = fighters._load_native_baseline(ROOT)
        for fighter, slug, version in ((0, 'damian', 'v5'), (9, 'reston', 'v4'),
                                       (11, 'lars', 'v4'), (1, 'ivo', 'v6'),
                                       (6, 'fernando', 'v6'), (7, 'cristian', 'v6')):
            directory = ROOT / f'assets/art/characters/{fighter:02}-{slug}'
            revision = fighters._load_revision_sources(ROOT, fighter, slug, directory,
                                                       baseline[fighter])
            self.assertEqual(revision['new_sources']['legacy'].name, f'atlas-{version}.png')
        directory = self.root / 'assets/art/characters/00-damian'
        shutil.copytree(ROOT / directory.relative_to(self.root), directory)
        path = directory / 'native-revision.json'
        original = json.loads(path.read_text())
        for field in ('new_sources', 'provenance_files'):
            value = copy.deepcopy(original)
            if field == 'new_sources':
                target = directory / 'atlas-v4.png'
                value[field]['legacy'] = {'file':target.relative_to(self.root).as_posix(),
                                          'sha256':sha(target.read_bytes())}
            else:
                target = directory / 'likeness-v4.json'
                value[field][0] = {'file':target.relative_to(self.root).as_posix(),
                                   'sha256':sha(target.read_bytes())}
            write_json(path, value)
            registration = {**fighters.NATIVE_REVISION_REGISTRY[0],
                            'contract_sha256':sha(path.read_bytes())}
            with self.subTest(field=field), mock.patch.dict(fighters.NATIVE_REVISION_REGISTRY,
                                                           {0:registration}):
                with self.assertRaisesRegex(AssertionError, 'registered v5|same-folder likeness-v5'):
                    fighters._load_revision_sources(self.root, 0, 'damian', directory, baseline[0])
        registration = {**fighters.NATIVE_REVISION_REGISTRY[0], 'source_version':'v7'}
        with mock.patch.dict(fighters.NATIVE_REVISION_REGISTRY, {0:registration}):
            with self.assertRaisesRegex(AssertionError, 'unsupported registered source version'):
                fighters._load_revision_sources(self.root, 0, 'damian', directory, baseline[0])

    def test_registered_head_portrait_mutations(self):
        baseline = fighters._load_native_baseline(ROOT)[1]
        directory = self.root / 'assets/art/characters/01-ivo'
        directory.mkdir(parents=True)
        path = directory / 'native-revision.json'
        original = json.loads((ROOT / path.relative_to(self.root)).read_text())
        outside = directory.parent / 'outside-head.png'
        outside.write_bytes(b'unapproved external portrait')
        for label, value in (
            ('missing', None),
            ('hash', {**original['portrait_source'], 'sha256':'0' * 64}),
            ('escape', {'file':'assets/art/characters/outside-head.png',
                        'sha256':sha(outside.read_bytes())}),
        ):
            record = copy.deepcopy(original)
            record['portrait_source'] = value
            if label == 'hash':
                master = self.root / value['file']
                master.parent.mkdir(parents=True, exist_ok=True)
                master.write_bytes((ROOT / value['file']).read_bytes())
            write_json(path, record)
            registration = {**fighters.NATIVE_REVISION_REGISTRY[1],
                            'contract_sha256':sha(path.read_bytes())}
            with self.subTest(mutation=label), mock.patch.dict(
                    fighters.NATIVE_REVISION_REGISTRY, {1:registration}):
                with self.assertRaisesRegex(AssertionError,
                        'source descriptor|source hash changed|source escapes'):
                    fighters._load_revision_sources(self.root, 1, 'ivo', directory, baseline)

    def test_native_frame_and_palette_shapes(self):
        frames, palette, block, expected = self.native_fixture()
        self.assertEqual(fighters._palette_colors_from_bytes(expected['palette_bytes']), palette)
        for invalid in (frames[:63], frames + frames[:1], [b'\0'] + frames[1:]):
            with self.subTest(frames=len(invalid)), self.assertRaises(AssertionError):
                fighters._native_frame_hashes(invalid)
        for size in (0, 30, 31, 33, 34):
            with self.subTest(palette_bytes=size), self.assertRaises(AssertionError):
                fighters._palette_colors_from_bytes(bytes(size))
        for invalid in (block['frame_hashes'][:63], ['short'] * 64):
            with self.subTest(hashes=len(invalid)), self.assertRaises(AssertionError):
                fighters._frame_hash_summary(invalid)

    def test_revision_native_metadata_mutations(self):
        frames, palette, block, expected = self.native_fixture()
        checked = fighters._validate_revision_native_block(block, {}, 'fixture')
        self.assertEqual(checked, expected)
        mutations = [('frame_hashes', block['frame_hashes'][:63]),
                     ('frame_hashes_sha256', '0' * 64), ('palette_hex', '00' * 15),
                     ('palette_sha256', '0' * 64), ('uniform_scale', float('nan')),
                     ('physical_scale', .5)]
        for key, value in mutations:
            with self.subTest(field=key), self.assertRaises(AssertionError):
                fighters._validate_revision_native_block({**block, key: value}, {}, 'fixture')

    def test_native_baseline_and_reviewed_output_identity(self):
        frames, palette, block, expected = self.native_fixture()
        calls = [lambda f, p, s: fighters._assert_native_baseline64('fixture', 0, f, p, s, {0: expected}),
                 lambda f, p, s: fighters._assert_reviewed_revision('fixture', 0, f, p, s, {'expected_native': expected})]
        for call in calls:
            call(frames, palette, .25)
            for f, p, scale in (([bytes(96 * 80)] * 64, palette, .25),
                                (frames, [(248, 0, 0)] + palette[1:], .25),
                                (frames, palette, .5)):
                with self.subTest(scale=scale), self.assertRaises(AssertionError):
                    call(f, p, scale)

    def test_scales_and_lazy_error_messages(self):
        class QuietScale(float):
            def __repr__(self):
                raise RuntimeError('A passing validation evaluated its error message')

        fighters._assert_same_scale(QuietScale(.25), QuietScale(.25), 'fixture')
        for actual, expected in ((float('nan'), .25), (.25, float('inf')), (.5, .25), ('bad', .25)):
            with self.subTest(actual=actual, expected=expected), self.assertRaises(AssertionError):
                fighters._assert_same_scale(actual, expected, 'fixture')
        figure = Image.new('RGBA', (20, 100), (80, 16, 32, 255))
        normalized, scale = fighters._normalize_animation([figure], 50)
        self.assertEqual((normalized[0].size, scale), ((10, 50), .5))
        for figures in ([], [Image.new('RGBA', (20, 0))]):
            with self.assertRaises(AssertionError):
                fighters._normalize_animation(figures, 50)
        for scale in (0, -.25, float('nan'), float('inf')):
            with self.subTest(scale=scale), self.assertRaises(AssertionError):
                fighters._normalize_animation_locked([figure], scale, 'fixture')

    def test_atlas_shape_and_cycle_uniqueness(self):
        path = self.root / 'atlas.png'
        for count in (16, 15, 17):
            sheet = Image.new('RGBA', (160, 128))
            draw = ImageDraw.Draw(sheet)
            for i in range(count):
                x, y = i % 5 * 32, i // 5 * 32
                draw.rectangle((x, y, x + 26, y + 26), fill=(80, 16, 32, 255))
            sheet.save(path)
            if count == 16:
                figures, metadata = fighters.extract_atlas(path)
                self.assertEqual((len(figures), len(metadata)), (16, 16))
            else:
                with self.subTest(silhouettes=count), self.assertRaisesRegex(AssertionError, 'sixteen separate'):
                    fighters.extract_atlas(path)
        with self.assertRaisesRegex(AssertionError, 'sixteen pose names'):
            fighters.extract_atlas(path, pose_names=['idle'] * 15)
        figures = []
        for i in range(64):
            figure = Image.new('RGBA', (8, 8))
            figure.putpixel((i % 8, i // 8), (80, 16, 32, 255))
            figures.append(figure)
        fighters._assert_animation_cycles('fixture', figures)
        frames = self.native_fixture()[0]
        fighters._assert_native_animation_cycles('fixture', frames)
        with self.assertRaisesRegex(AssertionError, 'distinct source figures'):
            fighters._assert_animation_cycles('fixture', [figures[0]] * 64)
        with self.assertRaisesRegex(AssertionError, 'distinct indexed frames'):
            fighters._assert_native_animation_cycles('fixture', [frames[0]] * 64)

    def test_bg1_budget_before_publication(self):
        namespace = self.authoring_functions()
        image = Image.new('RGB', (256, 224), (16, 24, 32))
        namespace['background']('valid', image)
        self.assertEqual(len(namespace['asset'].call_args_list[0].args[1]), 32)
        namespace['asset'].reset_mock()
        # A malformed encoder's 33-byte tiles must never cross BG1's 0x7000
        # byte limit or publish payloads. Give every tile a distinct encoding.
        counter = iter(range(896))
        namespace['tile'] = lambda pixels: next(counter).to_bytes(33, 'little')
        with self.assertRaises(AssertionError):
            namespace['background']('overflow', image)
        namespace['asset'].assert_not_called()
        self.assertFalse((self.root / 'overflow.png').exists())

    def test_portrait_ui_and_fighter_shapes_before_publication(self):
        path = ROOT / 'tools/make_assets.py'
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        glyphs = next(node for node in tree.body if isinstance(node, ast.Assign)
                      and any(isinstance(target, ast.Name) and target.id == 'GLYPHS'
                              for target in node.targets))

        def loop_using(key):
            return next(node for node in tree.body if isinstance(node, ast.For)
                        and any(isinstance(item, ast.Constant) and item.value == key
                                for item in ast.walk(node)))

        start = next(i for i, node in enumerate(tree.body) if isinstance(node, ast.Assign)
                     and any(isinstance(target, ast.Name) and target.id == 'ui'
                             for target in node.targets))
        end = next(i for i, node in enumerate(tree.body) if isinstance(node, ast.Expr)
                   and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
                   and node.value.func.id == 'asset' and node.value.args
                   and isinstance(node.value.args[0], ast.Constant)
                   and node.value.args[0].value == 'ui_tiles')
        sections = [('portrait', [loop_using('portrait_large')], 2560),
                    ('ui', tree.body[start:end + 1], 384 * 32),
                    ('fighter', [loop_using('indices')], 30720)]
        for name, statements, expected_bytes in sections:
            with self.subTest(section=name):
                namespace = self.authoring_functions()
                portrait = Image.new('RGB', (64, 80))
                portrait.putdata([(i % 15 * 16, 16, 32) for i in range(64 * 80)])
                frames, palette, block, expected = self.native_fixture()
                namespace['roster'] = [{'portrait_large': portrait, 'indices': frames,
                                        'palette': palette}]
                code = compile(ast.Module(body=[glyphs, *statements], type_ignores=[]), str(path), 'exec')
                exec(code, namespace)
                self.assertEqual(len(namespace['asset'].call_args_list[0].args[1]), expected_bytes)
                namespace['asset'].reset_mock()
                namespace['tile'] = lambda pixels: bytes(33)
                with self.assertRaises(AssertionError):
                    exec(code, namespace)
                namespace['asset'].assert_not_called()

    def test_it_header_and_sample_shapes_before_write(self):
        namespace = self.authoring_functions()
        for function in ('make_it', 'make_effects_it'):
            output = self.root / f'{function}.it'
            args = (output, [[0, 100, -100]] * 4) if function == 'make_effects_it' else (output,)
            namespace[function](*args)
            self.assertEqual(output.read_bytes()[:4], b'IMPM')
            output.unlink()
            for malformed_format in ('<8H', '<7I'):
                def malformed_pack(fmt, *values):
                    encoded = struct.pack(fmt, *values)
                    return encoded + b'\0' if fmt == malformed_format else encoded
                with self.subTest(function=function, shape=malformed_format):
                    with mock.patch.dict(namespace, struct=SimpleNamespace(pack=malformed_pack)):
                        with self.assertRaises(AssertionError):
                            namespace[function](*args)
                    self.assertFalse(output.exists())


if __name__ == '__main__':
    print(f'Authoring guard mutations: optimize={sys.flags.optimize}', flush=True)
    unittest.main(verbosity=2)
