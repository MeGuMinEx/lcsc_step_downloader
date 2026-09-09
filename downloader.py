"""Optional Flask interface; use jlc-downloader for direct CLI downloads."""

from io import BytesIO

from flask import Flask, abort, request, send_file

from jlc_downloader.core import ModelNotFound, UpstreamError, download_step, normalize_lcsc_id


def get_lcsc_model(lcsc_id):
    model = download_step(lcsc_id)
    return model.name, model.data


app = Flask(__name__)


@app.route("/get_model", methods=["GET"])
@app.route("/get_model/<lcsc_id>", methods=["GET"])
def get_model(lcsc_id=None):
    try:
        lcsc_id = normalize_lcsc_id(lcsc_id or request.args.get("lcsc_id", ""))
    except ValueError as exc:
        abort(400, description=str(exc))
    try:
        name, data = get_lcsc_model(lcsc_id)
    except ModelNotFound as exc:
        abort(404, description=str(exc))
    except UpstreamError as exc:
        app.logger.warning("Download failed for %s: %s", lcsc_id, exc)
        abort(502, description=str(exc))
    except Exception:
        app.logger.exception("Failed to process model for %s", lcsc_id)
        abort(500, description="处理模型时发生错误，具体原因见终端日志。")
    return send_file(BytesIO(data), as_attachment=True, download_name=name + ".step",
                     mimetype="application/step")


@app.route("/")
def index():
    return """<title>LCSC STEP downloader</title><h2>LCSC STEP file downloader</h2><form action="/get_model" method="GET">LCSC ID: <input type="text" name="lcsc_id"> <input type="submit" value="Download"></form>"""


if __name__ == "__main__":
    app.run()
