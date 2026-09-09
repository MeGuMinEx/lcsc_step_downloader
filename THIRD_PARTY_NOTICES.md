# Third-party notices

This project's source is distributed under the MIT license in LICENSE, retaining
the original downloader's copyright notice.

The standalone executable includes Python (PSF License), Requests (Apache 2.0),
urllib3 (MIT), certifi (MPL 2.0), charset-normalizer (MIT), and idna (BSD 3-Clause).
Their installed license files are collected by packaging/collect_licenses.py and
embedded in the executable's licenses directory. PyInstaller builds the executable
using its bootloader exception; see https://pyinstaller.org/en/stable/license.html.

The CLI reads the public EasyEDA/LCSC footprint and model APIs directly. It does
not bundle Flask or easyeda2kicad. Flask is only needed for the optional web page.

Downloaded model files belong to their respective providers and are not part of
the software's source-code license.
