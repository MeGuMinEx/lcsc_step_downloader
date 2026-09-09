import json
import re
from io import BytesIO

import requests
from flask import Flask, send_file, request, abort
from werkzeug.exceptions import HTTPException, NotFound
from easyeda2kicad.easyeda.easyeda_api import API_ENDPOINT, EasyedaApi
from easyeda2kicad.easyeda.easyeda_importer import Easyeda3dModelImporter


def request_json(session, method, url, **kwargs):
    """Retain upstream errors instead of treating every failure as a missing model."""
    try:
        response = session.request(method, url, timeout=30, **kwargs)
        if response.status_code == 404:
            abort(404, description="EasyEDA 接口未找到对应数据。")
        response.raise_for_status()
        info = response.json()
    except (requests.RequestException, ValueError):
        app.logger.exception("Failed to query %s", url)
        abort(502, description="查询 EasyEDA 失败，请检查网络连接或稍后重试。具体原因见终端日志。")
    if not isinstance(info, dict):
        abort(502, description="EasyEDA 返回了无法识别的数据。")
    if info.get("success") is not True:
        app.logger.warning("EasyEDA lookup failed at %s: %s", url, info)
        if str(info.get("code")) == "404":
            abort(404, description="EasyEDA 接口未找到对应数据。")
        abort(502, description="EasyEDA 查询失败，具体原因见终端日志。")
    return info.get("result")


def model_from_package(package):
    if not package or not package.get("dataStr"):
        return None
    return Easyeda3dModelImporter(
        {"packageDetail": package}, download_raw_3d_model=False
    ).output


def get_preview_model(session, lcsc_id):
    """Use the same footprint lookup as the LCSC browser's SMT 3D preview."""
    session.headers.update({"Referer": "https://lceda.cn/", "Origin": "https://lceda.cn"})
    mapping = request_json(
        session, "GET", "https://lceda.cn/api/products/getPackageUuidByCodes",
        params={"codes": lcsc_id},
    )
    if not isinstance(mapping, dict) or not isinstance(mapping.get("data"), list):
        abort(502, description="EasyEDA 返回的封装索引不完整。")
    uuid = next(
        (item.get("package_uuid") for item in mapping["data"] if item.get("code") == lcsc_id),
        None,
    )
    if not uuid:
        abort(404, description=f"EasyEDA 中未找到 {lcsc_id} 对应的封装。")
    packages = request_json(
        session, "POST", "https://lceda.cn/api/components/searchByUuids",
        data={"uuids": json.dumps([uuid])},
    )
    if not isinstance(packages, list):
        abort(502, description="EasyEDA 返回的封装数据不完整。")
    package = next((item for item in packages if item.get("uuid") == uuid), None)
    model = model_from_package(package)
    if model is None:
        abort(404, description=f"EasyEDA 中的 {lcsc_id} 没有关联 3D 模型。")
    return model


def get_lcsc_model(lcsc_id):
    with requests.Session() as session:
        session.headers.update(EasyedaApi().headers)
        try:
            cad_data = request_json(session, "GET", API_ENDPOINT.format(lcsc_id=lcsc_id))
        except NotFound:
            cad_data = None
        model = model_from_package(cad_data.get("packageDetail")) if cad_data else None
        model_host = "modules.easyeda.com"
        if model is None:
            # Some parts have a footprint and 3D model but no schematic symbol,
            # so the legacy component endpoint returns "Component not found".
            model = get_preview_model(session, lcsc_id)
            model_host = "modules.lceda.cn"

        url = f"https://{model_host}/qAxj6KHrDKw4blvCG8QJPs7Y/{model.uuid}"
        try:
            response = session.get(url, timeout=30)
            if response.status_code == 404:
                abort(404, description=f"已找到 {lcsc_id} 的 3D 模型，但服务器未提供对应 STEP 文件。")
            response.raise_for_status()
        except requests.RequestException:
            app.logger.exception("Failed to download STEP for %s from %s", lcsc_id, url)
            abort(502, description="STEP 文件下载失败，请检查网络连接或稍后重试。具体原因见终端日志。")
        data = response.content
        if not data.lstrip().startswith(b"ISO-10303-21;") or not data.rstrip().endswith(b"END-ISO-10303-21;"):
            abort(502, description="服务器未返回完整的 STEP 文件，请稍后重试。")
        return model.name, data


app = Flask(__name__)

@app.route("/get_model", methods=['GET'])
@app.route("/get_model/<lcsc_id>", methods=['GET'])
def get_model(lcsc_id=None):
    lcsc_id = (lcsc_id or request.args.get('lcsc_id', '')).strip().upper()
    if not re.fullmatch(r"C[0-9]+", lcsc_id):
        abort(400, description="请输入有效的 LCSC ID，例如 C41427486。")
    try:
        name, data = get_lcsc_model(lcsc_id)
    except HTTPException:
        raise
    except Exception:
        app.logger.exception("Failed to process model for %s", lcsc_id)
        abort(500, description="处理模型时发生错误，具体原因见终端日志。")
    return send_file(
        BytesIO(data),
        as_attachment=True,
        download_name=name + ".step",
        mimetype='application/step'
    )

@app.route("/")
def index():
    return """<title>LCSC STEP downloader</title><h2>LCSC STEP file downloader</h2><form action="/get_model" method="GET">LCSC ID: <input type="text" name="lcsc_id"> <input type="submit" value="Download"></form>"""
    
if __name__ == '__main__':
    app.run()
