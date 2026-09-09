"""Publish complete model files without replacing existing files by default."""

import os
from pathlib import Path
import tempfile


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
