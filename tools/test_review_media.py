"""Bounded offline review mutations; no emulator execution or source edits."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from PIL import Image, ImageSequence
import review_media as review


class NativeReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT/'dist/manifest.json').read_bytes())
        v = cls.manifest['version']
        cls.proof = json.loads((ROOT/f'docs/crossup-practice-v{v}.json').read_bytes())
        cls.media = json.loads((ROOT/f'docs/crossup-practice-captures-v{v}.json').read_bytes())
        cls.cpu = json.loads((ROOT/'docs/cpu-anti-air-review.json').read_bytes())
        cls.training = (json.loads((ROOT/'docs/training-cpu-review.json').read_bytes())
                        if tuple(map(int, v.split('.'))) >= (0, 17, 0) else None)
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT/'build')
        cls.root = Path(cls.temporary.name)
        paths = set(review.PRACTICE_HELPERS | review.AI_HELPERS | {'tools/make_crossup_practice_review.py',
                    '.tools/core/snes9x_libretro.dll', 'docs/input-test-report.json'})
        if cls.training is not None:
            paths.update(review.TRAINING_HELPERS | {'docs/training-test-report.json'})
        paths.update(path.relative_to(ROOT).as_posix() for path in review.review_files(ROOT, v).values())
        for relative in paths:
            target = cls.root/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/relative, target)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def practice(self, proof=None, media=None):
        review.validate_practice(proof if proof is not None else self.proof,
                                 media if media is not None else self.media, self.root, self.manifest)

    def cpu_review(self, report=None):
        review.validate_cpu_review(report if report is not None else self.cpu, self.root, self.manifest)

    def test_current_recorded_media(self):
        self.practice()
        self.cpu_review()

    def test_practice_inventory_identity_and_landmarks(self):
        for mutation in ('stale', 'missing', 'duplicate', 'contact', 'recipe'):
            altered = copy.deepcopy(self.proof)
            if mutation == 'stale': altered['rom_sha256'] = '0'*64
            if mutation == 'missing': altered['cases'].pop()
            if mutation == 'duplicate': altered['cases'][-1] = altered['cases'][0]
            if mutation == 'contact': altered['cases'][0]['contact']['connected1'] = 0
            if mutation == 'recipe': altered['recipes']['4']['approach_gap_px'] = 24
            with self.subTest(mutation=mutation), self.assertRaises(review.ReviewError):
                self.practice(proof=altered)
        for mutation in ('path', 'landmark', 'helpers', 'core'):
            altered = copy.deepcopy(self.media)
            if mutation == 'path': altered['captures'][0]['gif'] = 'missing.gif'
            if mutation == 'landmark': altered['captures'][0]['proof']['first_contact_clip_frame'] += 1
            if mutation == 'helpers': altered['harness_sha256'].pop('tools/test_inputs.py')
            if mutation == 'core': altered['core_sha256'] = '0'*64
            with self.subTest(mutation=mutation), self.assertRaises(review.ReviewError):
                self.practice(media=altered)

    def test_cpu_contract_and_semantics(self):
        for mutation in ('checks', 'fixture', 'startup', 'contact', 'whiff', 'snapshot', 'host'):
            altered = copy.deepcopy(self.cpu)
            if mutation == 'checks': altered['checks'] = altered['checks'][:1]
            if mutation == 'fixture': altered['captures'][0]['fixture']['cpu_id'] = 5
            if mutation == 'startup':
                row = altered['captures'][0]
                row['trace'][row['proof']['first_uppercut_clip_frame']]['raw_keys2'] = 0
            if mutation == 'contact': altered['captures'][0]['proof']['first_contact_clip_frame'] += 1
            if mutation == 'whiff': altered['captures'][1]['proof']['first_contact_clip_frame'] = 15
            if mutation == 'snapshot': altered['captures'][0]['proof']['fixture_result']['first'] = {}
            if mutation == 'host': altered['host_contract']['audio_playback'] = True
            with self.subTest(mutation=mutation), self.assertRaises(review.ReviewError):
                self.cpu_review(altered)

    def test_changed_expanded_core_and_helper(self):
        for relative in ('.tools/core/snes9x_libretro.dll', 'tools/test_inputs.py'):
            path = self.root/relative
            original = path.read_bytes()
            try:
                path.write_bytes(original+b'changed')
                with self.assertRaises(review.ReviewError): self.practice()
                with self.assertRaises(review.ReviewError): self.cpu_review()
            finally:
                path.write_bytes(original)

    def test_gif_pixel_and_duration_changes_with_updated_outer_hash(self):
        row = self.cpu['captures'][0]
        path = self.root/row['gif']
        original = path.read_bytes()
        try:
            with Image.open(path) as image:
                frames = [frame.convert('RGB').copy() for frame in ImageSequence.Iterator(image)]
                durations = [frame.info['duration'] for frame in ImageSequence.Iterator(image)]
            frames[0].putpixel((0, 0), (255, 0, 255))
            frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=False)
            altered = copy.deepcopy(self.cpu)
            altered['captures'][0].update(gif_bytes=path.stat().st_size,
                                         gif_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            with self.assertRaises(review.ReviewError): self.cpu_review(altered)
            # Change only a GIF graphics-control duration and its outer hash.
            changed = bytearray(original)
            marker = changed.index(b'\x21\xf9\x04')
            changed[marker+4] += 1
            path.write_bytes(changed)
            altered['captures'][0].update(gif_bytes=len(changed), gif_sha256=hashlib.sha256(changed).hexdigest())
            with self.assertRaises(review.ReviewError): self.cpu_review(altered)
        finally:
            path.write_bytes(original)

    def test_embedded_companion_clip_must_match_fixed_native_file(self):
        path = self.root/f"docs/CROSSUP-PRACTICE-v{self.manifest['version']}.html"
        original = path.read_bytes()
        try:
            path.write_bytes(original.replace(b'data:image/gif;base64,', b'data:image/png;base64,', 1))
            with self.assertRaises(review.ReviewError): self.practice()
        finally:
            path.write_bytes(original)

    def test_package_binds_cpu_clips_to_native_input_fixtures(self):
        import package
        package.validate_cpu_review(self.cpu, self.root, self.manifest)
        path = self.root/'docs/input-test-report.json'
        original = path.read_bytes()
        try:
            altered = json.loads(original)
            altered['cpu_regressions']['anti_air']['hits'] = []
            path.write_bytes(json.dumps(altered).encode())
            with self.assertRaises(package.PackageError):
                package.validate_cpu_review(self.cpu, self.root, self.manifest)
        finally:
            path.write_bytes(original)

    def test_training_review_contract_pixels_and_native_proof(self):
        if self.training is None:
            self.skipTest('CPU Training is introduced in v0.17')
        validate = lambda report: review.validate_training_review(report, self.root, self.manifest)
        validate(self.training)
        for field, value in (('mode', 1), ('training_dummy', 3), ('seconds', 98), ('fighter_id2', 10)):
            altered = copy.deepcopy(self.training)
            altered['capture']['trace'][0][field] = value
            with self.subTest(field=field), self.assertRaises(review.ReviewError): validate(altered)
        altered = copy.deepcopy(self.training)
        altered['source_report_sha256'] = '0'*64
        with self.assertRaises(review.ReviewError): validate(altered)
        path = self.root/self.training['card']['png']
        original = path.read_bytes()
        try:
            with Image.open(path) as image: changed = image.convert('RGB')
            changed.putpixel((0, 0), (255, 0, 255))
            changed.save(path)
            altered = copy.deepcopy(self.training)
            altered['card'].update(png_bytes=path.stat().st_size,
                                   png_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            with self.assertRaises(review.ReviewError): validate(altered)
        finally:
            path.write_bytes(original)
        source = self.root/'docs/training-test-report.json'
        original = source.read_bytes()
        try:
            native = json.loads(original)
            native['cpu_training']['play'] = []
            source.write_bytes(json.dumps(native).encode())
            altered = copy.deepcopy(self.training)
            altered['source_report_sha256'] = hashlib.sha256(source.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
            with self.assertRaises(review.ReviewError): validate(altered)
        finally:
            source.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
