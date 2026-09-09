"""Public Python function for downloading and saving a model."""

from pathlib import Path

from .core import download_step, normalize_lcsc_id
from .storage import save_model


def download_model(lcsc_id, output_dir=None, *, overwrite=False, timeout=30):
    """Save a STEP model and return its absolute Path.

    The default output directory is the caller's current working directory.
    Existing files are returned unchanged unless overwrite=True. DownloadError
    reports model/network failures; OSError reports filesystem failures.
    """
    lcsc_id = normalize_lcsc_id(lcsc_id)
    directory = Path.cwd() if output_dir is None else Path(output_dir).expanduser().absolute()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{lcsc_id}.step"
    if path.exists() and not overwrite:
        if not path.is_file():
            raise IsADirectoryError(f"输出路径不是文件：{path}")
        return path
    model = download_step(lcsc_id, timeout=timeout)
    save_model(path, model.data, overwrite=overwrite)
    return path
