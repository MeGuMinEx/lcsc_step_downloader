"""Download logic shared by the CLI and optional web interface."""

import json
import logging
import math
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import requests
from easyeda2kicad.easyeda.easyeda_importer import Easyeda3dModelImporter

from .simplified import UnsupportedOutline, build_step, preview_regions

logger = logging.getLogger(__name__)
API_ENDPOINT = "https://easyeda.com/api/products/{lcsc_id}/components"
PREVIEW_API = "https://lceda.cn/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://easyeda.com/",
}


class DownloadError(Exception):
    """An expected download failure that can be shown to the user."""


class ModelNotFound(DownloadError):
    pass


class UpstreamError(DownloadError):
    pass


class SimplifiedModelAvailable(ModelNotFound):
    """No downloadable model, but the footprint can form a basic preview."""

    def __init__(self, lcsc_id, regions):
        super().__init__(f"{lcsc_id} 没有独立 3D 模型，但可以生成网页中的简化模型。")
        self.lcsc_id = lcsc_id
        self.regions = regions

    def generate(self):
        return DownloadedModel(self.lcsc_id, self.lcsc_id + "_simplified", "",
                               build_step(self.lcsc_id, self.regions), "simplified")


@dataclass(frozen=True)
class ModelReference:
    name: str
    uuid: str


@dataclass(frozen=True)
class DownloadedModel:
    lcsc_id: str
    name: str
    uuid: str
    data: bytes
    source: str


def normalize_lcsc_id(value):
    """Accept a part number or an LCSC URL that explicitly contains one."""
    value = value.strip()
    if re.fullmatch(r"C[0-9]+", value, re.IGNORECASE):
        return value.upper()
    parsed = urlparse(value)
    candidate = ""
    if parsed.scheme in ("https", "http"):
        if parsed.hostname in ("lcsc.com", "www.lcsc.com"):
            match = re.search(r"(?:/|_)(C[0-9]+)\.html$", parsed.path, re.IGNORECASE)
            if match:
                candidate = match.group(1)
        elif parsed.hostname == "so.szlcsc.com":
            candidate = parse_qs(parsed.query).get("k", [""])[0].strip()
    if re.fullmatch(r"C[0-9]+", candidate, re.IGNORECASE):
        return candidate.upper()
    raise ValueError("请输入 C 开头的 LCSC 编号或包含该编号的商城链接，例如 C41427486。")


def request_json(session, method, url, timeout, **kwargs):
    try:
        response = session.request(method, url, timeout=timeout, **kwargs)
        if response.status_code == 404:
            raise ModelNotFound("EasyEDA 接口未找到对应数据。")
        response.raise_for_status()
        info = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise UpstreamError(f"查询 EasyEDA 失败：{exc}") from exc
    if not isinstance(info, dict):
        raise UpstreamError("EasyEDA 返回了无法识别的数据。")
    if info.get("success") is not True:
        if str(info.get("code")) == "404":
            raise ModelNotFound("EasyEDA 接口未找到对应数据。")
        raise UpstreamError(f"EasyEDA 查询失败：{info.get('message') or info.get('code')}")
    return info.get("result")


def model_from_package(package):
    if package is None:
        return None
    if not isinstance(package, dict):
        raise UpstreamError("EasyEDA 返回的封装数据格式不正确。")
    data = package.get("dataStr")
    if not data:
        return None
    try:
        if isinstance(data, str):
            data = json.loads(data)
        if not isinstance(data, dict) or not isinstance(data.get("shape"), list):
            raise ValueError("missing footprint shapes")
        model = Easyeda3dModelImporter(
            {"packageDetail": {**package, "dataStr": data}}, download_raw_3d_model=False
        ).output
        if model is None:
            return None
        if not isinstance(model.uuid, str) or not re.fullmatch(r"[0-9a-fA-F]{32}", model.uuid):
            raise ValueError("invalid model UUID")
        if not isinstance(model.name, str) or not model.name:
            raise ValueError("invalid model name")
        return ModelReference(model.name, model.uuid)
    except (ValueError, TypeError, AttributeError, KeyError, IndexError) as exc:
        raise UpstreamError("EasyEDA 返回的 3D 模型信息不完整。") from exc


def get_preview_model(session, lcsc_id, timeout):
    session.headers.update({"Referer": "https://lceda.cn/", "Origin": "https://lceda.cn"})
    mapping = request_json(session, "GET", PREVIEW_API + "/products/getPackageUuidByCodes",
                           timeout, params={"codes": lcsc_id})
    if not isinstance(mapping, dict) or not isinstance(mapping.get("data"), list):
        raise UpstreamError("EasyEDA 返回的封装索引不完整。")
    uuid = next((item.get("package_uuid") for item in mapping["data"]
                 if isinstance(item, dict) and item.get("code") == lcsc_id), None)
    if not uuid:
        raise ModelNotFound(f"EasyEDA 中未找到 {lcsc_id} 对应的封装。")
    packages = request_json(session, "POST", PREVIEW_API + "/components/searchByUuids",
                            timeout, data={"uuids": json.dumps([uuid])})
    if not isinstance(packages, list):
        raise UpstreamError("EasyEDA 返回的封装数据不完整。")
    package = next((item for item in packages
                    if isinstance(item, dict) and item.get("uuid") == uuid), None)
    model = model_from_package(package)
    if model is None:
        try:
            regions = preview_regions(package)
        except (UnsupportedOutline, ValueError, TypeError, KeyError) as exc:
            raise ModelNotFound(f"{lcsc_id} 没有关联 3D 模型，且暂不能导出此简化轮廓：{exc}") from exc
        if regions:
            raise SimplifiedModelAvailable(lcsc_id, regions)
        raise ModelNotFound(f"EasyEDA 中的 {lcsc_id} 没有关联 3D 模型。")
    return model


def download_step(value, timeout=30):
    lcsc_id = normalize_lcsc_id(value)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be a positive finite number")
    with requests.Session() as session:
        session.headers.update(HEADERS)
        try:
            cad_data = request_json(session, "GET", API_ENDPOINT.format(lcsc_id=lcsc_id), timeout)
        except ModelNotFound:
            logger.debug("%s: trying footprint lookup after legacy component miss", lcsc_id)
            cad_data = None
        if cad_data is not None and not isinstance(cad_data, dict):
            raise UpstreamError("EasyEDA 返回的元件数据不完整。")
        model = model_from_package(cad_data.get("packageDetail")) if cad_data else None
        source, host = "legacy", "modules.easyeda.com"
        if model is None:
            model = get_preview_model(session, lcsc_id, timeout)
            source, host = "preview", "modules.lceda.cn"
        url = f"https://{host}/qAxj6KHrDKw4blvCG8QJPs7Y/{model.uuid}"
        try:
            response = session.get(url, timeout=timeout)
            if response.status_code == 404:
                raise ModelNotFound(f"已找到 {lcsc_id} 的 3D 模型，但服务器未提供对应 STEP 文件。")
            response.raise_for_status()
        except requests.RequestException as exc:
            raise UpstreamError(f"STEP 文件下载失败：{exc}") from exc
        data = response.content
        if not data.lstrip().startswith(b"ISO-10303-21;") or not data.rstrip().endswith(b"END-ISO-10303-21;"):
            raise UpstreamError("服务器未返回完整的 STEP 文件，请稍后重试。")
        return DownloadedModel(lcsc_id, model.name, model.uuid, data, source)
