"""Command-line interface for downloading one or more STEP models."""

import argparse
import json
import logging
import math
import os
from pathlib import Path
import sys
import tempfile

from . import __version__
from .core import DownloadError, download_step, normalize_lcsc_id


def part_argument(value):
    try:
        return normalize_lcsc_id(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def timeout_argument(value):
    try:
        seconds = float(value)
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError
        return seconds
    except ValueError as exc:
        raise argparse.ArgumentTypeError("超时必须是大于 0 的秒数。") from exc


def save_model(path, data, overwrite=False):
    """Publish only a complete file; refuse to replace files unless requested."""
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".jlc-", suffix=".tmp", delete=False) as file:
        temporary = Path(file.name)
        try:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        except BaseException:
            file.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        if overwrite:
            os.replace(temporary, path)
        elif os.name == "nt":
            os.rename(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def make_parser():
    parser = argparse.ArgumentParser(
        prog="jlc-downloader", description="按 LCSC 编号下载 STEP 模型，保留文件中的颜色定义。",
        epilog="示例：jlc-downloader --ID C41427486（下载到当前目录）",
    )
    parser.add_argument("parts", nargs="*", type=part_argument, metavar="LCSC_ID",
                        help="也可直接提供一个或多个编号，或包含编号的商城链接")
    parser.add_argument("--ID", "--id", dest="ids", nargs="+", action="extend", default=[],
                        type=part_argument, metavar="LCSC_ID",
                        help="要下载的 LCSC 编号，例如 --ID C41427486；支持多个编号")
    parser.add_argument("-o", "--output-dir", type=Path, default=Path.cwd(), metavar="DIR",
                        help="输出目录（默认：当前目录，文件名为 C编号.step）")
    parser.add_argument("--overwrite", action="store_true", help="覆盖已存在的模型文件")
    parser.add_argument("--timeout", type=timeout_argument, default=30, metavar="SECONDS",
                        help="每个网络请求的超时秒数（默认：30）")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果，便于脚本调用")
    parser.add_argument("--verbose", action="store_true", help="输出详细诊断日志")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = make_parser()
    args = parser.parse_args(argv)
    parts = args.parts + args.ids
    if not parts:
        parser.error("请提供 LCSC 编号，例如 --ID C41427486。")
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.ERROR,
                        format="%(levelname)s: %(message)s")
    output_dir = args.output_dir.expanduser().absolute()
    results = []
    failed = False
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"无法创建输出目录：{exc}", file=sys.stderr)
        if args.json:
            print(json.dumps({"ok": False, "error": str(exc), "results": []}, ensure_ascii=False))
        return 1
    try:
        for lcsc_id in dict.fromkeys(parts):
            path = output_dir / f"{lcsc_id}.step"
            if path.exists() and not args.overwrite:
                if not path.is_file():
                    failed = True
                    result = {"lcsc_id": lcsc_id, "status": "error", "error": f"输出路径不是文件：{path}"}
                    print(f"{lcsc_id}: {result['error']}", file=sys.stderr)
                else:
                    result = {"lcsc_id": lcsc_id, "status": "skipped", "path": str(path)}
                    if not args.json:
                        print(f"已存在，跳过：{path}")
                results.append(result)
                continue
            try:
                model = download_step(lcsc_id, timeout=args.timeout)
                save_model(path, model.data, args.overwrite)
                result = {"lcsc_id": lcsc_id, "status": "downloaded", "path": str(path),
                          "name": model.name, "uuid": model.uuid, "bytes": len(model.data),
                          "source": model.source}
                if not args.json:
                    print(f"已下载：{path} ({len(model.data):,} bytes)")
            except (DownloadError, OSError) as exc:
                failed = True
                result = {"lcsc_id": lcsc_id, "status": "error", "error": str(exc)}
                print(f"{lcsc_id}: {exc}", file=sys.stderr)
            results.append(result)
    except KeyboardInterrupt:
        print("下载已中断。", file=sys.stderr)
        if args.json:
            print(json.dumps({"ok": False, "interrupted": True, "results": results}, ensure_ascii=False))
        return 130
    if args.json:
        print(json.dumps({"ok": not failed, "results": results}, ensure_ascii=False))
    return 1 if failed else 0
