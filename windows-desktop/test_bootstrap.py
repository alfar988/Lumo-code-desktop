"""Portable tests for safe ZIP extraction used by the Windows bootstrap."""
import tempfile
import unittest
import zipfile
from pathlib import Path

from bootstrap import safe_extract_zip


class SafeExtractZipTests(unittest.TestCase):
    def test_extracts_archive_after_stripping_repository_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            archive = tmp / "source.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("repo-main/run.py", "print('hi')")
                zf.writestr("repo-main/lumo/cli.py", "# entry")
            target = tmp / "out"
            safe_extract_zip(archive, target, strip_first_component=True)
            self.assertEqual((target / "run.py").read_text(), "print('hi')")
            self.assertTrue((target / "lumo" / "cli.py").is_file())

    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            archive = tmp / "bad.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("../escape.txt", "bad")
            with self.assertRaises(RuntimeError):
                safe_extract_zip(archive, tmp / "out")
            self.assertFalse((tmp / "escape.txt").exists())

    def test_rejects_mixed_roots_in_source_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            archive = tmp / "bad.zip"
            with zipfile.ZipFile(archive, "w") as zf:
                zf.writestr("repo-main/run.py", "x")
                zf.writestr("another-root/evil.py", "y")
            with self.assertRaises(RuntimeError):
                safe_extract_zip(archive, tmp / "out", strip_first_component=True)


if __name__ == "__main__":
    unittest.main()
