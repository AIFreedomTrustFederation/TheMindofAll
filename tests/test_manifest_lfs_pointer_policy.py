"""Regression tests for LFS pointer substitution in ordinary model files."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate_manifest as validator  # noqa: E402


class LFSPointerPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "models" / "example").mkdir(parents=True)
        (self.root / ".gitattributes").write_text(
            "*.onnx filter=lfs diff=lfs merge=lfs -text\n"
        )
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        self.model_dir = self.root / "models" / "example"
        schema = {
            "properties": {
                "version": {"type": "integer"},
                "updatedAt": {"type": "string"},
                "models": {"type": "array", "items": {
                    "required": ["id", "name", "task", "path", "format",
                                 "runtime", "license", "source", "createdAt", "files"],
                    "properties": {
                        **{key: {"type": "string"} for key in
                           ("id", "name", "task", "path", "format",
                            "runtime", "license", "source", "createdAt")},
                        "files": {"type": "array", "items": {
                            "required": ["path", "sizeBytes", "sha256", "lfsTracked"],
                            "properties": {
                                "path": {"type": "string"},
                                "sizeBytes": {"type": "integer"},
                                "sha256": {"type": "string"},
                                "lfsTracked": {"type": "boolean"},
                            },
                        }},
                    },
                }},
            },
        }
        (self.root / "models" / "manifest.schema.json").write_text(json.dumps(schema))
        for name, value in (
            ("REPO_ROOT", self.root),
            ("MANIFEST_PATH", self.root / "models" / "manifest.json"),
            ("SCHEMA_PATH", self.root / "models" / "manifest.schema.json"),
        ):
            setting = patch.object(validator, name, value)
            setting.start()
            self.addCleanup(setting.stop)

    @staticmethod
    def original():
        return b"original model bytes that are not present in this checkout"

    def pointer(self):
        original = self.original()
        return (
            b"version https://git-lfs.github.com/spec/v1\n"
            + b"oid sha256:" + hashlib.sha256(original).hexdigest().encode()
            + b"\nsize " + str(len(original)).encode() + b"\n"
        )

    def set_manifest(self, filename, content, *, lfs):
        (self.model_dir / filename).write_bytes(content)
        original = self.original() if content.startswith(
            b"version https://git-lfs.github.com/spec/v1"
        ) else content
        model = {
            "id": "example", "name": "Example", "task": "embedding",
            "path": "models/example", "format": "onnx", "runtime": "test",
            "license": "MIT", "source": "fixture",
            "createdAt": "2026-10-13T00:00:00Z",
            "files": [{
                "path": filename, "sizeBytes": len(original),
                "sha256": hashlib.sha256(original).hexdigest(),
                "lfsTracked": lfs,
            }],
        }
        (self.root / "models" / "manifest.json").write_text(
            json.dumps({"version": 1, "updatedAt": "2026-10-13T00:00:00Z",
                        "models": [model]})
        )

    def test_untracked_pointer_cannot_claim_binary_integrity(self):
        self.set_manifest("config.json", self.pointer(), lfs=False)
        errors = validator.validate()
        self.assertTrue(any("non-LFS-tracked" in error for error in errors), errors)

    def test_tracked_pointer_remains_supported(self):
        self.set_manifest("model.onnx", self.pointer(), lfs=True)
        self.assertEqual(validator.validate(), [])

    def test_regular_file_remains_supported(self):
        self.set_manifest("config.json", b'{"model_type":"bert"}\n', lfs=False)
        self.assertEqual(validator.validate(), [])


if __name__ == "__main__":
    unittest.main()
