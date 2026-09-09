from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jlc_downloader.cli import main, save_model
from jlc_downloader.core import DownloadedModel, ModelNotFound, normalize_lcsc_id


DATA = b"ISO-10303-21;\nEND-ISO-10303-21;\n"


class CliTests(unittest.TestCase):
    def invoke(self, arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = main(arguments)
        return status, stdout.getvalue(), stderr.getvalue()

    @patch("jlc_downloader.cli.download_step")
    def test_batch_continues_after_failure_and_emits_json(self, download):
        download.side_effect = [ModelNotFound("missing"),
                               DownloadedModel("C2040", "model", "uuid", DATA, "legacy")]
        with tempfile.TemporaryDirectory() as directory:
            status, stdout, stderr = self.invoke(["C41427486", "C2040", "-o", directory, "--json"])
            result = json.loads(stdout)
            self.assertEqual(status, 1)
            self.assertFalse(result["ok"])
            self.assertEqual([r["status"] for r in result["results"]], ["error", "downloaded"])
            self.assertEqual((Path(directory) / "C2040.step").read_bytes(), DATA)
            self.assertFalse((Path(directory) / "C41427486.step").exists())
            self.assertIn("missing", stderr)

    @patch("jlc_downloader.cli.download_step")
    def test_existing_file_is_preserved_without_network_call(self, download):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "C2040.step"
            target.write_bytes(b"existing")
            status, stdout, _ = self.invoke(["C2040", "-o", directory, "--json"])
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(stdout)["results"][0]["status"], "skipped")
            self.assertEqual(target.read_bytes(), b"existing")
            download.assert_not_called()

    @patch("jlc_downloader.cli.download_step")
    def test_overwrite_unicode_directory_and_deduplication(self, download):
        download.return_value = DownloadedModel("C2040", "model", "uuid", DATA, "legacy")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "模型 文件"
            output.mkdir()
            (output / "C2040.step").write_bytes(b"old")
            status, stdout, _ = self.invoke(["c2040", "C2040", "-o", str(output), "--overwrite", "--json"])
            self.assertEqual(status, 0)
            self.assertEqual(len(json.loads(stdout)["results"]), 1)
            download.assert_called_once_with("C2040", timeout=30)
            self.assertEqual((output / "C2040.step").read_bytes(), DATA)
            self.assertEqual(list(output.glob(".jlc-*.tmp")), [])

    def test_atomic_publish_refuses_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "C2040.step"
            path.write_bytes(b"existing")
            with self.assertRaises(FileExistsError):
                save_model(path, DATA)
            self.assertEqual(path.read_bytes(), b"existing")
            self.assertEqual(list(Path(directory).glob(".jlc-*.tmp")), [])

    @patch("jlc_downloader.cli.download_step")
    def test_invalid_arguments_never_download(self, download):
        for arguments in [["../../bad"], ["C2040", "--timeout", "nan"], ["C2040", "--timeout", "0"]]:
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit) as raised:
                self.invoke(arguments)
            self.assertEqual(raised.exception.code, 2)
        download.assert_not_called()

    def test_urls_select_part_number_instead_of_tracking_parameters(self):
        self.assertEqual(normalize_lcsc_id("https://so.szlcsc.com/global.html?k=C41427486&hot-key=C2040"), "C41427486")
        self.assertEqual(normalize_lcsc_id("https://www.lcsc.com/product-detail/C41427486.html?x=1"), "C41427486")
        self.assertEqual(normalize_lcsc_id("https://www.lcsc.com/product-detail/Some-Device_C2040.html"), "C2040")
        with self.assertRaises(ValueError):
            normalize_lcsc_id("https://example.com/product-detail/C2040.html")

    @patch("jlc_downloader.cli.download_step", side_effect=KeyboardInterrupt())
    def test_interrupt_has_130_exit_status_and_valid_json(self, download):
        with tempfile.TemporaryDirectory() as directory:
            status, stdout, _ = self.invoke(["C2040", "-o", directory, "--json"])
            self.assertEqual(status, 130)
            self.assertTrue(json.loads(stdout)["interrupted"])
            self.assertEqual(list(Path(directory).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
