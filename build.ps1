$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python -m pip install -r requirements-dev.txt

$exe = Join-Path $PSScriptRoot "LocalPick.exe"
if (Test-Path $exe) {
    Remove-Item -Force $exe
}

python -m PyInstaller `
    --noconfirm `
    --windowed `
    --onefile `
    --name LocalPick `
    --distpath $PSScriptRoot `
    --workpath (Join-Path $PSScriptRoot "build") `
    --specpath (Join-Path $PSScriptRoot "build") `
    app.py

if (Test-Path (Join-Path $PSScriptRoot "dist")) {
    Remove-Item -Recurse -Force (Join-Path $PSScriptRoot "dist")
}

if (-not (Test-Path $exe)) {
    throw "LocalPick.exe was not created in the project folder"
}

Write-Host "Packed: $exe"
Write-Host "Keep config.json next to the exe. Do not upload config.json."
