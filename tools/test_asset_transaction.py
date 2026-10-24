"""Failure injection for staged native-asset publication; no emulation."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asset_transaction as transaction

WORKSPACE = Path(__file__).resolve().parents[1]


class AssetTransactionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='asset-transaction-test-', dir=WORKSPACE / 'build')
        self.root = Path(self.temporary.name).resolve()
        if not self.root.is_relative_to((WORKSPACE / 'build').resolve()):
            raise ValueError('test cleanup must stay under the workspace build directory')
        self.addCleanup(self.temporary.cleanup)
        self.target = self.root / 'assets/generated'
        self.target.mkdir(parents=True)
        (self.target / 'old.bin').write_bytes(b'last complete assets')

    def candidate(self):
        stage = transaction.begin(self.root)
        files = {'data.asm': b'.incbin "assets/generated/gfx.bin"\n',
                 'assets.h': b'/* header */', 'soundbank.asm': b'.incbin "assets/generated/soundbank.bnk"\n',
                 'soundbank.h': b'/* sound header */', 'soundbank.bnk': b'spc',
                 'stage-depth.json': b'{}', 'gfx.bin': bytes(32)}
        for name, raw in files.items():
            (stage / name).write_bytes(raw)
        return stage, files

    def original_intact(self):
        self.assertEqual([p.name for p in self.target.iterdir()], ['old.bin'])
        self.assertEqual((self.target / 'old.bin').read_bytes(), b'last complete assets')

    def test_success_retains_prior_complete_directory(self):
        stage, files = self.candidate()
        result = transaction.publish(self.root, stage)
        self.assertEqual({p.name: p.read_bytes() for p in self.target.iterdir()}, files)
        self.assertEqual(result['files'], len(files))
        self.assertEqual((self.root / result['previous_outputs'] / 'old.bin').read_bytes(), b'last complete assets')
        self.assertFalse(stage.exists())

    def test_incomplete_outputs_never_replace_current_assets(self):
        stage, _ = self.candidate()
        (stage / 'soundbank.h').unlink()
        with self.assertRaises(ValueError):
            transaction.publish(self.root, stage)
        self.original_intact()

    def test_bad_binary_reference_is_rejected_before_publication(self):
        stage, _ = self.candidate()
        (stage / 'data.asm').write_text('.incbin "../outside.bin"\n')
        with self.assertRaises(ValueError):
            transaction.publish(self.root, stage)
        self.original_intact()

    def test_failed_second_rename_restores_the_prior_directory(self):
        stage, _ = self.candidate()
        original = os.replace

        def fail_candidate(source, destination):
            if Path(source) == stage:
                raise PermissionError('injected candidate promotion failure')
            return original(source, destination)

        with patch.object(transaction.os, 'replace', side_effect=fail_candidate):
            with self.assertRaises(PermissionError):
                transaction.publish(self.root, stage)
        self.original_intact()
        self.assertTrue(stage.is_dir())
        self.assertFalse(transaction.journal_path(self.root).exists())

    def test_next_build_recovers_an_interrupted_directory_swap(self):
        stage, _ = self.candidate()
        backup = self.root / 'build/assets-prior-interrupted'
        self.assertTrue(backup.resolve().is_relative_to(self.root))
        journal = {'stage': stage.relative_to(self.root).as_posix(), 'backup': backup.relative_to(self.root).as_posix()}
        transaction.journal_path(self.root).write_text(json.dumps(journal))
        os.replace(self.target, backup)
        transaction.begin(self.root)
        self.original_intact()
        self.assertTrue(stage.is_dir())
        self.assertFalse(transaction.journal_path(self.root).exists())

    def test_first_publication_can_recover_without_a_prior_directory(self):
        stage, files = self.candidate()
        displaced = self.root / 'build/original-fixture'
        self.assertTrue(displaced.resolve().is_relative_to(self.root))
        os.replace(self.target, displaced)
        journal = {'stage': stage.relative_to(self.root).as_posix(), 'backup': 'build/assets-prior-never-created'}
        transaction.journal_path(self.root).write_text(json.dumps(journal))
        transaction.begin(self.root)
        self.assertEqual({p.name: p.read_bytes() for p in self.target.iterdir()}, files)

    def test_publications_cannot_overlap(self):
        stage, _ = self.candidate()
        with transaction.publication_lock(self.root):
            with self.assertRaises(OSError):
                transaction.publish(self.root, stage)
        self.original_intact()

    def test_journal_paths_cannot_escape_the_reserved_workspace(self):
        self.candidate()
        journal = {'stage': '../outside', 'backup': 'build/assets-prior-other'}
        transaction.journal_path(self.root).write_text(json.dumps(journal))
        with self.assertRaises(ValueError):
            transaction.begin(self.root)
        self.original_intact()


if __name__ == '__main__':
    unittest.main(verbosity=2)
