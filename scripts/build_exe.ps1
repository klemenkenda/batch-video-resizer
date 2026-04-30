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
& pyinstaller --noconfirm --clean --windowed --name $AppName --icon .\assets\app.ico --collect-all cv2 .\main.py

Write-Host "[5/5] Bundling ffmpeg/ffprobe binaries..."
$ffmpegBinDir = ".\dist\$AppName\ffmpeg"
New-Item -ItemType Directory -Force -Path $ffmpegBinDir | Out-Null

# Try winget install location first, then fall back to PATH
$wingetPattern = "$Env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg_*\ffmpeg-*\bin"
$wingetBin = Get-ChildItem -Path $wingetPattern -ErrorAction SilentlyContinue |
    Sort-Object FullName -Descending | Select-Object -First 1
if ($wingetBin) {
    Copy-Item "$($wingetBin.FullName)\ffmpeg.exe" $ffmpegBinDir
    Copy-Item "$($wingetBin.FullName)\ffprobe.exe" $ffmpegBinDir
    Write-Host "  Copied from winget: $($wingetBin.FullName)"
} else {
    $ffmpegPath = (Get-Command ffmpeg -ErrorAction SilentlyContinue)?.Source
    $ffprobePath = (Get-Command ffprobe -ErrorAction SilentlyContinue)?.Source
    if ($ffmpegPath -and $ffprobePath) {
        Copy-Item $ffmpegPath $ffmpegBinDir
        Copy-Item $ffprobePath $ffmpegBinDir
        Write-Host "  Copied from PATH: $ffmpegPath"
    } else {
        Write-Warning "ffmpeg not found locally. Installer will require ffmpeg to be installed separately."
    }
}

Write-Host "Build completed: .\dist\$AppName\$AppName.exe"
