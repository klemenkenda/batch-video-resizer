param(
    [string]$AppName = "VideoResizerStudio",
    [string]$AppVersion = "1.0.0"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".\dist\$AppName\$AppName.exe")) {
    throw "EXE not found. Run scripts/build_exe.ps1 first."
}

$possibleIscc = @(
    "$Env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe",
    "$Env:ProgramFiles\Inno Setup 6\ISCC.exe"
)

$iscc = $possibleIscc | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    throw "Inno Setup ISCC.exe not found. Install Inno Setup 6."
}

& $iscc "/DMyAppVersion=$AppVersion" ".\installer\VideoResizerStudio.iss"
Write-Host "Installer build completed in .\dist\installer"
