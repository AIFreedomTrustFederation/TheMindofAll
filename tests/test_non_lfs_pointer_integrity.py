"""Regression tests: Git LFS pointers are trusted only for LFS-tracked paths."""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate_manifest  # noqa: E402


class LfsPointerAttributeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.model_dir = self.root / "models" / "demo"
        self.model_dir.mkdir(parents=True)
        (self.root / ".gitattributes").write_text(
            "*.onnx filter=lfs diff=lfs merge=lfs -text\n", encoding="utf-8"
        )
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        shutil.copyfile(
            validate_manifest.SCHEMA_PATH,
            self.root / "models" / "manifest.schema.json",
        )

    def check_manifest(self, record):
        manifest = {
            "version": 1,
            "updatedAt": "2026-10-23T00:00:00+00:00",
            "models": [{
                "id": "demo",
                "name": "Demo",
                "task": "embedding",
                "path": "models/demo",
                "format": "onnx",
                "runtime": "test",
                "license": "test-license",
                "source": "local",
                "createdAt": "2026-10-23T00:00:00+00:00",
                "files": [record],
            }],
        }
        manifest_path = self.root / "models" / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with (
            patch.object(validate_manifest, "REPO_ROOT", self.root),
            patch.object(validate_manifest, "MANIFEST_PATH", manifest_path),
            patch.object(
                validate_manifest,
                "SCHEMA_PATH",
                self.root / "models" / "manifest.schema.json",
            ),
        ):
            return validate_manifest.validate()

    @staticmethod
    def pointer(size, digest):
        return (
            b"version https://git-lfs.github.com/spec/v1\n"
            + b"oid sha256:" + digest.encode("ascii")
            + b"\nsize " + str(size).encode("ascii") + b"\n"
        )

    def test_non_lfs_file_replaced_with_forged_pointer_fails(self):
        original = b'{"model_type":"bert"}\n'
        digest = hashlib.sha256(original).hexdigest()
        (self.model_dir / "config.json").write_bytes(
            self.pointer(len(original), digest)
        )
        errors = self.check_manifest({
            "path": "config.json",
            "sizeBytes": len(original),
            "sha256": digest,
            "lfsTracked": False,
        })
        self.assertTrue(any("size mismatch" in error for error in errors), errors)
        self.assertTrue(any("SHA-256 mismatch" in error for error in errors), errors)

    def test_genuine_lfs_pointer_still_validates(self):
        digest = "a" * 64
        (self.model_dir / "weights.onnx").write_bytes(
            self.pointer(123456, digest)
        )
        errors = self.check_manifest({
            "path": "weights.onnx",
            "sizeBytes": 123456,
            "sha256": digest,
            "lfsTracked": True,
        })
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
