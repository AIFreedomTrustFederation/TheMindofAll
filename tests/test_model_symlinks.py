"""Regression tests for unrecorded symbolic links in model directories."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate_manifest  # noqa: E402


class ModelSymlinkTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.model_root = self.root / "models" / "demo"
        self.model_root.mkdir(parents=True)
        data = b"valid model configuration\n"
        (self.model_root / "config.json").write_bytes(data)
        file_properties = {
            "path": {"type": "string"}, "sizeBytes": {"type": "integer"},
            "sha256": {"type": "string"}, "lfsTracked": {"type": "boolean"},
        }
        model_properties = {
            **{key: {"type": "string"} for key in
               ("id", "name", "task", "path", "format", "runtime", "license", "source", "createdAt")},
            "files": {"type": "array", "items": {
                "required": list(file_properties), "properties": file_properties,
            }},
        }
        schema = {"properties": {
            "version": {"type": "integer"},
            "models": {"type": "array", "items": {
                "required": list(model_properties), "properties": model_properties,
            }},
        }}
        manifest = {"version": 1, "models": [{
            "id": "demo", "name": "demo", "task": "embedding",
            "path": "models/demo", "format": "other", "runtime": "local",
            "license": "unknown", "source": "local",
            "createdAt": "2026-10-22T00:00:00Z",
            "files": [{
                "path": "config.json", "sizeBytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(), "lfsTracked": False,
            }],
        }]}
        manifest_path = self.root / "models" / "manifest.json"
        schema_path = self.root / "models" / "manifest.schema.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        schema_path.write_text(json.dumps(schema), encoding="utf-8")
        for key, value in (
            ("REPO_ROOT", self.root),
            ("MANIFEST_PATH", manifest_path),
            ("SCHEMA_PATH", schema_path),
        ):
            patched = patch.object(validate_manifest, key, value)
            patched.start()
            self.addCleanup(patched.stop)
        patched = patch.object(validate_manifest, "is_lfs_tracked", return_value=False)
        patched.start()
        self.addCleanup(patched.stop)

    def test_valid_model_passes(self):
        self.assertEqual(validate_manifest.validate(), [])

    def test_external_directory_symlink_rejected(self):
        external = self.root / "private"
        external.mkdir()
        (external / "secret.txt").write_text("private", encoding="utf-8")
        (self.model_root / "external").symlink_to(external, target_is_directory=True)
        self.assertIn(
            "demo/external: symbolic links are not allowed",
            validate_manifest.validate(),
        )

    def test_dangling_symlink_rejected(self):
        (self.model_root / "dangling").symlink_to(self.root / "missing")
        self.assertIn(
            "demo/dangling: symbolic links are not allowed",
            validate_manifest.validate(),
        )

    def test_internal_directory_symlink_rejected(self):
        (self.model_root / "alias").symlink_to(self.model_root, target_is_directory=True)
        self.assertIn(
            "demo/alias: symbolic links are not allowed",
            validate_manifest.validate(),
        )

    def test_unrecorded_regular_file_rejected(self):
        (self.model_root / "extra.txt").write_text("extra", encoding="utf-8")
        self.assertIn("demo: unrecorded file: extra.txt", validate_manifest.validate())


if __name__ == "__main__":
    unittest.main()
