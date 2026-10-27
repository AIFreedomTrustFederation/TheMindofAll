"""Regression tests for recoverable, atomic model-manifest publication."""

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import import_model  # noqa: E402


class ManifestAtomicWriteTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manifest_path = self.root / "manifest.json"
        manifest_patch = patch.object(import_model, "MANIFEST_PATH", self.manifest_path)
        manifest_patch.start()
        self.addCleanup(manifest_patch.stop)

    def assert_no_staging_files(self):
        self.assertEqual(
            sorted(path.name for path in self.root.iterdir()),
            ["manifest.json"],
        )

    def test_interrupted_serialization_preserves_previous_manifest(self):
        original = b'{"version": 1, "models": []}\n'
        self.manifest_path.write_bytes(original)

        def interrupted_dump(_value, handle, **_kwargs):
            handle.write('{"version":')
            raise OSError("simulated serialization interruption")

        with patch.object(import_model.json, "dump", side_effect=interrupted_dump):
            with self.assertRaisesRegex(OSError, "serialization interruption"):
                import_model.write_manifest({"version": 1, "models": []})

        self.assertEqual(self.manifest_path.read_bytes(), original)
        self.assert_no_staging_files()

    def test_failed_atomic_replace_preserves_previous_manifest(self):
        original = b'{"version": 1, "models": []}\n'
        self.manifest_path.write_bytes(original)
        with patch.object(import_model.os, "replace", side_effect=OSError("rename failed")):
            with self.assertRaisesRegex(OSError, "rename failed"):
                import_model.write_manifest({"version": 1, "models": [{"id": "new"}]})

        self.assertEqual(self.manifest_path.read_bytes(), original)
        self.assert_no_staging_files()

    def test_successful_replacement_preserves_file_mode(self):
        self.manifest_path.write_text("old", encoding="utf-8")
        os.chmod(self.manifest_path, 0o640)
        updated = {"version": 1, "models": [{"id": "new"}]}
        import_model.write_manifest(updated)

        self.assertEqual(json.loads(self.manifest_path.read_text(encoding="utf-8")), updated)
        self.assertEqual(stat.S_IMODE(self.manifest_path.stat().st_mode), 0o640)
        self.assert_no_staging_files()

    def test_new_manifest_is_complete_json(self):
        updated = {"version": 1, "models": []}
        import_model.write_manifest(updated)

        self.assertEqual(json.loads(self.manifest_path.read_text(encoding="utf-8")), updated)
        self.assert_no_staging_files()


if __name__ == "__main__":
    unittest.main()
