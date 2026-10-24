"""Content-cache invalidation tests in a private project fixture."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asset_cache as cache

WORKSPACE = Path(__file__).resolve().parents[1]


class AssetCacheTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='asset-cache-test-', dir=WORKSPACE / 'build')
        self.root = Path(self.temporary.name).resolve()
        if not self.root.is_relative_to((WORKSPACE / 'build').resolve()):
            raise ValueError('test cleanup must stay under workspace build')
        self.addCleanup(self.temporary.cleanup)
        for name, raw in {'tools/make_assets.py': b'from helper import encode\n',
                          'tools/helper.py': b'import encoder_dep\ndef encode(): return 1\n',
                          'tools/encoder_dep.py': b'COLOR=1\n',
                          'src/game.c': b'void game(void){}\n',
                          'assets/art/master.png': b'authored pixels',
                          'assets/generated/gfx.bin': b'encoded pixels',
                          'assets/generated/soundbank.h': b'header',
                          cache.TOOL: b'pinned test encoder'}.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)

    def save(self):
        self.assertTrue(cache.save(self.root, cache.inputs(self.root), cache.outputs(self.root)))
        self.assertTrue(cache.status(self.root)[0])

    def test_absent_or_malformed_cache_requests_regeneration(self):
        self.assertFalse(cache.status(self.root)[0])
        path = self.root / 'build/asset-cache-v1.json'
        for raw in (b'[]', b'{', b'null', b'{"schema":99}'):
            path.write_bytes(raw)
            self.assertFalse(cache.status(self.root)[0])

    def test_unchanged_files_allow_reuse(self):
        self.save()
        self.assertTrue(cache.status(self.root)[0])

    def test_transitive_encoder_edits_invalidate(self):
        self.save()
        (self.root / 'tools/encoder_dep.py').write_text('COLOR=2\n')
        self.assertFalse(cache.status(self.root)[0])

    def test_art_and_new_source_files_invalidate(self):
        self.save()
        (self.root / 'assets/art/master.png').write_bytes(b'new authored pixels')
        self.assertFalse(cache.status(self.root)[0])
        self.save()
        (self.root / 'assets/art/new-source.json').write_text('{}')
        self.assertFalse(cache.status(self.root)[0])

    def test_c_and_unrelated_test_edits_do_not_reencode_art(self):
        self.save()
        (self.root / 'src/game.c').write_text('void game(void){return;}\n')
        (self.root / 'tools/test_unrelated.py').write_text('raise RuntimeError()\n')
        self.assertTrue(cache.status(self.root)[0])

    def test_modified_generated_bytes_invalidate(self):
        self.save()
        (self.root / 'assets/generated/gfx.bin').write_bytes(b'modified encoded pixels')
        self.assertFalse(cache.status(self.root)[0])

    def test_missing_required_output_invalidates(self):
        self.save()
        (self.root / 'assets/generated/soundbank.h').unlink()
        self.assertFalse(cache.status(self.root)[0])

    def test_missing_generated_directory_requests_regeneration(self):
        self.save()
        target = self.root / 'assets/generated'
        displaced = self.root / 'build/displaced-generated'
        self.assertTrue(displaced.resolve().is_relative_to(self.root))
        target.rename(displaced)
        self.assertFalse(cache.status(self.root)[0])

    def test_encoder_binary_change_invalidates(self):
        self.save()
        (self.root / cache.TOOL).write_bytes(b'changed encoder binary')
        self.assertFalse(cache.status(self.root)[0])

    def test_newly_imported_encoder_dependency_is_tracked(self):
        self.save()
        (self.root / 'tools/helper.py').write_text('from added import COLOR\n')
        (self.root / 'tools/added.py').write_text('COLOR=3\n')
        self.assertFalse(cache.status(self.root)[0])
        self.save()
        (self.root / 'tools/added.py').write_text('COLOR=4\n')
        self.assertFalse(cache.status(self.root)[0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
