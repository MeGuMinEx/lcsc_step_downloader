"""Command-line interface for downloading one or more STEP models."""

import argparse
import json
import logging
import math
from pathlib import Path
import sys

from . import __version__
from .core import DownloadError, SimplifiedModelAvailable, download_step, normalize_lcsc_id
from .storage import save_model


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


def choose_simplified(lcsc_id):
    print(f"{lcsc_id} 没有独立 3D 模型，可根据封装轮廓生成简化模型。", file=sys.stderr)
    print("简化模型采用网页预设厚度，仅作外观参考。", file=sys.stderr)
    print("1. 下载简化模型\n2. 放弃下载简化模型", file=sys.stderr)
    while True:
        try:
            print("请选择 [1/2]（默认 2）：", end="", file=sys.stderr, flush=True)
            choice = input().strip()
        except EOFError:
            return False
        if choice == "1":
            return True
        if choice in ("", "2"):
            return False
        print("请输入 1 或 2。", file=sys.stderr)


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
    parser.add_argument("--simplified", action="store_true",
                        help="无独立模型时允许生成简化模型，跳过交互询问（供脚本调用）")
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
                try:
                    model = download_step(lcsc_id, timeout=args.timeout)
                except SimplifiedModelAvailable as candidate:
                    if args.json and not args.simplified:
                        raise DownloadError(str(candidate) + " 使用 --simplified 可允许生成简化模型。")
                    if not args.simplified and not choose_simplified(lcsc_id):
                        failed = True
                        results.append({"lcsc_id": lcsc_id, "status": "cancelled"})
                        print(f"已放弃下载 {lcsc_id} 的简化模型。", file=sys.stderr)
                        continue
                    path = output_dir / f"{lcsc_id}_simplified.step"
                    if path.exists() and not args.overwrite:
                        if not path.is_file():
                            raise IsADirectoryError(f"输出路径不是文件：{path}")
                        results.append({"lcsc_id": lcsc_id, "status": "skipped", "path": str(path)})
                        if not args.json:
                            print(f"已存在，跳过：{path}")
                        continue
                    model = candidate.generate()
                save_model(path, model.data, args.overwrite)
                status = "generated" if model.source == "simplified" else "downloaded"
                result = {"lcsc_id": lcsc_id, "status": status, "path": str(path),
                          "name": model.name, "uuid": model.uuid, "bytes": len(model.data),
                          "source": model.source}
                if not args.json:
                    action = "已生成简化模型" if model.source == "simplified" else "已下载"
                    print(f"{action}：{path} ({len(model.data):,} bytes)")
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
