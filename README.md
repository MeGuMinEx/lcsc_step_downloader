# Download .STEP files from LCSC / EasyEDA

Uses the [easyeda2kicad](https://github.com/uPesy/easyeda2kicad.py/) Python library.  
Try it [here](https://powerful-thicket-50815-63ddd8e12426.herokuapp.com/).

To run locally on Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe downloader.py
```

Open http://127.0.0.1:5000 and enter an LCSC part number such as `C41427486`.
Downloads also work directly at `/get_model/C41427486`.

If the legacy EasyEDA component lookup cannot find a model, the downloader uses
the footprint lookup used by LCSC's SMT 3D preview. This supports parts that have
a footprint and 3D model even when their schematic symbol is unavailable. The
server must still provide a STEP file; a browser preview alone does not guarantee one.
Network failures and missing models are reported separately, with unexpected
errors logged to the terminal.

Run the offline regression checks with:

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```
