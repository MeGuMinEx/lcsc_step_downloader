from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from jlc_downloader import download_model
from jlc_downloader.cli import main
from jlc_downloader.core import SimplifiedModelAvailable, download_step
from jlc_downloader.simplified import UnsupportedOutline, build_step, preview_regions
from test_downloader import response


def basic_package():
    # The browser's layer-99 body and layer-100 lead outlines for C49234121.
    return {"uuid": "03c2b7b63f724ecd89424662c56b4e42", "dataStr": {
        "head": {"x": 3952.8662, "y": 2958.2676},
        "shape": [
            "SOLIDREGION~99~~M 3946.9607 2963.1888 L 3946.9607 2953.3463 L 3958.7717 2953.3463 L 3958.7717 2963.1888 Z~solid",
            "SOLIDREGION~100~~M 3958.3781 2955.5117 L 3960.7403 2955.5117 L 3960.7403 2961.0235 L 3958.3781 2961.0235 Z~solid",
            "SOLIDREGION~100~~M 3944.9921 2955.5117 L 3947.3543 2955.5117 L 3947.3543 2961.0235 L 3944.9921 2961.0235 Z~solid",
        ],
    }}


def candidate():
    return SimplifiedModelAvailable("C49234121", preview_regions(basic_package()))


class SimplifiedTests(unittest.TestCase):
    def invoke(self, arguments):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            status = main(arguments)
        return status, out.getvalue(), err.getvalue()

    def test_preview_geometry_and_step_references(self):
        regions = preview_regions(basic_package())
        self.assertEqual([r.name for r in regions], ["Body", "Lead", "Lead"])
        self.assertAlmostEqual(max(x for x, y in regions[0].points) - min(x for x, y in regions[0].points), 3, places=4)
        self.assertEqual((regions[0].bottom, regions[0].top), (0.127, 0.889))
        self.assertEqual((regions[1].bottom, regions[1].top), (0, 0.381))
        text = build_step("C49234121", regions).decode("ascii")
        definitions = re.findall(r"(?m)^(#\d+)=", text)
        self.assertEqual(len(definitions), len(set(definitions)))
        self.assertTrue(set(re.findall(r"#\d+", text)).issubset(set(definitions)))
        self.assertEqual(text.count("=FACETED_BREP("), 3)
        self.assertEqual(text.count("=COLOUR_RGB("), 3)
        self.assertIn("heights are generic", text)

    def test_unsupported_curves_are_not_silently_discarded(self):
        package = basic_package()
        package["dataStr"]["shape"][0] = "SOLIDREGION~99~~M 0 0 C 0 1 1 1 1 0 Z~solid"
        with self.assertRaises(UnsupportedOutline):
            preview_regions(package)

    @patch("jlc_downloader.core.requests.Session.request")
    def test_missing_model_exposes_candidate_without_generating_it(self, request):
        package = basic_package()
        request.side_effect = [
            response({"success": True, "result": {"packageDetail": package}}),
            response({"success": True, "result": {"data": [{"code": "C49234121", "package_uuid": package["uuid"]}]}}),
            response({"success": True, "result": [package]}),
        ]
        with self.assertRaises(SimplifiedModelAvailable) as raised:
            download_step("C49234121")
        self.assertEqual(len(raised.exception.regions), 3)
        self.assertEqual(request.call_count, 3)

    @patch("jlc_downloader.cli.download_step", side_effect=lambda *a, **k: (_ for _ in ()).throw(candidate()))
    @patch("builtins.input", side_effect=["bad", "1"])
    def test_choice_one_generates_a_labelled_model(self, input_mock, download):
        with tempfile.TemporaryDirectory() as directory:
            status, out, err = self.invoke(["--ID", "C49234121", "-o", directory])
            self.assertEqual(status, 0)
            self.assertIn("1. 下载简化模型", err)
            self.assertIn("2. 放弃下载简化模型", err)
            self.assertIn("请输入 1 或 2", err)
            self.assertIn("已生成简化模型", out)
            self.assertTrue((Path(directory) / "C49234121_simplified.step").is_file())
            self.assertFalse((Path(directory) / "C49234121.step").exists())

    @patch("jlc_downloader.cli.download_step", side_effect=lambda *a, **k: (_ for _ in ()).throw(candidate()))
    def test_choice_two_empty_input_and_eof_write_nothing(self, download):
        for choice in ("2", "", EOFError()):
            with self.subTest(choice=choice), tempfile.TemporaryDirectory() as directory:
                options = {"side_effect": choice} if isinstance(choice, Exception) else {"return_value": choice}
                with patch("builtins.input", **options):
                    status, _, _ = self.invoke(["--ID", "C49234121", "-o", directory])
                self.assertEqual(status, 1)
                self.assertEqual(list(Path(directory).iterdir()), [])

    @patch("jlc_downloader.cli.download_step", side_effect=lambda *a, **k: (_ for _ in ()).throw(candidate()))
    @patch("builtins.input")
    def test_json_requires_explicit_opt_in_and_never_prompts(self, input_mock, download):
        with tempfile.TemporaryDirectory() as directory:
            status, out, _ = self.invoke(["--ID", "C49234121", "-o", directory, "--json"])
            self.assertEqual(status, 1)
            self.assertFalse(json.loads(out)["ok"])
            status, out, _ = self.invoke(["--ID", "C49234121", "-o", directory, "--json", "--simplified"])
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(out)["results"][0]["source"], "simplified")
            input_mock.assert_not_called()

    @patch("jlc_downloader.api.download_step", side_effect=lambda *a, **k: (_ for _ in ()).throw(candidate()))
    def test_python_function_also_requires_explicit_opt_in(self, download):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SimplifiedModelAvailable):
                download_model("C49234121", directory)
            path = download_model("C49234121", directory, simplified=True)
            self.assertEqual(path.name, "C49234121_simplified.step")
            self.assertTrue(path.read_bytes().startswith(b"ISO-10303-21;"))


if __name__ == "__main__":
    unittest.main()
