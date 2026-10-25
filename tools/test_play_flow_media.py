"""Capture inventory integrity and native format checks in isolated fixtures."""
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from play_flow_media import inventory, SCREENSHOTS

WORKSPACE = Path(__file__).resolve().parents[1]


class PlayFlowMediaTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='play-media-test-', dir=WORKSPACE / 'build')
        self.root = Path(self.temporary.name).resolve()
        if not self.root.is_relative_to((WORKSPACE / 'build').resolve()):
            raise ValueError('media fixture cleanup must stay inside workspace build')
        self.addCleanup(self.temporary.cleanup)
        self.folder = self.root / SCREENSHOTS
        self.folder.mkdir(parents=True)
        for name in ('result-p1-mirror.png', 'result-p2-mirror.png'):
            Image.new('RGB', (256, 224), '#112244').save(self.folder / name)

    def test_fixed_inventory_and_native_dimensions(self):
        rows = inventory(self.root, 'results')
        self.assertEqual([r['path'] for r in rows], [SCREENSHOTS + 'result-p1-mirror.png', SCREENSHOTS + 'result-p2-mirror.png'])
        self.assertTrue(all(r['width'] == 256 and r['height'] == 224 and len(r['sha256']) == 64 for r in rows))

    def test_missing_capture_is_rejected(self):
        (self.folder / 'result-p2-mirror.png').unlink()
        with self.assertRaises(ValueError):
            inventory(self.root, 'results')

    def test_changed_capture_bytes_change_its_recorded_digest(self):
        before = inventory(self.root, 'results')
        Image.new('RGB', (256, 224), '#224411').save(self.folder / 'result-p1-mirror.png')
        self.assertNotEqual(inventory(self.root, 'results')[0]['sha256'], before[0]['sha256'])

    def test_wrong_native_capture_dimensions_are_rejected(self):
        Image.new('RGB', (512, 448)).save(self.folder / 'result-p1-mirror.png')
        with self.assertRaises(ValueError):
            inventory(self.root, 'results')

    def test_unknown_producer_cannot_choose_an_arbitrary_inventory(self):
        with self.assertRaises(ValueError):
            inventory(self.root, '../another-report')

    def test_motion_reports_require_actual_animation_frames(self):
        for name in ('roster-hold-snes9x.gif', 'roster-hold-accuracy.gif'):
            Image.new('RGB', (256, 224)).save(self.folder / name)
        with self.assertRaises(ValueError):
            inventory(self.root, 'repeat')


if __name__ == '__main__':
    unittest.main(verbosity=2)
