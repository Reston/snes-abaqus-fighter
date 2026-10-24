"""Native file-format/publication faults, including real process interruption.

Fixture ROMs test the file format only; no emulator executes these synthetic
images. Actual cartridge behavior is checked by the separate native suites.
"""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_artifacts as artifacts
from asset_transaction import publication_lock, workspace_lock

WORKSPACE = Path(__file__).resolve().parents[1]


def bundle(directory, marker):
    directory.mkdir(parents=True, exist_ok=True)
    raw = bytearray(4194304)
    raw[256] = marker
    raw[0x7fd5], raw[0x7fd7], raw[0x7fd9] = 0x30, 0x0c, 1
    raw[0x7fdc:0x7fe0] = b'\xff\xff\0\0'
    checksum = sum(raw) & 65535
    raw[0x7fdc:0x7fe0] = struct.pack('<HH', checksum ^ 65535, checksum)
    manifest = {'version': '0.26.0', 'rom': artifacts.NAMES[2], 'bytes': len(raw),
                'sha256': artifacts.sha(raw), 'checksum': f'{checksum:04X}',
                'mapping': '4 MiB FastROM LoROM', 'region': 'NTSC 60 Hz'}
    (directory / artifacts.NAMES[2]).write_bytes(raw)
    (directory / artifacts.NAMES[0]).write_text(f'; no$snes symbolic information for "fixture.sfc".\n000080{marker:02x} fixture\n')
    (directory / 'manifest.json').write_text(json.dumps(manifest))


class NativeArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='native-artifact-test-', dir=WORKSPACE / 'build')
        self.root = Path(self.temporary.name).resolve()
        if not self.root.is_relative_to((WORKSPACE / 'build').resolve()):
            raise ValueError('test cleanup must remain inside workspace build')
        self.addCleanup(self.temporary.cleanup)
        self.dist = self.root / 'dist'
        bundle(self.dist, 65)
        self.old = {n: (self.dist / n).read_bytes() for n in artifacts.NAMES}
        (self.dist / 'historical.zip').write_bytes(b'retained historical archive')
        self.stage = artifacts.begin(self.root)
        bundle(self.stage, 66)

    def original_intact(self):
        self.assertEqual({n: (self.dist / n).read_bytes() for n in artifacts.NAMES}, self.old)
        self.assertEqual((self.dist / 'historical.zip').read_bytes(), b'retained historical archive')

    def test_complete_trio_is_published_and_prior_bytes_retained(self):
        expected = artifacts.validate(self.root, self.stage)
        backup = artifacts.publish(self.root, self.stage)
        self.assertEqual({n: artifacts.sha((self.dist / n).read_bytes()) for n in artifacts.NAMES}, expected)
        self.assertEqual({n: (self.root / backup / n).read_bytes() for n in artifacts.NAMES}, self.old)
        self.assertEqual((self.dist / 'historical.zip').read_bytes(), b'retained historical archive')

    def test_identical_trio_needs_no_replacement(self):
        bundle(self.stage, 65)
        self.assertIsNone(artifacts.publish(self.root, self.stage))
        self.original_intact()

    def test_invalid_checksum_never_replaces_the_playable_file(self):
        path = self.stage / artifacts.NAMES[2]
        raw = bytearray(path.read_bytes())
        raw[256] ^= 1
        path.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, 'checksum'):
            artifacts.publish(self.root, self.stage)
        self.original_intact()

    def test_manifest_hash_must_match_the_candidate(self):
        path = self.stage / 'manifest.json'
        value = json.loads(path.read_bytes())
        value['sha256'] = '0' * 64
        path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'manifest'):
            artifacts.publish(self.root, self.stage)
        self.original_intact()

    def test_missing_symbols_cannot_publish(self):
        (self.stage / artifacts.NAMES[0]).unlink()
        with self.assertRaises(ValueError):
            artifacts.publish(self.root, self.stage)
        self.original_intact()

    def test_malformed_symbols_cannot_publish(self):
        (self.stage / artifacts.NAMES[0]).write_text('; not a linked no$snes symbol table\n')
        with self.assertRaises(ValueError):
            artifacts.publish(self.root, self.stage)
        self.original_intact()

    def test_failed_rom_replacement_rolls_back_prior_metadata(self):
        original = os.replace

        def denied(source, destination):
            if Path(source) == self.stage / artifacts.NAMES[2]:
                raise PermissionError('injected ROM replacement denial')
            return original(source, destination)

        with patch.object(artifacts.os, 'replace', side_effect=denied):
            with self.assertRaises(PermissionError):
                artifacts.publish(self.root, self.stage)
        self.original_intact()
        self.assertFalse(artifacts.journal_path(self.root).exists())

    def interrupted(self, filename):
        command = [sys.executable] + (['-O'] if not __debug__ else []) + [str(Path(__file__).resolve()),
                   '--interrupt', str(self.root), str(self.stage), filename]
        result = subprocess.run(command, capture_output=True)
        self.assertEqual(result.returncode, 55, result.stderr)
        self.assertTrue(artifacts.journal_path(self.root).is_file())

    def test_next_build_recovers_a_killed_partial_publication(self):
        self.interrupted('manifest.json')
        self.assertEqual((self.dist / artifacts.NAMES[2]).read_bytes(), self.old[artifacts.NAMES[2]])
        artifacts.recover(self.root)
        self.original_intact()
        self.assertFalse(artifacts.journal_path(self.root).exists())

    def test_recovery_recognizes_a_complete_trio_after_process_death(self):
        expected = artifacts.validate(self.root, self.stage)
        self.interrupted(artifacts.NAMES[2])
        artifacts.recover(self.root)
        self.assertEqual({n: artifacts.sha((self.dist / n).read_bytes()) for n in artifacts.NAMES}, expected)
        self.assertFalse(artifacts.journal_path(self.root).exists())

    def test_compiler_lock_is_exclusive_but_independent_of_asset_publication(self):
        with workspace_lock(self.root, 'native-build.lock'):
            with self.assertRaises(OSError):
                with workspace_lock(self.root, 'native-build.lock'):
                    pass
            with publication_lock(self.root):
                pass

    def test_candidate_path_must_be_inside_its_reserved_build_directory(self):
        with self.assertRaises(ValueError):
            artifacts.publish(self.root, self.root / 'dist')
        self.original_intact()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--interrupt':
        root, stage, filename = Path(sys.argv[2]).resolve(), Path(sys.argv[3]).resolve(), sys.argv[4]
        if not root.is_relative_to((WORKSPACE / 'build').resolve()) or filename not in artifacts.NAMES:
            raise ValueError('interruption fixture must remain inside workspace build')
        original = os.replace

        def stop_after(source, destination):
            result = original(source, destination)
            if Path(source) == stage / filename:
                os._exit(55)
            return result

        artifacts.os.replace = stop_after
        artifacts.publish(root, stage)
        raise RuntimeError('requested process interruption did not happen')
    unittest.main(verbosity=2)
