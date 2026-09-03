# 打一份可以公开分发的 zip：不含 config.json、agent.md、handoff.md、dist、build。
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$stage = Join-Path $PSScriptRoot "build\public-stage"
$zip = Join-Path $PSScriptRoot "LocalPick-public.zip"

if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
New-Item -ItemType Directory -Path $stage | Out-Null

$files = @(
    "README.md",
    "LICENSE",
    "app.py",
    "core.py",
    "build.ps1",
    "export-public.ps1",
    "requirements-dev.txt",
    "config.example.json",
    ".gitignore"
)
foreach ($name in $files) {
    $src = Join-Path $PSScriptRoot $name
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $stage $name)
    }
}

New-Item -ItemType Directory -Path (Join-Path $stage "tests") | Out-Null
Copy-Item (Join-Path $PSScriptRoot "tests\test_core.py") (Join-Path $stage "tests\test_core.py")

$exe = Join-Path $PSScriptRoot "LocalPick.exe"
if (Test-Path $exe) {
    Copy-Item $exe (Join-Path $stage "LocalPick.exe")
}

if (Test-Path $zip) { Remove-Item -Force $zip }
Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zip

Write-Host "Public zip: $zip"
Write-Host "Upload this zip, not the whole project folder."
