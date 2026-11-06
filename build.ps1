# PDF Stüdyo: exe'yi PyInstaller ile derler, Inno Setup ile kurulum dosyası üretir.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$py = ".\.venv\Scripts\python.exe"

if (-not (Test-Path icon.ico)) { & $py make_icon.py }

& $py -m PyInstaller --noconfirm --clean --windowed --name "PDF Studyo" --icon icon.ico `
    --paths app --add-data "app\static;static" `
    --collect-data docx --collect-data pptx --collect-data pyhanko --collect-data pyhanko_certvalidator `
    --hidden-import keyring.backends.Windows --hidden-import win32timezone `
    app\main.py
if ($LASTEXITCODE) { throw "PyInstaller başarısız" }

$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe") |
    Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup bulunamadı: winget install JRSoftware.InnoSetup" }
& $iscc /Q installer.iss
if ($LASTEXITCODE) { throw "Inno Setup başarısız" }
Write-Host "Hazır: $(Resolve-Path 'Output\PDF Studyo Kurulum.exe')"
