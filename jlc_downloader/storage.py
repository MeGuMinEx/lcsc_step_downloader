"""Publish complete model files without replacing existing files by default."""

import os
from pathlib import Path
import re
import tempfile


def output_filename(lcsc_id, filename=None, *, simplified=False):
    """Build a portable file name; the output directory is supplied separately."""
    if filename is None:
        name = lcsc_id
    elif isinstance(filename, str):
        name = filename.strip()
    else:
        raise ValueError("文件名必须是字符串。")
    if not name or name in (".", "..") or name.endswith("."):
        raise ValueError("文件名不能为空，也不能以句点结尾。")
    if re.search(r'[<>:"/\\|?*\x00-\x1f\x7f]', name):
        raise ValueError("请只提供文件名，不要包含路径或非法字符；下载目录请用 -o 指定。")
    base = name.split(".", 1)[0].rstrip().upper()
    if re.fullmatch(r"CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|(?:COM|LPT)[1-9¹²³]", base):
        raise ValueError("该文件名是 Windows 保留名称，请换一个名称。")
    extension = Path(name).suffix
    if extension.lower() in (".step", ".stp"):
        stem = name[:-len(extension)]
    else:
        stem, extension = name, ".step"
    if simplified and not stem.lower().endswith("_simplified"):
        stem += "_simplified"
    result = stem + extension
    if len(result.encode("utf-8")) > 255 or len(result.encode("utf-16-le")) // 2 > 255:
        raise ValueError("文件名过长，请使用更短的名称。")
    return result


def save_model(path, data, overwrite=False):
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
