# Third-party notices

This repository's own source retains the MIT license and original copyright
notice in LICENSE. It is based on wormyrocks/lcsc_step_downloader:
https://github.com/wormyrocks/lcsc_step_downloader.

The executable includes easyeda2kicad 1.0.1 (AGPL-3.0) and uses its
Easyeda3dModelImporter to read model references from footprint data. That
dependency's license applies to its use and distribution. Its upstream source
and license are available at:
- https://github.com/uPesy/easyeda2kicad.py
- https://pypi.org/project/easyeda2kicad/1.0.1/#files

Other bundled runtime components are Python (PSF License), Requests (Apache 2.0),
urllib3 (MIT), certifi (MPL 2.0), charset-normalizer (MIT), and idna (BSD 3-Clause).
Their installed license files are collected by packaging/collect_licenses.py
and embedded in the executable's licenses directory. PyInstaller uses its
bootloader exception: https://pyinstaller.org/en/stable/license.html.

The Python edition contains this project's source; users install its dependencies
themselves. Flask is only needed for the optional web interface and is not bundled
into the command-line executable. Downloaded models belong to their respective
providers and are not covered by the software's source-code license.
