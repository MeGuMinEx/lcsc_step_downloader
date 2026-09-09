"""Package the Python edition without installed dependencies or local data."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

root = Path(__file__).resolve().parents[1]
files = [root / name for name in (
    "jlc-downloader.py", "jlc-downloader", "downloader.py", "README.md", "LICENSE",
    "THIRD_PARTY_NOTICES.md", "requirements.txt", "requirements-build.txt",
    "pyproject.toml", "MANIFEST.in", "build_exe.ps1", "RELEASE_NOTES.md",
    "test_api.py", "test_cli.py", "test_downloader.py", "test_simplified.py",
)]
files += sorted((root / "jlc_downloader").glob("*.py"))
files += sorted((root / "packaging").glob("*.py"))
destination = root / "dist" / "jlc-downloader-python.zip"
destination.parent.mkdir(exist_ok=True)
with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
    for path in files:
        archive.write(path, "jlc-downloader-python/" + path.relative_to(root).as_posix())
print(f"Python edition: {destination}")
