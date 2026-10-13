"""Regression tests for safe model-import source/destination boundaries."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import import_model  # noqa: E402


class ImportModelOverlapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.models = self.root / "models"
        self.models.mkdir()
        self.manifest = self.models / "manifest.json"
        self.manifest.write_text(
            json.dumps({"version": 1, "updatedAt": None, "models": []}) + "\n",
            encoding="utf-8",
        )
        self.addCleanup(patch.stopall)
        patch.object(import_model, "MODELS_DIR", self.models).start()
        patch.object(import_model, "MANIFEST_PATH", self.manifest).start()

    def run_import(self, source, *options):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return import_model.main([str(source), *options])

    def test_rejects_self_replace_without_deleting_model(self):
        destination = self.models / "demo"
        destination.mkdir()
        sentinel = destination / "model.gguf"
        sentinel.write_bytes(b"precious model bytes")
        manifest_before = self.manifest.read_bytes()

        self.assertEqual(self.run_import(destination, "--id", "demo", "--replace"), 1)
        self.assertEqual(sentinel.read_bytes(), b"precious model bytes")
        self.assertEqual(self.manifest.read_bytes(), manifest_before)

    def test_dry_run_rejects_self_replace_instead_of_false_success(self):
        destination = self.models / "demo"
        destination.mkdir()
        sentinel = destination / "model.gguf"
        sentinel.write_bytes(b"keep")
        self.assertEqual(
            self.run_import(destination, "--id", "demo", "--replace", "--dry-run"), 1
        )
        self.assertEqual(sentinel.read_bytes(), b"keep")

    def test_rejects_source_inside_destination(self):
        destination = self.models / "demo"
        source = destination / "backup"
        source.mkdir(parents=True)
        sentinel = source / "model.gguf"
        sentinel.write_bytes(b"keep nested data")

        self.assertEqual(self.run_import(source, "--id", "demo", "--replace"), 1)
        self.assertEqual(sentinel.read_bytes(), b"keep nested data")

    def test_rejects_destination_inside_source(self):
        source = self.models
        (source / "model.gguf").write_bytes(b"keep ancestor data")
        self.assertEqual(self.run_import(source, "--id", "demo"), 1)
        self.assertFalse((self.models / "demo").exists())
        self.assertEqual((source / "model.gguf").read_bytes(), b"keep ancestor data")

    def test_direct_copy_model_cannot_bypass_guard(self):
        destination = self.models / "demo"
        destination.mkdir()
        sentinel = destination / "model.gguf"
        sentinel.write_bytes(b"keep")
        with self.assertRaisesRegex(ValueError, "overlap"):
            import_model.copy_model(destination, destination, True)
        self.assertEqual(sentinel.read_bytes(), b"keep")

    def test_external_source_can_replace_existing_model(self):
        source = self.root / "incoming"
        source.mkdir()
        (source / "model.gguf").write_bytes(b"new bytes")
        destination = self.models / "demo"
        destination.mkdir()
        (destination / "model.gguf").write_bytes(b"old bytes")

        self.assertEqual(self.run_import(source, "--id", "demo", "--replace"), 0)
        self.assertEqual((destination / "model.gguf").read_bytes(), b"new bytes")
        manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(manifest["models"][0]["id"], "demo")

    def test_external_source_dry_run_preserves_existing_model(self):
        source = self.root / "incoming"
        source.mkdir()
        (source / "model.gguf").write_bytes(b"new bytes")
        destination = self.models / "demo"
        destination.mkdir()
        (destination / "model.gguf").write_bytes(b"old bytes")
        manifest_before = self.manifest.read_bytes()

        self.assertEqual(
            self.run_import(source, "--id", "demo", "--replace", "--dry-run"), 0
        )
        self.assertEqual((destination / "model.gguf").read_bytes(), b"old bytes")
        self.assertEqual(self.manifest.read_bytes(), manifest_before)


if __name__ == "__main__":
    unittest.main()
