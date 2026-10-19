"""Regression tests for staged model imports and safe replacement."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import import_model  # noqa: E402


class ImportStagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.models = self.root / "models"
        self.models.mkdir()
        models_patch = patch.object(import_model, "MODELS_DIR", self.models)
        models_patch.start()
        self.addCleanup(models_patch.stop)

    def test_replace_copy_failure_preserves_previous_model(self):
        source = self.root / "source"
        source.mkdir()
        (source / "weights.bin").write_bytes(b"new weights")
        destination = self.models / "demo"
        destination.mkdir()
        (destination / "weights.bin").write_bytes(b"valuable weights")
        original_copytree = import_model.shutil.copytree

        def interrupted_copy(src, dst, **kwargs):
            original_copytree(src, dst, **kwargs)
            raise OSError("simulated interrupted copy")

        with patch.object(import_model.shutil, "copytree", side_effect=interrupted_copy):
            with self.assertRaisesRegex(OSError, "interrupted copy"):
                import_model.copy_model(source, destination, True)
        self.assertEqual((destination / "weights.bin").read_bytes(), b"valuable weights")
        self.assertEqual(sorted(p.name for p in self.models.iterdir()), ["demo"])

    def test_new_import_copy_failure_leaves_no_partial_destination(self):
        source = self.root / "source"
        source.mkdir()
        (source / "weights.bin").write_bytes(b"new weights")
        destination = self.models / "demo"
        original_copytree = import_model.shutil.copytree

        def interrupted_copy(src, dst, **kwargs):
            original_copytree(src, dst, **kwargs)
            raise OSError("simulated interrupted copy")

        with patch.object(import_model.shutil, "copytree", side_effect=interrupted_copy):
            with self.assertRaisesRegex(OSError, "interrupted copy"):
                import_model.copy_model(source, destination, False)
        self.assertFalse(destination.exists())
        self.assertEqual(list(self.models.iterdir()), [])

    def test_successful_replace_removes_old_files(self):
        source = self.root / "source"
        source.mkdir()
        (source / "weights.bin").write_bytes(b"new weights")
        destination = self.models / "demo"
        destination.mkdir()
        (destination / "old.txt").write_text("obsolete", encoding="utf-8")
        import_model.copy_model(source, destination, True)
        self.assertEqual((destination / "weights.bin").read_bytes(), b"new weights")
        self.assertFalse((destination / "old.txt").exists())
        self.assertEqual(sorted(p.name for p in self.models.iterdir()), ["demo"])

    def test_failed_publish_restores_previous_model(self):
        source = self.root / "source"
        source.mkdir()
        (source / "weights.bin").write_bytes(b"new weights")
        destination = self.models / "demo"
        destination.mkdir()
        (destination / "weights.bin").write_bytes(b"valuable weights")
        original_rename = Path.rename

        def interrupted_publish(path, target):
            if path.name == "model" and Path(target) == destination:
                raise OSError("simulated publish failure")
            return original_rename(path, target)

        with patch.object(Path, "rename", interrupted_publish):
            with self.assertRaisesRegex(OSError, "publish failure"):
                import_model.copy_model(source, destination, True)
        self.assertEqual((destination / "weights.bin").read_bytes(), b"valuable weights")
        self.assertEqual(sorted(p.name for p in self.models.iterdir()), ["demo"])


if __name__ == "__main__":
    unittest.main()
