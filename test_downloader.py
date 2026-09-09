import json
import unittest
from unittest.mock import patch

import requests

from downloader import app


MODEL_UUID = "acc874d37bd64412bddcc16d8c567e67"
PACKAGE_UUID = "79b28989ab2c4df6926e1aa590fd206f"
STEP = b"ISO-10303-21;\r\nHEADER;\r\nENDSEC;\r\nDATA;\r\nENDSEC;\r\nEND-ISO-10303-21;\r\n"


def response(body, status=200):
    result = requests.Response()
    result.status_code = status
    result._content = body if isinstance(body, bytes) else json.dumps(body).encode()
    return result


def package(with_model=True):
    return {
        "uuid": PACKAGE_UUID,
        "dataStr": {
            "head": {"x": 4005, "y": 2995.6102},
            "shape": ["SVGNODE~" + json.dumps({"attrs": {
                "title": "SW-TH_3P-L6.0-W5.0-P4.50",
                "uuid": MODEL_UUID,
                "c_origin": "4005,2995.6693",
                "c_rotation": "0,0,0",
                "z": "-16.9291",
            }})] if with_model else [],
        },
    }


def fallback_responses(with_model=True):
    return [
        response({"success": False, "code": 404, "message": "Component not found"}),
        response({"success": True, "result": {"data": [
            {"code": "C1", "package_uuid": "unrelated"},
            {"code": "C41427486", "package_uuid": PACKAGE_UUID},
        ]}}),
        response({"success": True, "result": [
            {"uuid": "unrelated"}, package(with_model),
        ]}),
    ]


class DownloaderTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.logger = patch.object(app.logger, "disabled", True)
        self.logger.start()
        self.addCleanup(self.logger.stop)

    @patch("jlc_downloader.core.requests.Session.request")
    def test_preview_download_works_without_schematic_symbol(self, request):
        request.side_effect = fallback_responses() + [response(STEP)]
        result = self.client.get("/get_model/C41427486")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data, STEP)
        self.assertEqual(result.mimetype, "application/step")
        self.assertIn("SW-TH_3P-L6.0-W5.0-P4.50.step", result.headers["Content-Disposition"])
        calls = request.call_args_list
        self.assertEqual(calls[1].kwargs["params"], {"codes": "C41427486"})
        self.assertEqual(json.loads(calls[2].kwargs["data"]["uuids"]), [PACKAGE_UUID])
        self.assertEqual(calls[3].args[1],
                         "https://modules.lceda.cn/qAxj6KHrDKw4blvCG8QJPs7Y/" + MODEL_UUID)

    @patch("jlc_downloader.core.requests.Session.request")
    def test_legacy_download_and_input_normalization(self, request):
        request.side_effect = [
            response({"success": True, "result": {"packageDetail": package()}}),
            response(STEP),
        ]
        result = self.client.get("/get_model?lcsc_id=%20c2040%20")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data, STEP)
        self.assertEqual(request.call_count, 2)
        self.assertIn("/C2040/", request.call_args_list[0].args[1])
        self.assertIn("modules.easyeda.com/", request.call_args_list[1].args[1])

    @patch("jlc_downloader.core.requests.Session.request")
    def test_invalid_id_does_not_query_upstream(self, request):
        for url in ["/get_model", "/get_model?lcsc_id=", "/get_model?lcsc_id=C12%2F34"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 400)
        request.assert_not_called()

    @patch("jlc_downloader.core.requests.Session.request")
    def test_missing_package_is_explained(self, request):
        request.side_effect = fallback_responses()[:1] + [
            response({"success": True, "result": {"data": []}}),
        ]
        result = self.client.get("/get_model/C41427486")
        self.assertEqual(result.status_code, 404)
        self.assertIn("对应的封装", result.get_data(as_text=True))

    @patch("jlc_downloader.core.requests.Session.request")
    def test_missing_3d_model_is_explained(self, request):
        request.side_effect = fallback_responses(with_model=False)
        result = self.client.get("/get_model/C41427486")
        self.assertEqual(result.status_code, 404)
        self.assertIn("没有关联 3D 模型", result.get_data(as_text=True))

    @patch("jlc_downloader.core.requests.Session.request", side_effect=requests.Timeout())
    def test_network_failure_is_not_reported_as_missing_model(self, request):
        self.assertEqual(self.client.get("/get_model/C41427486").status_code, 502)

    @patch("jlc_downloader.core.requests.Session.request")
    def test_invalid_step_is_not_sent_as_download(self, request):
        request.side_effect = fallback_responses() + [response(b"<html>Access denied</html>")]
        result = self.client.get("/get_model/C41427486")
        self.assertEqual(result.status_code, 502)
        self.assertNotIn("Content-Disposition", result.headers)

    @patch("jlc_downloader.core.requests.Session.request")
    def test_missing_step_is_distinct_from_missing_3d_model(self, request):
        request.side_effect = fallback_responses() + [response(b"Not found", 404)]
        result = self.client.get("/get_model/C41427486")
        self.assertEqual(result.status_code, 404)
        self.assertIn("服务器未提供对应 STEP 文件", result.get_data(as_text=True))

    @patch("jlc_downloader.core.requests.Session.request", return_value=response(b"not JSON"))
    def test_invalid_api_response_is_reported(self, request):
        self.assertEqual(self.client.get("/get_model/C41427486").status_code, 502)


if __name__ == "__main__":
    unittest.main()
