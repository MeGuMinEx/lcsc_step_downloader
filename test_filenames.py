from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jlc_downloader import download_model
from jlc_downloader.cli import main
from jlc_downloader.core import DownloadedModel
from test_simplified import candidate

DATA = b"ISO-10303-21;\nEND-ISO-10303-21;\n"


class FilenameTests(unittest.TestCase):
    def invoke(self, arguments):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            status = main(arguments)
        return status, out.getvalue(), err.getvalue()

    @patch("jlc_downloader.cli.download_step")
    def test_custom_names_preserve_data_and_json_path(self, download):
        download.return_value = DownloadedModel("C2040", "model", "uuid", DATA, "legacy")
        cases = [("复位 按键", "复位 按键.step"), ("RP2040.STP", "RP2040.STP"),
                 ("按钮.step", "按钮.step"), ("Switch.v2", "Switch.v2.step")]
        for name, expected in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                status, stdout, _ = self.invoke(["--ID", "C2040", "--name", name, "-o", directory, "--json"])
                path = Path(directory) / expected
                self.assertEqual(status, 0)
                self.assertEqual(path.read_bytes(), DATA)
                self.assertEqual(json.loads(stdout)["results"][0]["path"], str(path))
                self.assertFalse((Path(directory) / "C2040.step").exists())

    @patch("jlc_downloader.cli.download_step")
    def test_custom_name_obeys_skip_overwrite_and_id_deduplication(self, download):
        download.return_value = DownloadedModel("C2040", "model", "uuid", DATA, "legacy")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "MCU.step"
            path.write_bytes(b"existing")
            args = ["--ID", "C2040", "C2040", "-n", "MCU", "-o", directory, "--json"]
            status, stdout, _ = self.invoke(args)
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(stdout)["results"][0]["status"], "skipped")
            self.assertEqual(path.read_bytes(), b"existing")
            download.assert_not_called()
            self.assertEqual(self.invoke(args + ["--overwrite"])[0], 0)
            self.assertEqual(path.read_bytes(), DATA)
            download.assert_called_once_with("C2040", timeout=30)

    @patch("jlc_downloader.cli.download_step")
    def test_invalid_names_and_batch_are_rejected_before_writes(self, download):
        names = ["", "..", "../outside", r"folder\file", "bad:name", "NUL.step", "a" * 256]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "should-not-exist"
            cases = [["--ID", "C2040", "--name", name] for name in names]
            cases.append(["--ID", "C2040", "C41427486", "--name", "same"])
            for args in cases:
                with self.subTest(args=args), self.assertRaises(SystemExit) as raised:
                    self.invoke(args + ["-o", str(output)])
                self.assertEqual(raised.exception.code, 2)
            self.assertFalse(output.exists())
            download.assert_not_called()

    @patch("jlc_downloader.api.download_step")
    def test_python_api_naming_and_existing_file_protection(self, download):
        download.return_value = DownloadedModel("C2040", "model", "uuid", DATA, "legacy")
        with tempfile.TemporaryDirectory() as directory:
            path = download_model("C2040", directory, filename="主控 芯片")
            self.assertEqual(path.name, "主控 芯片.step")
            self.assertEqual(path.read_bytes(), DATA)
            path.write_bytes(b"existing")
            self.assertEqual(download_model("C2040", directory, filename="主控 芯片"), path)
            self.assertEqual(path.read_bytes(), b"existing")
            download.assert_called_once()
            download_model("C2040", directory, filename="主控 芯片", overwrite=True)
            self.assertEqual(path.read_bytes(), DATA)

    @patch("jlc_downloader.api.download_step")
    def test_python_api_rejects_paths_before_creating_directory(self, download):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "not-created"
            with self.assertRaises(ValueError):
                download_model("C2040", output, filename="../outside.step")
            self.assertFalse(output.exists())
            download.assert_not_called()

    @patch("jlc_downloader.cli.download_step", side_effect=candidate())
    @patch("builtins.input", return_value="1")
    def test_simplified_interactive_name_stays_labelled_and_protected(self, input_mock, download):
        with tempfile.TemporaryDirectory() as directory:
            args = ["--ID", "C49234121", "--name", "轻触 按键.step", "-o", directory]
            self.assertEqual(self.invoke(args)[0], 0)
            path = Path(directory) / "轻触 按键_simplified.step"
            self.assertTrue(path.read_bytes().startswith(b"ISO-10303-21;"))
            self.assertFalse((Path(directory) / "轻触 按键.step").exists())
            path.write_bytes(b"existing")
            self.assertEqual(self.invoke(args)[0], 0)
            self.assertEqual(path.read_bytes(), b"existing")

    @patch("jlc_downloader.api.download_step", side_effect=candidate())
    def test_api_simplified_suffix_is_not_duplicated(self, download):
        with tempfile.TemporaryDirectory() as directory:
            path = download_model("C49234121", directory, filename="按键_simplified.stp", simplified=True)
            self.assertEqual(path.name, "按键_simplified.stp")
            self.assertTrue(path.read_bytes().startswith(b"ISO-10303-21;"))


if __name__ == "__main__":
    unittest.main()
