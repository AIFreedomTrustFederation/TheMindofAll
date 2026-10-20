"""Regression tests for bounded-memory model integrity verification."""

import hashlib
import sys
import tempfile
import tracemalloc
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_manifest import artifact_identity  # noqa: E402


class ArtifactIdentityTests(unittest.TestCase):
    def test_git_lfs_pointer_reports_declared_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "model.onnx"
            artifact.write_bytes(
                b"version https://git-lfs.github.com/spec/v1\n"
                + b"oid sha256:"
                + b"a" * 64
                + b"\nsize 22972370\n"
            )
            self.assertEqual(artifact_identity(artifact, lfs_tracked=True), (22972370, "a" * 64))

    def test_untracked_pointer_text_is_hashed_as_actual_file(self):
        # An untracked text file must not impersonate a large model binary.
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "weights.data"
            content = (
                b"version https://git-lfs.github.com/spec/v1\n"
                + b"oid sha256:"
                + b"a" * 64
                + b"\nsize 22972370\n"
            )
            artifact.write_bytes(content)
            self.assertEqual(
                artifact_identity(artifact, lfs_tracked=False),
                (len(content), hashlib.sha256(content).hexdigest()),
            )

    def test_lfs_tracked_real_bytes_are_hashed(self):
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "weights.onnx"
            content = b"real model bytes"
            artifact.write_bytes(content)
            self.assertEqual(
                artifact_identity(artifact, lfs_tracked=True),
                (len(content), hashlib.sha256(content).hexdigest()),
            )

    def test_regular_file_reports_actual_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "config.json"
            content = b'{"model_type":"bert"}\n'
            artifact.write_bytes(content)
            self.assertEqual(
                artifact_identity(artifact),
                (len(content), hashlib.sha256(content).hexdigest()),
            )

    def test_invalid_lfs_pointer_is_not_trusted(self):
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "model.onnx"
            content = (
                b"version https://git-lfs.github.com/spec/v1\n"
                + b"oid sha256:"
                + b"a" * 64
                + b"\nsize 22972370\nextra"
            )
            artifact.write_bytes(content)
            self.assertEqual(
                artifact_identity(artifact),
                (len(content), hashlib.sha256(content).hexdigest()),
            )

    def test_large_file_does_not_load_entire_artifact_into_memory(self):
        with tempfile.TemporaryDirectory() as temp:
            artifact = Path(temp) / "model.onnx"
            block = b"0123456789ABCDEF" * 65536
            with artifact.open("wb") as handle:
                for _ in range(16):
                    handle.write(block)
            tracemalloc.start()
            try:
                size, digest = artifact_identity(artifact)
                _, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            self.assertEqual(size, 16 * 1024 * 1024)
            self.assertEqual(digest, hashlib.sha256(block * 16).hexdigest())
            self.assertLess(peak, 8 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
