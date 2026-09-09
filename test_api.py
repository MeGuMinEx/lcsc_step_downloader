import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jlc_downloader import download_model, ModelNotFound
from jlc_downloader.core import DownloadedModel, model_from_package
from test_downloader import package


DATA = b"ISO-10303-21;\nEND-ISO-10303-21;\n"


class ApiTests(unittest.TestCase):
    @patch("jlc_downloader.api.download_step")
    def test_public_function_saves_in_cwd_and_protects_existing_file(self, download):
        download.return_value = DownloadedModel("C2040", "model", "uuid", DATA, "legacy")
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                path = download_model("c2040")
                self.assertEqual(path, Path(directory) / "C2040.step")
                self.assertEqual(path.read_bytes(), DATA)
                self.assertEqual(download_model("C2040"), path)
                download.assert_called_once_with("C2040", timeout=30)
                path.write_bytes(b"old")
                self.assertEqual(download_model("C2040", overwrite=True), path)
                self.assertEqual(path.read_bytes(), DATA)
            finally:
                os.chdir(previous)

    @patch("jlc_downloader.api.download_step")
    def test_explicit_directory_and_failure_propagation(self, download):
        download.return_value = DownloadedModel("C2040", "model", "uuid", DATA, "legacy")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "models"
            path = download_model("C2040", output, timeout=5)
            self.assertEqual(path.read_bytes(), DATA)
            download.assert_called_once_with("C2040", timeout=5)
            download.side_effect = ModelNotFound("no model")
            with self.assertRaises(ModelNotFound):
                download_model("C41427486", output)
            self.assertFalse((output / "C41427486.step").exists())

    def test_importer_accepts_serialized_footprint_data(self):
        import json
        data = package()
        expected = model_from_package(data)
        data["dataStr"] = json.dumps(data["dataStr"])
        self.assertEqual(model_from_package(data), expected)


if __name__ == "__main__":
    unittest.main()
