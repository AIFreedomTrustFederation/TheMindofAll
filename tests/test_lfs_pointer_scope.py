"""Reject Git LFS pointer impersonation in non-LFS manifest files."""

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate_manifest  # noqa: E402
from validate_manifest import artifact_identity  # noqa: E402


class LfsPointerScopeTests(unittest.TestCase):
    def test_non_lfs_pointer_must_not_impersonate_file(self):
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "config.json"
            artifact.write_bytes(
                b"version https://git-lfs.github.com/spec/v1\n"
                + b"oid sha256:"
                + b"a" * 64
                + b"\nsize 650\n"
            )
            with self.assertRaisesRegex(ValueError, "unexpected Git LFS pointer"):
                artifact_identity(artifact, allow_lfs_pointer=False)

    def test_real_non_lfs_file_is_hashed_when_pointers_disallowed(self):
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "config.json"
            artifact.write_bytes(b"valid configuration\n")
            self.assertEqual(
                artifact_identity(artifact, allow_lfs_pointer=False),
                (artifact.stat().st_size, hashlib.sha256(artifact.read_bytes()).hexdigest()),
            )

    def test_manifest_rejects_spoofed_non_lfs_file(self):
        # Exercise the public CLI entry point with real manifest/schema parsing.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            model_dir = root / "models" / "demo"
            model_dir.mkdir(parents=True)
            artifact = model_dir / "config.json"
            artifact.write_bytes(
                b"version https://git-lfs.github.com/spec/v1\n"
                + b"oid sha256:"
                + b"a" * 64
                + b"\nsize 650\n"
            )
            schema = {
                "properties": {
                    "version": {"type": "integer"},
                    "models": {"type": "array", "items": {
                        "required": ["id", "path", "files"],
                        "properties": {
                            "id": {"type": "string"},
                            "path": {"type": "string"},
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
            manifest = {
                "version": 1,
                "models": [{
                    "id": "demo", "path": "models/demo",
                    "files": [{"path": "config.json", "sizeBytes": 650,
                               "sha256": "a" * 64, "lfsTracked": False}],
                }],
            }
            schema_path = root / "models" / "manifest.schema.json"
            manifest_path = root / "models" / "manifest.json"
            schema_path.write_text(json.dumps(schema), encoding="utf-8")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            stderr = io.StringIO()
            with (
                patch.object(validate_manifest, "REPO_ROOT", root),
                patch.object(validate_manifest, "SCHEMA_PATH", schema_path),
                patch.object(validate_manifest, "MANIFEST_PATH", manifest_path),
                patch.object(validate_manifest, "is_lfs_tracked", return_value=False),
                contextlib.redirect_stderr(stderr),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                exit_code = validate_manifest.main()
            self.assertEqual(exit_code, 1, "spoofed config must fail manifest validation")
            self.assertIn("unexpected Git LFS pointer", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
