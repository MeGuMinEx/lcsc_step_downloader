param([string]$Python = 'python')

$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$pythonExe = (Get-Command $Python -CommandType Application -ErrorAction Stop).Source
Push-Location -LiteralPath $projectRoot
try {
    $env:PYINSTALLER_CONFIG_DIR = Join-Path $projectRoot 'build\pyinstaller-cache'
    & $pythonExe packaging\collect_licenses.py
    if ($LASTEXITCODE -ne 0) { throw 'License collection failed.' }
    $licenseFile = Join-Path $projectRoot 'LICENSE'
    $thirdPartyLicenses = Join-Path $projectRoot 'build\third-party-licenses'
    & $pythonExe -m PyInstaller --noconfirm --onefile --console --noupx --name jlc-downloader --paths $projectRoot --specpath build --collect-data certifi --copy-metadata easyeda2kicad --add-data "${licenseFile}:licenses" --add-data "${thirdPartyLicenses}:licenses" packaging\entrypoint.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
    & $pythonExe packaging\make_python_zip.py
    if ($LASTEXITCODE -ne 0) { throw 'Python source archive build failed.' }
    Write-Output ('Executable: ' + (Join-Path $projectRoot 'dist\jlc-downloader.exe'))
} finally {
    Pop-Location
}
