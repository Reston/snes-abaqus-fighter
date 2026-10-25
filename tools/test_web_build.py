"""Small integrity checks for the native-ROM browser deployment boundary."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_web


class WebBuildTests(unittest.TestCase):
    def test_bundle_matches_native_rom_and_pinned_runtime(self):
        with redirect_stdout(io.StringIO()):
            build_web.build()
        root = build_web.ROOT
        output = build_web.OUTPUT
        manifest = json.loads((root / "dist/manifest.json").read_text())
        release = json.loads((output / "release.json").read_text())
        self.assertEqual((output / manifest["rom"]).read_bytes(), (root / "dist" / manifest["rom"]).read_bytes())
        self.assertEqual(release["rom_sha256"], manifest["sha256"])
        for name, expected in release["vendor_sha256"].items():
            self.assertEqual(hashlib.sha256((output / release["emulator_path"] / name).read_bytes()).hexdigest(), expected, name)
        self.assertFalse(any(p.name in {".git", ".tools", "node_modules", ".env"} for p in output.rglob("*")))

    def test_corrupt_cached_dependency_is_rejected_without_network(self):
        with tempfile.TemporaryDirectory(dir=build_web.ROOT / "build") as directory:
            cache = Path(directory) / "runtime.js"
            cache.write_bytes(b"modified")
            with patch("build_web.urllib.request.urlopen") as network:
                with self.assertRaisesRegex(ValueError, "Cached dependency"):
                    build_web.pinned_download("https://example.invalid/runtime.js", cache, "0" * 64)
                network.assert_not_called()

    def test_corrupt_download_is_not_cached(self):
        with tempfile.TemporaryDirectory(dir=build_web.ROOT / "build") as directory:
            cache = Path(directory) / "runtime.js"
            with patch("build_web.urllib.request.urlopen") as network:
                network.return_value.__enter__.return_value.read.return_value = b"modified"
                with self.assertRaisesRegex(ValueError, "Downloaded dependency"):
                    build_web.pinned_download("https://example.invalid/runtime.js", cache, "0" * 64)
                self.assertFalse(cache.exists())

    def test_wrong_native_rom_hash_fails_before_output_replacement(self):
        original = build_web.json.loads

        def changed_manifest(data):
            value = original(data)
            if "rom" in value and "sha256" in value:
                value["sha256"] = "0" * 64
            return value

        before = (build_web.OUTPUT / "index.html").read_bytes()
        with patch("build_web.json.loads", side_effect=changed_manifest):
            with self.assertRaisesRegex(ValueError, "Native ROM"):
                build_web.build()
        self.assertEqual((build_web.OUTPUT / "index.html").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
