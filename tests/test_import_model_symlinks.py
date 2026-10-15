"""Regression tests for model source path validation."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from import_model import iter_files


class SourcePathTests(unittest.TestCase):
    def test_regular_files_are_discovered(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "model"
            root.mkdir()
            (root / "model.onnx").write_bytes(b"test")
            self.assertEqual([p.name for p in iter_files(root)], ["model.onnx"])

    def test_symbolic_link_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "model"
            root.mkdir()
            target = Path(temp) / "fixture.txt"
            target.write_text("fixture")
            (root / "config.json").symlink_to(target)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                iter_files(root)

    def test_symbolic_link_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "model"
            root.mkdir()
            target = Path(temp) / "fixture"
            target.mkdir()
            (root / "nested").symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                iter_files(root)

    def test_hidden_files_remain_ignored(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "model"
            root.mkdir()
            (root / ".hidden").write_text("ignored")
            (root / "model.onnx").write_bytes(b"test")
            self.assertEqual([p.name for p in iter_files(root)], ["model.onnx"])


if __name__ == "__main__":
    unittest.main()
