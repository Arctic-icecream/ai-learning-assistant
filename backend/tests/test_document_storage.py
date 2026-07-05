from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.app.document_storage import stage_uploaded_file


class DocumentStorageTests(unittest.TestCase):
    def test_stages_and_finalizes_an_uploaded_file(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            upload_directory = Path(temporary_directory) / "uploads"
            upload_directory.mkdir()
            original_path = upload_directory / "document.pdf"
            original_path.write_bytes(b"pdf data")

            staged = stage_uploaded_file(original_path, upload_directory)

            self.assertIsNotNone(staged)
            assert staged is not None
            self.assertFalse(original_path.exists())
            self.assertTrue(staged.staged_path.exists())

            staged.finalize()
            self.assertFalse(staged.staged_path.exists())

    def test_restores_a_staged_file_after_failure(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            upload_directory = Path(temporary_directory) / "uploads"
            upload_directory.mkdir()
            original_path = upload_directory / "document.pdf"
            original_path.write_bytes(b"important data")
            staged = stage_uploaded_file(original_path, upload_directory)

            assert staged is not None
            staged.restore()

            self.assertEqual(original_path.read_bytes(), b"important data")
            self.assertFalse(staged.staged_path.exists())

    def test_missing_file_needs_no_staging(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            upload_directory = Path(temporary_directory) / "uploads"
            upload_directory.mkdir()

            staged = stage_uploaded_file(
                upload_directory / "missing.pdf", upload_directory
            )

            self.assertIsNone(staged)

    def test_rejects_paths_outside_upload_directory(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            upload_directory = root / "uploads"
            upload_directory.mkdir()
            outside_file = root / "outside.pdf"
            outside_file.write_bytes(b"do not delete")

            with self.assertRaises(ValueError):
                stage_uploaded_file(outside_file, upload_directory)

            self.assertTrue(outside_file.exists())


if __name__ == "__main__":
    unittest.main()
