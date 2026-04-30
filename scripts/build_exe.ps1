param(
    [string]$AppName = "VideoResizerStudio"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "[1/4] Installing build dependencies..."
& python -m pip install --upgrade pip
& python -m pip install -r requirements-dev.txt

Write-Host "[2/4] Generating app icon..."
& python .\scripts\generate_icon.py

Write-Host "[3/4] Cleaning previous build artifacts..."
if (Test-Path .\build) { Remove-Item .\build -Recurse -Force }
if (Test-Path .\dist) { Remove-Item .\dist -Recurse -Force }
if (Test-Path ".\$AppName.spec") { Remove-Item ".\$AppName.spec" -Force }

Write-Host "[4/4] Building EXE via PyInstaller..."
& pyinstaller --noconfirm --clean --windowed --name $AppName --icon .\assets\app.ico .\main.py

Write-Host "Build completed: .\dist\$AppName\$AppName.exe"
