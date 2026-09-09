"""Collect notices for the runtime dependencies included in the executable."""

from importlib.metadata import distribution
from pathlib import Path
import shutil
import sys


project = Path(__file__).resolve().parents[1]
target = project / "build" / "third-party-licenses"
target.mkdir(parents=True, exist_ok=True)
for name in ("requests", "urllib3", "certifi", "charset-normalizer", "idna"):
    package = distribution(name)
    for file in package.files or []:
        if "dist-info" in str(file) and file.name.upper().startswith(("LICENSE", "COPYING", "NOTICE")):
            shutil.copyfile(package.locate_file(file), target / f"{name}-{file.name}")
python_license = Path(sys.base_prefix) / "LICENSE.txt"
if python_license.is_file():
    shutil.copyfile(python_license, target / "Python-LICENSE.txt")
shutil.copyfile(project / "THIRD_PARTY_NOTICES.md", target / "THIRD_PARTY_NOTICES.md")
print(f"Collected {len(list(target.iterdir()))} license files in {target}")
