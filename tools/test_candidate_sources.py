"""Regression checks for complete, portable native-evidence source binding."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from candidate_sources import snapshot

WORKSPACE = Path(__file__).resolve().parents[1]


class CandidateSourceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='candidate-source-test-', dir=WORKSPACE / 'build')
        self.root = Path(self.temporary.name).resolve()
        if not self.root.is_relative_to((WORKSPACE / 'build').resolve()):
            raise ValueError('source fixture cleanup must stay under workspace build')
        self.addCleanup(self.temporary.cleanup)
        for name in ('Build.cmd', 'Test.cmd', 'Play.cmd', 'src/game.c', 'tools/harness.py', 'tools/play.ps1'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'first\nsecond\n')

    def test_native_scripts_and_all_entry_commands_are_bound(self):
        self.assertEqual(set(snapshot(self.root)), {'Build.cmd', 'Test.cmd', 'Play.cmd',
                         'src/game.c', 'tools/harness.py', 'tools/play.ps1'})

    def test_crlf_and_lf_have_identical_canonical_hashes(self):
        before = snapshot(self.root)
        (self.root / 'tools/play.ps1').write_bytes(b'first\r\nsecond\r\n')
        self.assertEqual(snapshot(self.root), before)

    def test_powershell_and_command_changes_cannot_hide(self):
        before = snapshot(self.root)
        for name in ('tools/play.ps1', 'Test.cmd'):
            (self.root / name).write_bytes(b'changed\n')
        after = snapshot(self.root)
        self.assertEqual({n for n in after if after[n] != before[n]}, {'tools/play.ps1', 'Test.cmd'})

    def test_nested_and_new_producers_are_included(self):
        path = self.root / 'tools/nested/new_producer.py'
        path.parent.mkdir()
        path.write_bytes(b'pass\n')
        self.assertIn('tools/nested/new_producer.py', snapshot(self.root))

    def test_report_and_build_outputs_do_not_change_source_identity(self):
        before = snapshot(self.root)
        for name in ('docs/verification.json', 'build/diagnostic.py', 'assets/generated/data.asm'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'output only')
        self.assertEqual(snapshot(self.root), before)

    def test_missing_entry_command_is_rejected(self):
        (self.root / 'Test.cmd').unlink()
        with self.assertRaises(ValueError):
            snapshot(self.root)


if __name__ == '__main__':
    unittest.main(verbosity=2)
