"""Regression tests for safe model-import source/destination paths."""

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import import_model  # noqa: E402


class ImportPathTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.models = self.root / "models"
        self.models.mkdir()
        models_patch = patch.object(import_model, "MODELS_DIR", self.models)
        models_patch.start()
        self.addCleanup(models_patch.stop)

    def test_replace_from_destination_preserves_existing_model(self):
        destination = self.models / "demo"
        destination.mkdir()
        (destination / "weights.bin").write_bytes(b"valuable weights")
        with self.assertRaisesRegex(ValueError, "must not overlap"):
            import_model.copy_model(destination, destination, True)
        self.assertEqual((destination / "weights.bin").read_bytes(), b"valuable weights")

    def test_source_parent_of_destination_is_rejected(self):
        destination = self.models / "demo"
        with self.assertRaisesRegex(ValueError, "must not overlap"):
            import_model.copy_model(self.root, destination, False)
        self.assertFalse(destination.exists())

    def test_source_inside_destination_is_rejected_without_deletion(self):
        destination = self.models / "demo"
        source = destination / "nested"
        source.mkdir(parents=True)
        (source / "config.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "must not overlap"):
            import_model.copy_model(source, destination, True)
        self.assertEqual((source / "config.json").read_text(encoding="utf-8"), "{}")

    def test_disjoint_source_still_imports(self):
        source = self.root / "external"
        source.mkdir()
        (source / "config.json").write_text("{}", encoding="utf-8")
        destination = self.models / "demo"
        import_model.copy_model(source, destination, False)
        self.assertEqual((destination / "config.json").read_text(encoding="utf-8"), "{}")

    def test_dry_run_rejects_self_import_before_mutation(self):
        destination = self.models / "demo"
        destination.mkdir()
        (destination / "weights.bin").write_bytes(b"valuable weights")
        output = io.StringIO()
        with contextlib.redirect_stderr(output), contextlib.redirect_stdout(io.StringIO()):
            result = import_model.main(
                [str(destination), "--id", "demo", "--replace", "--dry-run"]
            )
        self.assertEqual(result, 1)
        self.assertIn("must not overlap", output.getvalue())
        self.assertEqual((destination / "weights.bin").read_bytes(), b"valuable weights")


if __name__ == "__main__":
    unittest.main()
