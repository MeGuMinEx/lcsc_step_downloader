$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw 'Create .venv and install requirements-build.txt first. See README.md.'
}
Push-Location -LiteralPath $projectRoot
try {
    $env:PYINSTALLER_CONFIG_DIR = Join-Path $projectRoot 'build\pyinstaller-cache'
    & $pythonExe packaging\collect_licenses.py
    if ($LASTEXITCODE -ne 0) { throw 'License collection failed.' }
    $licenseFile = Join-Path $projectRoot 'LICENSE'
    $thirdPartyLicenses = Join-Path $projectRoot 'build\third-party-licenses'
    & $pythonExe -m PyInstaller --noconfirm --onefile --console --noupx --name jlc-downloader --paths $projectRoot --specpath build --collect-data certifi --add-data "${licenseFile}:licenses" --add-data "${thirdPartyLicenses}:licenses" packaging\entrypoint.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
    & $pythonExe -m build --no-isolation
    if ($LASTEXITCODE -ne 0) { throw 'Python package build failed.' }
    Write-Output ('Executable: ' + (Join-Path $projectRoot 'dist\jlc-downloader.exe'))
} finally {
    Pop-Location
}
